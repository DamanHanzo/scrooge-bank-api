"""
Bank API - Account Routes

REST API endpoints for account management.
All schemas imported from centralized registry.
"""

from flask_smorest import Blueprint
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError as PydanticValidationError

from app.models import db
from app.services.account_service import AccountService
from app.schemas.account import AccountCreateRequest
from app.exceptions import NotFoundError, ValidationError, BusinessRuleViolationError

# Import all schemas from centralized registry
from app.api.schemas import (
    AccountCreateSchema,
    AccountResponseSchema,
    BalanceResponseSchema
)

# ============================================================================
# Blueprint
# ============================================================================

accounts_bp = Blueprint(
    'accounts',
    __name__,
    url_prefix='/v1/accounts',
    description='Account management operations'
)

# ============================================================================
# Routes
# ============================================================================

@accounts_bp.route('', methods=['POST'])
@accounts_bp.arguments(AccountCreateSchema, description="Account creation details")
@accounts_bp.response(201, AccountResponseSchema, description="Account created successfully")
@accounts_bp.alt_response(400, description="Validation error")
@accounts_bp.alt_response(403, description="Not authorized")
@jwt_required()
def create_account(args):
    """
    Create a new account.
    
    Creates a new checking or loan account for a customer.
    Customers can only create accounts for themselves.
    """
    try:
        data = AccountCreateRequest(**args)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(data.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        service = AccountService(db.session)
        account = service.create_account(data)
        
        return {
            'id': str(account.id),
            'customer_id': str(account.customer_id),
            'account_type': account.account_type,
            'account_number': account.account_number,
            'status': account.status,
            'balance': str(account.balance),
            'currency': account.currency
        }, 201
    except (PydanticValidationError, ValidationError) as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@accounts_bp.route('/<uuid:account_id>', methods=['GET'])
@accounts_bp.response(200, AccountResponseSchema, description="Account details")
@accounts_bp.alt_response(403, description="Not authorized")
@accounts_bp.alt_response(404, description="Account not found")
@jwt_required()
def get_account(account_id):
    """
    Get account by ID.
    
    Retrieves account details. Customers can only view their own accounts.
    """
    try:
        service = AccountService(db.session)
        account = service.get_account(account_id)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        return {
            'id': str(account.id),
            'customer_id': str(account.customer_id),
            'account_type': account.account_type,
            'account_number': account.account_number,
            'status': account.status,
            'balance': str(account.balance),
            'currency': account.currency
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@accounts_bp.route('/<uuid:account_id>/balance', methods=['GET'])
@accounts_bp.response(200, BalanceResponseSchema, description="Account balance")
@accounts_bp.alt_response(403, description="Not authorized")
@accounts_bp.alt_response(404, description="Account not found")
@jwt_required()
def get_account_balance(account_id):
    """
    Get account balance.
    
    Retrieves current balance for an account.
    Customers can only view their own account balances.
    """
    try:
        service = AccountService(db.session)
        account = service.get_account(account_id)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        balance_info = service.get_balance(account_id)
        
        return {
            'account_id': str(balance_info['account_id']),
            'account_number': balance_info['account_number'],
            'balance': str(balance_info['balance']),
            'currency': balance_info['currency'],
            'status': balance_info['status'],
            'as_of': balance_info['as_of'].isoformat()
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
