"""
Bank API - Authentication Routes

REST API endpoints for authentication operations.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError as PydanticValidationError

from app.models import db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    PasswordChangeRequest
)
from app.exceptions import AuthenticationError, ValidationError

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new customer user.
    
    Returns:
        201: User registered successfully with tokens
        400: Validation error
    """
    try:
        # Parse and validate request
        data = RegisterRequest(**request.json)
        
        # Register user
        service = AuthService(db.session)
        result = service.register_customer(data)
        
        return jsonify({
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token'],
            'token_type': 'bearer',
            'expires_in': 3600,
            'user': {
                'id': str(result['user'].id),
                'email': result['user'].email,
                'role': result['user'].role,
                'is_active': result['user'].is_active,
                'customer_id': str(result['user'].customer_id) if result['user'].customer_id else None
            }
        }), 201
        
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return tokens.
    
    Returns:
        200: Login successful with tokens
        401: Invalid credentials
    """
    try:
        # Parse and validate request
        data = LoginRequest(**request.json)
        
        # Authenticate user
        service = AuthService(db.session)
        result = service.login(data)
        
        return jsonify({
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token'],
            'token_type': 'bearer',
            'expires_in': 3600,
            'user': {
                'id': str(result['user'].id),
                'email': result['user'].email,
                'role': result['user'].role,
                'is_active': result['user'].is_active,
                'customer_id': str(result['user'].customer_id) if result['user'].customer_id else None
            }
        }), 200
        
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except AuthenticationError as e:
        return jsonify({'error': {'code': 'AUTHENTICATION_ERROR', 'message': str(e)}}), 401
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.
    
    Returns:
        200: New access token
        401: Invalid refresh token
    """
    try:
        user_id = get_jwt_identity()
        
        # Generate new access token
        service = AuthService(db.session)
        access_token = service.refresh_access_token(user_id)
        
        return jsonify({
            'access_token': access_token,
            'token_type': 'bearer',
            'expires_in': 3600
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user information.
    
    Returns:
        200: User information
        401: Not authenticated
    """
    try:
        user_id = get_jwt_identity()
        
        # Get user
        service = AuthService(db.session)
        user = service.get_user(user_id)
        
        return jsonify({
            'id': str(user.id),
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'customer_id': str(user.customer_id) if user.customer_id else None,
            'created_at': user.created_at.isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password.
    
    Returns:
        200: Password changed successfully
        401: Invalid current password
    """
    try:
        user_id = get_jwt_identity()
        
        # Parse request
        data = PasswordChangeRequest(**request.json)
        
        # Change password
        service = AuthService(db.session)
        service.change_password(
            user_id,
            data.current_password,
            data.new_password
        )
        
        return jsonify({'message': 'Password changed successfully'}), 200
        
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except AuthenticationError as e:
        return jsonify({'error': {'code': 'AUTHENTICATION_ERROR', 'message': str(e)}}), 401
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500

