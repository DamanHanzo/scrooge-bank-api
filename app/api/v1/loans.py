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
from app.schemas.loan import LoanApplicationRequest, LoanApplicationStatusUpdateRequest
from app.exceptions import NotFoundError, ValidationError, BusinessRuleViolationError

# Import all schemas from centralized registry
from app.api.schemas import (
    LoanApplicationSchema,
    LoanApplicationStatusUpdateSchema,
    LoanResponseSchema,
    LoanListSchema,
    LoanFilterSchema,
    MessageSchema
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
@loans_bp.doc(operationId="submitLoanApplication")
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
            'applied_at': application.applied_at  # Let Marshmallow serialize the datetime
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
@loans_bp.doc(operationId="getLoanApplication")
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

        # Return full application - let Marshmallow handle serialization
        return application
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@loans_bp.route('', methods=['GET'])
@loans_bp.arguments(LoanFilterSchema, location='query', description="Filter parameters")
@loans_bp.response(200, LoanListSchema, description="List of loan applications")
@loans_bp.alt_response(403, description="Not authorized")
@loans_bp.doc(operationId="listLoanApplications")
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


@loans_bp.route('/<uuid:application_id>', methods=['PATCH'])
@loans_bp.arguments(LoanApplicationStatusUpdateSchema, description="Loan application status update")
@loans_bp.response(200, LoanResponseSchema, description="Loan application updated")
@loans_bp.alt_response(403, description="Not authorized")
@loans_bp.alt_response(404, description="Loan application not found")
@loans_bp.alt_response(422, description="Business rule violation")
@loans_bp.doc(operationId="updateLoanApplicationStatus")
@jwt_required()
def update_loan_application_status(args, application_id):
    """
    Update loan application status.

    Customers can cancel their own pending applications (status: CANCELLED).
    Admins can approve or reject applications (status: APPROVED or REJECTED).
    """
    try:
        data = LoanApplicationStatusUpdateRequest(**args)
        service = LoanService(db.session)
        application = service.get_application(application_id)

        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')

        # Authorization check
        if user_role == 'CUSTOMER':
            # Customers can only cancel their own applications
            if str(user_customer_id) != str(application.customer_id):
                return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
            if data.status != 'CANCELLED':
                return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Customers can only cancel applications'}}), 403

            # Cancel the application
            service.cancel_application(application_id)
            application = service.get_application(application_id)
        else:
            # Admins can approve or reject
            if data.status == 'CANCELLED':
                return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Admins cannot cancel applications'}}), 403

            # Use existing review_application method
            from app.schemas.loan import LoanReviewRequest
            review_data = LoanReviewRequest(
                status=data.status,
                approved_amount=data.approved_amount,
                interest_rate=data.interest_rate,
                term_months=data.term_months,
                rejection_reason=data.rejection_reason
            )
            application = service.review_application(application_id, review_data)

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
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except (PydanticValidationError, ValidationError) as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
