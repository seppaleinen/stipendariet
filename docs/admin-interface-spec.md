# Specification: Admin Interface

## 1. Overview
The Admin Interface is a React-based frontend application that provides administrative capabilities for managing scholarship data. It connects to the Data Engine service to perform administrative tasks such as reviewing, approving, and managing scholarship entries.

## 2. Architecture & Tech Stack

The Admin Interface is a separate frontend application that communicates with the Data Engine service.

```mermaid
graph TD
    AdminFE[Admin Frontend\n(React/Vite)]
    DataEngine[Data Engine Service\n(Python/FastAPI)]
    DB[(PostgreSQL\n+ pgvector)]

    AdminFE --> DataEngine
    DataEngine --> DB

    subgraph "External"
        Auth[Authentication Service\n(JWT/OAuth)]
    end
    
    Auth -.-> AdminFE
```

## 3. Features & Functionality

The Admin Interface provides the following capabilities:

1. **Scholarship Queue Management**
   - View all scholarships with `NEW` or `FAILED` status
   - Access to trigger scraping for pending scholarships
   - Filter and search capabilities

2. **Scholarship Review**
   - View AI-extracted data alongside raw scraped content
   - Compare extracted information with original source
   - Ability to approve or reject scholarship data

3. **Scholarship Approval**
   - Validate scholarship information accuracy
   - Approve scholarships to make them publicly available
   - Generate vector embeddings upon approval
   - Track approval history

4. **Authentication & Authorization**
   - Secure login for admin users
   - Role-based access control
   - Session management

## 4. API Endpoints Used

The Admin Interface consumes the following endpoints from the Data Engine:

* `GET /api/v1/scholarships/queue`
  * Retrieves scholarships with status=NEW or FAILED
* `POST /api/v1/scholarships/{id}/trigger-scrape`
  * Initiates scraping for a specific scholarship
* `GET /api/v1/scholarships/{id}/review`
  * Retrieves scholarship data for review
* `PATCH /api/v1/scholarships/{id}/approve`
  * Approves and publishes a scholarship

## 5. Tech Stack & Structure

Based on the existing frontend structure:

* **Framework**: React with TypeScript
* **Build Tool**: Vite
* **Styling**: Tailwind CSS with shadcn/ui components
* **State Management**: React hooks / Zustand (to be determined)
* **HTTP Client**: Axios or fetch
* **Authentication**: JWT tokens or OAuth integration

The structure will follow the same patterns as the existing frontend:

```
src/
├── components/     # Reusable UI components
├── pages/          # Page-level components
├── hooks/          # Custom React hooks
├── lib/            # Utility functions and libraries
├── types/          # TypeScript type definitions
├── App.tsx         # Main application component
└── main.tsx        # Application entry point
```

## 6. Authentication

The Admin Interface will implement authentication via:
- JWT token-based authentication
- Secure login page
- Protected routes
- Automatic token refresh
- Session timeout handling

## 7. Deployment

The Admin Interface will be deployed as a separate service:
- Containerized with Docker
- Deployed on k3s cluster
- Exposed via Traefik at stipendieadmin.labb.site
- Separate from the user-facing frontend