# syntax reference: multi-stage build -> static bundle served by nginx.

# ---- Build stage: compile the Vite/React app to static files ----
FROM node:20-alpine AS build
WORKDIR /app

# Install dependencies first for better layer caching.
COPY package.json package-lock.json* ./
RUN npm install

# Build the production bundle. VITE_API_BASE_URL is optional; when unset the
# app calls the relative path /api/v1 (proxied by nginx), so no backend host is
# baked into the bundle.
COPY . .
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ---- Runtime stage: serve the static bundle + reverse-proxy the API ----
FROM nginx:1.27-alpine AS runtime

# The template is rendered to /etc/nginx/conf.d/default.conf by the base image's
# entrypoint using envsubst against the container environment.
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

# Non-secret infrastructure defaults so the image also boots when run bare.
# docker-compose overrides all three from the environment (.env) at deploy time.
ENV FRONTEND_PORT=8080 \
    BACKEND_HOST=backend \
    BACKEND_PORT=8000

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -qO- "http://127.0.0.1:${FRONTEND_PORT}/healthz" >/dev/null 2>&1 || exit 1

# Base image's entrypoint runs envsubst on the template, then launches nginx.
