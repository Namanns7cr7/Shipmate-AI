#!/usr/bin/env python3
"""
Seed a demo GitHub repository with intentional issues for live hackathon demos.

Creates a public repo called `shipmate-demo` (or --name <name>) with:
  - Python FastAPI app missing tests, missing Dockerfile, hardcoded secret
  - No CI/CD workflow
  - CORS wildcard
  - Obvious SQL-injection-style pattern in a route

When ShipMate analyzes it you'll see:
  Score ~35/100 · NOT READY
  GuardRail: hardcoded secret + CORS wildcard
  TestPilot: 0% coverage
  PlanForge: no CI/CD, no Docker

After the Coder agent auto-fixes it, the score jumps to ~70/100.

Usage:
  python scripts/seed_demo_repo.py --token ghp_xxx
  python scripts/seed_demo_repo.py --token ghp_xxx --name my-demo-repo --org myorg
"""
import argparse
import base64
import json
import sys

import httpx

_GH = "https://api.github.com"

FILES: dict[str, str] = {
    "README.md": """\
# shipmate-demo

A minimal FastAPI app intentionally seeded with issues for ShipMate AI demos.
ShipMate will detect the problems and the Coder agent can auto-fix them.
""",

    "main.py": """\
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

# ⚠️  Hardcoded secret — GuardRail will flag this
SECRET_KEY = "super-secret-key-do-not-commit-abc123"
DB_PASS    = "postgres://admin:hunter2@db.internal/prod"

app.add_middleware(
    CORSMiddleware,
    # ⚠️  Wildcard CORS — GuardRail will flag this
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/users/{user_id}")
def get_user(user_id: str):
    # ⚠️  SQL injection risk — GuardRail will flag this
    conn = sqlite3.connect("users.db")
    cur  = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = {user_id}")
    row = cur.fetchone()
    conn.close()
    return {"user": row}


@app.get("/health")
def health():
    return {"status": "healthy"}
""",

    "requirements.txt": """\
fastapi>=0.115.0
uvicorn[standard]>=0.24.0
""",

    # Intentionally no Dockerfile, no .github/workflows/, no tests/
}


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _b64(content: str) -> str:
    return base64.b64encode(content.encode()).decode()


def create_repo(client: httpx.Client, token: str, name: str, org: str | None) -> str:
    payload = {
        "name": name,
        "description": "ShipMate AI demo repo — intentionally broken for live demos",
        "private": False,
        "auto_init": False,
    }
    url = f"{_GH}/orgs/{org}/repos" if org else f"{_GH}/user/repos"
    r = client.post(url, headers=_headers(token), json=payload)
    if r.status_code == 422 and "already exists" in r.text:
        # Repo exists — fetch owner/name
        me = client.get(f"{_GH}/user", headers=_headers(token))
        me.raise_for_status()
        owner = org or me.json()["login"]
        print(f"  repo already exists: {owner}/{name}")
        return owner
    r.raise_for_status()
    owner = r.json()["owner"]["login"]
    print(f"  created: {owner}/{name}")
    return owner


def push_file(client: httpx.Client, token: str, owner: str, repo: str, path: str, content: str) -> None:
    url = f"{_GH}/repos/{owner}/{repo}/contents/{path}"
    # Check if file exists (for idempotency)
    existing = client.get(url, headers=_headers(token))
    payload: dict = {"message": f"seed: add {path}", "content": _b64(content)}
    if existing.status_code == 200:
        payload["sha"] = existing.json()["sha"]
    r = client.put(url, headers=_headers(token), json=payload)
    r.raise_for_status()
    print(f"  pushed: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a ShipMate demo repo")
    parser.add_argument("--token", required=True, help="GitHub personal access token (repo scope)")
    parser.add_argument("--name", default="shipmate-demo", help="Repo name (default: shipmate-demo)")
    parser.add_argument("--org", default=None, help="GitHub org to create the repo under (default: your user)")
    args = parser.parse_args()

    with httpx.Client(timeout=20.0) as client:
        print(f"\n→ Creating repo '{args.name}'...")
        owner = create_repo(client, args.token, args.name, args.org)

        print(f"\n→ Pushing {len(FILES)} seed files...")
        for path, content in FILES.items():
            push_file(client, args.token, owner, args.name, path, content)

    print(f"""
✓ Demo repo ready: https://github.com/{owner}/{args.name}

Analyze it in ShipMate with:
  Owner : {owner}
  Repo  : {args.name}
  Branch: main

Expected result:
  Score     ~35/100
  GuardRail : hardcoded secret, wildcard CORS, SQL injection
  TestPilot : 0% coverage, no tests directory
  PlanForge : no CI/CD, no Dockerfile

After Coder auto-fix: score should reach ~68-75/100.
""")


if __name__ == "__main__":
    main()
