"""
Bank API - Authentication Routes

REST API endpoints for authentication operations.
All schemas imported from centralized registry.
"""

from flask_smorest import Blueprint
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError as PydanticValidationError

from app.models import db
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest, RegisterRequest, PasswordChangeRequest

# Import all schemas from centralized registry
from app.api.schemas import (
    LoginSchema,
    RegisterSchema,
    PasswordChangeSchema,
    TokenResponseSchema,
    UserInfoSchema,
    MessageSchema
)

# ============================================================================
# Blueprint
# ============================================================================

auth_bp = Blueprint(
    'auth',
    __name__,
    url_prefix='/v1/auth',
    description='Authentication operations'
)

# ============================================================================
# Routes
# ============================================================================

@auth_bp.route('/register', methods=['POST'])
@auth_bp.arguments(RegisterSchema, description="User registration details")
@auth_bp.response(201, TokenResponseSchema, description="User registered successfully")
@auth_bp.alt_response(400, description="Validation error or email already exists")
def register(args):
    """
    Register a new customer user.
    
    Creates a new customer account with the provided details.
    Returns JWT tokens for immediate authentication.
    """
    try:
        data = RegisterRequest(**args)
        service = AuthService(db.session)
        result = service.register_customer(data)
        
        return {
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token'],
            'token_type': 'bearer',
            'expires_in': 3600
        }, 201
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/login', methods=['POST'])
@auth_bp.arguments(LoginSchema, description="Login credentials")
@auth_bp.response(200, TokenResponseSchema, description="Login successful")
@auth_bp.alt_response(401, description="Invalid credentials")
def login(args):
    """
    Authenticate a user and return access tokens.
    
    Validates email and password, returns JWT tokens if successful.
    """
    try:
        data = LoginRequest(**args)
        service = AuthService(db.session)
        result = service.login(data)
        
        return {
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token'],
            'token_type': 'bearer',
            'expires_in': 3600
        }
    except Exception as e:
        return jsonify({'error': {'code': 'AUTHENTICATION_ERROR', 'message': str(e)}}), 401


@auth_bp.route('/refresh', methods=['POST'])
@auth_bp.response(200, TokenResponseSchema, description="New access token generated")
@auth_bp.alt_response(401, description="Invalid refresh token")
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.
    
    Provide a valid refresh token in the Authorization header.
    Returns a new access token.
    """
    try:
        user_id = get_jwt_identity()
        service = AuthService(db.session)
        access_token = service.refresh_access_token(user_id)
        
        return {
            'access_token': access_token,
            'token_type': 'bearer',
            'expires_in': 3600
        }
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/me', methods=['GET'])
@auth_bp.response(200, UserInfoSchema, description="Current user information")
@auth_bp.alt_response(401, description="Not authenticated")
@jwt_required()
def get_current_user():
    """
    Get current authenticated user information.
    
    Returns details about the currently authenticated user.
    Requires valid JWT token in Authorization header.
    """
    try:
        user_id = get_jwt_identity()
        service = AuthService(db.session)
        user = service.get_user(user_id)
        
        return {
            'id': str(user.id),
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'customer_id': str(user.customer_id) if user.customer_id else None,
            'created_at': user.created_at.isoformat()
        }
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/change-password', methods=['POST'])
@auth_bp.arguments(PasswordChangeSchema, description="Password change request")
@auth_bp.response(200, MessageSchema, description="Password changed successfully")
@auth_bp.alt_response(401, description="Invalid current password")
@jwt_required()
def change_password(args):
    """
    Change password for authenticated user.
    
    Requires current password for verification.
    Updates to new password if current password is valid.
    """
    try:
        user_id = get_jwt_identity()
        data = PasswordChangeRequest(**args)
        service = AuthService(db.session)
        service.change_password(user_id, data.current_password, data.new_password)
        
        return {'message': 'Password changed successfully'}
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
