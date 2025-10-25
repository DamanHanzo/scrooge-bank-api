"""
Bank API - Admin Routes

REST API endpoints for administrative operations.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.models import db
from app.services.customer_service import CustomerService
from app.services.account_service import AccountService
from app.services.transaction_service import TransactionService
from app.services.loan_service import LoanService
from app.schemas.loan import LoanReviewRequest, LoanDisbursementRequest
from app.exceptions import (
    NotFoundError,
    ValidationError,
    BusinessRuleViolationError,
    AuthorizationError
)

admin_bp = Blueprint('admin', __name__)


def require_admin():
    """Check if user has admin role."""
    claims = get_jwt()
    user_role = claims.get('role')
    if user_role not in ['ADMIN', 'SUPER_ADMIN']:
        raise AuthorizationError('Admin access required')


@admin_bp.route('/customers', methods=['GET'])
@jwt_required()
def list_all_customers():
    """
    List all customers (admin only).
    
    Query Parameters:
        - status: Filter by status
        - limit: Number of results (default 20)
        - offset: Pagination offset (default 0)
    
    Returns:
        200: List of customers
        403: Not authorized
    """
    try:
        require_admin()
        
        # Parse query parameters
        status = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Get customers
        service = CustomerService(db.session)
        customers, total = service.list_customers(
            status=status,
            limit=limit,
            offset=offset
        )
        
        return jsonify({
            'data': [{
                'id': str(customer.id),
                'email': customer.email,
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'status': customer.status,
                'created_at': customer.created_at.isoformat()
            } for customer in customers],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total
            }
        }), 200
        
    except AuthorizationError as e:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': str(e)}}), 403
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@admin_bp.route('/customers/<customer_id>/suspend', methods=['POST'])
@jwt_required()
def suspend_customer(customer_id: str):
    """
    Suspend a customer account (admin only).
    
    Returns:
        200: Customer suspended
        403: Not authorized
        404: Customer not found
    """
    try:
        require_admin()
        
        reason = request.json.get('reason', 'Administrative action')
        
        # Suspend customer
        service = CustomerService(db.session)
        customer = service.suspend_customer(UUID(customer_id), reason)
        
        return jsonify({
            'id': str(customer.id),
            'status': customer.status,
            'message': 'Customer suspended successfully'
        }), 200
        
    except AuthorizationError as e:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': str(e)}}), 403
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@admin_bp.route('/customers/<customer_id>/activate', methods=['POST'])
@jwt_required()
def activate_customer(customer_id: str):
    """
    Activate a customer account (admin only).
    
    Returns:
        200: Customer activated
        403: Not authorized
        404: Customer not found
    """
    try:
        require_admin()
        
        # Activate customer
        service = CustomerService(db.session)
        customer = service.activate_customer(UUID(customer_id))
        
        return jsonify({
            'id': str(customer.id),
            'status': customer.status,
            'message': 'Customer activated successfully'
        }), 200
        
    except AuthorizationError as e:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': str(e)}}), 403
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@admin_bp.route('/accounts/<account_id>/freeze', methods=['POST'])
@jwt_required()
def freeze_account(account_id: str):
    """
    Freeze an account (admin only).
    
    Returns:
        200: Account frozen
        403: Not authorized
        404: Account not found
    """
    try:
        require_admin()
        
        reason = request.json.get('reason', 'Administrative action')
        
        # Freeze account
        service = AccountService(db.session)
        account = service.freeze_account(UUID(account_id), reason)
        
        return jsonify({
            'id': str(account.id),
            'status': account.status,
            'message': 'Account frozen successfully'
        }), 200
        
    except AuthorizationError as e:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': str(e)}}), 403
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@admin_bp.route('/accounts/<account_id>/unfreeze', methods=['POST'])
@jwt_required()
def unfreeze_account(account_id: str):
    """
    Unfreeze an account (admin only).
    
    Returns:
        200: Account unfrozen
        403: Not authorized
        404: Account not found
    """
    try:
        require_admin()
        
        # Unfreeze account
        service = AccountService(db.session)
        account = service.unfreeze_account(UUID(account_id))
        
        return jsonify({
            'id': str(account.id),
            'status': account.status,
            'message': 'Account unfrozen successfully'
        }), 200
        
    except AuthorizationError as e:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': str(e)}}), 403
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@admin_bp.route('/loan-applications/<application_id>/review', methods=['POST'])
@jwt_required()
def review_loan_application(application_id: str):
    """
    Review a loan application - approve or reject (admin only).
    
    Returns:
        200: Application reviewed
        400: Validation error
        403: Not authorized
        404: Application not found
        422: Cannot review application
    """
    try:
        require_admin()
        
        # Parse and validate request
        data = LoanReviewRequest(**request.json)
        
        # Review application
        service = LoanService(db.session)
        application = service.review_application(UUID(application_id), data)
        
        return jsonify({
            'id': str(application.id),
            'status': application.status,
            'approved_amount': str(application.approved_amount) if application.approved_amount else None,
            'interest_rate': str(application.interest_rate) if application.interest_rate else None,
            'rejection_reason': application.rejection_reason,
            'message': f'Application {data.status.lower()} successfully'
        }), 200
        
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except AuthorizationError as e:
        return jsonify({'error': {'code': 'FORBIDDEN', 'message': str(e)}}), 403
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500