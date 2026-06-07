```markdown
# Specification: Data Engine Service

## 1. Overview
The Data Engine is a Python/FastAPI service responsible for the "Enrichment Pipeline". It does not handle user traffic. Its sole purpose is to find, clean, and structure scholarship data.

## 2. API Endpoints (Internal)

These endpoints are consumed by the **Admin Frontend**.

* `GET /scholarships/queue`
    * Returns list of scholarships with `status=NEW` or `FAILED`.
* `POST /scholarships/{id}/trigger-scrape`
    * Starts an async background task to process a specific scholarship.
* `GET /scholarships/{id}/review`
    * Returns the AI-extracted data alongside the raw scraped text for manual comparison.
* `PATCH /scholarships/{id}/approve`
    * Admin validates data. Updates status to `PUBLISHED` and generates the Vector Embedding.

## 3. The Scraping Pipeline (Logic Flow)

The agent must follow this strict sequence using **LangChain** (or similar orchestration) and **Playwright**.

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant Agent as Logic Controller
    participant Google as Google Search Tool
    participant Web as Playwright Browser
    participant LLM as OpenAI GPT-4o
    participant DB as Postgres

    API->>Agent: Start Job (OrgNr, Name)
    
    rect rgb(240, 240, 240)
        Note over Agent, Web: Step 1: Discovery
        Agent->>Google: Search query: "{Name} stipendium ansökan officiell sida"
        Google-->>Agent: Return Top 3 URLs
    end

    rect rgb(230, 240, 255)
        Note over Agent, Web: Step 2: Content Extraction
        Agent->>Web: Visit Best URL
        Web->>Web: Render JS, scroll to bottom
        Web->>Agent: Return Markdown/Text content (Max 20k chars)
    end

    rect rgb(255, 240, 230)
        Note over Agent, LLM: Step 3: Intelligence
        Agent->>LLM: Prompt: Extract fields (Deadline, Method, Reqs) from text.
        LLM-->>Agent: JSON Output (Pydantic Model)
    end

    Agent->>DB: Update Record (Data + Status=NEEDS_REVIEW)
```
```