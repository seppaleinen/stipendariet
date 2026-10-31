# StipendieAssistenten Architecture Overview

## System Context Diagram

```mermaid
C4Context
  title System Context Diagram - StipendieAssistenten

  Person(user, "User (Family)", "Swedish families seeking grants/scholarships")
  Person(admin, "Admin", "Manages enrichment pipeline, reviews scholarships")

  Boundary(system_boundary, "StipendieAssistenten System") {
    System(frontend, "Frontend App", "React/Vite + TypeScript", "User-facing grant discovery")
    System(admin_app, "Admin Panel", "React/Vite + TypeScript", "Pipeline management, review workflow")
    System(backend, "Backend API", "FastAPI + PostgreSQL + pgvector", "Grants, foundations, enrichment pipeline")
  }

  System_Ext(bolagsverket, "Bolagsverket API", "Swedish Companies Registration Office", "Foundation registry lookup")
  System_Ext(searxng, "SearXNG", "Self-hosted meta-search", "Multi-engine web discovery")
  System_Ext(ollama, "LiteLLM/Ollama", "LLM proxy + models", "Extraction, validation, translation")
  System_Ext(authentik, "Authentik", "Identity provider", "ForwardAuth for admin panel")

  Rel(user, frontend, "Uses", "HTTPS")
  Rel(admin, admin_app, "Uses", "HTTPS")
  Rel(frontend, backend, "Consumes API", "HTTPS /api")
  Rel(admin_app, backend, "Consumes API", "HTTPS /api")
  Rel(backend, bolagsverket, "Stage 0 lookup", "HTTPS REST API")
  Rel(backend, searxng, "Stage 1 discovery", "HTTP search")
  Rel(backend, ollama, "LLM calls", "HTTP OpenAI-compatible")
  Rel(admin_app, authentik, "ForwardAuth exchange", "HTTPS headers")

  UpdateRelStyle(user, frontend, $offsetY="-40")
  UpdateRelStyle(admin, admin_app, $offsetY="-40")
  UpdateRelStyle(frontend, backend, $offsetX="60")
  UpdateRelStyle(admin_app, backend, $offsetX="-60")
```

## Container Diagram (Backend Focus)

```mermaid
C4Container
  title Backend Container Diagram

  Person(user, "User")
  Person(admin, "Admin")

  Container_Boundary(backend, "Backend") {
    Container(api, "FastAPI App", "Python 3.13", "REST API, CORS, startup events")
    Container(worker, "Enrichment Worker", "Python + Arq", "Async job queue processor")
    ContainerDb(postgres, "PostgreSQL", "pgvector:pg16", "Grants, foundations, enrichment data, embeddings")
    ContainerDb(redis, "Redis", "Redis 7", "Arq job queue, SearXNG cache")
  }

  Container(searxng, "SearXNG", "Docker", "Multi-engine search (Google, Bing, DDG, Brave)")
  Container(litellm, "LiteLLM Proxy", "External", "LLM routing (gemma-4-12b, nomic-embed-text)")
  Container(bolagsverket, "Bolagsverket API", "External", "Swedish foundation registry")

  Rel(user, api, "GET /grants, POST /profile", "HTTPS")
  Rel(admin, api, "GET /admin/enrich/*", "HTTPS")
  Rel(api, postgres, "CRUD operations", "SQLAlchemy + pgvector")
  Rel(api, redis, "Read/write cache", "Redis client")
  Rel(api, worker, "Enqueue jobs", "Arq Redis queue")
  Rel(worker, postgres, "Read foundation, write enrichment", "SQLAlchemy")
  Rel(worker, searxng, "Stage 1: Discovery search", "HTTP")
  Rel(worker, bolagsverket, "Stage 0: Registry lookup", "HTTPS REST")
  Rel(worker, litellm, "Stage 2-5: LLM extraction", "HTTP OpenAI API")

  UpdateRelStyle(api, postgres, $offsetY="-30")
  UpdateRelStyle(worker, searxng, $offsetX="80")
```

## Enrichment Pipeline v2 Flow

