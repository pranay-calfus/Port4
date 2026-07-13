from typing import Any


class AppError(Exception):

    def __init__(self, message: str, code: str, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details


class ValidationError(AppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, "VALIDATION_ERROR", details)


class AIUnavailableError(AppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, "AI_UNAVAILABLE", details)


class AIResponseError(AppError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(message, "AI_RESPONSE_ERROR", details)
