"""
Bank API - Utility Functions

Common utility functions used across the application.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID


def serialize_for_json(obj: Any) -> Any:
    """
    Serialize Python objects to JSON-compatible types.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON-serializable representation
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: serialize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    return obj


def mask_account_number(account_number: str, visible_digits: int = 4) -> str:
    """
    Mask an account number, showing only the last few digits.
    
    Args:
        account_number: Full account number
        visible_digits: Number of digits to show at the end
        
    Returns:
        Masked account number (e.g., "***1234")
    """
    if not account_number or len(account_number) <= visible_digits:
        return account_number
    
    return f"***{account_number[-visible_digits:]}"


def format_currency(amount: Decimal, currency: str = "USD") -> str:
    """
    Format a decimal amount as currency.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
    }
    
    symbol = currency_symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def validate_uuid(uuid_string: str) -> bool:
    """
    Validate if a string is a valid UUID.
    
    Args:
        uuid_string: String to validate
        
    Returns:
        True if valid UUID, False otherwise
    """
    try:
        UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


def calculate_age(date_of_birth: date) -> int:
    """
    Calculate age from date of birth.
    
    Args:
        date_of_birth: Date of birth
        
    Returns:
        Age in years
    """
    today = date.today()
    age = today.year - date_of_birth.year
    
    # Adjust if birthday hasn't occurred yet this year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    
    return age


def paginate_query(query_result: list, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """
    Paginate a query result.
    
    Args:
        query_result: List of results
        limit: Number of items per page
        offset: Offset from start
        
    Returns:
        Dictionary with data and pagination metadata
    """
    total = len(query_result)
    paginated_data = query_result[offset:offset + limit]
    
    return {
        'data': paginated_data,
        'pagination': {
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': (offset + limit) < total
        }
    }


def generate_reference_number(prefix: str, timestamp: datetime = None) -> str:
    """
    Generate a reference number with prefix and timestamp.
    
    Args:
        prefix: Prefix for the reference number
        timestamp: Optional timestamp (default: now)
        
    Returns:
        Reference number string
    """
    import random
    import string
    
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    date_str = timestamp.strftime('%Y%m%d')
    random_suffix = ''.join(random.choices(string.digits, k=6))
    
    return f"{prefix}-{date_str}-{random_suffix}"


def safe_decimal(value: Any, default: Decimal = Decimal('0.00')) -> Decimal:
    """
    Safely convert a value to Decimal.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Decimal value
    """
    try:
        if value is None:
            return default
        return Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError):
        return default

