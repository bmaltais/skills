# Review Checklist & Troubleshooting

## Dockerfile Review Checklist

- [ ] Multi-stage build used (compiled languages, heavy build tools)?
- [ ] Minimal, version-pinned base image (`alpine`, `slim`, `distroless`)?
- [ ] Layers optimized (combined `RUN`, cleanup in same layer)?
- [ ] `.dockerignore` present and comprehensive?
- [ ] `COPY` instructions specific and minimal?
- [ ] Non-root `USER` defined?
- [ ] `EXPOSE` used for port documentation?
- [ ] `CMD`/`ENTRYPOINT` in exec form (not shell form)?
- [ ] No hardcoded secrets or sensitive data in layers?
- [ ] `HEALTHCHECK` instruction defined?
- [ ] Environment variables used for configuration (not hardcoded)?
- [ ] Static analysis (Hadolint, Trivy) integrated in CI?

---

## Troubleshooting

### Large Image Size

1. Check layer sizes: `docker history <image>`
2. Switch to smaller base image (alpine/distroless)
3. Implement multi-stage build
4. Combine `RUN` commands and clean temp files in same layer
5. Review `.dockerignore` for missing exclusions
6. Check for unnecessary dev dependencies in final stage

### Slow Builds

1. Reorder instructions: least-changing first
2. Add/update `.dockerignore` to reduce build context
3. Copy dependency files before source code (cache deps install)
4. Use BuildKit for parallel stage builds
5. Debug with `docker build --no-cache` to isolate cache issues

### Container Not Starting / Crashing

1. Check CMD/ENTRYPOINT syntax (exec form vs shell form)
2. Review logs: `docker logs <container_id>`
3. Verify all runtime dependencies present in final stage
4. Check resource limits aren't too restrictive
5. Verify file permissions for non-root user
6. Test interactively: `docker run -it --entrypoint sh <image>`

### Permission Errors

1. Verify `chown` runs before `USER` switch
2. Check mounted volume permissions match container user UID/GID
3. Ensure writable directories exist and are owned by app user
4. For mounted volumes: match host UID to container user UID

### Network Connectivity Issues

1. Verify `EXPOSE` matches actual application port
2. Check `-p` mapping in `docker run` or ports in compose
3. Verify container is on correct Docker network
4. Check firewall rules on host
5. Test from inside container: `docker exec -it <id> sh`
