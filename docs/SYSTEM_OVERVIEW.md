# Stipendiatet - System Overview

## 1. Project Mission
To build a platform that solves information asymmetry in the scholarship market.
1.  **Data Engine (Admin):** Automates the discovery and structuring of scholarship data using LLMs and scraping.
2.  **User Platform:** Matches individuals with relevant scholarships via vector search and generates application drafts.

## 2. Architecture & Tech Stack

The system consists of two backends sharing a single PostgreSQL database.

```mermaid
graph TD
    %% Clients
    UserFE[User Frontend\n(Next.js)]
    AdminFE[Admin Frontend\n(React/Next.js)]

    %% Services
    UserAPI[User API Service\n(Node.js/TypeScript)]
    DataEngine[Data Engine Service\n(Python/FastAPI)]

    %% Database
    DB[(PostgreSQL\n+ pgvector)]

    %% External
    Web[Internet/Playwright]
    LLM[OpenAI API]

    %% Connections
    UserFE --> UserAPI
    AdminFE --> DataEngine
    UserAPI --> DB
    DataEngine --> DB
    DataEngine --> Web
    DataEngine --> LLM
    UserAPI --> LLM