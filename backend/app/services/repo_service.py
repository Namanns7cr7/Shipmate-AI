import zipfile
import io
import json
from pathlib import Path
from typing import Dict, List, Optional
from app.models.schemas import RepoSummary

# Files to extract content from
KEY_FILES = {
    "readme": ["README.md", "readme.md", "README.rst", "readme.rst"],
    "package": ["package.json"],
    "requirements": ["requirements.txt", "requirements-dev.txt"],
    "pyproject": ["pyproject.toml"],
    "pom": ["pom.xml"],
    "compose": ["docker-compose.yml", "docker-compose.yaml"],
    "env_example": [".env.example", ".env.sample"],
    "gitignore": [".gitignore"],
    "ci": [".github/workflows/ci.yml", ".github/workflows/main.yml", "Jenkinsfile", ".travis.yml"],
}

# Source file extensions to detect tech stack
SRC_EXTENSIONS = {
    ".ts": "TypeScript", ".tsx": "TypeScript/React",
    ".js": "JavaScript", ".jsx": "JavaScript/React",
    ".py": "Python", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby", ".php": "PHP",
    ".cs": "C#", ".swift": "Swift",
}

MAX_FILE_CONTENT_SIZE = 10_000  # 10KB per file
MAX_TOTAL_FILES = 500


def detect_stack(file_list: List[str]) -> List[str]:
    """Detect tech stack from file extensions and key files."""
    stack = set()

    for f in file_list:
        ext = Path(f).suffix.lower()
        if ext in SRC_EXTENSIONS:
            stack.add(SRC_EXTENSIONS[ext])

    # Framework detection from filenames
    filenames = [Path(f).name.lower() for f in file_list]
    paths_lower = [f.lower() for f in file_list]

    if "package.json" in filenames:
        stack.add("Node.js")
    if "requirements.txt" in filenames or "pyproject.toml" in filenames:
        stack.add("Python")
    if "pom.xml" in filenames or "build.gradle" in filenames:
        stack.add("Java/JVM")
    if "go.mod" in filenames:
        stack.add("Go")
    if "cargo.toml" in filenames:
        stack.add("Rust")
    if any("dockerfile" in f for f in filenames):
        stack.add("Docker")
    if any("docker-compose" in f for f in filenames):
        stack.add("Docker Compose")
    if any(".github/workflows" in f for f in paths_lower):
        stack.add("GitHub Actions")
    if any("terraform" in f for f in filenames):
        stack.add("Terraform")

    return sorted(list(stack))


async def process_repo_zip(file_bytes: bytes) -> RepoSummary:
    """Extract and analyze a ZIP file, returning a structured repo summary."""

    try:
        zip_buffer = io.BytesIO(file_bytes)
        with zipfile.ZipFile(zip_buffer, 'r') as zf:
            all_names = zf.namelist()

            # Build file tree (limit)
            file_tree = []
            for name in all_names[:MAX_TOTAL_FILES]:
                if not name.endswith('/'):  # Skip directory entries
                    file_tree.append(name)

            # Detect stack
            detected_stack = detect_stack(file_tree)

            # Extract key file contents
            key_contents: Dict[str, str] = {}
            readme_content: Optional[str] = None
            package_json: Optional[dict] = None
            requirements_txt: Optional[str] = None

            # Build a lookup map for fast access
            name_map = {n.lower(): n for n in all_names}

            for category, candidates in KEY_FILES.items():
                for candidate in candidates:
                    # Try exact and stripped path matching
                    normalized = candidate.lower()
                    # Also check without first directory component (common in ZIPs)
                    for zip_name_lower, zip_name in name_map.items():
                        if zip_name_lower.endswith("/" + normalized) or zip_name_lower == normalized:
                            try:
                                content = zf.read(zip_name).decode("utf-8", errors="replace")
                                content = content[:MAX_FILE_CONTENT_SIZE]
                                key_contents[candidate] = content

                                if category == "readme":
                                    readme_content = content
                                elif category == "package" and candidate == "package.json":
                                    try:
                                        package_json = json.loads(content)
                                    except json.JSONDecodeError:
                                        pass
                                elif category == "requirements":
                                    requirements_txt = content
                            except Exception:
                                pass
                            break

            # Build repo context string for agents
            context_parts = []
            if detected_stack:
                context_parts.append(f"Tech Stack: {', '.join(detected_stack)}")
            if file_tree:
                sample_files = file_tree[:30]
                context_parts.append(f"Key files ({len(file_tree)} total):\n" + "\n".join(f"  - {f}" for f in sample_files))
            if readme_content:
                context_parts.append(f"README:\n{readme_content[:2000]}")
            if package_json:
                deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
                dep_list = list(deps.keys())[:20]
                context_parts.append(f"Dependencies: {', '.join(dep_list)}")
            if requirements_txt:
                context_parts.append(f"Python requirements:\n{requirements_txt[:500]}")

            repo_context = "\n\n".join(context_parts)

            return RepoSummary(
                file_tree=file_tree[:100],  # Return top 100 for display
                file_count=len(file_tree),
                detected_stack=detected_stack,
                readme_content=readme_content,
                package_json=package_json,
                requirements_txt=requirements_txt,
                key_files={k: v[:500] for k, v in key_contents.items()},  # Truncate for response
                repo_context=repo_context
            )

    except zipfile.BadZipFile:
        raise ValueError("Invalid ZIP file. Please upload a valid repository ZIP.")
    except Exception as e:
        raise ValueError(f"Failed to process repository: {str(e)}")


