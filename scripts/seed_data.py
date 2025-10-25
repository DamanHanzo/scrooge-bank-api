"""
Bank API - Database Seeding Script

Seed database with sample data for development and testing.
"""

from datetime import date, datetime
from decimal import Decimal

from app import create_app
from app.models import db, Customer, Account, Transaction, User, LoanApplication


def seed_database():
    """Seed the database with sample data."""
    app = create_app()
    
    with app.app_context():
        print("🌱 Seeding database...")
        
        # Clear existing data (be careful with this in production!)
        print("  Clearing existing data...")
        db.drop_all()
        db.create_all()
        
        # Create admin user
        print("  Creating admin user...")
        admin_user = User(
            email='admin@bank-api.local',
            role='ADMIN',
            is_active=True
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        
        # Create super admin user
        super_admin = User(
            email='superadmin@bank-api.local',
            role='SUPER_ADMIN',
            is_active=True
        )
        super_admin.set_password('superadmin123')
        db.session.add(super_admin)
        
        # Create sample customer 1
        print("  Creating sample customers...")
        customer1 = Customer(
            email='john.doe@example.com',
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 5, 15),
            phone='+1-555-0123',
            address_line_1='123 Main St',
            address_line_2='Apt 4B',
            city='San Francisco',
            state='CA',
            zip_code='94102',
            status='ACTIVE'
        )
        db.session.add(customer1)
        db.session.flush()  # Flush to get customer1.id
        
        # Create user for customer1
        user1 = User(
            email='john.doe@example.com',
            role='CUSTOMER',
            is_active=True,
            customer_id=customer1.id
        )
        user1.set_password('password123')
        db.session.add(user1)
        
        # Create sample customer 2
        customer2 = Customer(
            email='jane.smith@example.com',
            first_name='Jane',
            last_name='Smith',
            date_of_birth=date(1985, 8, 20),
            phone='+1-555-0456',
            address_line_1='456 Oak Ave',
            city='Los Angeles',
            state='CA',
            zip_code='90001',
            status='ACTIVE'
        )
        db.session.add(customer2)
        db.session.flush()
        
        # Create user for customer2
        user2 = User(
            email='jane.smith@example.com',
            role='CUSTOMER',
            is_active=True,
            customer_id=customer2.id
        )
        user2.set_password('password123')
        db.session.add(user2)
        
        # Create checking accounts
        print("  Creating sample accounts...")
        account1 = Account(
            customer_id=customer1.id,
            account_type='CHECKING',
            account_number='CHK-1234567890',
            status='ACTIVE',
            balance=Decimal('1500.00'),
            currency='USD'
        )
        db.session.add(account1)
        
        account2 = Account(
            customer_id=customer2.id,
            account_type='CHECKING',
            account_number='CHK-9876543210',
            status='ACTIVE',
            balance=Decimal('5000.00'),
            currency='USD'
        )
        db.session.add(account2)
        
        db.session.flush()
        
        # Create sample transactions for account1
        print("  Creating sample transactions...")
        transaction1 = Transaction(
            account_id=account1.id,
            transaction_type='DEPOSIT',
            amount=Decimal('1000.00'),
            currency='USD',
            balance_after=Decimal('1000.00'),
            description='Initial deposit',
            reference_number='TXN-20251025-000001',
            status='COMPLETED',
            processed_at=datetime.utcnow()
        )
        db.session.add(transaction1)
        
        transaction2 = Transaction(
            account_id=account1.id,
            transaction_type='DEPOSIT',
            amount=Decimal('500.00'),
            currency='USD',
            balance_after=Decimal('1500.00'),
            description='Paycheck deposit',
            reference_number='TXN-20251025-000002',
            status='COMPLETED',
            processed_at=datetime.utcnow()
        )
        db.session.add(transaction2)
        
        # Create sample transactions for account2
        transaction3 = Transaction(
            account_id=account2.id,
            transaction_type='DEPOSIT',
            amount=Decimal('5000.00'),
            currency='USD',
            balance_after=Decimal('5000.00'),
            description='Initial deposit',
            reference_number='TXN-20251025-000003',
            status='COMPLETED',
            processed_at=datetime.utcnow()
        )
        db.session.add(transaction3)
        
        # Create sample loan application
        print("  Creating sample loan application...")
        loan_app = LoanApplication(
            customer_id=customer2.id,
            application_number='LOAN-20251025-000001',
            requested_amount=Decimal('25000.00'),
            purpose='Home renovation',
            term_months=36,
            employment_status='FULL_TIME',
            annual_income=Decimal('75000.00'),
            status='PENDING',
            applied_at=datetime.utcnow(),
            external_account_number='9876543210',
            external_routing_number='121000248'
        )
        db.session.add(loan_app)
        
        # Commit all changes
        db.session.commit()
        
        print("✅ Database seeded successfully!")
        print("\n📋 Sample credentials:")
        print("  Super Admin: superadmin@bank-api.local / superadmin123")
        print("  Admin:       admin@bank-api.local / admin123")
        print("  Customer 1:  john.doe@example.com / password123")
        print("  Customer 2:  jane.smith@example.com / password123")
        print("\n💰 Sample accounts:")
        print(f"  John's Account: {account1.account_number} (Balance: ${account1.balance})")
        print(f"  Jane's Account: {account2.account_number} (Balance: ${account2.balance})")


if __name__ == '__main__':
    seed_database()

