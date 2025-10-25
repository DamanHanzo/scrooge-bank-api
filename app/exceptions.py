"""
Bank API - Custom Exceptions

Custom exception classes for the Bank API.
"""


class BankAPIException(Exception):
    """Base exception class for all custom exceptions."""
    status_code = 500
    error_code = "INTERNAL_ERROR"
    
    def __init__(self, message: str = None):
        self.message = message or "An internal error occurred"
        super().__init__(self.message)


class ValidationError(BankAPIException):
    """Exception raised for validation errors."""
    status_code = 400
    error_code = "VALIDATION_ERROR"
    
    def __init__(self, message: str = "Validation error"):
        super().__init__(message)


class AuthenticationError(BankAPIException):
    """Exception raised for authentication failures."""
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class AuthorizationError(BankAPIException):
    """Exception raised for authorization failures."""
    status_code = 403
    error_code = "FORBIDDEN"
    
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message)


class NotFoundError(BankAPIException):
    """Exception raised when a resource is not found."""
    status_code = 404
    error_code = "NOT_FOUND"
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class ConflictError(BankAPIException):
    """Exception raised for resource conflicts."""
    status_code = 409
    error_code = "CONFLICT"
    
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message)


class BusinessRuleViolationError(BankAPIException):
    """Exception raised when a business rule is violated."""
    status_code = 422
    error_code = "BUSINESS_RULE_VIOLATION"
    
    def __init__(self, message: str = "Business rule violation"):
        super().__init__(message)


class InsufficientFundsError(BusinessRuleViolationError):
    """Exception raised when account has insufficient funds."""
    error_code = "INSUFFICIENT_FUNDS"
    
    def __init__(self, message: str = "Insufficient funds"):
        super().__init__(message)


class AccountFrozenError(BusinessRuleViolationError):
    """Exception raised when attempting to operate on a frozen account."""
    error_code = "ACCOUNT_FROZEN"
    
    def __init__(self, message: str = "Account is frozen"):
        super().__init__(message)


class TransactionLimitError(BusinessRuleViolationError):
    """Exception raised when transaction limit is exceeded."""
    error_code = "TRANSACTION_LIMIT_EXCEEDED"
    
    def __init__(self, message: str = "Transaction limit exceeded"):
        super().__init__(message)


class RateLimitError(BankAPIException):
    """Exception raised when rate limit is exceeded."""
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message)

