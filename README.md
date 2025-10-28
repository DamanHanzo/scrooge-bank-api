# Bank API

A RESTful banking API built with Flask, PostgreSQL, and Docker. Implements core banking operations with secure authentication, role-based access control, and comprehensive transaction management.

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd scoorge-bank-api
cp .env.example .env

# Start services and run migrations
make up
make migrate

# Access API documentation
open http://localhost:5025/api/docs

# Run tests
make test
```

## What This Project Does

### Core Features (Requirements)

1. **Customer Management** - Register customers and manage their profiles
2. **Account Management** - Create and manage checking accounts
3. **Deposits** - Add funds to checking accounts
4. **Withdrawals** - Withdraw funds with balance validation and limits
5. **Loan Applications** - Submit, review, and manage personal loan applications
6. **Authentication & Authorization** - JWT-based auth with role-based access control (Customer, Admin, Super Admin)
7. **Admin Operations** - Customer status management, loan reviews, bank financial oversight

### Bonus Feature: Transaction History

**User Story:**
> As a customer, I want to view my complete transaction history with filtering options, so that I can track my spending, verify deposits/withdrawals, monitor loan payments, and maintain accurate financial records for budgeting and tax purposes.

**Why This Feature?**

The requirements include endpoints to create transactions (deposits, withdrawals, loan payments), but provided no way for customers to verify these transactions were actually created or to review their transaction history. This creates several problems:

- **Trust Issue**: Customers cannot verify that their deposits/withdrawals were recorded correctly
- **Compliance Gap**: Banking regulations typically require transaction history access
- **User Value**: Essential for personal finance management, budgeting, and tax record-keeping
- **Foundation for Future Features**: Enables dispute resolution, account reconciliation, and fraud detection

**Implementation:**

- `GET /v1/accounts/{account_id}/transactions` - List transactions with date range and type filters
- `GET /v1/transactions/{transaction_id}` - Get specific transaction details
- Supports filtering by date range, transaction type, and pagination
- Customer authorization ensures users only see their own transactions

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.11+ |
| **Framework** | Flask 3.0+ |
| **Database** | PostgreSQL 15+ |
| **ORM** | SQLAlchemy 2.0+ |
| **Validation** | Pydantic 2.5+ |
| **API Documentation** | Flask-SMOREST (OpenAPI 3.0) |
| **Authentication** | Flask-JWT-Extended |
| **Migrations** | Alembic |
| **Containerization** | Docker & Docker Compose |
| **Testing** | Pytest |

## Project Structure

```
scrooge-bank-api/
├── app/
│   ├── api/
│   │   ├── v1/              # API endpoints (accounts, customers, loans, admin, auth, transactions)
│   │   └── schemas/         # Marshmallow schemas for OpenAPI
│   ├── models/              # SQLAlchemy database models
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic layer
│   ├── middleware/          # Authentication & error handling
│   └── config.py            # Application configuration
├── alembic/                 # Database migrations
├── tests/
│   ├── unit/                # Unit tests for services
│   └── integration/         # Integration tests for API endpoints
├── docker-compose.yml       # Docker services configuration
├── Dockerfile               # API container definition
├── requirements.txt         # Python dependencies
├── Makefile                 # Common development commands
└── .env.example             # Environment variables template
```

### Architecture

The application follows a layered architecture:

- **API Layer** (`app/api/v1/`) - REST endpoints, request/response handling
- **Service Layer** (`app/services/`) - Business logic, transaction management
- **Data Layer** (`app/models/`) - Database models and relationships
- **Schema Layer** (`app/schemas/`) - Request validation and serialization

## Getting Started

### Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Git

### Running Locally

1. **Clone and setup environment:**
```bash
git clone <repo-url>
cd scrooge-bank-api
cp .env.example .env
```

2. **Start services:**
```bash
docker-compose up -d
```

3. **Run database migrations:**
```bash
docker-compose exec api alembic upgrade head
```

4. **Seed with sample data (optional):**
```bash
docker-compose exec api python scripts/seed_data.py
```

5. **Access the API:**
- API Base URL: `http://localhost:5025`
- API Documentation: `http://localhost:5025/api/docs`

### Using the Makefile (Recommended)

```bash
make up          # Start all services
make migrate     # Run database migrations
make test        # Run all tests
make logs        # View API logs
make shell       # Access Python shell
make down        # Stop all services
make fresh       # Clean restart (removes all data)
make help        # Show all available commands
```

## Running Tests

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test file
docker-compose exec api pytest tests/unit/services/test_account_service.py

# Run tests matching a pattern
docker-compose exec api pytest -k "test_deposit"
```

**Test Coverage:** 112 integration tests covering all API endpoints and business logic.

## API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:5025/api/docs
- **OpenAPI JSON Spec**: http://localhost:5025/api/openapi.json

The Swagger UI provides:
- Complete endpoint documentation
- Request/response schemas with examples
- Interactive "Try it out" functionality
- Authentication support (JWT bearer tokens)

### Key API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/auth/register` | POST | Register new user |
| `/v1/auth/login` | POST | User login |
| `/v1/accounts` | GET, POST | List/create accounts |
| `/v1/accounts/{id}/transactions` | GET, POST | Transaction history/create transaction |
| `/v1/accounts/{id}/balance` | GET | Get account balance |
| `/v1/loan-applications` | GET, POST | List/submit loan applications |
| `/v1/admin/customers` | GET | List all customers (admin) |
| `/v1/admin/loan-applications/{id}` | PATCH | Review loan application (admin) |

## Development

### Common Commands

```bash
# View API logs
docker-compose logs -f api

# Access database
docker-compose exec db psql -U bank_user -d bank_api_dev

# Format code
docker-compose exec api black app tests

# Run linters
docker-compose exec api flake8 app tests

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Stop services
docker-compose down

# Remove all data and restart fresh
make fresh
```

### Environment Variables

Key configuration in `.env`:

```bash
DATABASE_URL=postgresql://bank_user:bank_password@db:5432/bank_api_dev
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
FLASK_ENV=development
```

## Security Features

- **JWT Authentication**: Secure token-based authentication with refresh tokens
- **Role-Based Access Control**: Customer, Admin, and Super Admin roles
- **Input Validation**: All requests validated with Pydantic schemas
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **Audit Trail**: All financial transactions logged with timestamps
- **Account Authorization**: Customers can only access their own accounts

## Author

**Daman Singh**
GitHub: [@damanhanzo](https://github.com/damanhanzo)

---

Built with Python, Flask, PostgreSQL, and Docker.
