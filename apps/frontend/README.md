# Welcome to your Lovable project

## Project info

**URL**: https://lovable.dev/projects/0b883ba7-353c-41cc-b963-661284ea3b2e

## How can I edit this code?

There are several ways of editing your application.

**Use Lovable**

Simply visit the [Lovable Project](https://lovable.dev/projects/0b883ba7-353c-41cc-b963-661284ea3b2e) and start prompting.

Changes made via Lovable will be committed automatically to this repo.

**Use your preferred IDE**

If you want to work locally using your own IDE, you can clone this repo and push changes. Pushed changes will also be reflected in Lovable.

The only requirement is having Node.js & npm installed - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating)

Follow these steps:

```sh
# Step 1: Clone the repository with submodules using the project's Git URL.
git clone --recurse-submodules <YOUR_GIT_URL>
# OR if you have the alias set up: git clone-recursive <YOUR_GIT_URL>

# Step 2: Navigate to the project directory.
cd <YOUR_PROJECT_NAME>

# Step 3: Install the necessary dependencies.
npm i

# Step 4: Start the development server with auto-reloading and an instant preview.
npm run dev
```

## Working with Submodules

This project includes the `infra-test` repository as a Git submodule. If you didn't clone with `--recurse-submodules`, initialize it:

```sh
# Initialize and update submodules
git submodule update --init --recursive
# OR if you have the alias: git submodule-update

# Update submodules to latest
git submodule update --remote
```

**Edit a file directly in GitHub**

- Navigate to the desired file(s).
- Click the "Edit" button (pencil icon) at the top right of the file view.
- Make your changes and commit the changes.

**Use GitHub Codespaces**

- Navigate to the main page of your repository.
- Click on the "Code" button (green button) near the top right.
- Select the "Codespaces" tab.
- Click on "New codespace" to launch a new Codespace environment.
- Edit files directly within the Codespace and commit and push your changes once you're done.

## What technologies are used for this project?

This project is built with:

- Vite
- TypeScript
- React
- shadcn-ui
- Tailwind CSS

## Docker Development Setup

This project includes a complete Docker setup with hot reload for both frontend and backend development.

### Quick Start with Docker

```sh
# Navigate to the infrastructure directory
cd infra-test

# Start development environment with hot reload
./dev.sh

# Or use docker compose directly
docker compose watch
```

### Available Services

- **Frontend**: http://localhost:8080 (React + Vite with hot reload)
- **Backend**: http://localhost:8000 (FastAPI with auto-reload)

### Development Features

- ✅ **Hot Reload**: File changes automatically trigger reloads
- ✅ **File Sync**: Source files are synced to containers in real-time
- ✅ **Auto Rebuild**: Dependency changes trigger container rebuilds
- ✅ **Health Checks**: Built-in health monitoring

See `infra-test/README.md` for detailed Docker setup documentation.

## How can I deploy this project?

Simply open [Lovable](https://lovable.dev/projects/0b883ba7-353c-41cc-b963-661284ea3b2e) and click on Share -> Publish.

## Can I connect a custom domain to my Lovable project?

Yes, you can!

To connect a domain, navigate to Project > Settings > Domains and click Connect Domain.

Read more here: [Setting up a custom domain](https://docs.lovable.dev/features/custom-domain#custom-domain)
