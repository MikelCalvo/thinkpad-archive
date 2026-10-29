# Static HTTP origin behind NetBird

The Dockerfile builds only public catalogue data and local assets. Tests and the internal-link checker run before the serving image is produced. Python and source data are absent from the final Caddy image. No manufacturer originals or mirrors are included.

Build:

    docker build -t thinkpad-archive .

The build requires Docker BuildKit. Ordinary builds also generate a collection-free bilingual ZIP and checksum under `/downloads/`, used by the native offline menu. These are generated files copied into the serving images, not a writable runtime volume. Static-only hosting serves them without counting. The opt-in statistics stack proxies only versioned catalogue ZIP paths to its bounded transfer handler, which keeps a separate daily version counter after a full send; checksum files remain static. The hosted menu displays the actual ZIP's SHA-256 in a compact selectable field; its sibling checksum file remains available for tooling without requiring a separate UI download. Archive assembly disables its own download control and never nests another ZIP.

Its test step mounts `/tmp` as a disposable tmpfs so SQLite test commits do not depend on the writable image layer's fsync latency. All tests and their production timeout/refusal limits remain in place. This mount exists only during that build step; it does not change `/data`, the runtime statistics volume or its durability.

The container serves plain HTTP on port 8080 as UID/GID 10001. Map it to an available private host port and point the NetBird reverse proxy there. NetBird manages the public domain, HTTPS and certificates; this origin needs no certificate, private key or port 443. Restrict the host bind to the mesh interface required by that proxy.

Caddy serves ordinary files, not an SPA fallback: missing paths return 404. /healthz is a liveness endpoint. Its admin API is disabled. Run with a read-only filesystem, all capabilities dropped, no-new-privileges and bounded memory/PIDs. /tmp, /config and /data may use temporary filesystems; give UID/GID 10001 ownership of /config and /data. No writable persistent application data is needed.

## Explicit opt-in statistics

The default/last Docker target still builds the static-only site. The optional `stats` and `stats-web` targets and `deploy/compose.stats.yaml` enable the public dashboard and first-party collection; see [statistics setup and privacy boundaries](statistics.md). Use the Compose build pack for this stack, with `/deploy/compose.stats.yaml` as the repository file. Set ANALYTICS_ORIGIN to the exact public HTTPS origin, STATS_BIND to the private host interface and STATS_PORT to the existing origin port; retain COOLIFY_WEBHOOK_UPSTREAM when the existing signed GitHub deployment hook is used. Preserve the named stats-data volume across redeployments and rollback. It stores only public aggregate counters, retained indefinitely. Do not apply the static-only no-volume rollback description below to that optional stack. An ordinary Dockerfile deployment remains collection-free.

## Coolify auto-deploy

Create a public Git application from MikelCalvo/thinkpad-archive, branch main, using the Dockerfile build pack. Expose container port 8080, map an available private host port and enable automatic deployment. Do not enable Coolify's HTTPS redirect: NetBird terminates TLS. Disable preview deployments unless explicitly needed.

Set COOLIFY_WEBHOOK_UPSTREAM at runtime to a private HTTP endpoint for the existing Coolify instance. Only POST /_deploy/github is proxied, to the fixed Coolify manual GitHub webhook path. Other deployment paths and the Coolify admin/API routes are not forwarded. The POST body limit is 2 MB. Choose a reachable private endpoint and never supply a user-controlled destination.

Generate a random GitHub webhook secret in Coolify, then configure the same secret for a repository webhook at https://YOUR_NETBIRD_DOMAIN/_deploy/github, content type application/json, push events only and TLS verification enabled. Do not store that secret in this repository. Coolify checks HMAC signatures, repository and configured branch. GET on the hook returns 404; an unsigned push must not enqueue a deployment.

An update starts after a push to main, not after a local-only commit. Initial deployment must succeed before enabling the external webhook. Verify an authenticated delivery, a rejected unsigned delivery and the deployed commit after a real push before claiming end-to-end auto-deploy.

## Rollback

Use Coolify's deployment history to redeploy the previous successful commit/image. No database migration or content-volume restoration is needed for this static site. A fixed host-port mapping causes a short interruption while Coolify replaces the running container; it is not a zero-downtime rolling deployment. If bootstrap fails, leave the webhook inactive and fix the origin before routing public traffic.
