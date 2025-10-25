"""
Bank API - Loan Routes

REST API endpoints for loan application management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.models import db
from app.services.loan_service import LoanService
from app.schemas.loan import LoanApplicationRequest
from app.exceptions import NotFoundError, ValidationError, BusinessRuleViolationError

loans_bp = Blueprint('loans', __name__)


@loans_bp.route('', methods=['POST'])
@jwt_required()
def submit_loan_application():
    """
    Submit a new loan application.
    
    Returns:
        201: Application submitted successfully
        400: Validation error
        403: Not authorized
        422: Business rule violation
    """
    try:
        # Parse and validate request
        data = LoanApplicationRequest(**request.json)
        
        # Check authorization - customers can only apply for their own loans
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(data.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to submit loan application for this customer'
                }
            }), 403
        
        # Submit application
        service = LoanService(db.session)
        application = service.submit_application(data)
        
        return jsonify({
            'id': str(application.id),
            'customer_id': str(application.customer_id),
            'application_number': application.application_number,
            'requested_amount': str(application.requested_amount),
            'purpose': application.purpose,
            'term_months': application.term_months,
            'employment_status': application.employment_status,
            'annual_income': str(application.annual_income),
            'status': application.status,
            'applied_at': application.applied_at.isoformat(),
            'external_account': {
                'account_number': f"***{application.external_account_number[-4:]}",
                'routing_number': application.external_routing_number
            }
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


@loans_bp.route('/<application_id>', methods=['GET'])
@jwt_required()
def get_loan_application(application_id: str):
    """
    Get loan application by ID.
    
    Returns:
        200: Application details
        403: Not authorized
        404: Application not found
    """
    try:
        service = LoanService(db.session)
        application = service.get_application(UUID(application_id))
        
        # Check authorization
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(application.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to view this application'
                }
            }), 403
        
        return jsonify({
            'id': str(application.id),
            'customer_id': str(application.customer_id),
            'loan_account_id': str(application.loan_account_id) if application.loan_account_id else None,
            'application_number': application.application_number,
            'requested_amount': str(application.requested_amount),
            'approved_amount': str(application.approved_amount) if application.approved_amount else None,
            'interest_rate': str(application.interest_rate) if application.interest_rate else None,
            'term_months': application.term_months,
            'purpose': application.purpose,
            'employment_status': application.employment_status,
            'annual_income': str(application.annual_income),
            'status': application.status,
            'applied_at': application.applied_at.isoformat(),
            'reviewed_at': application.reviewed_at.isoformat() if application.reviewed_at else None,
            'disbursed_at': application.disbursed_at.isoformat() if application.disbursed_at else None,
            'rejection_reason': application.rejection_reason,
            'external_account': {
                'account_number': f"***{application.external_account_number[-4:]}",
                'routing_number': application.external_routing_number
            } if application.external_account_number else None
        }), 200
        
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@loans_bp.route('', methods=['GET'])
@jwt_required()
def list_loan_applications():
    """
    List loan applications.
    
    For customers: returns only their applications
    For admins: returns all applications
    
    Query Parameters:
        - status: Filter by status
        - limit: Number of results (default 20)
        - offset: Pagination offset (default 0)
    
    Returns:
        200: List of applications
    """
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        # Parse query parameters
        status = request.args.get('status')
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        service = LoanService(db.session)
        
        # Customers can only see their own applications
        if user_role == 'CUSTOMER':
            applications = service.get_customer_applications(
                UUID(user_customer_id),
                status=status
            )
            total = len(applications)
            applications = applications[offset:offset+limit]
        else:
            # Admins can see all applications
            applications, total = service.list_applications(
                status=status,
                limit=limit,
                offset=offset
            )
        
        return jsonify({
            'data': [{
                'id': str(app.id),
                'customer_id': str(app.customer_id),
                'application_number': app.application_number,
                'requested_amount': str(app.requested_amount),
                'approved_amount': str(app.approved_amount) if app.approved_amount else None,
                'status': app.status,
                'applied_at': app.applied_at.isoformat(),
                'purpose': app.purpose
            } for app in applications],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@loans_bp.route('/<application_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_loan_application(application_id: str):
    """
    Cancel a loan application.
    
    Returns:
        200: Application cancelled
        403: Not authorized
        404: Application not found
        422: Cannot cancel application in current status
    """
    try:
        service = LoanService(db.session)
        application = service.get_application(UUID(application_id))
        
        # Check authorization
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(application.customer_id):
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to cancel this application'
                }
            }), 403
        
        # Cancel application
        application = service.cancel_application(UUID(application_id))
        
        return jsonify({
            'id': str(application.id),
            'status': application.status,
            'message': 'Application cancelled successfully'
        }), 200
        
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except BusinessRuleViolationError as e:
        return jsonify({'error': {'code': 'BUSINESS_RULE_VIOLATION', 'message': str(e)}}), 422
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500

