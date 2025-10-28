"""
Bank API - Transaction Routes

Handles transaction-specific operations.

**For transaction creation and listing, see accounts blueprint:**
- POST /v1/accounts/<account_id>/transactions (create transaction)
- POST /v1/accounts/mine/transactions (customer shortcut)
- GET /v1/accounts/<account_id>/transactions (list transactions)
- GET /v1/accounts/mine/transactions (customer shortcut)

**This blueprint provides:**
- GET /v1/transactions/<transaction_id> (get transaction by ID)
"""

from flask_smorest import Blueprint
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.models import db
from app.services.transaction_service import TransactionService
from app.services.account_service import AccountService
from app.exceptions import NotFoundError

# Import schemas from centralized registry
from app.api.schemas import TransactionResponseSchema

# ============================================================================
# Blueprint
# ============================================================================

transactions_bp = Blueprint(
    'transactions',
    __name__,
    url_prefix='/v1/transactions',
    description='Transaction operations'
)

# ============================================================================
# Routes
# ============================================================================

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

    **Authorization:**
    - Customers can only view transactions from their own accounts
    - Admins can view any transaction

    **Returns:**
    - 200: Transaction details
    - 403: Not authorized (customer trying to view another's transaction)
    - 404: Transaction not found
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
