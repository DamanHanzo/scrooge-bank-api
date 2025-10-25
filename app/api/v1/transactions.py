"""
Bank API - Transaction Routes

REST API endpoints for transaction operations (deposits, withdrawals).
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID
from datetime import datetime

from app.models import db
from app.services.transaction_service import TransactionService
from app.services.account_service import AccountService
from app.schemas.transaction import DepositRequest, WithdrawalRequest
from app.exceptions import (
    NotFoundError,
    ValidationError,
    BusinessRuleViolationError,
    InsufficientFundsError,
    AccountFrozenError,
    TransactionLimitError
)

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/accounts/<account_id>/deposits', methods=['POST'])
@jwt_required()
def create_deposit(account_id: str):
    """
    Create a deposit transaction.
    
    Returns:
        201: Deposit successful
        400: Validation error
        403: Not authorized
        404: Account not found
        422: Business rule violation
    """
    try:
        # Check account ownership
        account_service = AccountService(db.session)
        account = account_service.get_account(UUID(account_id))
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to deposit to this account'
                }
            }), 403
        
        # Parse and validate request
        data = DepositRequest(**request.json)
        
        # Create deposit
        service = TransactionService(db.session)
        transaction = service.deposit(UUID(account_id), data)
        
        return jsonify({
            'id': str(transaction.id),
            'account_id': str(transaction.account_id),
            'transaction_type': transaction.transaction_type,
            'amount': str(transaction.amount),
            'currency': transaction.currency,
            'balance_after': str(transaction.balance_after),
            'description': transaction.description,
            'reference_number': transaction.reference_number,
            'status': transaction.status,
            'created_at': transaction.created_at.isoformat(),
            'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None
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


@transactions_bp.route('/accounts/<account_id>/withdrawals', methods=['POST'])
@jwt_required()
def create_withdrawal(account_id: str):
    """
    Create a withdrawal transaction.
    
    Returns:
        201: Withdrawal successful
        400: Validation error
        403: Not authorized
        404: Account not found
        422: Insufficient funds or business rule violation
    """
    try:
        # Check account ownership
        account_service = AccountService(db.session)
        account = account_service.get_account(UUID(account_id))
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to withdraw from this account'
                }
            }), 403
        
        # Parse and validate request
        data = WithdrawalRequest(**request.json)
        
        # Create withdrawal
        service = TransactionService(db.session)
        transaction = service.withdraw(UUID(account_id), data)
        
        return jsonify({
            'id': str(transaction.id),
            'account_id': str(transaction.account_id),
            'transaction_type': transaction.transaction_type,
            'amount': str(transaction.amount),
            'currency': transaction.currency,
            'balance_after': str(transaction.balance_after),
            'description': transaction.description,
            'reference_number': transaction.reference_number,
            'status': transaction.status,
            'created_at': transaction.created_at.isoformat(),
            'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None
        }), 201
        
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except InsufficientFundsError as e:
        return jsonify({'error': {'code': 'INSUFFICIENT_FUNDS', 'message': str(e)}}), 422
    except TransactionLimitError as e:
        return jsonify({'error': {'code': 'TRANSACTION_LIMIT_EXCEEDED', 'message': str(e)}}), 422
    except AccountFrozenError as e:
        return jsonify({'error': {'code': 'ACCOUNT_FROZEN', 'message': str(e)}}), 422
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@transactions_bp.route('/accounts/<account_id>/transactions', methods=['GET'])
@jwt_required()
def get_account_transactions(account_id: str):
    """
    Get transaction history for an account.
    
    Query Parameters:
        - start_date: Filter from this date (ISO format)
        - end_date: Filter until this date (ISO format)
        - transaction_type: Filter by type (DEPOSIT, WITHDRAWAL, etc.)
        - status: Filter by status (COMPLETED, PENDING, etc.)
        - limit: Number of results (default 20)
        - offset: Pagination offset (default 0)
    
    Returns:
        200: List of transactions
        403: Not authorized
        404: Account not found
    """
    try:
        # Check account ownership
        account_service = AccountService(db.session)
        account = account_service.get_account(UUID(account_id))
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to view transactions for this account'
                }
            }), 403
        
        # Parse query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        transaction_type = request.args.get('transaction_type')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Convert dates
        start_date_obj = datetime.fromisoformat(start_date) if start_date else None
        end_date_obj = datetime.fromisoformat(end_date) if end_date else None
        
        # Get transactions
        service = TransactionService(db.session)
        transactions, total = service.get_account_transactions(
            UUID(account_id),
            start_date=start_date_obj,
            end_date=end_date_obj,
            transaction_type=transaction_type,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'data': [{
                'id': str(txn.id),
                'account_id': str(txn.account_id),
                'transaction_type': txn.transaction_type,
                'amount': str(txn.amount),
                'currency': txn.currency,
                'balance_after': str(txn.balance_after),
                'description': txn.description,
                'reference_number': txn.reference_number,
                'status': txn.status,
                'created_at': txn.created_at.isoformat(),
                'processed_at': txn.processed_at.isoformat() if txn.processed_at else None
            } for txn in transactions],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total
            }
        }), 200
        
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@transactions_bp.route('/<transaction_id>', methods=['GET'])
@jwt_required()
def get_transaction(transaction_id: str):
    """
    Get transaction by ID.
    
    Returns:
        200: Transaction details
        403: Not authorized
        404: Transaction not found
    """
    try:
        service = TransactionService(db.session)
        transaction = service.get_transaction(UUID(transaction_id))
        
        # Check account ownership
        account_service = AccountService(db.session)
        account = account_service.get_account(transaction.account_id)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(account.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to view this transaction'
                }
            }), 403
        
        return jsonify({
            'id': str(transaction.id),
            'account_id': str(transaction.account_id),
            'transaction_type': transaction.transaction_type,
            'amount': str(transaction.amount),
            'currency': transaction.currency,
            'balance_after': str(transaction.balance_after),
            'description': transaction.description,
            'reference_number': transaction.reference_number,
            'status': transaction.status,
            'created_at': transaction.created_at.isoformat(),
            'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None
        }), 200
        
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500

