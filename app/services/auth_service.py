"""
Bank API - Authentication Service

Business logic for user authentication and authorization.
"""

from typing import Optional, Dict
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import create_access_token, create_refresh_token

from app.models import User, Customer
from app.schemas.auth import LoginRequest, RegisterRequest
from app.exceptions import (
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError
)


class AuthService:
    """Service class for authentication and authorization logic."""
    
    def __init__(self, db: Session):
        """
        Initialize AuthService.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def register_customer(
        self,
        registration_data: RegisterRequest
    ) -> Dict[str, any]:
        """
        Register a new customer user.
        
        Args:
            registration_data: Registration data
            
        Returns:
            Dictionary with user and tokens
            
        Raises:
            ValidationError: If email already exists or validation fails
        """
        # Check if email already exists
        existing_user = self.db.query(User).filter(
            User.email == registration_data.email
        ).first()
        
        if existing_user:
            raise ValidationError(f"User with email {registration_data.email} already exists")
        
        # Create customer first
        customer = Customer(
            email=registration_data.email,
            first_name=registration_data.first_name,
            last_name=registration_data.last_name,
            date_of_birth=datetime.utcnow().date(),  # Placeholder - should be from registration
            status='ACTIVE'
        )
        
        try:
            self.db.add(customer)
            self.db.flush()  # Flush to get customer ID
            
            # Create user
            user = User(
                email=registration_data.email,
                role='CUSTOMER',
                is_active=True,
                customer_id=customer.id
            )
            user.set_password(registration_data.password)
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            # Generate tokens
            access_token = self._create_access_token(user)
            refresh_token = self._create_refresh_token(user)
            
            return {
                'user': user,
                'access_token': access_token,
                'refresh_token': refresh_token
            }
            
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error registering user: {str(e)}")
    
    def login(self, login_data: LoginRequest) -> Dict[str, any]:
        """
        Authenticate user and generate tokens.
        
        Args:
            login_data: Login credentials
            
        Returns:
            Dictionary with user and tokens
            
        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Find user by email
        user = self.db.query(User).filter(
            User.email == login_data.email
        ).first()
        
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        # Check password
        if not user.check_password(login_data.password):
            raise AuthenticationError("Invalid email or password")
        
        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("User account is inactive")
        
        # Generate tokens
        access_token = self._create_access_token(user)
        refresh_token = self._create_refresh_token(user)
        
        return {
            'user': user,
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    
    def refresh_access_token(self, user_id: UUID) -> str:
        """
        Generate new access token using refresh token.
        
        Args:
            user_id: User UUID
            
        Returns:
            New access token
            
        Raises:
            NotFoundError: If user not found
            AuthenticationError: If user is inactive
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        if not user.is_active:
            raise AuthenticationError("User account is inactive")
        
        return self._create_access_token(user)
    
    def get_user(self, user_id: UUID) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            User instance
            
        Raises:
            NotFoundError: If user not found
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        
        return user
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: User email
            
        Returns:
            User instance or None
        """
        return self.db.query(User).filter(User.email == email).first()
    
    def change_password(
        self,
        user_id: UUID,
        current_password: str,
        new_password: str
    ) -> User:
        """
        Change user password.
        
        Args:
            user_id: User UUID
            current_password: Current password
            new_password: New password
            
        Returns:
            Updated user
            
        Raises:
            NotFoundError: If user not found
            AuthenticationError: If current password is incorrect
        """
        user = self.get_user(user_id)
        
        # Verify current password
        if not user.check_password(current_password):
            raise AuthenticationError("Current password is incorrect")
        
        # Set new password
        user.set_password(new_password)
        
        try:
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error changing password: {str(e)}")
    
    def create_admin_user(
        self,
        email: str,
        password: str,
        role: str = 'ADMIN'
    ) -> User:
        """
        Create an admin user (super admin operation).
        
        Args:
            email: Admin email
            password: Admin password
            role: Admin role (ADMIN or SUPER_ADMIN)
            
        Returns:
            Created user
            
        Raises:
            ValidationError: If email already exists or role is invalid
        """
        # Check if email already exists
        existing_user = self.get_user_by_email(email)
        if existing_user:
            raise ValidationError(f"User with email {email} already exists")
        
        # Validate role
        if role not in ('ADMIN', 'SUPER_ADMIN'):
            raise ValidationError("Invalid role. Must be ADMIN or SUPER_ADMIN")
        
        # Create admin user (no customer link)
        user = User(
            email=email,
            role=role,
            is_active=True,
            customer_id=None
        )
        user.set_password(password)
        
        try:
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user
        except IntegrityError as e:
            self.db.rollback()
            raise ValidationError(f"Error creating admin user: {str(e)}")
    
    def deactivate_user(self, user_id: UUID) -> User:
        """
        Deactivate a user account (admin operation).
        
        Args:
            user_id: User UUID
            
        Returns:
            Updated user
        """
        user = self.get_user(user_id)
        user.is_active = False
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def activate_user(self, user_id: UUID) -> User:
        """
        Activate a user account (admin operation).
        
        Args:
            user_id: User UUID
            
        Returns:
            Updated user
        """
        user = self.get_user(user_id)
        user.is_active = True
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    @staticmethod
    def verify_permission(user: User, required_roles: list) -> None:
        """
        Verify user has required role.
        
        Args:
            user: User instance
            required_roles: List of allowed roles
            
        Raises:
            AuthorizationError: If user doesn't have required role
        """
        if user.role not in required_roles:
            raise AuthorizationError(
                f"This operation requires one of: {', '.join(required_roles)}"
            )
    
    @staticmethod
    def _create_access_token(user: User) -> str:
        """
        Create JWT access token.
        
        Args:
            user: User instance
            
        Returns:
            JWT access token
        """
        additional_claims = {
            'role': user.role,
            'email': user.email,
            'customer_id': str(user.customer_id) if user.customer_id else None
        }
        
        return create_access_token(
            identity=str(user.id),
            additional_claims=additional_claims
        )
    
    @staticmethod
    def _create_refresh_token(user: User) -> str:
        """
        Create JWT refresh token.
        
        Args:
            user: User instance
            
        Returns:
            JWT refresh token
        """
        return create_refresh_token(identity=str(user.id))

