from __future__ import annotations

from abc import ABC, abstractmethod

from orchestrator.context import ProjectContext


class BaseBackend(ABC):
    """
    Common interface for all LLM backends.
    LangGraph nodes call backend.run() — never interact with a specific backend directly.
    """

    @abstractmethod
    async def run(self, agent_name: str, state: ProjectContext) -> ProjectContext:
        """
        Execute one agent turn.

        Args:
            agent_name: "pm" | "analyser" | "engineer" | "qa"
            state:       current LangGraph state

        Returns:
            Updated state after the agent completes its submit tool call.
        """
        ...
