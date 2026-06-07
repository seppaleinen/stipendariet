# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Development Commands

### Running the Application

```bash
# Local development (from backend directory)
python main.py

# Or with uvicorn directly (recommended for development with hot reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Using Docker Compose (recommended for full stack with dependencies)
docker-compose up

# Docker Compose in detached mode
docker-compose up -d

# View logs from Docker containers
docker-compose logs -f backend
```

### Testing

```bash
# Run basic foundation API test
python tests/test_foundation_api.py

# Note: No full pytest setup exists yet. Tests are manually executed scripts.
```

### Database Management

```bash
# Start only PostgreSQL (if needed independently)
docker-compose up postgres -d

# Access PostgreSQL database directly
docker exec -it stipendariet_postgres psql -U postgres -d stipendariet

# Stop and remove all containers (including data)
docker-compose down
```

### Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Note: Uses Python 3.11 (Docker) or 3.14.0 (local), though 3.11-3.12 recommended for SQLAlchemy compatibility
```

## Architecture Overview

### Tech Stack

- **Framework**: FastAPI with Uvicorn
- **Database**: PostgreSQL (primary), SQLite (legacy/local dev fallback)
- **Task Scheduling**: APScheduler for background jobs
- **LLM Integration**: External Ollama API (https://ollama.labb.site)
- **Embeddings**: PostgreSQL with pgvector for semantic search

### Core Application Structure

The application follows a layered FastAPI architecture:

```
app/
├── main.py              # FastAPI app initialization, CORS, startup events, health checks
├── api/v1/routers/      # API endpoints grouped by domain
│   ├── grants.py        # Grant CRUD operations
│   ├── applications.py  # Application tracking and management
│   ├── profile.py       # User profile management
│   ├── foundations.py   # Foundation API access
│   ├── foundation_sync.py  # Foundation syncing and LLM proxy
│   ├── funding.py       # Unified funding opportunities (grants + foundations)
│   └── search.py        # SQL text search
├── db/
│   ├── database.py      # SQLAlchemy engine, session management, connection retry logic
│   ├── models.py        # SQLAlchemy ORM models (Grant, Application, Profile, Foundation)
│   └── schemas.py       # Pydantic models for request/response validation
├── crud/
│   └── crud.py          # Data access layer - database operations
├── foundation/
│   ├── foundation_api.py    # External API client for stiftelser.lansstyrelsen.se
│   ├── scheduler.py          # APScheduler setup for daily foundation syncs (6 AM)
│   └── sync_service.py       # Foundation data processing and synchronization
└── services/            # Business logic services
```

### Key Architectural Patterns

**1. Foundation Sync Pipeline**
The application syncs Swedish foundation data from an external API:

- Daily scheduled sync at 6:00 AM via APScheduler
- Manual sync trigger available via `/api/foundation-sync/trigger-sync`
- Process: Fetch from external API → Extract/refine data (including basic NLP for categorization) → Store in PostgreSQL
- Full sync strategy: deletes all foundations before inserting updated data

**2. Search Strategy**
- Uses SQL text search with ILIKE patterns
- Future: pgvector embeddings for semantic search

**3. Database Connection Resilience**
`database.py` implements retry logic for database connections to handle Docker container startup races and transient connection issues.

**4. Unified Funding Model**
The `/api/funding` endpoints combine two data sources:

- Traditional grants (manually curated)
- Foundations (synced from external API)
- Both are normalized to a common schema for frontend consumption

**5. LLM Integration**

- The backend acts as a proxy to an external Ollama API to avoid CORS issues
- Endpoint: `/api/foundation-sync/generate-application`
- Falls back through multiple models: gemma3:12b → qwen3:8b → qwen3:14b → llama3.1 → llama3 → mistral
- Used for generating grant application drafts (Swedish language)

### Database Models

**Grant**: Traditional grant opportunities (name, provider, summary, description, amount, deadline, cadence, link, tags)

**Application**: Tracks applications to grants (grant_id FK, status, applied_at, next_allowed_application_date, notes)

**Profile**: User/family profile for application generation (family_members JSON, economic_situation, background, achievements, goals)

**Foundation**: Swedish foundations synced from external API (foundation_id unique, name, orgnr, purpose, summary, address, postal info, last_updated, target_groups JSON, funding_areas JSON, tags JSON, raw_data JSON)

### Environment Configuration

Required environment variables (see docker-compose.yml for examples):

- `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME` (PostgreSQL connection)
- `DATA_DIR` (optional, for persistent data storage)

### Docker Services

- **postgres**: PostgreSQL 15 database
- **backend**: FastAPI application (exposed on port 8080, internally runs on 8000)

### Important Implementation Details

**Foundation Data Processing**: The `sync_service.py` contains keyword-based extraction logic for categorizing foundations by target groups (barn/ungdom, äldre, sjuka, idrott, kultur, forskning) and funding areas (utbildning, boende, resor, ekonomiskt stöd). This is a placeholder for future LLM-based extraction.

**Pydantic Compatibility**: Code includes fallbacks for both Pydantic v1 (`.dict()`) and v2 (`.model_dump()`) to handle version differences.

**CORS Configuration**: Allows origins from localhost:3000, 127.0.0.1:3000, localhost:8080, 127.0.0.1:8080 for frontend development.

### API Endpoints Summary

- `/` - Root endpoint with version info
- `/health` - Health check with database connectivity test
- `/api/grants/` - Grant CRUD operations
- `/api/applications/` - Application tracking
- `/api/profile/` - Profile management
- `/api/foundations/` - Direct foundation API access
- `/api/foundation-sync/` - Foundation sync management and LLM proxy
- `/api/funding/` - Unified funding opportunities
- `/api/search/foundations` - Semantic search for foundations
- `/api/search/profiles` - Semantic search for profiles

### Known Issues and Considerations

- Python 3.14.0 has SQLAlchemy compatibility issues; Python 3.11-3.12 recommended
- Foundation sync uses a full-replace strategy (not incremental updates)
- LLM generation is a basic template system; actual LLM call happens via proxy endpoint
- No comprehensive test suite; only manual test scripts exist
