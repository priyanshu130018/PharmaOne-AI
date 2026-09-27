# Multi-stage build for frontend using Node alpine without Nginx.
# Runs the built React application using Vite's production preview server.

FROM node:20-alpine

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY package.json package-lock.json* ./

# Install all dependencies required to build and serve
RUN npm install

# Copy frontend source code
COPY . .

# Build argument: public API URL reachable from the browser
ARG VITE_API_BASE_URL="http://localhost:8000/api/v1"
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Compile production bundle into dist/
RUN npm run build

# Default frontend port
ENV FRONTEND_PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- "http://127.0.0.1:8080/" >/dev/null 2>&1 || exit 1

# Launch Vite's built-in preview server on 0.0.0.0:8080
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "8080"]
