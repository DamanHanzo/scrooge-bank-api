"""
Bank API - Transaction Routes

REST API endpoints for transaction operations.
All schemas imported from centralized registry.
"""

from flask_smorest import Blueprint
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.models import db
from app.services.transaction_service import TransactionService
from app.services.account_service import AccountService
from app.schemas.transaction import DepositRequest, WithdrawalRequest
from app.exceptions import (
    NotFoundError, BusinessRuleViolationError,
    InsufficientFundsError, TransactionLimitError,
    ValidationError
)

# Import all schemas from centralized registry
from app.api.schemas import (
    DepositSchema,
    WithdrawalSchema,
    TransactionResponseSchema,
    TransactionListSchema,
    TransactionFilterSchema
)

# ============================================================================
# Blueprint
# ============================================================================

transactions_bp = Blueprint(
    'transactions',
    __name__,
    url_prefix='/v1/transactions',
    description='Transaction operations (deposits, withdrawals)'
)

# ============================================================================
# Routes
# ============================================================================

@transactions_bp.route('/accounts/<uuid:account_id>/deposits', methods=['POST'])
@transactions_bp.arguments(DepositSchema, description="Deposit details")
@transactions_bp.response(201, TransactionResponseSchema, description="Deposit successful")
@transactions_bp.alt_response(403, description="Not authorized")
@transactions_bp.alt_response(404, description="Account not found")
@jwt_required()
def create_deposit(args, account_id):
    """
    Create a deposit transaction.
    
    Deposits funds into an account. Customers can only deposit to their own accounts.
    """
    try:
        account_service = AccountService(db.session)
        account = account_service.get_account(account_id)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        data = DepositRequest(**args)
        service = TransactionService(db.session)
        transaction = service.deposit(account_id, data)
        
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
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@transactions_bp.route('/accounts/<uuid:account_id>/withdrawals', methods=['POST'])
@transactions_bp.arguments(WithdrawalSchema, description="Withdrawal details")
@transactions_bp.response(201, TransactionResponseSchema, description="Withdrawal successful")
@transactions_bp.alt_response(403, description="Not authorized")
@transactions_bp.alt_response(422, description="Insufficient funds or limit exceeded")
@jwt_required()
def create_withdrawal(args, account_id):
    """
    Create a withdrawal transaction.
    
    Withdraws funds from an account. Subject to balance and daily limit checks.
    Customers can only withdraw from their own accounts.
    """
    try:
        account_service = AccountService(db.session)
        account = account_service.get_account(account_id)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        data = WithdrawalRequest(**args)
        service = TransactionService(db.session)
        transaction = service.withdraw(account_id, data)
        
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
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 422
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    #TODO: Think through this design i.e. generic BusinessRuleViolationError or specific named exceptions
    # except (InsufficientFundsError, TransactionLimitError) as e:
    #     return jsonify({'error': {'code': e.__class__.__name__, 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@transactions_bp.route('/accounts/<uuid:account_id>/transactions', methods=['GET'])
@transactions_bp.arguments(TransactionFilterSchema, location='query', description="Filter parameters")
@transactions_bp.response(200, TransactionListSchema, description="Transaction history")
@transactions_bp.alt_response(403, description="Not authorized")
@jwt_required()
def get_account_transactions(query_args, account_id):
    """
    Get transaction history for an account.
    
    Retrieves transaction history with optional filtering by date range and type.
    Customers can only view their own account transactions.
    """
    try:
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
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@transactions_bp.route('/<uuid:transaction_id>', methods=['GET'])
@transactions_bp.response(200, TransactionResponseSchema, description="Transaction details")
@transactions_bp.alt_response(403, description="Not authorized")
@transactions_bp.alt_response(404, description="Transaction not found")
@jwt_required()
def get_transaction(transaction_id):
    """
    Get transaction by ID.
    
    Retrieves details of a specific transaction.
    Customers can only view transactions from their own accounts.
    """
    try:
        service = TransactionService(db.session)
        transaction = service.get_transaction(transaction_id)
        
        account_service = AccountService(db.session)
        account = account_service.get_account(transaction.account_id)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        return {
            'id': str(transaction.id),
            'account_id': str(transaction.account_id),
            'transaction_type': transaction.transaction_type,
            'amount': str(transaction.amount),
            'balance_after': str(transaction.balance_after),
            'reference_number': transaction.reference_number,
            'status': transaction.status
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
