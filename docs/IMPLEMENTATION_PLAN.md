# Implementation plan

This plan turns the confirmed product decisions into small, reviewable increments. The implementation target is the existing Hetzner KVM 1 VPS (1 vCPU, 4 GB RAM), so the first release is deliberately a single Python application and SQLite database.

## Confirmed scope

- Telegram Bot API as the only MVP user interface.
- Stores are registered manually; no preloaded store catalog.
- Initial store candidates: Gamerhut, Amazon Brasil, Shopee, Mercado Livre, Netshoes, Centauro, Dafiti and Adidas Brasil. See SOURCE_CATALOG.md.
- Promotion-site shortlist: Pelando, Promobit and Gatry.
- First Telegram channel candidate: Ofertas Nintendo BR (@ofertasnintendobr); bot access/owner permission remains pending.
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

Goal: validate access and extraction for the owner-selected candidates before implementing broad automation.

**Selected store candidates**
- Games/electronics: Gamerhut, Amazon Brasil, Shopee and Mercado Livre.
- Clothing/sneakers: Netshoes, Centauro, Dafiti and Adidas Brasil.

**Selected promotion website shortlist**
- Pelando — broad user-submitted community offers and voting.
- Promobit — moderated/curated offers, coupons and community.
- Gatry — active community deal threads and comments.

These are the first three to evaluate, not an assertion that they expose official APIs or permit scraping. Verify each site's terms, public endpoints/feeds, robots policy, rate limits and stable offer links before collection.

**Telegram candidate**
- Ofertas Nintendo BR (@ofertasnintendobr), public channel URL https://t.me/ofertasnintendobr.
- Channel description restricts submissions and directs suggestions to ofertasnintendo.com.br. Do not submit posts or messages.
- Confirm whether the channel owner permits adding the bot with read visibility. Until then, treat it as reference-only; do not assume the bot can read it.
- Bot API collection is for new messages after access is granted; historical backfill remains out of scope.

**Validation work**
- Confirm canonical domains and product-page patterns for stores.
- Review access/terms and identify official API, feed or permitted collection method.
- Capture representative product URLs and fixture examples.
- Determine how seller, new/used condition, shipping, coupons, membership and installment prices are represented.
- Define conservative polling intervals, rate limits, caching and backoff.
- Assign each source a status: candidate, validated, adapter implemented, enabled or unsupported.
- Do not mark a source as actively monitored until its adapter is implemented and tested.

Acceptance: at least one store candidate has a documented viable collection method and fixture; each selected promotion site and Telegram candidate has an explicit access/permission status; no source is represented as monitored when it is not.

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
- Choose first store adapter after Phase 0 validation; Gamerhut is the first candidate to assess.
- Evaluate Pelando, Promobit and Gatry for permitted collection. Implement only a source with a stable, documented access method.
- Keep remaining registered candidates pending until validated.
- Store source evidence URL, seller, product match confidence, price, shipping/coupon context, availability and observed timestamp.
- Add fixture-based parser tests and adapter contract tests.
- Add per-source timeout, rate limit, retry/backoff and health status.

Acceptance: fixture tests cover normal, malformed and changed markup cases; collector stores valid observations and surfaces adapter failures without crashing the bot.

### Phase 4 — Telegram promotion ingestion

Goal: ingest new promotion posts from manually configured Telegram chats.

- Add the bot to selected chats/channels only after owner permission and required visibility are confirmed.
- Start with Ofertas Nintendo BR only if channel access is explicitly granted.
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

1. PR 1 — feat: add application skeleton and quality gates.
2. PR 2 — feat: add persistence models and repositories.
3. PR 3 — feat: add Telegram bot and guided watch flows.
4. PR 4 — feat: add source adapter framework and first validated collectors.
5. PR 5 — feat: ingest configured Telegram promotion chats.
6. PR 6 — feat: schedule price checks and send alerts.
7. PR 7 — ci: add container publishing and VPS deployment.

Each PR should be independently testable and update the docs when a decision changes. Avoid implementing all source adapters at once.

## First implementation PR exit criteria

Before coding the bot, establish:
- A clean local developer setup and documented commands.
- CI that runs tests and lint on PRs and pushes to develop.
- Configuration validation with no real secrets required for tests.
- A minimal app entry point and graceful shutdown.
- Clear module boundaries that do not couple Telegram/LLM SDKs to the domain.
