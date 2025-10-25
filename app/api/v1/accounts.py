"""
Bank API - Account Routes

REST API endpoints for account management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.models import db
from app.services.account_service import AccountService
from app.schemas.account import AccountCreateRequest
from app.exceptions import NotFoundError, ValidationError, BusinessRuleViolationError

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('', methods=['POST'])
@jwt_required()
def create_account():
    """
    Create a new account.
    
    Returns:
        201: Account created successfully
        400: Validation error
        403: Not authorized
    """
    try:
        # Parse and validate request
        data = AccountCreateRequest(**request.json)
        
        # Check authorization - customers can only create their own accounts
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(data.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to create account for this customer'
                }
            }), 403
        
        # Create account
        service = AccountService(db.session)
        account = service.create_account(data)
        
        return jsonify({
            'id': str(account.id),
            'customer_id': str(account.customer_id),
            'account_type': account.account_type,
            'account_number': account.account_number,
            'status': account.status,
            'balance': str(account.balance),
            'currency': account.currency,
            'created_at': account.created_at.isoformat(),
            'updated_at': account.updated_at.isoformat()
        }), 201
        
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@accounts_bp.route('/<account_id>', methods=['GET'])
@jwt_required()
def get_account(account_id: str):
    """
    Get account by ID.
    
    Returns:
        200: Account details
        403: Not authorized
        404: Account not found
    """
    try:
        service = AccountService(db.session)
        account = service.get_account(UUID(account_id))
        
        # Check authorization
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to view this account'
                }
            }), 403
        
        return jsonify({
            'id': str(account.id),
            'customer_id': str(account.customer_id),
            'account_type': account.account_type,
            'account_number': account.account_number,
            'status': account.status,
            'balance': str(account.balance),
            'currency': account.currency,
            'created_at': account.created_at.isoformat(),
            'updated_at': account.updated_at.isoformat()
        }), 200
        
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@accounts_bp.route('/<account_id>/balance', methods=['GET'])
@jwt_required()
def get_account_balance(account_id: str):
    """
    Get account balance.
    
    Returns:
        200: Account balance
        403: Not authorized
        404: Account not found
    """
    try:
        service = AccountService(db.session)
        account = service.get_account(UUID(account_id))
        
        # Check authorization
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to view this balance'
                }
            }), 403
        
        balance_info = service.get_balance(UUID(account_id))
        
        return jsonify({
            'account_id': str(balance_info['account_id']),
            'account_number': balance_info['account_number'],
            'balance': str(balance_info['balance']),
            'currency': balance_info['currency'],
            'status': balance_info['status'],
            'as_of': balance_info['as_of'].isoformat()
        }), 200
        
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500

