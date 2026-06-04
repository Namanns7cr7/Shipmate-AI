from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def run(self, context: Dict[str, Any]) -> Any:
        """Execute agent and return structured Pydantic output."""
        ...

    def _file_tree(self, ctx: Dict) -> List[str]:
        return ctx.get("file_tree", [])

    def _key_files(self, ctx: Dict) -> Dict[str, str]:
        return ctx.get("key_files", {})

    def _repo_info(self, ctx: Dict) -> Dict[str, Any]:
        return ctx.get("repo_info", {})

    def _feature_context(self, ctx: Dict) -> str:
        return ctx.get("feature_context", "")
