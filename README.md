# Bank API

A RESTful banking API built with Python Flask, PostgreSQL, and Docker. This project demonstrates production-grade API design, clean architecture, and best practices for financial software development.

## ⚡ Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd bank-api
cp .env.example .env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec api alembic upgrade head

# Access API docs
open http://localhost:5000/api/docs
```

## 📋 Features

### Phase 1 (MVP)
- ✅ **Customer Management**: Create and manage customer accounts
- ✅ **Checking Accounts**: Create accounts, check balances
- ✅ **Deposits**: Add money to checking accounts
- ✅ **Withdrawals**: Withdraw with balance validation and transaction limits
- ✅ **Transaction History**: Query past transactions with filtering
- ✅ **Loan Applications**: Submit and track personal loan applications
- ✅ **JWT Authentication**: Secure, role-based access control (RBAC)
- ✅ **Admin Operations**: Bank administration with full audit trail

### Admin Capabilities
- 🏦 **Customer Management**: View, suspend, and activate customer accounts
- 📋 **Loan Review**: Review, approve, or reject loan applications
- 📝 **Audit Logging**: Complete audit trail of all administrative actions
- 👥 **User Management**: Create and manage admin users (Super Admin only)

### Core Capabilities
- **Role-Based Access Control**: Customer, Admin, and Super Admin roles
- **RESTful API** with OpenAPI 3.0 documentation
- **ACID-compliant transactions** using PostgreSQL
- **Comprehensive validation** with Pydantic
- **Database migrations** with Alembic
- **Dockerized development** environment
- **Extensive test coverage** (unit, integration, E2E)

## 🏗️ Architecture

```
┌─────────────────┐
│   API Clients   │
└────────┬────────┘
         │
         │ HTTPS/REST
         │
┌────────▼────────────────────┐
│   Flask API (v1)            │
│  - Authentication           │
│  - Request Validation       │
│  - Business Logic           │
└────────┬────────────────────┘
         │
┌────────▼────────────────────┐
│   SQLAlchemy ORM            │
└────────┬────────────────────┘
         │
┌────────▼────────────────────┐
│   PostgreSQL Database       │
│  - Customers                │
│  - Accounts                 │
│  - Transactions             │
│  - Loan Applications        │
└─────────────────────────────┘
```

## 🛠️ Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Language** | Python | 3.11+ |
| **Framework** | Flask | 3.0+ |
| **Database** | PostgreSQL | 15+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Migrations** | Alembic | 1.12+ |
| **Validation** | Pydantic | 2.5+ |
| **API Docs** | Flask-SMOREST | 0.42+ |
| **Containerization** | Docker | 24+ |

## 🚀 Development

### Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Git
- Text editor (VS Code recommended)

### Setup

```bash
# Clone repository
git clone <repo-url>
cd bank-api

# Copy environment file
cp .env.example .env

# Start all services (database + API)
docker-compose up -d

# Run database migrations
docker-compose exec api alembic upgrade head

# Seed with sample data (optional)
docker-compose exec api python scripts/seed_data.py
```

### Common Commands

```bash
# View logs
docker-compose logs -f api

# Run tests
docker-compose exec api pytest

# Run tests with coverage
docker-compose exec api pytest --cov=app --cov-report=html

# Format code
docker-compose exec api black app tests

# Run linters
docker-compose exec api flake8 app tests
docker-compose exec api mypy app

# Access Python shell
docker-compose exec api flask shell

# Access PostgreSQL
docker-compose exec db psql -U bank_user -d bank_api_dev

# Stop services
docker-compose down
```

### Using Makefile (Recommended)

```bash
make up          # Start services
make test        # Run tests
make logs        # View logs
make shell       # Python shell
make migrate     # Run migrations
make format      # Format code
make lint        # Run linters
make fresh       # Clean restart
make help        # Show all commands
```

## 🧪 Testing

```bash
# Run all tests
make test

# Run with coverage report
make test-cov

# Run specific test file
docker-compose exec api pytest tests/unit/services/test_transaction_service.py

# Run tests matching pattern
docker-compose exec api pytest -k "test_deposit"
```

## 📖 API Documentation

Once the application is running, access interactive documentation at:

- **Swagger UI**: http://localhost:5000/api/docs
- **OpenAPI Spec**: http://localhost:5000/api/openapi.json

## 🗂️ Project Structure

```
bank-api/
├── app/
│   ├── api/v1/              # API route handlers
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic validation schemas
│   ├── services/            # Business logic layer
│   ├── middleware/          # Authentication, logging
│   └── exceptions.py        # Custom exceptions
├── alembic/                 # Database migrations
│   └── versions/
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── conftest.py          # Test fixtures
├── docs/                    # Detailed documentation
├── scripts/                 # Utility scripts
├── docker-compose.yml       # Docker services
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
├── Makefile                 # Common commands
└── README.md                # This file
```

## 🔐 Security

- **JWT Authentication**: Secure, role-based access control (RBAC)
- **Input Validation**: Pydantic schemas for all requests
- **Audit Logging**: All financial operations logged


## 📝 License

[Specify License]

## 👤 Author

**Daman Singh**  
[GitHub](https://github.com/damanhanzo)

---

**Built with:**
- Python 🐍
- Flask ⚡
- PostgreSQL 🐘
- Docker 🐳
- Love ❤️