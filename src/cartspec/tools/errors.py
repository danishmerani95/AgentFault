class ToolExecutionFailure(RuntimeError):
    """An explicitly classified, recoverable failure from a tool invocation."""

    def __init__(self, tool_name: str, original_error: Exception) -> None:
        self.tool_name = tool_name
        self.original_error = original_error
        self.error_type = type(original_error).__name__
        self.message = str(original_error) or self.error_type
        super().__init__(self.message)
