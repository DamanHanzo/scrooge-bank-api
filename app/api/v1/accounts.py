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
from app.services.transaction_service import TransactionService
from app.services.loan_service import LoanService
from app.schemas.account import AccountCreateRequest, AccountStatusUpdateRequest
from app.schemas.transaction import TransactionCreateRequest, DepositRequest, WithdrawalRequest
from app.exceptions import (
    NotFoundError,
    ValidationError,
    BusinessRuleViolationError
)

# Import all schemas from centralized registry
from app.api.schemas import (
    AccountCreateSchema,
    AccountStatusUpdateSchema,
    AccountResponseSchema,
    BalanceResponseSchema,
    AccountFilterSchema,
    AccountListSchema,
    TransactionCreateSchema,
    TransactionResponseSchema,
    TransactionListSchema,
    TransactionFilterSchema
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
@accounts_bp.doc(operationId="listAccounts")
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
@accounts_bp.doc(operationId="createAccount")
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


@accounts_bp.route('/<account_id>/transactions', methods=['POST'])
@accounts_bp.arguments(TransactionCreateSchema, description="Transaction details")
@accounts_bp.response(201, TransactionResponseSchema, description="Transaction created successfully")
@accounts_bp.alt_response(403, description="Not authorized")
@accounts_bp.alt_response(404, description="Account not found")
@accounts_bp.alt_response(422, description="Business rule violation")
@jwt_required()
def create_transaction(args, account_id):
    """
    Create a transaction.

    Creates a deposit, withdrawal, or loan payment transaction for an account.

    **URL Parameters:**
    - account_id: UUID of the account, or "mine" to use authenticated user's account

    **Request Body:**
    - type: Transaction type (DEPOSIT, WITHDRAWAL, or LOAN_PAYMENT)
    - amount: Transaction amount (must be positive)
    - currency: Currency code (default: USD)
    - description: Optional transaction description

    **Authorization:**
    - Customers can only create transactions for their own accounts
    - Admins can create transactions for any account

    **Examples:**
    ```json
    {
      "type": "DEPOSIT",
      "amount": 500.00,
      "currency": "USD",
      "description": "Paycheck deposit"
    }
    ```

    ```json
    {
      "type": "WITHDRAWAL",
      "amount": 200.00,
      "currency": "USD",
      "description": "ATM withdrawal"
    }
    ```

    ```json
    {
      "type": "LOAN_PAYMENT",
      "amount": 1000.00,
      "currency": "USD",
      "description": "Monthly loan payment"
    }
    ```
    """
    try:
        from uuid import UUID

        # Handle "mine" shortcut for account_id
        if account_id == "mine":
            claims = get_jwt()
            user_customer_id = claims.get('customer_id')
            user_role = claims.get('role')

            if user_role != 'CUSTOMER' or not user_customer_id:
                return jsonify({
                    'error': {
                        'code': 'BAD_REQUEST',
                        'message': 'The "mine" shortcut is only available for customer users'
                    }
                }), 400

            # Get customer's account
            account_service = AccountService(db.session)
            accounts = account_service.get_customer_accounts(user_customer_id, account_type='CHECKING')

            if not accounts:
                return jsonify({
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': 'No checking account found for user'
                    }
                }), 404

            account_id = accounts[0].id
        else:
            # Parse UUID
            try:
                account_id = UUID(account_id)
            except ValueError:
                return jsonify({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid account_id format. Use UUID or "mine"'
                    }
                }), 400

        # Get account and check authorization
        account_service = AccountService(db.session)
        account = account_service.get_account(account_id)

        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')

        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403

        # Validate and create transaction
        data = TransactionCreateRequest(**args)
        service = TransactionService(db.session)

        # Route to appropriate service method based on type
        if data.type == "DEPOSIT":
            deposit_req = DepositRequest(
                amount=data.amount,
                currency=data.currency,
                description=data.description
            )
            transaction = service.deposit(account_id, deposit_req)
        elif data.type == "WITHDRAWAL":
            withdrawal_req = WithdrawalRequest(
                amount=data.amount,
                currency=data.currency,
                description=data.description
            )
            transaction = service.withdraw(account_id, withdrawal_req)
        elif data.type == "LOAN_PAYMENT":
            # Handle loan payment through loan service
            loan_service = LoanService(db.session)
            transaction = loan_service.make_loan_payment(
                loan_account_id=account_id,
                payment_amount=data.amount,
                description=data.description
            )
        else:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': f'Unsupported transaction type: {data.type}'
                }
            }), 400

        return {
            'id': str(transaction.id),
            'account_id': str(transaction.account_id),
            'transaction_type': transaction.transaction_type,
            'amount': str(transaction.amount),
            'balance_after': str(transaction.balance_after),
            'reference_number': transaction.reference_number,
            'status': transaction.status
        }, 201

    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except (PydanticValidationError, ValidationError) as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@accounts_bp.route('/<account_id>/transactions', methods=['GET'])
