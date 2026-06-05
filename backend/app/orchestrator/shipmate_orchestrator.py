from app.schemas.agent_schemas import AgentName


class ShipMateOrchestrator:
    """Orchestrates execution of multiple agents in sequence."""

    def __init__(self):
        """Initialize the orchestrator with available agents."""
        self.agents = {
            AgentName.REPO_LENS: self._execute_repo_lens,
            AgentName.PLAN_FORGE: self._execute_plan_forge,
            AgentName.GUARDRAIL: self._execute_guardrail,
            AgentName.TESTPILOT: self._execute_testpilot,
        }

    async def execute_all(self, repo_url: str, branch: str = "main") -> dict:
        """Execute all agents and aggregate results."""
        results = {}
        for agent_name in AgentName:
            try:
                results[agent_name.value] = await self.agents[agent_name](
                    repo_url, branch
                )
            except Exception as e:
                results[agent_name.value] = {"error": str(e)}
        return results

    async def execute_agent(self, agent_name: str, repo_url: str, branch: str = "main") -> dict:
        """Execute a specific agent by name."""
        try:
            agent_enum = AgentName(agent_name)
        except ValueError:
            raise ValueError(
                f"Unknown agent: {agent_name}. Valid agents: {', '.join([a.value for a in AgentName])}"
            )
        return await self.agents[agent_enum](repo_url, branch)

    async def _execute_repo_lens(self, repo_url: str, branch: str) -> dict:
        """Execute RepoLens agent."""
        # Implementation placeholder
        return {"agent": AgentName.REPO_LENS.value, "status": "completed"}

    async def _execute_plan_forge(self, repo_url: str, branch: str) -> dict:
        """Execute PlanForge agent."""
        # Implementation placeholder
        return {"agent": AgentName.PLAN_FORGE.value, "status": "completed"}

    async def _execute_guardrail(self, repo_url: str, branch: str) -> dict:
        """Execute GuardRail agent."""
        # Implementation placeholder
        return {"agent": AgentName.GUARDRAIL.value, "status": "completed"}

    async def _execute_testpilot(self, repo_url: str, branch: str) -> dict:
        """Execute TestPilot agent."""
        # Implementation placeholder
        return {"agent": AgentName.TESTPILOT.value, "status": "completed"}
