from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """Base class for all tools that can be used by the AI agent."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the tool."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what the tool does."""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool with the given parameters."""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Return the schema for the tool's parameters."""
        return {} 