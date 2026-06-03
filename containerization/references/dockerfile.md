# Dockerfile Authoring

## Multi-Stage Builds (Golden Rule)

Separate build-time dependencies from runtime. Always use for compiled languages.

```dockerfile
# Stage 1: Dependencies
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Stage 2: Build
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 3: Test
FROM build AS test
RUN npm run test
RUN npm run lint

# Stage 4: Production
FROM node:18-alpine AS production
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package*.json ./
USER node
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

**Rules:**
- Name stages descriptively (`AS build`, `AS test`, `AS production`)
- Copy only necessary artifacts between stages via `COPY --from=<stage>`
- Use different base images for build vs runtime when appropriate
- Parallel stages (no dependencies) can be built concurrently

---

## Base Image Selection

| Priority | Image Type     | Use Case                          |
| -------- | -------------- | --------------------------------- |
| 1        | `distroless`   | Maximum security, no shell needed |
| 2        | `alpine`       | ~5MB base, most use cases         |
| 3        | `slim`         | When musl/Alpine causes issues    |
| 4        | Full distro    | Only for debugging/special deps   |

- **Always** pin to a specific version: `node:18.17-alpine`, not `node:latest`
- Use language-specific images: `python:3.11-slim-bookworm`, `openjdk:17-jre-slim`
- Prefer Alpine unless musl libc causes compatibility issues (some compiled binaries need glibc)

---

## Layer Optimization

**Order:** Least-changing → most-changing instructions.

```dockerfile
# BAD: Multiple layers, no cleanup
FROM ubuntu:20.04
RUN apt-get update
RUN apt-get install -y python3 python3-pip
RUN pip3 install flask
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*

# GOOD: Single layer with cleanup
FROM ubuntu:20.04
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install flask && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
```

**Rules:**
- Combine related `RUN` commands to minimize layers
- Clean temp files in the **same** `RUN` (otherwise they persist in prior layer)
- Use `\` for multi-line readability
- Place `COPY package*.json` before `COPY . .` to cache dependency installs

---

## COPY Strategy

```dockerfile
# Copy dependency manifests first (changes rarely)
COPY package*.json ./
RUN npm ci

# Copy source code (changes often)
COPY src/ ./src/
COPY public/ ./public/
COPY config/ ./config/
```

- Be specific — avoid `COPY . .` when possible
- Copy files that change together in the same instruction
- Never copy secrets or `.env` files

---

## .dockerignore

Always include. Reduces build context size and prevents accidental inclusion.

```dockerignore
# Version control
.git*

# Dependencies (installed in container)
node_modules
vendor
__pycache__

# Build artifacts
dist
build
*.o
*.so

# Development/sensitive files
.env.*
*.log
coverage
.nyc_output

# IDE/OS files
.vscode
.idea
*.swp
.DS_Store
Thumbs.db

# Documentation and tests
*.md
docs/
test/
tests/
spec/
__tests__/
```

---

## CMD & ENTRYPOINT

| Pattern                | Use Case                              |
| ---------------------- | ------------------------------------- |
| `CMD ["exe", "arg"]`  | Simple execution, most containers     |
| `ENTRYPOINT + CMD`    | Container-as-executable with defaults |

```dockerfile
# Container as executable — users can override args
ENTRYPOINT ["/app/start.sh"]
CMD ["--config", "prod.conf"]
```

- **Always use exec form** (`["cmd"]`) not shell form (`cmd`) for proper signal handling
- Shell scripts as entrypoints are fine for complex startup logic

---

## Environment Variables

```dockerfile
# Build-time variables
ARG BUILD_VERSION
ENV APP_VERSION=$BUILD_VERSION

# Runtime defaults (overridable)
ENV NODE_ENV=production
ENV PORT=3000
ENV LOG_LEVEL=info
```

- Use `ENV` for defaults; allow runtime override
- Use `ARG` for build-time-only values
- **Never** put secrets in `ENV` — use secrets management at runtime
- Validate required env vars at application startup (fail fast)
