"""
E2E Test - Checking Account Happy Path

Tests customer journey with checking account:
Register → Login → Create Account → Deposit → Withdrawal → Transaction History
"""

from decimal import Decimal


def test_checking_account_happy_path(client):
    """Test complete checking account workflow."""

    # Step 1: Register
    register_data = {
        "email": "checking.user@example.com",
        "password": "Password123!",
        "password_confirm": "Password123!",
        "first_name": "Checking",
        "last_name": "User"
    }

    response = client.post('/v1/auth/register', json=register_data)
    assert response.status_code == 201
    assert 'access_token' in response.json

    # Step 2: Login
    login_data = {
        "email": "checking.user@example.com",
        "password": "Password123!"
    }

    response = client.post('/v1/auth/login', json=login_data)
    assert response.status_code == 200
    token = response.json['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    # Step 3: Create checking account
    account_data = {
        "account_type": "CHECKING",
        "initial_deposit": 0.0,
        "currency": "USD"
    }

    response = client.post('/v1/accounts', json=account_data, headers=headers)
    assert response.status_code == 201
    assert response.json['account_type'] == 'CHECKING'
    assert response.json['status'] == 'ACTIVE'
    account_id = response.json['id']

    # Step 4: Deposit
    deposit_data = {
        "type": "DEPOSIT",
        "amount": 5000.00,
        "currency": "USD",
        "description": "Initial deposit"
    }

    response = client.post(
        f'/v1/accounts/{account_id}/transactions',
        json=deposit_data,
        headers=headers
    )
    assert response.status_code == 201
    assert response.json['transaction_type'] == 'DEPOSIT'
    assert Decimal(response.json['amount']) == Decimal('5000.00')
    assert Decimal(response.json['balance_after']) == Decimal('5000.00')

    # Step 5: Withdraw
    withdrawal_data = {
        "type": "WITHDRAWAL",
        "amount": 1200.00,
        "currency": "USD",
        "description": "ATM withdrawal"
    }

    response = client.post(
        f'/v1/accounts/{account_id}/transactions',
        json=withdrawal_data,
        headers=headers
    )
    assert response.status_code == 201
    assert response.json['transaction_type'] == 'WITHDRAWAL'
    assert Decimal(response.json['amount']) == Decimal('1200.00')
    assert Decimal(response.json['balance_after']) == Decimal('3800.00')

    # Step 6: View transaction history (bonus feature)
    response = client.get(
        f'/v1/accounts/{account_id}/transactions',
        headers=headers
    )
    assert response.status_code == 200
    assert response.json['pagination']['total'] == 2
    transactions = response.json['data']
    assert len(transactions) == 2

    # Verify transactions in history
    txn_types = [t['transaction_type'] for t in transactions]
    assert 'DEPOSIT' in txn_types
    assert 'WITHDRAWAL' in txn_types

    # Verify final balance
    response = client.get(f'/v1/accounts/{account_id}/balance', headers=headers)
    assert response.status_code == 200
    assert Decimal(response.json['balance']) == Decimal('3800.00')
