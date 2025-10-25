"""
Schema Bridge - Pydantic to Marshmallow Converter

Automatically converts Pydantic models to Marshmallow schemas for Flask-SMOREST.
This enables automatic OpenAPI documentation generation from Pydantic schemas.
"""

from typing import Type, Dict, Any, get_type_hints, get_origin, get_args
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from enum import Enum

from marshmallow import Schema, fields, validate
from pydantic import BaseModel


class PydanticToMarshmallow:
    """Convert Pydantic models to Marshmallow schemas."""
    
    # Type mapping from Python/Pydantic types to Marshmallow fields
    TYPE_MAPPING = {
        str: fields.String,
        int: fields.Integer,
        float: fields.Float,
        bool: fields.Boolean,
        datetime: fields.DateTime,
        date: fields.Date,
        Decimal: fields.Decimal,
        UUID: fields.UUID,
        dict: fields.Dict,
        list: fields.List,
    }
    
    @classmethod
    def convert(cls, pydantic_model: Type[BaseModel], name: str = None) -> Type[Schema]:
        """
        Convert a Pydantic model to a Marshmallow schema.
        
        Args:
            pydantic_model: The Pydantic model class to convert
            name: Optional name for the Marshmallow schema (defaults to model name + 'Schema')
            
        Returns:
            A Marshmallow Schema class
            
        Example:
            ```python
            from app.schemas.auth import LoginRequest
            LoginSchema = PydanticToMarshmallow.convert(LoginRequest)
            ```
        """
        if name is None:
            name = f"{pydantic_model.__name__}Schema"
        
        # Get field definitions from Pydantic model
        ma_fields = {}
        
        # Get type hints
        type_hints = get_type_hints(pydantic_model)
        
        # Get Pydantic model fields
        for field_name, field_info in pydantic_model.model_fields.items():
            field_type = type_hints.get(field_name)
            
            # Convert to Marshmallow field
            ma_field = cls._convert_field(field_name, field_type, field_info)
            if ma_field:
                ma_fields[field_name] = ma_field
        
        # Create Marshmallow schema class dynamically
        schema_class = type(name, (Schema,), ma_fields)
        
        return schema_class
    
    @classmethod
    def _convert_field(cls, field_name: str, field_type: Any, field_info: Any) -> fields.Field:
        """Convert a single Pydantic field to Marshmallow field."""
        
        # Handle Optional types
        is_optional = False
        origin = get_origin(field_type)
        
        if origin is type(None):
            return None
            
        # Check for Optional/Union types
        if origin is Union:
            args = get_args(field_type)
            # Filter out NoneType
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                field_type = non_none_args[0]
                is_optional = True
                origin = get_origin(field_type)
        
        # Handle List types
        if origin is list:
            args = get_args(field_type)
            if args:
                inner_type = args[0]
                inner_field_class = cls.TYPE_MAPPING.get(inner_type, fields.Field)
                return fields.List(inner_field_class(), allow_none=is_optional)
        
        # Get base field class
        field_class = cls.TYPE_MAPPING.get(field_type, fields.String)
        
        # Build field kwargs
        kwargs = {
            'allow_none': is_optional or not field_info.is_required(),
            'required': field_info.is_required() and not is_optional,
        }
        
        # Add metadata from Pydantic field
        if hasattr(field_info, 'description') and field_info.description:
            kwargs['metadata'] = {'description': field_info.description}
        
        # Add validation from Pydantic constraints
        # Note: Convert Decimal to float for JSON serialization compatibility
        if hasattr(field_info, 'metadata'):
            for constraint in field_info.metadata:
                if hasattr(constraint, 'gt'):
                    # Convert Decimal to float for JSON serialization
                    min_val = float(constraint.gt) if isinstance(constraint.gt, Decimal) else constraint.gt
                    kwargs['validate'] = validate.Range(min=min_val, min_inclusive=False)
                elif hasattr(constraint, 'ge'):
                    min_val = float(constraint.ge) if isinstance(constraint.ge, Decimal) else constraint.ge
                    kwargs['validate'] = validate.Range(min=min_val)
                elif hasattr(constraint, 'lt'):
                    max_val = float(constraint.lt) if isinstance(constraint.lt, Decimal) else constraint.lt
                    if 'validate' in kwargs:
                        kwargs['validate'].max = max_val
                    else:
                        kwargs['validate'] = validate.Range(max=max_val, max_inclusive=False)
                elif hasattr(constraint, 'le'):
                    max_val = float(constraint.le) if isinstance(constraint.le, Decimal) else constraint.le
                    if 'validate' in kwargs:
                        kwargs['validate'].max = max_val
                    else:
                        kwargs['validate'] = validate.Range(max=max_val)
                elif hasattr(constraint, 'min_length'):
                    kwargs['validate'] = validate.Length(min=constraint.min_length)
                elif hasattr(constraint, 'max_length'):
                    if 'validate' in kwargs:
                        kwargs['validate'].max = constraint.max_length
                    else:
                        kwargs['validate'] = validate.Length(max=constraint.max_length)
        
        # Add default value (only for non-required fields)
        if field_info.default is not None and field_info.default != ...:
            # Marshmallow doesn't allow load_default on required fields
            if not kwargs.get('required', False):
                # Convert Decimal defaults to float for JSON serialization
                default_val = field_info.default
                if isinstance(default_val, Decimal):
                    default_val = float(default_val)
                kwargs['load_default'] = default_val
                kwargs['dump_default'] = default_val
        
        return field_class(**kwargs)