```mermaid
flowchart TD
  subgraph Pipeline["Foundation Enrichment Pipeline v2 (7 Stages)"]
    A[Stage 0: Bolagsverket<br/>Registry Lookup] -->|Has website?| B{Skip Discovery?}
    B -->|Yes| D
    B -->|No| C[Stage 1: SearXNG<br/>Multi-Engine Search]
    C -->|4 strategies + Redis cache| D[Stage 2: Validation<br/>LLM + Heuristics]
    D -->|Matched candidates| E[Stage 3: Crawl<br/>Trafilatura → Playwright fallback]
    E -->|Deduped pages| F[Stage 4: Per-Source Extraction<br/>LLM + Confidence scoring]
    F -->|Top 5 sources| G[Stage 5: Merge<br/>Highest-confidence-wins]
    G -->|Missing fields?| H{Gap Analysis}
    H -->|Yes, <2 iters| I[Stage 6: Targeted Re-Search<br/>Field-specific queries]
    I --> E
    H -->|No| J[Stage 7: Service Area<br/>Geographic extraction]
    J --> K[(EnrichmentData<br/>+ trace JSON)]
  end

  L[Bolagsverket API] --> A
  M[SearXNG + DDG fallback] --> C
  N[LiteLLM: gemma-4-12b] --> D
  N --> F
  N --> J
  O[Trafilatura + Playwright] --> E
  P[Redis cache 7-day TTL] <--> C

  style A fill:#e1f5ff
  style C fill:#e1f5ff
  style D fill:#fff4e1
  style E fill:#f0e1ff
  style F fill:#ffe1e1
  style G fill:#e1ffe1
  style I fill:#fff4e1
  style J fill:#f0e1ff
```

## Admin Authentication Flow (Authentik ForwardAuth)

```mermaid
sequenceDiagram
  participant Admin as Admin Browser
  participant Traefik as Traefik + ForwardAuth
  participant Authentik as Authentik IdP
  participant AdminApp as Admin Frontend
  participant Backend as Backend API

  Admin->>Traefik: GET /admin/*
  Traefik->>Authentik: ForwardAuth challenge
  Authentik->>Admin: Login prompt (if unauthenticated)
  Admin->>Authentik: Credentials
  Authentik-->>Traefik: Inject headers:<br/>X-Forwarded-Email<br/>X-Forwarded-User<br/>X-Forwarded-Groups
  Traefik->>Backend: POST /api/auth/exchange<br/>+ X-Internal-Auth header
  Backend->>Backend: Validate:<br/>1. X-Internal-Auth token<br/>2. Internal network IP<br/>3. Admin group membership
  Backend->>Backend: Auto-provision User<br/>(hashed_password=null)
  Backend-->>AdminApp: JWT access_token
  AdminApp->>AdminApp: Store in localStorage<br/>Auto-refresh <5min to expiry
  AdminApp->>Backend: Subsequent requests<br/>Authorization: Bearer <token>
  Backend-->>AdminApp: 401 → redirect /login
```

## Database Schema (Key Entities)

```mermaid
erDiagram
  users ||--o{ profiles : "owns"
  users ||--o{ applications : "submits"
  users ||--o{ saved_grants : "saves"

  foundations ||--o{ enrichment_sources : "discovered from"
  enrichment_sources ||--o{ enrichment_pages : "contains"
  enrichment_sources ||--o{ enrichment_data : "extracted from"

  enrichment_prompts ||--o{ enrichment_data : "used for extraction"

  users {
    uuid id PK
    varchar email UK
    varchar hashed_password "nullable for OAuth"
    varchar name
    boolean is_active
    timestamp created_at
    timestamp updated_at
    varchar google_id
  }

  profiles {
    uuid id PK
    uuid user_id FK
    varchar name
    jsonb life_situations
    jsonb health_conditions
    jsonb occupations
    varchar self_description
    varchar county_code
    varchar municipality_code
  }

  foundations {
    integer id PK
    varchar orgnr UK
    varchar name
    text purpose
    text translated_purpose
    vector purpose_embedding "768-dim"
    jsonb roles
    jsonb business_entities
    varchar service_area_status
    varchar enriched_description
  }

  enrichment_sources {
    integer id PK
    integer foundation_id FK
    varchar url
    varchar source_type "bolagsverket|searxng|ddg"
    boolean is_match
    float confidence
    jsonb trace
  }

  enrichment_data {
    integer id PK
    integer foundation_id FK
    integer prompt_id FK "nullable"
    jsonb extracted_data "8 fields + confidence"
    varchar source_url "Phase 4: which URL contributed"
    jsonb trace "full pipeline execution"
    timestamp extracted_at
    varchar status "PENDING|COMPLETED|FAILED"
  }

  enrichment_prompts {
    integer id PK
    varchar name UK
    varchar version "semver"
    text template "Jinja2"
    jsonb variables
    boolean is_production
    jsonb metrics "avg_confidence, field_completeness, runs_count"
  }
```

## Frontend Architecture

