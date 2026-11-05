# Promo Sniffer

> Project bootstrap. Product scope and implementation details are intentionally pending confirmation.

Promo Sniffer is the working name for this project. This repository is being initialized with the shared conventions used by `nat-rib/personal-server-tools`.

## Current status

- [x] Repository initialized
- [x] Baseline documentation and repository hygiene
- [ ] Product requirements and supported sources defined
- [ ] Runtime, language and framework selected
- [ ] Application implementation and tests
- [ ] Docker image and deployment workflow
- [ ] VPS deployment and private ingress

## Project decisions

Before implementation, record the agreed product scope, supported promotion sources, collection frequency, persistence requirements, notification channels, and operational constraints in [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md).

## Development

No runtime or package manager has been selected yet. Avoid adding application code or CI commands that assume a language/framework until that decision is recorded.

## Deployment conventions

The intended host conventions are documented in [nat-rib/personal-server-tools](https://github.com/nat-rib/personal-server-tools):

- Compose configuration: `/opt/personal-cloud/apps/promo-sniffer`
- Persistent data: `/opt/personal-cloud/data/promo-sniffer`
- Local backups: `/opt/personal-cloud/backups/promo-sniffer`
- Keep service ports bound to loopback; configure Tailscale Serve separately.
- Keep secrets outside Git and use GitHub Actions secrets for CI/CD.

The application repository will own its Dockerfile, tests, healthcheck, GHCR publishing, deployment workflow, and application-specific rollback.
