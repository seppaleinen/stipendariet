# Stipendie Admin Interface

The admin interface for managing scholarship data in the Stipendiatet platform.

## Overview

This is a React-based admin panel that provides administrative capabilities for managing scholarship data. It connects to the Data Engine service to perform administrative tasks such as reviewing, approving, and managing scholarship entries.

## Features

- Login/Authentication
- Scholarship Queue Management
- Scholarship Review Interface
- Approval Workflow
- Admin Dashboard

## Tech Stack

- React 18
- TypeScript
- Vite
- Tailwind CSS
- Radix UI Primitives
- React Router DOM
- Axios for API requests

## Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Run the development server:
   ```bash
   npm run dev
   ```

3. The app will run on http://localhost:5173

## Environment Variables

- `VITE_API_URL`: The base URL for the Data Engine API (defaults to http://localhost:8000)

## Building

To build the application for production:

```bash
npm run build
```

## Docker

To build and run with Docker:

```bash
# Build the image
docker build -t stipendie-admin .

# Run the container
docker run -p 8080:80 stipendie-admin
```