def get_sample_repo() -> RepoSummary:
    """Return a sample repo summary for demo purposes."""

    file_tree = [
        "ecommerce-app/README.md",
        "ecommerce-app/package.json",
        "ecommerce-app/tsconfig.json",
        "ecommerce-app/.env.example",
        "ecommerce-app/.github/workflows/ci.yml",
        "ecommerce-app/src/index.ts",
        "ecommerce-app/src/app.ts",
        "ecommerce-app/src/middleware/cors.ts",
        "ecommerce-app/src/middleware/errorHandler.ts",
        "ecommerce-app/src/routes/users.ts",
        "ecommerce-app/src/routes/products.ts",
        "ecommerce-app/src/routes/orders.ts",
        "ecommerce-app/src/controllers/userController.ts",
        "ecommerce-app/src/controllers/productController.ts",
        "ecommerce-app/src/controllers/orderController.ts",
        "ecommerce-app/src/services/userService.ts",
        "ecommerce-app/src/services/emailService.ts",
        "ecommerce-app/src/services/paymentService.ts",
        "ecommerce-app/src/models/User.ts",
        "ecommerce-app/src/models/Product.ts",
        "ecommerce-app/src/models/Order.ts",
        "ecommerce-app/src/lib/db.ts",
        "ecommerce-app/src/lib/redis.ts",
        "ecommerce-app/src/lib/logger.ts",
        "ecommerce-app/src/types/index.ts",
        "ecommerce-app/database/migrations/0001_init.sql",
        "ecommerce-app/database/migrations/0002_add_orders.sql",
        "ecommerce-app/database/seeds/users.sql",
        "ecommerce-app/tests/unit/userService.test.ts",
        "ecommerce-app/tests/integration/auth.test.ts",
        "ecommerce-app/Dockerfile",
        "ecommerce-app/docker-compose.yml",
    ]

    package_json = {
        "name": "ecommerce-app",
        "version": "2.1.0",
        "description": "Full-stack e-commerce platform with TypeScript",
        "scripts": {
            "dev": "ts-node-dev src/index.ts",
            "build": "tsc",
            "test": "jest --coverage",
            "lint": "eslint src --ext .ts"
        },
        "dependencies": {
            "express": "^4.18.2",
            "typescript": "^5.0.0",
            "pg": "^8.11.0",
            "redis": "^4.6.7",
            "jsonwebtoken": "^8.5.1",
            "bcryptjs": "^2.4.3",
            "passport": "^0.5.3",
            "axios": "^0.21.1",
            "mongoose": "^5.13.20",
            "nodemailer": "^6.9.4",
            "stripe": "^13.3.0",
            "joi": "^17.9.2",
            "winston": "^3.10.0",
            "helmet": "^7.0.0",
            "cors": "^2.8.5"
        },
        "devDependencies": {
            "jest": "^29.6.2",
            "@types/jest": "^29.5.3",
            "supertest": "^6.3.3",
            "ts-jest": "^29.1.1",
            "eslint": "^8.46.0",
            "prettier": "^3.0.1"
        }
    }

    readme = """# E-Commerce Platform

A full-stack TypeScript e-commerce application with product catalog, shopping cart, order management, and payment processing.

## Stack
- **Backend:** Node.js + Express + TypeScript
- **Database:** PostgreSQL + Redis (caching)
- **Auth:** JWT (stateless) — no role-based access yet
- **Payments:** Stripe integration
- **Tests:** Jest + Supertest (~45% coverage)
- **CI/CD:** GitHub Actions (build + test only, no security scanning)

## Quick Start
```bash
npm install
cp .env.example .env
npm run dev
```

## Architecture
The app follows a Controller → Service → Repository pattern with middleware for CORS and error handling. Authentication is currently basic JWT with no role differentiation — all authenticated users have equal access."""

    context = """Tech Stack: TypeScript, Node.js, PostgreSQL, Redis, Docker

E-Commerce Platform with 32 files. No authentication roles or analytics currently implemented. JWT auth exists but without RBAC. Test coverage ~45%. No security scanning in CI pipeline.

Key files:
  - src/middleware/cors.ts (no auth middleware)
  - src/routes/users.ts (unprotected endpoints)
  - src/lib/redis.ts (Redis client available)
  - database/migrations/ (2 existing migrations)

Dependencies include jsonwebtoken@8.5.1 (CVE present), passport@0.5.3 (deprecated), axios@0.21.1 (SSRF vulnerability)."""

    return RepoSummary(
        file_tree=file_tree,
        file_count=32,
        detected_stack=["TypeScript", "Node.js", "Docker", "GitHub Actions", "Docker Compose"],
        readme_content=readme,
        package_json=package_json,
        requirements_txt=None,
        key_files={"README.md": readme[:500], "package.json": json.dumps(package_json, indent=2)[:500]},
        repo_context=context
    )
