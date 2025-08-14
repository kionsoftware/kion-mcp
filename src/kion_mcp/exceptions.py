"""Custom exceptions for Kion MCP Server."""


class KionMCPError(Exception):
    """Base exception for all Kion MCP errors."""
    pass


class UserDeniedOperationError(KionMCPError):
    """Raised when user denies a financial operation."""
    pass


class ConfigurationError(KionMCPError):
    """Raised when there are configuration issues."""
    pass


class AuthenticationError(KionMCPError):
    """Raised when authentication fails."""
    pass


class KionAPIError(KionMCPError):
    """Raised when Kion API returns an error."""
    
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text