# StipendieAssistenten Backend

## Structure

The backend has been restructured into a more organized and maintainable format:

```
backend/
├── app/                    # Source code root
│   ├── __init__.py
│   ├── main.py             # Application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/             # API versioning
│   │       ├── __init__.py
│   │       └── routers/    # API route handlers
│   │           ├── __init__.py
│   │           ├── grants.py
│   │           ├── applications.py
│   │           ├── profile.py
│   │           ├── generate.py
│   │           └── foundations.py
│   ├── db/                 # Database related code
│   │   ├── __init__.py
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── database.py     # Database connection setup
│   │   └── schemas.py      # Pydantic schemas
│   ├── crud/               # Data access layer
│   │   ├── __init__.py
│   │   └── crud.py         # Database operations
│   └── foundation/         # Foundation API specific code
│       ├── __init__.py
│       ├── foundation_api.py
│       └── foundation_schemas.py
├── tests/                  # Test files
│   └── test_foundation_api.py
├── main.py                 # Entry point (simplified)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
└── stipendariet.db         # Database file (if exists)
```

## Running the Application

To run the backend server:

```bash
cd backend
python main.py
```

Or using uvicorn directly:

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Notes

- The application uses Python 3.14.0 with FastAPI, SQLAlchemy, and other dependencies
- The routers now follow a structured import pattern using the new package structure
- All imports have been updated to reflect the new directory structure
- The foundation polling functionality (for stiftelser.lansstyrelsen.se) is available under /api/foundations/

## Compatibility Note

This project may have compatibility issues with Python 3.14.0 due to SQLAlchemy version incompatibilities. If you encounter issues, consider using Python 3.11 or 3.12.
