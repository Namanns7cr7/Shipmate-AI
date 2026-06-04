from enum import StrEnum
from pydantic import BaseModel, Field
from typing import Optional, Any


class AgentName(StrEnum):
    """Enumeration of all valid agent identifiers."""
    REPO_LENS = "repo_lens"
    PLAN_FORGE = "plan_forge"
    GUARDRAIL = "guardrail"
    TESTPILOT = "testpilot"


class AgentRequest(BaseModel):
    """Request schema for agent execution."""
    agent_name: str = Field(..., description="Name of the agent to execute")
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: Optional[str] = Field(default="main", description="Branch to analyze")
    extra_params: Optional[dict[str, Any]] = Field(default=None, description="Additional parameters")


class AgentResponse(BaseModel):
    """Response schema for agent execution."""
    agent_name: str = Field(..., description="Name of the agent that executed")
    status: str = Field(..., description="Execution status")
    output: Optional[dict[str, Any]] = Field(default=None, description="Agent output")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