# Import Union for type checking
from typing import Union


def pydantic_to_marshmallow(pydantic_model: Type[BaseModel], name: str = None) -> Type[Schema]:
    """
    Convenience function to convert Pydantic model to Marshmallow schema.
    
    This is a shorthand for PydanticToMarshmallow.convert().
    
    Args:
        pydantic_model: The Pydantic model to convert
        name: Optional name for the schema
        
    Returns:
        Marshmallow Schema class
        
    Example:
        ```python
        from app.schemas.auth import LoginRequest
        from app.api.schema_bridge import pydantic_to_marshmallow
        
        LoginSchema = pydantic_to_marshmallow(LoginRequest)
        
        @auth_bp.route('/login', methods=['POST'])
        @auth_bp.arguments(LoginSchema)
        @auth_bp.response(200, TokenResponseSchema)
        def login(args):
            # args is already validated and parsed
            pass
        ```
    """
    return PydanticToMarshmallow.convert(pydantic_model, name)


def create_response_schema(name: str, properties: Dict[str, Type[fields.Field]]) -> Type[Schema]:
    """
    Create a simple Marshmallow schema for responses.
    
    Args:
        name: Schema name
        properties: Dictionary of field_name -> Marshmallow field type
        
    Returns:
        Marshmallow Schema class
        
    Example:
        ```python
        SuccessSchema = create_response_schema(
            'SuccessResponse',
            {
                'message': fields.String,
                'id': fields.UUID
            }
        )
        ```
    """
    schema_fields = {}
    for field_name, field_type in properties.items():
        if isinstance(field_type, type) and issubclass(field_type, fields.Field):
            schema_fields[field_name] = field_type()
        else:
            schema_fields[field_name] = field_type
    
    return type(name, (Schema,), schema_fields)


# Pre-defined common response schemas
class MessageResponseSchema(Schema):
    """Generic message response."""
    message = fields.String(required=True, metadata={'example': 'Operation successful'})


class ErrorResponseSchema(Schema):
    """Standard error response."""
    error = fields.Dict(
        required=True,
        metadata={
            'example': {
                'code': 'ERROR_CODE',
                'message': 'Error description'
            }
        }
    )


class PaginationSchema(Schema):
    """Pagination metadata."""
    total = fields.Integer(required=True, metadata={'example': 100})
    limit = fields.Integer(required=True, metadata={'example': 20})
    offset = fields.Integer(required=True, metadata={'example': 0})

