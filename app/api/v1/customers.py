"""
Bank API - Customer Routes

REST API endpoints for customer management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from pydantic import ValidationError as PydanticValidationError
from uuid import UUID

from app.models import db
from app.services.customer_service import CustomerService
from app.schemas.customer import CustomerCreateRequest, CustomerUpdateRequest
from app.exceptions import NotFoundError, ValidationError

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('', methods=['POST'])
@jwt_required()
def create_customer():
    """
    Create a new customer.
    
    Returns:
        201: Customer created successfully
        400: Validation error
        403: Not authorized
    """
    try:
        # Check if user is admin (customers created via registration)
        claims = get_jwt()
        if claims.get('role') not in ['ADMIN', 'SUPER_ADMIN']:
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Only admins can create customers directly'
                }
            }), 403
        
        # Parse and validate request
        data = CustomerCreateRequest(**request.json)
        
        # Create customer
        service = CustomerService(db.session)
        customer = service.create_customer(data)
        
        return jsonify({
            'id': str(customer.id),
            'email': customer.email,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'date_of_birth': customer.date_of_birth.isoformat(),
            'phone': customer.phone,
            'address_line_1': customer.address_line_1,
            'address_line_2': customer.address_line_2,
            'city': customer.city,
            'state': customer.state,
            'zip_code': customer.zip_code,
            'status': customer.status,
            'created_at': customer.created_at.isoformat(),
            'updated_at': customer.updated_at.isoformat()
        }), 201
        
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@customers_bp.route('/<customer_id>', methods=['GET'])
@jwt_required()
def get_customer(customer_id: str):
    """
    Get customer by ID.
    
    Returns:
        200: Customer details
        403: Not authorized
        404: Customer not found
    """
    try:
        # Check authorization
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        # Customers can only view their own profile
        if user_role == 'CUSTOMER' and str(user_customer_id) != customer_id:
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to view this customer'
                }
            }), 403
        
        # Get customer
        service = CustomerService(db.session)
        customer = service.get_customer(UUID(customer_id))
        
        return jsonify({
            'id': str(customer.id),
            'email': customer.email,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'date_of_birth': customer.date_of_birth.isoformat(),
            'phone': customer.phone,
            'address_line_1': customer.address_line_1,
            'address_line_2': customer.address_line_2,
            'city': customer.city,
            'state': customer.state,
            'zip_code': customer.zip_code,
            'status': customer.status,
            'created_at': customer.created_at.isoformat(),
            'updated_at': customer.updated_at.isoformat()
        }), 200
        
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@customers_bp.route('/<customer_id>', methods=['PATCH'])
@jwt_required()
def update_customer(customer_id: str):
    """
    Update customer information.
    
    Returns:
        200: Customer updated successfully
        400: Validation error
        403: Not authorized
        404: Customer not found
    """
    try:
        # Check authorization
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        # Customers can only update their own profile
        if user_role == 'CUSTOMER' and str(user_customer_id) != customer_id:
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to update this customer'
                }
            }), 403
        
        # Parse and validate request
        data = CustomerUpdateRequest(**request.json)
        
        # Update customer
        service = CustomerService(db.session)
        customer = service.update_customer(UUID(customer_id), data)
        
        return jsonify({
            'id': str(customer.id),
            'email': customer.email,
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'date_of_birth': customer.date_of_birth.isoformat(),
            'phone': customer.phone,
            'address_line_1': customer.address_line_1,
            'address_line_2': customer.address_line_2,
            'city': customer.city,
            'state': customer.state,
            'zip_code': customer.zip_code,
            'status': customer.status,
            'created_at': customer.created_at.isoformat(),
            'updated_at': customer.updated_at.isoformat()
        }), 200
        
    except PydanticValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except ValidationError as e:
        return jsonify({'error': {'code': 'VALIDATION_ERROR', 'message': str(e)}}), 400
    except NotFoundError as e:
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': str(e)}}), 404
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500


@customers_bp.route('/<customer_id>/accounts', methods=['GET'])
@jwt_required()
def get_customer_accounts(customer_id: str):
    """
    Get all accounts for a customer.
    
    Returns:
        200: List of accounts
        403: Not authorized
    """
    try:
        # Check authorization
        claims = get_jwt()
        user_role = claims.get('role')
        user_customer_id = claims.get('customer_id')
        
        # Customers can only view their own accounts
        if user_role == 'CUSTOMER' and str(user_customer_id) != customer_id:
            return jsonify({
                'error': {
                    'code': 'FORBIDDEN',
                    'message': 'Not authorized to view these accounts'
                }
            }), 403
        
        # Get accounts
        from app.services.account_service import AccountService
        service = AccountService(db.session)
        accounts = service.get_customer_accounts(UUID(customer_id))
        
        return jsonify({
            'data': [{
                'id': str(account.id),
                'customer_id': str(account.customer_id),
                'account_type': account.account_type,
                'account_number': account.account_number,
                'status': account.status,
                'balance': str(account.balance),
                'currency': account.currency,
                'created_at': account.created_at.isoformat(),
                'updated_at': account.updated_at.isoformat()
            } for account in accounts]
        }), 200
        
    except Exception as e:
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': str(e)}}), 500

