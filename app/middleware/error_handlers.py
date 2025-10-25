"""
Bank API - Error Handlers

Global error handlers for consistent error responses.
"""

from datetime import datetime
from flask import jsonify, request
from werkzeug.exceptions import HTTPException

from app.exceptions import (
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    BusinessRuleViolationError
)


def create_error_response(error_code: str, message: str, status_code: int, details: dict = None):
    """
    Create a standardized error response.
    
    Args:
        error_code: Error code identifier
        message: Human-readable error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        JSON response tuple (response, status_code)
    """
    error_response = {
        'error': {
            'code': error_code,
            'message': message,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    }
    
    if details:
        error_response['error']['details'] = details
    
    # Add request ID if available (useful for debugging)
    if hasattr(request, 'id'):
        error_response['error']['request_id'] = request.id
    
    return jsonify(error_response), status_code


def handle_validation_error(error: ValidationError):
    """
    Handle validation errors.
    
    Args:
        error: ValidationError instance
        
    Returns:
        JSON error response
    """
    return create_error_response(
        error_code=error.error_code,
        message=str(error),
        status_code=error.status_code
    )


def handle_authentication_error(error: AuthenticationError):
    """
    Handle authentication errors.
    
    Args:
        error: AuthenticationError instance
        
    Returns:
        JSON error response
    """
    return create_error_response(
        error_code=error.error_code,
        message=str(error),
        status_code=error.status_code
    )


def handle_authorization_error(error: AuthorizationError):
    """
    Handle authorization errors.
    
    Args:
        error: AuthorizationError instance
        
    Returns:
        JSON error response
    """
    return create_error_response(
        error_code=error.error_code,
        message=str(error),
        status_code=error.status_code
    )


def handle_not_found_error(error: NotFoundError):
    """
    Handle not found errors.
    
    Args:
        error: NotFoundError instance
        
    Returns:
        JSON error response
    """
    return create_error_response(
        error_code=error.error_code,
        message=str(error),
        status_code=error.status_code
    )


def handle_business_rule_violation(error: BusinessRuleViolationError):
    """
    Handle business rule violation errors.
    
    Args:
        error: BusinessRuleViolationError instance
        
    Returns:
        JSON error response
    """
    return create_error_response(
        error_code=error.error_code,
        message=str(error),
        status_code=error.status_code
    )


def handle_http_exception(error: HTTPException):
    """
    Handle standard HTTP exceptions from Werkzeug.
    
    Args:
        error: HTTPException instance
        
    Returns:
        JSON error response
    """
    return create_error_response(
        error_code='HTTP_ERROR',
        message=error.description or str(error),
        status_code=error.code
    )


def handle_generic_error(error: Exception):
    """
    Handle generic uncaught exceptions.
    
    Args:
        error: Exception instance
        
    Returns:
        JSON error response
    """
    # Log the error for debugging
    import traceback
    print(f"Unhandled exception: {str(error)}")
    print(traceback.format_exc())
    
    # Don't expose internal error details in production
    return create_error_response(
        error_code='INTERNAL_ERROR',
        message='An internal server error occurred',
        status_code=500
    )

