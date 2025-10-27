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
from app.services.account_service import AccountService
from app.services.loan_service import LoanService
from app.services.bank_service import BankService
from app.schemas.loan import LoanReviewRequest
from app.exceptions import NotFoundError, BusinessRuleViolationError, AuthorizationError

# Import all schemas from centralized registry
from app.api.schemas import (
    LoanReviewSchema,
    CustomerListSchema,
    CustomerFilterSchema,
    ReasonSchema,
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


@admin_bp.route("/customers/<uuid:customer_id>/suspend", methods=["POST"])
@admin_bp.arguments(ReasonSchema, description="Optional suspension reason")
@admin_bp.response(200, AdminActionResponseSchema, description="Customer suspended")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.alt_response(404, description="Customer not found")
@jwt_required()
def suspend_customer(args, customer_id):
    """
    Suspend a customer account (Admin only).

    Suspends a customer account, preventing access to the system.
    Only accessible by administrators.
    """
    try:
        require_admin()

        service = CustomerService(db.session)
        customer = service.suspend_customer(customer_id, args.get("reason", "No reason provided"))

        return {
            "message": "Customer suspended successfully",
            "id": str(customer.id),
            "status": customer.status,
        }
    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except NotFoundError as e:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(e)}}), 404
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@admin_bp.route("/customers/<uuid:customer_id>/activate", methods=["POST"])
@admin_bp.response(200, AdminActionResponseSchema, description="Customer activated")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.alt_response(404, description="Customer not found")
@jwt_required()
def activate_customer(customer_id):
    """
    Activate a customer account (Admin only).

    Activates a suspended or inactive customer account.
    Only accessible by administrators.
    """
    try:
        require_admin()

        service = CustomerService(db.session)
        customer = service.activate_customer(customer_id)

        return {
            "message": "Customer activated successfully",
            "id": str(customer.id),
            "status": customer.status,
        }
    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except NotFoundError as e:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(e)}}), 404
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@admin_bp.route("/accounts/<uuid:account_id>/freeze", methods=["POST"])
@admin_bp.arguments(ReasonSchema, description="Optional freeze reason")
@admin_bp.response(200, AdminActionResponseSchema, description="Account frozen")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.alt_response(404, description="Account not found")
@jwt_required()
def freeze_account(args, account_id):
    """
    Freeze an account (Admin only).

    Freezes an account to prevent transactions.
    Only accessible by administrators.
    """
    try:
        require_admin()

        service = AccountService(db.session)
        account = service.freeze_account(account_id, args.get("reason", "No reason provided"))

        return {
            "message": "Account frozen successfully",
            "id": str(account.id),
            "status": account.status,
        }
    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except NotFoundError as e:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(e)}}), 404
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@admin_bp.route("/accounts/<uuid:account_id>/unfreeze", methods=["POST"])
@admin_bp.response(200, AdminActionResponseSchema, description="Account unfrozen")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.alt_response(404, description="Account not found")
@jwt_required()
def unfreeze_account(account_id):
    """
    Unfreeze an account (Admin only).

    Unfreezes a previously frozen account.
    Only accessible by administrators.
    """
    try:
        require_admin()

        service = AccountService(db.session)
        account = service.unfreeze_account(account_id)

        return {
            "message": "Account unfrozen successfully",
            "id": str(account.id),
            "status": account.status,
        }
    except AuthorizationError as e:
        return jsonify({"error": {"code": "FORBIDDEN", "message": str(e)}}), 403
    except NotFoundError as e:
        return jsonify({"error": {"code": "NOT_FOUND", "message": str(e)}}), 404
    except Exception as e:
        return jsonify({"error": {"code": "INTERNAL_ERROR", "message": str(e)}}), 500


@admin_bp.route("/loan-applications/<uuid:application_id>/review", methods=["POST"])
@admin_bp.arguments(LoanReviewSchema, description="Loan review decision")
@admin_bp.response(200, AdminActionResponseSchema, description="Loan application reviewed")
@admin_bp.alt_response(403, description="Admin access required")
@admin_bp.alt_response(404, description="Loan application not found")
@admin_bp.alt_response(422, description="Application not in pending status")
@jwt_required()
def review_loan_application(args, application_id):
    """
    Review a loan application (Admin only).

    Approve or reject a pending loan application.
    Only accessible by administrators.
    """
    try:
        require_admin()

        data = LoanReviewRequest(**args)
        service = LoanService(db.session)
        application = service.review_application(application_id, data)

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


# ============================================================================
# Bank Financial Status (Bank Operator Requirements)
# ============================================================================


@admin_bp.route("/bank/financial-status", methods=["GET"])
@admin_bp.response(200, BankFinancialStatusSchema)
@admin_bp.doc(
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
