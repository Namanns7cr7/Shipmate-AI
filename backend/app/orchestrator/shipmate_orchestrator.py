import asyncio
from typing import AsyncGenerator, Dict, Any
from app.agents.repo_lens import RepoLens
from app.agents.plan_forge import PlanForge
from app.agents.guardrail import GuardRail
from app.agents.testpilot import TestPilot


class ShipMateOrchestrator:
    """
    Orchestrates execution of all ShipMate agents and streams results
    as each agent completes.
    """

    def __init__(
        self,
        repo_owner: str,
        repo_name: str,
        branch: str = "main",
        github_token: str = None,
    ):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.github_token = github_token

        # Initialize agents
        self.repo_lens = RepoLens(
            repo_owner=repo_owner,
            repo_name=repo_name,
            branch=branch,
            github_token=github_token,
        )
        self.plan_forge = PlanForge(
            repo_owner=repo_owner,
            repo_name=repo_name,
            branch=branch,
            github_token=github_token,
        )
        self.guardrail = GuardRail(
            repo_owner=repo_owner,
            repo_name=repo_name,
            branch=branch,
            github_token=github_token,
        )
        self.testpilot = TestPilot(
            repo_owner=repo_owner,
            repo_name=repo_name,
            branch=branch,
            github_token=github_token,
        )

    async def run_agents_streaming(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run all agents concurrently and yield results as each completes.
        Each yielded dict contains:
        {
            "type": "agent_result",
            "agent": "repo_lens" | "plan_forge" | "guardrail" | "testpilot",
            "status": "complete" | "error",
            "data": <agent_output> or None,
            "error": <error_message> or None,
        }
        """
        # Create tasks for all agents
        tasks = {
            "repo_lens": asyncio.create_task(self._run_repo_lens()),
            "plan_forge": asyncio.create_task(self._run_plan_forge()),
            "guardrail": asyncio.create_task(self._run_guardrail()),
            "testpilot": asyncio.create_task(self._run_testpilot()),
        }

        # Yield results as they complete
        pending = set(tasks.values())
        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                agent_name, result = await task
                yield result

    async def _run_repo_lens(self):
        """Run RepoLens agent and return result tuple."""
        try:
            output = await self.repo_lens.analyze()
            return (
                "repo_lens",
                {
                    "type": "agent_result",
                    "agent": "repo_lens",
                    "status": "complete",
                    "data": output,
                    "error": None,
                },
            )
        except Exception as e:
            return (
                "repo_lens",
                {
                    "type": "agent_result",
                    "agent": "repo_lens",
                    "status": "error",
                    "data": None,
                    "error": str(e),
                },
            )

    async def _run_plan_forge(self):
        """Run PlanForge agent and return result tuple."""
        try:
            output = await self.plan_forge.analyze()
            return (
                "plan_forge",
                {
                    "type": "agent_result",
                    "agent": "plan_forge",
                    "status": "complete",
                    "data": output,
                    "error": None,
                },
            )
        except Exception as e:
            return (
                "plan_forge",
                {
                    "type": "agent_result",
                    "agent": "plan_forge",
                    "status": "error",
                    "data": None,
                    "error": str(e),
                },
            )

    async def _run_guardrail(self):
        """Run GuardRail agent and return result tuple."""
        try:
            output = await self.guardrail.analyze()
            return (
                "guardrail",
                {
                    "type": "agent_result",
                    "agent": "guardrail",
                    "status": "complete",
                    "data": output,
                    "error": None,
                },
            )
        except Exception as e:
            return (
                "guardrail",
                {
                    "type": "agent_result",
                    "agent": "guardrail",
                    "status": "error",
                    "data": None,
                    "error": str(e),
                },
            )

    async def _run_testpilot(self):
        """Run TestPilot agent and return result tuple."""
        try:
            output = await self.testpilot.analyze()
            return (
                "testpilot",
                {
                    "type": "agent_result",
                    "agent": "testpilot",
                    "status": "complete",
                    "data": output,
                    "error": None,
                },
            )
        except Exception as e:
            return (
                "testpilot",
                {
                    "type": "agent_result",
                    "agent": "testpilot",
                    "status": "error",
                    "data": None,
                    "error": str(e),
                },
            )
