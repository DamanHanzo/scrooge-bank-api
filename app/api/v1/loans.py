"""
Bank API - Loan Routes

REST API endpoints for loan application management.
All schemas imported from centralized registry.
"""

from flask_smorest import Blueprint
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError as PydanticValidationError
from decimal import Decimal

from app.models import db
from app.services.loan_service import LoanService
from app.services.account_service import AccountService
from app.schemas.loan import LoanApplicationRequest, LoanPaymentRequest
from app.exceptions import NotFoundError, ValidationError, BusinessRuleViolationError

# Import all schemas from centralized registry
from app.api.schemas import (
    LoanApplicationSchema,
    LoanResponseSchema,
    LoanListSchema,
    LoanFilterSchema,
    MessageSchema,
    TransactionResponseSchema,
    LoanPaymentSchema
)

# ============================================================================
# Blueprint
# ============================================================================

loans_bp = Blueprint(
    'loans',
    __name__,
    url_prefix='/v1/loan-applications',
    description='Loan application management'
)

# ============================================================================
# Routes
# ============================================================================

@loans_bp.route('', methods=['POST'])
@loans_bp.arguments(LoanApplicationSchema, description="Loan application details")
@loans_bp.response(201, LoanResponseSchema, description="Loan application submitted")
@loans_bp.alt_response(403, description="Not authorized")
@loans_bp.alt_response(422, description="Business rule violation")
@jwt_required()
def submit_loan_application(args):
    """
    Submit a new loan application.
    
    Submits a loan application for review. Customers can only apply for their own loans.
    Maximum loan amount is $100,000.
    """
    try:
        data = LoanApplicationRequest(**args)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(data.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        service = LoanService(db.session)
        application = service.submit_application(data)
        
        return {
            'id': str(application.id),
            'customer_id': str(application.customer_id),
            'application_number': application.application_number,
            'requested_amount': str(application.requested_amount),
            'status': application.status,
            'applied_at': application.applied_at.isoformat()
        }, 201
    except (PydanticValidationError, ValidationError) as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@loans_bp.route('/<uuid:application_id>', methods=['GET'])
@loans_bp.response(200, LoanResponseSchema, description="Loan application details")
@loans_bp.alt_response(403, description="Not authorized")
@loans_bp.alt_response(404, description="Loan application not found")
@jwt_required()
def get_loan_application(application_id):
    """
    Get loan application by ID.
    
    Retrieves loan application details.
    Customers can only view their own applications.
    """
    try:
        service = LoanService(db.session)
        application = service.get_application(application_id)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(application.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        return {
            'id': str(application.id),
            'customer_id': str(application.customer_id),
            'application_number': application.application_number,
            'requested_amount': str(application.requested_amount),
            'status': application.status,
            'applied_at': application.applied_at.isoformat()
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@loans_bp.route('', methods=['GET'])
@loans_bp.arguments(LoanFilterSchema, location='query', description="Filter parameters")
@loans_bp.response(200, LoanListSchema, description="List of loan applications")
@loans_bp.alt_response(403, description="Not authorized")
@jwt_required()
def list_loan_applications(query_args):
    """
    List loan applications.
    
    For customers: returns only their applications.
    For admins: returns all applications.
    """
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        service = LoanService(db.session)
        
        if user_role == 'CUSTOMER':
            applications, total = service.get_customer_applications(
                user_customer_id,
                status=query_args.get('status'),
                limit=query_args.get('limit', 20),
                offset=query_args.get('offset', 0)
            )
        else:
            applications, total = service.get_all_applications(
                status=query_args.get('status'),
                limit=query_args.get('limit', 20),
                offset=query_args.get('offset', 0)
            )
        
        return {
            'data': [{
                'id': str(app.id),
                'customer_id': str(app.customer_id),
                'application_number': app.application_number,
                'requested_amount': str(app.requested_amount),
                'status': app.status,
                'applied_at': app.applied_at.isoformat()
            } for app in applications],
            'pagination': {
                'total': total,
                'limit': query_args.get('limit', 20),
                'offset': query_args.get('offset', 0)
            }
        }
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@loans_bp.route('/<uuid:application_id>/cancel', methods=['POST'])
@loans_bp.response(200, MessageSchema, description="Loan application cancelled")
@loans_bp.alt_response(403, description="Not authorized")
@loans_bp.alt_response(404, description="Loan application not found")
@loans_bp.alt_response(422, description="Cannot cancel - already approved or disbursed")
@jwt_required()
def cancel_loan_application(application_id):
    """
    Cancel a loan application.
    
    Only customers can cancel their own pending applications.
    Approved or disbursed loans cannot be cancelled.
    """
    try:
        service = LoanService(db.session)
        application = service.get_application(application_id)
        
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(application.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        service.cancel_application(application_id)
        
        return {'message': 'Loan application cancelled successfully'}
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@loans_bp.route('/loan-accounts/<uuid:loan_account_id>/payments', methods=['POST'])
@loans_bp.arguments(LoanPaymentSchema, description="Loan payment details", location='json')
@loans_bp.response(201, TransactionResponseSchema, description="Payment processed")
@loans_bp.alt_response(403, description="Not authorized")
@loans_bp.alt_response(404, description="Loan account not found")
@loans_bp.alt_response(422, description="Business rule violation")
@jwt_required()
def make_loan_payment(args, loan_account_id):
    """
    Make a payment on a loan account.

    Customers can only make payments on their own loan accounts.
    Reduces the loan balance (debt) by the payment amount.
    Automatically closes the loan account when fully paid off.
    """
    try:
        # Validate and parse payment request
        payment_request = LoanPaymentRequest(**args)

        # Get loan account and verify ownership
        account_service = AccountService(db.session)
        loan_account = account_service.get_account(loan_account_id)

        # Authorization: customers can only pay their own loans
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')

        if user_role == 'CUSTOMER' and str(user_customer_id) != str(loan_account.customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403

        # Process payment
        loan_service = LoanService(db.session)
        transaction = loan_service.make_loan_payment(
            loan_account_id=loan_account_id,
            payment_amount=payment_request.amount,
            description=payment_request.description
        )

        return {
            'id': str(transaction.id),
            'account_id': str(transaction.account_id),
            'transaction_type': transaction.transaction_type,
            'amount': str(transaction.amount),
            'balance_after': str(transaction.balance_after),
            'reference_number': transaction.reference_number,
            'status': transaction.status,
            'description': transaction.description,
            'processed_at': transaction.processed_at.isoformat() if transaction.processed_at else None
        }, 201

    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 422
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