@accounts_bp.arguments(TransactionFilterSchema, location='query', description="Filter parameters")
@accounts_bp.response(200, TransactionListSchema, description="Transaction history")
@accounts_bp.alt_response(403, description="Not authorized")
@jwt_required()
def get_account_transactions(query_args, account_id):
    """
    Get transaction history for an account.

    Retrieves transaction history with optional filtering by date range and type.

    **URL Parameters:**
    - account_id: UUID of the account, or "mine" to use authenticated user's account

    **Authorization:**
    - Customers can only view their own account transactions
    - Admins can view any account's transactions
    """
    try:
        from uuid import UUID

        # Handle "mine" shortcut for account_id
        if account_id == "mine":
            claims = get_jwt()
            user_customer_id = claims.get('customer_id')
            user_role = claims.get('role')

            if user_role != 'CUSTOMER' or not user_customer_id:
                return jsonify({
                    'error': {
                        'code': 'BAD_REQUEST',
                        'message': 'The "mine" shortcut is only available for customer users'
                    }
                }), 400

            # Get customer's account
            account_service = AccountService(db.session)
            accounts = account_service.get_customer_accounts(user_customer_id, account_type='CHECKING')

            if not accounts:
                return jsonify({
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': 'No checking account found for user'
                    }
                }), 404

            account_id = accounts[0].id
        else:
            # Parse UUID
            try:
                account_id = UUID(account_id)
            except ValueError:
                return jsonify({
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Invalid account_id format. Use UUID or "mine"'
                    }
                }), 400

        # Get account and check authorization
        account_service = AccountService(db.session)
        account = account_service.get_account(account_id)

        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')

        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403

        service = TransactionService(db.session)
        transactions, total = service.get_account_transactions(
            account_id,
            start_date=query_args.get('start_date'),
            end_date=query_args.get('end_date'),
            transaction_type=query_args.get('transaction_type'),
            limit=query_args.get('limit', 50),
            offset=query_args.get('offset', 0)
        )

        return {
            'data': [{
                'id': str(t.id),
                'transaction_type': t.transaction_type,
                'amount': str(t.amount),
                'balance_after': str(t.balance_after),
                'reference_number': t.reference_number,
                'status': t.status,
                'created_at': t.created_at.isoformat()
            } for t in transactions],
            'pagination': {
                'total': total,
                'limit': query_args.get('limit', 50),
                'offset': query_args.get('offset', 0)
            }
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@accounts_bp.route('/<uuid:account_id>', methods=['PATCH'])
@accounts_bp.arguments(AccountStatusUpdateSchema, description="Account status update")
@accounts_bp.response(200, AccountResponseSchema, description="Account updated successfully")
@accounts_bp.alt_response(403, description="Not authorized")
@accounts_bp.alt_response(404, description="Account not found")
@accounts_bp.alt_response(422, description="Business rule violation")
@jwt_required()
def update_account_status(args, account_id):
    """
    Update account status.

    Updates account properties, primarily status changes (e.g., closing an account).

    **Supported Status Changes:**
    - ACTIVE → CLOSED (close account)

    **Business Rules for Closing:**
    - Account balance must be exactly 0.00
    - Only ACTIVE accounts can be closed
    - Cannot reopen a closed account

    **Authorization:**
    - Customers can only update their own accounts
    - Admins can update any account

    **Request Body:**
    ```json
    {
      "status": "CLOSED",
      "reason": "Customer requested account closure"
    }
    ```

    **Returns:**
    - 200: Account updated successfully
    - 403: Not authorized
    - 404: Account not found
    - 422: Business rule violation (e.g., non-zero balance)
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

        # Validate and parse request
        data = AccountStatusUpdateRequest(**args)

        # Handle status change
        if data.status == 'CLOSED':
            # Use existing close_account service method
            updated_account = service.close_account(account_id)
        else:
            return jsonify({
                'error': {
                    'code': 'VALIDATION_ERROR',
                    'message': f'Unsupported status transition to {data.status}'
                }
            }), 400

        return {
            'id': str(updated_account.id),
            'customer_id': str(updated_account.customer_id),
            'account_type': updated_account.account_type,
            'account_number': updated_account.account_number,
            'status': updated_account.status,
            'balance': str(updated_account.balance),
            'currency': updated_account.currency
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except (PydanticValidationError, ValidationError) as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
