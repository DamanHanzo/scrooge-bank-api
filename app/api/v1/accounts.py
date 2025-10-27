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
    BalanceResponseSchema,
    AccountFilterSchema,
    AccountListSchema
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

@accounts_bp.route('', methods=['GET'])
@accounts_bp.arguments(AccountFilterSchema, location='query', description="Filter parameters")
@accounts_bp.response(200, AccountListSchema, description="List of accounts")
@accounts_bp.alt_response(400, description="Bad request")
@accounts_bp.alt_response(403, description="Not authorized")
@jwt_required()
def list_accounts(query_args):
    """
    List accounts for the authenticated customer.
    
    Returns all accounts (checking and loan) owned by the authenticated customer.
    Admins can view all accounts by providing customer_id parameter.
    
    **Authorization:**
    - **Customers**: Automatically see their own accounts (customer_id from JWT)
    - **Admins**: Must provide customer_id query parameter to view accounts for any customer
    
    **Query Parameters:**
    - account_type: Filter by type (CHECKING, LOAN) - optional
    - status: Filter by status (ACTIVE, CLOSED) - optional
    - customer_id: (Admin only) View accounts for specific customer - required for admins
    
    **Returns:**
    - 200: List of accounts with total count
    - 400: Bad request (missing customer_id for admin)
    - 403: Forbidden (customer trying to view another's accounts)
    """
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        # Determine which customer's accounts to retrieve
        target_customer_id = query_args.get('customer_id')
        
        # Authorization: customers can only view their own accounts
        if user_role == 'CUSTOMER':
            if target_customer_id and str(target_customer_id) != str(user_customer_id):
                return jsonify({
                    'error': {
                        'code': 'FORBIDDEN',
                        'message': 'Not authorized to view other customer accounts'
                    }
                }), 403
            target_customer_id = user_customer_id
        elif user_role == 'ADMIN':
            if not target_customer_id:
                return jsonify({
                    'error': {
                        'code': 'BAD_REQUEST',
                        'message': 'customer_id query parameter is required for admin users'
                    }
                }), 400
        else:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        service = AccountService(db.session)
        accounts = service.get_customer_accounts(
            customer_id=target_customer_id,
            account_type=query_args.get('account_type')
        )
        
        # Filter by status if provided
        status_filter = query_args.get('status')
        if status_filter:
            accounts = [a for a in accounts if a.status == status_filter]
        
        return {
            'data': [{
                'id': str(acc.id),
                'customer_id': str(acc.customer_id),
                'account_type': acc.account_type,
                'account_number': acc.account_number,
                'status': acc.status,
                'balance': str(acc.balance),
                'currency': acc.currency,
                'created_at': acc.created_at  # Let Marshmallow serialize the datetime
            } for acc in accounts],
            'total': len(accounts)
        }
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@accounts_bp.route('', methods=['POST'])
@accounts_bp.arguments(AccountCreateSchema, description="Account creation details")
@accounts_bp.response(201, AccountResponseSchema, description="Account created successfully")
@accounts_bp.alt_response(400, description="Validation error")
@accounts_bp.alt_response(422, description="Business rule violation")
@jwt_required()
def create_account(args):
    """
    Create a new account.
    
    Creates a new checking or loan account for a customer.
    
    **Authorization:**
    - **Customers**: Automatically creates account for themselves (customer_id from JWT token)
    - **Admins**: Must provide `customer_id` as query parameter to create account for any customer
    
    **Request Body** (no customer_id needed):
    - account_type: CHECKING or LOAN
    - initial_deposit: Optional initial deposit amount
    - currency: Currency code (default: USD)
    
    **Query Parameters** (Admin only):
    - customer_id: UUID of the customer (required for admin users)
    """
    try:
        from flask import request
        from uuid import UUID
        
        data = AccountCreateRequest(**args)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        # Determine customer_id based on role
        if user_role == 'CUSTOMER':
            # Customers create accounts for themselves
            customer_id = UUID(user_customer_id)
        elif user_role == 'ADMIN':
            # Admins must provide customer_id as query parameter
            customer_id_param = request.args.get('customer_id')
            if not customer_id_param:
                return jsonify({
                    'error': {
                        'code': 'BAD_REQUEST',
                        'message': 'customer_id query parameter is required for admin users'
                    }
                }), 400
            try:
                customer_id = UUID(customer_id_param)
            except ValueError:
                return jsonify({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid customer_id format'
                    }
                }), 400
        else:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        service = AccountService(db.session)
        account = service.create_account(data, customer_id)
        
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


@accounts_bp.route('/<uuid:account_id>/close', methods=['POST'])
@accounts_bp.response(200, AccountResponseSchema, description="Account closed successfully")
@accounts_bp.alt_response(403, description="Not authorized")
@accounts_bp.alt_response(404, description="Account not found")
@accounts_bp.alt_response(422, description="Cannot close account - business rule violation")
@jwt_required()
def close_account(account_id):
    """
    Close an account.
    
    Closes a checking or loan account. Account must have zero balance to be closed.
    Customers can only close their own accounts. Admins can close any account.
    
    **Business Rules:**
    - Account balance must be exactly 0.00
    - Only ACTIVE accounts can be closed
    - Account status will be set to CLOSED
    - Cannot reopen a closed account
    
    **Authorization:**
    - Customers can only close their own accounts
    - Admins can close any customer's account
    
    **Returns:**
    - 200: Account closed successfully
    - 403: Not authorized (customer trying to close another's account)
    - 404: Account not found
    - 422: Business rule violation (non-zero balance or already closed)
    """
    try:
        service = AccountService(db.session)
        account = service.get_account(account_id)
        
        # Authorization check
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        # Close the account
        closed_account = service.close_account(account_id)
        
        return {
            'id': str(closed_account.id),
            'customer_id': str(closed_account.customer_id),
            'account_type': closed_account.account_type,
            'account_number': closed_account.account_number,
            'status': closed_account.status,
            'balance': str(closed_account.balance),
            'currency': closed_account.currency
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
