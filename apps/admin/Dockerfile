# Multi-stage build for pnpm monorepo workspace (context: repo root)
# Builds @stipendariet/admin with all workspace dependencies

# Stage 1: Install deps (cache-friendly — only invalidated by lockfile changes)
FROM node:22-alpine AS deps
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

# Copy package.json files for all workspace packages the admin needs
COPY packages/types/package.json ./packages/types/
COPY packages/ui/package.json ./packages/ui/
COPY packages/api-client/package.json ./packages/api-client/
COPY packages/eslint-config/package.json ./packages/eslint-config/
COPY apps/admin/package.json ./apps/admin/

RUN pnpm install --frozen-lockfile

# Stage 2: Build
FROM node:22-alpine AS builder
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Copy root config
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml turbo.json tsconfig.base.json ./

# Copy node_modules and workspace structure from deps
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/packages ./packages
COPY --from=deps /app/apps ./apps

# Copy workspace package sources (overlays on top of deps structure)
COPY packages/types/src ./packages/types/src
COPY packages/types/tsconfig.json ./packages/types/
COPY packages/ui/src ./packages/ui/src
COPY packages/ui/tsconfig.json ./packages/ui/
COPY packages/api-client/src ./packages/api-client/src
COPY packages/api-client/tsconfig.json ./packages/api-client/

# Copy admin sources (overlays on top of deps app skeleton)
COPY apps/admin/src ./apps/admin/src
COPY apps/admin/public ./apps/admin/public
COPY apps/admin/tsconfig.json apps/admin/vite.config.ts apps/admin/index.html apps/admin/tailwind.config.ts apps/admin/postcss.config.js apps/admin/nginx.conf ./apps/admin/

RUN pnpm turbo run build --filter=@stipendariet/admin

# Stage 3: Production (nginx)
FROM nginx:1.29-alpine AS production

RUN apk add --no-cache dumb-init

COPY --from=builder /app/apps/admin/dist /usr/share/nginx/html
COPY apps/admin/nginx.conf /etc/nginx/nginx.conf

RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    chmod -R 755 /usr/share/nginx/html && \
    chmod 1777 /tmp

USER nginx
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=2s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

ENTRYPOINT ["dumb-init", "--"]
CMD ["nginx", "-g", "daemon off;"]
