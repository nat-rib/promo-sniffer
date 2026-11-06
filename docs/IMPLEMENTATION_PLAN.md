# Implementation plan

This plan turns the confirmed product decisions into small, reviewable increments. The implementation target is the existing Hetzner KVM 1 VPS (1 vCPU, 4 GB RAM), so the first release is deliberately a single Python application and SQLite database.

## Confirmed scope

- Telegram Bot API as the only MVP user interface.
- Stores are registered manually; no preloaded store catalog.
- Source categories: Telegram groups/channels, promotion websites and store websites.
- Optional LLM interpretation. Core workflows must work without an LLM.
- Brazil / BRL, single authorized owner, no public web UI.
- Historical Telegram backfill, WhatsApp and multi-user support are deferred.

## Proposed technical baseline

- Python 3.12+ (confirm exact runtime in the bootstrap PR).
- A maintained Telegram Bot API library; select and pin it in the first code PR.
- SQLAlchemy 2 + Alembic for persistence and schema evolution.
- SQLite for the first single-instance deployment.
- APScheduler or a small in-process scheduler; jobs must be idempotent and recover safely after restart.
- Pydantic settings and domain schemas for configuration/input validation.
- pytest, Ruff and type checking in CI.
- Docker Compose, GHCR and GitHub Actions, following personal-server-tools.
- Optional LLM integration behind a provider-neutral interface, disabled by default and configured only by environment variables.

## Phases and acceptance criteria

### Phase 0 — Source feasibility spike

Goal: prove that the first sources can be accessed and parsed before building broad automation.

- Define the source registry fields and source lifecycle.
- Select a small initial test set manually: at least one store website, one promotion website and one Telegram channel/group.
- For each candidate, record URL/chat identifier, access method, terms/access review, expected polling interval and sample evidence.
- Build fixture examples for representative product/price messages/pages.
- Verify that the Telegram bot can see new posts only after it is added with sufficient permissions.
- Mark sources without a viable adapter as pending, not active.

Acceptance: each source selected for the MVP has an explicit access method, a fixture and a documented rate-limit policy; unsupported sources are clearly identified.

### Phase 1 — Application skeleton and persistence

Goal: establish a runnable, testable modular monolith.

- Add package structure for bot, application, domain, sources, collector, interpretation, persistence and config.
- Add settings validation and safe startup checks.
- Add SQLAlchemy models and initial Alembic migration for products, watches, sources, offers, observations, alerts and ingestion checkpoints.
- Add repository interfaces and SQLite implementation.
- Add pytest, Ruff, type checking and GitHub Actions for tests/lint.
- Add structured logging and graceful shutdown.

Acceptance: application starts with a local SQLite database, applies migrations, passes CI and does not require Telegram or LLM credentials for unit tests.

### Phase 2 — Telegram bot and watch management

Goal: manage watches through a private Telegram conversation.

- Configure bot token through environment/secret.
- Authorize only configured Telegram user IDs.
- Implement /help, /watch, /list, /pause, /resume, /remove and /status.
- Implement a guided /watch flow with confirmation before persistence.
- Add deterministic parsing for simple natural-language patterns.
- Add source registry commands or guided flow for manually registering/listing/enabling/disabling stores and promotion sources.
- Keep optional LLM parsing behind a feature flag and provider interface; do not block this phase on it.

Acceptance: authorized owner can create and manage a watch and source without an LLM; unauthorized users cannot read or mutate data; ambiguous product/rule input requires confirmation.

### Phase 3 — First store and promotion-site adapters

Goal: collect real offers from a narrow, validated source set.

- Implement common adapter protocol and normalized offer schema.
- Implement one store adapter and one promotion website adapter selected in Phase 0.
- Store source evidence URL, seller, product match confidence, price, shipping/coupon context, availability and observed timestamp.
- Add fixture-based parser tests and adapter contract tests.
- Add per-source timeout, rate limit, retry/backoff and health status.

Acceptance: fixture tests cover normal, malformed and changed markup cases; collector stores valid observations and surfaces adapter failures without crashing the bot.

### Phase 4 — Telegram promotion ingestion

Goal: ingest new promotion posts from manually configured Telegram chats.

- Add the bot to selected chats/channels with required visibility.
- Persist message identifiers and ingestion checkpoints.
- Parse new posts into candidate offers and route them through the same product-matching/evidence pipeline.
- Handle edits/deletions where supported and deduplicate repeated posts.
- Document that arbitrary historical backfill is not supported by Bot API.

Acceptance: new posts are ingested once, source visibility limitations are surfaced and no historical backfill claim is made.

### Phase 5 — Scheduler, price history and alerts

Goal: make monitoring continuous and useful.

- Add configurable per-source polling intervals and bounded concurrency.
- Add idempotent scheduling, backoff and restart-safe checkpoints.
- Implement target-price crossing and new observed minimum rules.
- Add stable alert deduplication keys and cooldown.
- Send Telegram alerts with evidence URL, timestamp and price caveats.
- Add /history and source health/status visibility.

Acceptance: repeated identical observations do not spam alerts; target and historical-observed-low tests pass; every alert can be traced to stored evidence.

### Phase 6 — Deployment and operations

Goal: deploy safely using shared VPS conventions.

- Add Dockerfile, Compose template, non-root runtime where practical and healthcheck.
- Persist SQLite under /opt/personal-cloud/data/promo-sniffer.
- Keep application files under /opt/personal-cloud/apps/promo-sniffer.
- Use /opt/personal-cloud/backups/promo-sniffer for backups.
- Add GHCR build/publish and deploy workflow; tests run on pull requests and develop.
- Configure secrets in GitHub/VPS, never in repository.
- Add SQLite online backup/restore procedure and rollback instructions.
- Bind any future local endpoint to loopback; Telegram long polling needs no public inbound port.

Acceptance: deployment is repeatable, healthcheck reports application/database status, backup restore is tested and rollback is documented.

### Phase 7 — Post-MVP evaluation

Only after the core MVP is stable:
- Evaluate additional store/site adapters.
- Evaluate MTProto historical Telegram import with a separate security and privacy review.
- Evaluate external price-history integrations and provenance quality.
- Evaluate optional LLM provider(s) for more flexible natural language.
- Consider WhatsApp only after cost, policy and operational tradeoffs are reviewed.
- Revisit PostgreSQL or a separate worker only if measured load/concurrency requires it.

## Proposed pull-request sequence

1. PR 1 — feat: add application skeleton and quality gates: package layout, settings, logging, tests, lint/type checks and CI.
2. PR 2 — feat: add persistence models and repositories: SQLAlchemy, Alembic, SQLite schema and repository tests.
3. PR 3 — feat: add Telegram bot and guided watch flows: authorization, commands, deterministic conversation and source registry management.
4. PR 4 — feat: add source adapter framework and first collectors: common adapter contract plus the first validated store and deal-site adapters.
5. PR 5 — feat: ingest configured Telegram promotion chats: new-message ingestion and checkpoints.
6. PR 6 — feat: schedule price checks and send alerts: scheduler, history, target and historical-low rules, deduplication.
7. PR 7 — ci: add container publishing and VPS deployment: Docker, GHCR, deploy, backup/restore and rollback.

Each PR should be independently testable and update the docs when a decision changes. Avoid implementing all source adapters at once.

## First implementation PR exit criteria

Before coding the bot, the first PR should establish:
- A clean local developer setup and documented commands.
- CI that runs tests and lint on PRs and pushes to develop.
- Configuration validation with no real secrets required for tests.
- A minimal app entry point and graceful shutdown.
- A clear module structure that does not couple Telegram/LLM SDKs to the domain.
