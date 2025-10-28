"""
Bank API - Admin Routes

REST API endpoints for administrative operations.
All schemas imported from centralized registry.
"""

from flask_smorest import Blueprint
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt

from app.models import db
from app.services.customer_service import CustomerService
from app.services.loan_service import LoanService
from app.services.bank_service import BankService
from app.schemas.loan import LoanReviewRequest, LoanApplicationStatusUpdateRequest, LoanDisbursementRequest
from app.schemas.customer import CustomerStatusUpdateRequest
from app.exceptions import NotFoundError, BusinessRuleViolationError, AuthorizationError

# Import all schemas from centralized registry
from app.api.schemas import (
    LoanApplicationStatusUpdateSchema,
    LoanDisbursementSchema,
    CustomerListSchema,
    CustomerFilterSchema,
    CustomerStatusUpdateSchema,
    CustomerResponseSchema,
    AdminActionResponseSchema,
    BankFinancialStatusSchema,
)

# ============================================================================
# Blueprint
# ============================================================================

admin_bp = Blueprint(
    "admin", __name__, url_prefix="/v1/admin", description="Administrative operations"
)

# ============================================================================
# Helper Functions
# ============================================================================


def require_admin():
    """Check if user has admin role."""
    claims = get_jwt()
    user_role = claims.get("role")
    if user_role not in ["ADMIN", "SUPER_ADMIN"]:
        raise AuthorizationError("Admin access required")


# ============================================================================
# Routes
# ============================================================================


@admin_bp.route("/customers", methods=["GET"])
@admin_bp.arguments(CustomerFilterSchema, location="query", description="Filter parameters")
@admin_bp.response(200, CustomerListSchema, description="List of customers")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.doc(operationId="listAllCustomers")
@jwt_required()
def list_all_customers(query_args):
    """
    List all customers (Admin only).

    Retrieves a list of all customers with optional filtering by status.
    Only accessible by administrators.
    """
    try:
        require_admin()

        service = CustomerService(db.session)
        customers, total = service.list_customers(
            status=query_args.get("status"),
            limit=query_args.get("limit", 50),
            offset=query_args.get("offset", 0),
        )

        return {
            "data": [
                {
                    "id": str(c.id),
                    "email": c.email,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "status": c.status,
                    "created_at": c.created_at.isoformat(),
                }
                for c in customers
            ],
            "pagination": {
                "total": total,
                "limit": query_args.get("limit", 50),
                "offset": query_args.get("offset", 0),
            },
        }
    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@admin_bp.route("/customers/<uuid:customer_id>", methods=["PATCH"])
@admin_bp.arguments(CustomerStatusUpdateSchema, description="Customer status update")
@admin_bp.response(200, CustomerResponseSchema, description="Customer status updated")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.alt_response(404, description="Customer not found")
@admin_bp.doc(operationId="updateCustomerStatus")
@jwt_required()
def update_customer_status(args, customer_id):
    """
    Update customer status (Admin only).

    Updates a customer's status (ACTIVE or SUSPENDED) using PATCH.
    Only accessible by administrators.
    """
    try:
        require_admin()

        data = CustomerStatusUpdateRequest(**args)
        service = CustomerService(db.session)

        if data.status == 'SUSPENDED':
            customer = service.suspend_customer(customer_id, data.reason or "No reason provided")
        else:  # ACTIVE
            customer = service.activate_customer(customer_id)

        return {
            "id": str(customer.id),
            "email": customer.email,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "date_of_birth": customer.date_of_birth.isoformat(),
            "phone": customer.phone,
            "address_line_1": customer.address_line_1,
            "address_line_2": customer.address_line_2,
            "city": customer.city,
            "state": customer.state,
            "zip_code": customer.zip_code,
            "status": customer.status,
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
        }
    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except NotFoundError as e:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(e)}}), 404
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@admin_bp.route("/loan-applications/<uuid:application_id>", methods=["PATCH"])
@admin_bp.arguments(LoanApplicationStatusUpdateSchema, description="Loan application status update")
@admin_bp.response(200, AdminActionResponseSchema, description="Loan application updated")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.alt_response(404, description="Loan application not found")
@admin_bp.alt_response(422, description="Business rule violation")
@admin_bp.doc(operationId="reviewLoanApplication")
@jwt_required()
def update_loan_application_status_admin(args, application_id):
    """
    Update loan application status (Admin only).

    Admins can approve or reject pending loan applications.
    Only accessible by administrators.
    """
    try:
        require_admin()

        data = LoanApplicationStatusUpdateRequest(**args)
        service = LoanService(db.session)

        # Admins can only approve or reject
        if data.status == 'CANCELLED':
            return jsonify({"error": {"code": "FORBIDDEN", "message": "Admins cannot cancel applications"}}), 403

        # Use existing review_application method
        review_data = LoanReviewRequest(
            status=data.status,
            approved_amount=data.approved_amount,
            interest_rate=data.interest_rate,
            term_months=data.term_months,
            rejection_reason=data.rejection_reason
        )
        application = service.review_application(application_id, review_data)

        return {
            "message": f"Loan application {data.status.lower()}",
            "id": str(application.id),
            "status": application.status,
        }
    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except NotFoundError as e:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(e)}}), 404
    except BusinessRuleViolationError as e:
        return jsonify({"error": {"code": "BUSINESS_RULE_VIOLATION", "message": str(e)}}), 422
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@admin_bp.route("/loan-applications/<uuid:application_id>/disburse", methods=["POST"])
@admin_bp.arguments(LoanDisbursementSchema, description="Disbursement confirmation")
@admin_bp.response(200, AdminActionResponseSchema, description="Loan disbursed successfully")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.alt_response(404, description="Loan application not found")
@admin_bp.alt_response(422, description="Business rule violation")
@admin_bp.doc(operationId="disburseLoan")
@jwt_required()
def disburse_loan_application(args, application_id):
    """
    Disburse an approved loan (Admin only).

    Creates loan account and transfers funds to customer's external account.
    Re-validates bank funds and customer eligibility at disbursement time.
    """
    try:
        require_admin()

        data = LoanDisbursementRequest(**args)
        service = LoanService(db.session)

        application = service.disburse_loan(application_id, data)

        return {
            "message": "Loan disbursed successfully",
            "id": str(application.id),
            "status": application.status,
        }
    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except NotFoundError as e:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(e)}}), 404
    except BusinessRuleViolationError as e:
        return jsonify({"error": {"code": "BUSINESS_RULE_VIOLATION", "message": str(e)}}), 422
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


# ============================================================================
# Bank Financial Status (Bank Operator Requirements)
# ============================================================================


@admin_bp.route("/bank/financial-status", methods=["GET"])
@admin_bp.response(200, BankFinancialStatusSchema)
@admin_bp.doc(
    operationId="getBankFinancialStatus",
    description="Get comprehensive bank financial status including cash position and account breakdown"
)
@jwt_required()
def get_bank_financial_status():
    """
    Get bank financial status.

    Returns comprehensive financial metrics including:
    - Total customer deposits (active checking accounts)
    - Total loans outstanding (active loan accounts)
    - Net cash position (can be negative if bank in debt)
    - Whether bank is in debt
    - Account breakdown by type
    - Timestamp of calculation

    **Admin only**: Requires ADMIN or SUPER_ADMIN role.

    Returns:
        dict: Complete bank financial status

    Raises:
        403: If user is not an admin
        500: If internal error occurs
    """
    try:
        # Check admin authorization
        require_admin()

        # Get financial status from service
        service = BankService(db.session)
        status = service.get_bank_financial_status()

        return status

    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500
