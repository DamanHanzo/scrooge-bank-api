"""
Bank API - Customer Routes

REST API endpoints for customer management.
All schemas imported from centralized registry.
"""

from flask_smorest import Blueprint
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError as PydanticValidationError

from app.models import db
from app.services.customer_service import CustomerService
from app.schemas.customer import CustomerCreateRequest, CustomerUpdateRequest
from app.exceptions import NotFoundError, ValidationError

# Import all schemas from centralized registry
from app.api.schemas import (
    CustomerCreateSchema,
    CustomerUpdateSchema,
    CustomerResponseSchema,
    AccountListSchema
)

# ============================================================================
# Blueprint
# ============================================================================

customers_bp = Blueprint(
    'customers',
    __name__,
    url_prefix='/v1/customers',
    description='Customer management operations'
)

# ============================================================================
# Routes
# ============================================================================

@customers_bp.route('', methods=['POST'])
@customers_bp.arguments(CustomerCreateSchema, description="Customer details")
@customers_bp.response(201, CustomerResponseSchema, description="Customer created successfully")
@customers_bp.alt_response(400, description="Validation error")
@customers_bp.alt_response(403, description="Admin access required")
@jwt_required()
def create_customer(args):
    """
    Create a new customer (Admin only).
    
    Only administrators can create customers directly.
    Regular users should use /auth/register.
    """
    try:
        claims = get_jwt()
        if claims.get('role') not in ['ADMIN', 'SUPER_ADMIN']:
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Admin access required'}}), 403
        
        data = CustomerCreateRequest(**args)
        service = CustomerService(db.session)
        customer = service.create_customer(data)
        
        return {
            'id': str(customer.id),
            'email': customer.email,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'status': customer.status
        }, 201
    except (PydanticValidationError, ValidationError) as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@customers_bp.route('/<uuid:customer_id>', methods=['GET'])
@customers_bp.response(200, CustomerResponseSchema, description="Customer details")
@customers_bp.alt_response(403, description="Not authorized")
@customers_bp.alt_response(404, description="Customer not found")
@jwt_required()
def get_customer(customer_id):
    """
    Get customer by ID.
    
    Customers can only view their own profile.
    Administrators can view any customer.
    """
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        service = CustomerService(db.session)
        customer = service.get_customer(customer_id)
        
        return {
            'id': str(customer.id),
            'email': customer.email,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'status': customer.status
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@customers_bp.route('/<uuid:customer_id>', methods=['PATCH'])
@customers_bp.arguments(CustomerUpdateSchema, description="Customer update data")
@customers_bp.response(200, CustomerResponseSchema, description="Customer updated successfully")
@customers_bp.alt_response(403, description="Not authorized")
@customers_bp.alt_response(404, description="Customer not found")
@jwt_required()
def update_customer(args, customer_id):
    """
    Update customer information.
    
    Customers can only update their own profile.
    Administrators can update any customer.
    """
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        data = CustomerUpdateRequest(**args)
        service = CustomerService(db.session)
        customer = service.update_customer(customer_id, data)
        
        return {
            'id': str(customer.id),
            'email': customer.email,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'status': customer.status
        }
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@customers_bp.route('/<uuid:customer_id>/accounts', methods=['GET'])
@customers_bp.response(200, AccountListSchema, description="List of customer accounts")
@customers_bp.alt_response(403, description="Not authorized")
@jwt_required()
def get_customer_accounts(customer_id):
    """
    Get all accounts for a customer.
    
    Customers can only view their own accounts.
    Administrators can view any customer's accounts.
    """
    try:
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        if user_role == 'CUSTOMER' and str(user_customer_id) != str(customer_id):
            return jsonify({'error': {'code': 'FORBIDDEN', 'message': 'Not authorized'}}), 403
        
        from app.services.account_service import AccountService
        service = AccountService(db.session)
        accounts = service.get_customer_accounts(customer_id)
        
        return {
            'data': [{
                'id': str(account.id),
                'account_type': account.account_type,
                'account_number': account.account_number,
                'status': account.status,
                'balance': str(account.balance)
            } for account in accounts]
        }
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500