```mermaid
flowchart LR
  subgraph Frontend["apps/frontend"]
    A[App.tsx<br/>Router + Providers] --> B[Pages]
    B --> C1[Home]
    B --> C2[Grants]
    B --> C3[Matching]
    B --> C4[Generate]
    B --> C5[Family Setup]

    D[features/grants] --> E[hooks/useGrantsList.ts]
    D --> F[hooks/useSavedGrants.ts]
    D --> G[components/GrantCard.tsx]

    H[lib/api.ts] --> I[@stipendariet/api-client]
    J[contexts/AuthContext] --> K[JWT storage]
    L[contexts/ProfileContext] --> M[Profile state]
  end

  subgraph Shared["Shared Packages"]
    I --> N[@stipendariet/types<br/>Type definitions]
    O[@stipendariet/ui<br/>Radix components]
  end

  subgraph Admin["apps/admin"]
    P[EnrichmentResultsPage] --> Q[Per-field source + confidence]
    P --> R[View Trace modal]
    S[EnrichmentPromptsPage] --> T[Prompt versioning UI]
  end

  style Frontend fill:#e1f5ff
  style Shared fill:#f0f0f0
  style Admin fill:#ffe1e1
```

## Deployment Topology (Kubernetes)

```mermaid
flowchart TB
  subgraph Cluster["Kubernetes Cluster"]
    subgraph Ingress["Ingress Layer"]
      A[Traefik Ingress<br/>+ ForwardAuth Middleware]
    end

    subgraph Apps["Application Pods"]
      B[Backend Deployment<br/>FastAPI + uvicorn]
      C[Enrichment Worker<br/>Arq + Redis]
      D[Frontend Deployment<br/>Nginx + React SPA]
      E[Admin Frontend<br/>Nginx + React SPA]
    end

    subgraph Stateful["Stateful Services"]
      F[PostgreSQL StatefulSet<br/>pgvector:pg16]
      G[Redis StatefulSet<br/>Redis 7]
    end
  end

  subgraph External["External Services"]
    H[Authentik IdP<br/>ForwardAuth provider]
    I[LiteLLM Proxy<br/>gemma-4-12b]
    J[SearXNG<br/>Multi-engine search]
    K[Bolagsverket API<br/>Swedish registry]
  end

  User((User)) --> A
  Admin((Admin)) --> A

  A --> B
  A --> D
  A --> E

  B --> F
  B --> G
  C --> F
  C --> G

  B --> H
  E --> H
  C --> I
  C --> J
  C --> K

  style Cluster fill:#f9f9f9,stroke:#333
  style External fill:#fff4e1,stroke:#333
```

## Key Architectural Decisions

| Decision | ADR | Rationale |
|----------|-----|-----------|
| **Alembic migration gating** | ADR-0001 | Fail-fast with clear error if DB revision unknown to image |
| **Model separation** | ADR-0004 | One file per entity, single `Base` in `__init__.py` |
| **Authentik ForwardAuth** | ADR-0003 | Tokenless exchange, auto-provisioning, centralized identity |
| **Pipeline service abstraction** | ADR-0008 | `PipelineStage` interface, `PipelineContext` for state |
| **SearXNG multi-engine** | ADR-0011 | 4x coverage, self-hosted, Redis cache, DDG fallback |
| **Bolagsverket Stage 0** | ADR-0010 | Authoritative data, skip Discovery when official site found |
| **Prompt versioning** | ADR-0009 | Jinja2 templates, A/B testing, metrics tracking |
| **Confidence-based merge** | ADR-0012 | Per-field confidence, targeted re-search, observability |

## Technology Stack Summary

| Layer | Technology | Version | Notes |
|-------|------------|---------|-------|
| **Backend** | FastAPI + uvicorn | Python 3.13 | Async API, CORS, startup events |
| **Database** | PostgreSQL + pgvector | 16 | Embeddings, text search |
| **Cache/Queue** | Redis | 7 | Arq job queue, SearXNG cache |
| **LLM** | LiteLLM proxy + Ollama | gemma-4-12b | OpenAI-compatible API |
| **Search** | SearXNG | latest | Google, Bing, DDG, Brave engines |
| **Frontend** | React + Vite | 18 + 5 | SWC, TypeScript, shadcn-ui |
| **Admin** | React + Vite | 18 + 5 | Radix UI, React Query |
| **Shared Types** | TypeScript | workspace | `@stipendariet/types` |
| **UI Components** | Radix + Tailwind | 3.x | `@stipendariet/ui` |
| **Auth** | Authentik + JWT | ForwardAuth | Tokenless exchange |
| **Deployment** | Kubernetes + helmfile | - | Traefik ingress, StatefulSets |

---

## Related Documentation

- [ADR Index](./adr/) — All architectural decision records
- [Enrichment Pipeline User Guide](./enrichment-pipeline.md) — Admin usage
- [CONTEXT.md](../CONTEXT.md) — Domain language and concepts
- [AGENTS.md](../AGENTS.md) — Agent instructions for this repo