# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**Stipendium Assistenten** is a React-based web application that helps Swedish families discover and apply for grants and scholarships. Built with Vite, TypeScript, React, shadcn-ui, and Tailwind CSS, it connects to a FastAPI backend and is designed to work within a Lovable.dev project environment.

## Development Commands

### Local Development

```bash
# Install dependencies
npm i

# Start development server (runs on http://localhost:8080)
npm run dev

# Build for production
npm run build

# Build for development mode (includes dev optimizations)
npm run build:dev

# Preview production build
npm run preview

# Run linter
npm run lint
```

### Docker Development

The project includes a git submodule `infra-test` that contains Docker infrastructure for full-stack development:

```bash
# Navigate to infrastructure directory
cd infra-test

# Start development environment with hot reload
./dev.sh

# Or use docker compose directly
docker compose watch
```

**Services when running via Docker:**

- Frontend: http://localhost:8080
- Backend: http://localhost:8000

### Submodule Management

```bash
# Initialize submodules (if not cloned with --recurse-submodules)
git submodule update --init --recursive

# Update submodules to latest
git submodule update --remote
```

## Architecture

### Application Structure

The application follows a page-based routing architecture:

**Core Routes:**

- `/` - Home page with overview
- `/family-setup` - Family profile and information setup
- `/grants` - Browse available grants/scholarships
- `/grants/:id` - Individual grant details
- `/applications` - Manage grant applications
- `/generate` - AI-powered application generation
- `/generate/:id` - Generate application for specific grant

**Component Organization:**

- `src/components/` - Reusable components (Layout, NavLink)
- `src/components/ui/` - shadcn-ui component library (50+ components)
- `src/pages/` - Page components corresponding to routes
- `src/hooks/` - Custom React hooks (use-toast, use-mobile)
- `src/lib/` - Utility functions and API client
- `src/types/` - TypeScript type definitions

### Data Layer Architecture

**API Client (`src/lib/api.ts`):**

- Centralizes all backend communication
- Base URL configured via `VITE_API_URL` environment variable (defaults to `/api`)
- Falls back to mock data when backend unavailable
- Handles both unified `/funding` endpoint and legacy `/grants` endpoint

**Key API Functions:**

- `getGrants()` / `getGrant(id)` - Fetch grant data
- `getProfile()` / `saveProfile()` - Family profile management
- `getApplications()` / `createApplication()` / `updateApplication()` - Application tracking
- `generateApplicationWithAI()` - AI-powered application generation via `/foundation-sync/generate-application`

**Data Transformation:**

- Backend uses snake_case (`family_members`, `economic_situation`)
- Frontend uses camelCase (`members`, `economicSituation`)
- API client handles bidirectional transformation

### State Management

- **React Query** (`@tanstack/react-query`) for server state
- React Context for global UI state (TooltipProvider)
- Local component state for UI interactions

### Type System

**Core Types (`src/types/grants.ts`):**

```typescript
Grant - Grant/scholarship information
Application - Application tracking and status
FamilyProfile - Simple family profile (legacy)
FamilySetup - Detailed family setup with children, economy, mobility needs
FamilyMember - Individual family member info
GeneratedApplication - AI-generated application content
```

### Styling System

**Tailwind CSS + shadcn-ui:**

- Custom theme with CSS variables (see `tailwind.config.ts`)
- Path alias: `@/` → `./src/`
- shadcn-ui components configured via `components.json`
- Base color: slate, with CSS variables for theming

**Custom Color Extensions:**

- `success` color for positive states
- All colors support dark mode via CSS custom properties

### TypeScript Configuration

**Relaxed Type Checking:**

- `noImplicitAny: false` - Allows implicit any types
- `noUnusedParameters: false` - Unused parameters permitted
- `noUnusedLocals: false` - Unused variables permitted
- `strictNullChecks: false` - Relaxed null checking
- `allowJs: true` - JavaScript files allowed

This configuration prioritizes rapid development over strict type safety.

### ESLint Configuration

- Uses TypeScript ESLint with recommended rules
- React Hooks plugin for hooks validation
- React Refresh plugin for HMR
- **Disabled:** `@typescript-eslint/no-unused-vars` (unused variables allowed)

## Environment Variables

```bash
VITE_API_URL - Backend API base URL (defaults to /api)
```

## Working with the Codebase

### Adding New Pages

1. Create page component in `src/pages/`
2. Add route in `src/App.tsx`
3. Add navigation entry in `src/components/Layout.tsx`

### Adding shadcn-ui Components

shadcn-ui components are pre-installed. To add more:

```bash
npx shadcn-ui@latest add [component-name]
```

### API Integration

- All API calls should go through `src/lib/api.ts`
- Handle both backend response and mock data fallback
- Transform snake_case backend responses to camelCase frontend types

### Family Setup Context

The `FamilySetup` type represents detailed family information including:

- Municipality and household composition
- Children's diagnoses (ADHD, autism, intellectual disability, CP, acquired brain injury)
- Mobility needs (wheelchair, assistive devices, stairs, supervision)
- Economic situation and employment status
- Government benefits

This data is used for:

1. Matching families with relevant grants
2. AI-powered application generation
3. Eligibility determination

## Testing

The project has test infrastructure in place. Tests are located alongside components:

- `src/pages/FamilySetup.test.tsx` - Example test file

To run tests, check for test scripts in `package.json` (currently not configured).

## Related Projects

This frontend is part of a larger system that includes:

- **Backend:** FastAPI application (accessible via Docker setup)
- **Infrastructure:** `infra-test` submodule contains Docker configuration
