from fastapi import APIRouter, HTTPException, Query
from app.schemas.agent_schemas import AgentName
from app.orchestrator.shipmate_orchestrator import ShipMateOrchestrator

router = APIRouter(prefix="/analysis", tags=["analysis"])
orchestrator = ShipMateOrchestrator()


@router.post("/analyze")
async def analyze(
    repo_url: str = Query(..., description="GitHub repository URL"),
    branch: str = Query(default="main", description="Branch to analyze"),
):
    """Analyze a repository using all agents."""
    try:
        results = await orchestrator.execute_all(repo_url, branch)
        return {
            "status": "success",
            "repo_url": repo_url,
            "branch": branch,
            "agents": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{agent_name}")
async def analyze_with_agent(
    agent_name: str,
    repo_url: str = Query(..., description="GitHub repository URL"),
    branch: str = Query(default="main", description="Branch to analyze"),
):
    """Analyze a repository using a specific agent."""
    try:
        # Validate agent name against enum
        valid_agents = [a.value for a in AgentName]
        if agent_name not in valid_agents:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent: {agent_name}. Valid agents: {', '.join(valid_agents)}",
            )
        result = await orchestrator.execute_agent(agent_name, repo_url, branch)
        return {
            "status": "success",
            "agent": agent_name,
            "repo_url": repo_url,
            "branch": branch,
            "result": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def list_agents():
    """List all available agents."""
    return {
        "agents": [a.value for a in AgentName],
        "count": len(AgentName),
    }
