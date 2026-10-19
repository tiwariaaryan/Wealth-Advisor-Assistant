from abc import ABC, abstractmethod
import time
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, ValidationError

class ToolResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0

class BaseTool(ABC):
    """
    Abstract Base Class for all tools in the multi-agent system.
    Decouples agent logic from concrete tool implementations and provides
    standardized input validation, error handling, and performance tracing.
    """
    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None

    def run(self, **kwargs) -> ToolResult:
        """Standard wrapper with schema validation, exception isolation, and timing."""
        start_time = time.time()
        
        # Validate inputs against schema if provided
        if self.args_schema:
            try:
                validated_args = self.args_schema(**kwargs)
                kwargs = validated_args.model_dump()
            except ValidationError as ve:
                elapsed = (time.time() - start_time) * 1000
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"Input validation error for tool '{self.name}': {str(ve)}",
                    execution_time_ms=elapsed
                )

        try:
            result_data = self.execute(**kwargs)
            elapsed = (time.time() - start_time) * 1000
            return ToolResult(
                success=True,
                data=result_data,
                error=None,
                execution_time_ms=elapsed
            )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            return ToolResult(
                success=False,
                data=None,
                error=f"Execution error in tool '{self.name}': {str(e)}",
                execution_time_ms=elapsed
            )

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Concrete execution logic to be implemented by child tools."""
        pass
