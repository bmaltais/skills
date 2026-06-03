---
name: containerization
description: >
  Comprehensive best practices for creating optimized, secure, and efficient
  Docker images and managing containers. Covers multi-stage builds, image layer
  optimization, security scanning, and runtime best practices. Use when reviewing
  or writing Dockerfiles, docker-compose files, or container deployment configs.
  Trigger on phrases like "review my Dockerfile", "optimize this image",
  "Docker best practices", "container security", "multi-stage build",
  "reduce image size", "docker-compose review".
applyTo: '**/Dockerfile,**/Dockerfile.*,**/*.dockerfile,**/docker-compose*.yml,**/docker-compose*.yaml,**/compose*.yml,**/compose*.yaml'
categories: [software-development, devops]
agents: [copilot]
version: 1.0.0
metadata:
  source: custom
  scope: global
---

# Containerization & Docker Best Practices

Guide developers in building efficient, secure, and maintainable Docker images.

## Core Principles

1. **Immutability** — Never modify running containers; build new images for every change.
2. **Portability** — Externalize config; images run identically across environments.
3. **Isolation** — One process per container; use namespaces and resource limits.
4. **Efficiency** — Smaller images = faster builds, pulls, deploys, fewer CVEs.

## Routing Table

| Topic                                          | Reference                  |
| ---------------------------------------------- | -------------------------- |
| Dockerfile authoring (multi-stage, layers, COPY, CMD, ENV) | `references/dockerfile.md` |
| Security (non-root, minimal base, signing, secrets, caps)  | `references/security.md`   |
| Runtime & orchestration (resources, logging, volumes, nets) | `references/runtime.md`    |
| Review checklist & troubleshooting                          | `references/checklist.md`  |

## Quick Decision Guide

- **Compiled language?** → Multi-stage build mandatory. See `references/dockerfile.md`.
- **Security review?** → Start with `references/security.md` + `references/checklist.md`.
- **Image too large?** → Check base image, layer optimization, `.dockerignore` in `references/dockerfile.md`.
- **Runtime issues?** → Resource limits, health checks, logging in `references/runtime.md`.

## Key Rules (Always Apply)

- Use **specific version tags**, never `latest` in production.
- Run as **non-root user** — create a dedicated user in every Dockerfile.
- Use **exec form** for CMD/ENTRYPOINT (`["cmd", "arg"]` not shell form).
- **Never** embed secrets in image layers.
- Always include a **HEALTHCHECK** instruction.
- Always include a comprehensive **`.dockerignore`** file.
