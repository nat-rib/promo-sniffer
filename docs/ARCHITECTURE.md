# Architecture proposal

## Goals

Build a low-maintenance personal service that turns chat instructions into durable price watches, checks manually configured sources, records evidence-backed observations and sends actionable alerts. Keep the first deployment small enough for a 1 vCPU / 4 GB VPS.

## High-level design

Telegram user
  -> Telegram Bot Adapter
  -> Conversation / Command Handler <-> Optional LLM Parser
  -> validated intent
  -> Watch and Source Services
  -> Persistence + Scheduler
  -> Collection Runner
  -> Store adapters / Promotion-site adapters / Telegram adapters
  -> Price Observations
  -> Alert Rules
  -> Telegram Dispatcher
  -> Telegram user

## Architectural decisions

- One Python modular-monolith application, one deployable container initially.
- Telegram Bot API with long polling; no public inbound port required.
- SQLite on persistent storage for the initial single-instance deployment.
- Deterministic commands and guided prompts are the baseline interaction path.
- LLM parsing is an optional adapter. The application validates its output exactly like any other untrusted input; no LLM provider is required to boot or operate the service.
- Stores and promotion sources are registered manually. Registration does not imply an adapter exists: unsupported entries stay visible as configured-but-not-integrated.
- Collection adapters are isolated by source type and tested with saved fixtures.

## Suggested modules

- bot/: Telegram transport, authorization, commands, callback buttons and message formatting.
- application/: use cases for watches, source registry, ingestion, alert dispatch and user confirmation.
- domain/: product identity, watch rules, source state, offer, price observation and alert decisions.
- sources/: adapter contract plus store website, promotion website/feed and Telegram chat implementations.
- collector/: scheduler, polling, retries/backoff, concurrency limits and source health.
- interpretation/: deterministic command parser and optional LLM provider interface.
- persistence/: repositories, SQLite schema and migrations.
- config/: validated environment configuration.
- tests/: unit, adapter-contract and fixture-based parser tests.

Keep Telegram SDK types and LLM provider payloads out of domain logic.

## Core data model

- products: canonical product identity and normalized attributes.
- watches: product, user query, target price, currency, filters, status and cooldown.
- sources: manually registered source name/type, URL or chat identifier, enabled state, adapter key, polling policy, access/terms review and health metadata.
- offers: source listing identity, seller, URL, availability and product-match confidence.
- price_observations: offer, price, currency, shipping/coupon context, timestamp, provenance and extraction metadata.
- alerts: triggering observation, rule type, delivery state and deduplication key.
- ingestion_checkpoints: last processed item/message/cursor per source.

Secrets are stored in environment variables or mounted secret files, never in Git or ordinary source-registry fields.

## Conversation behavior

The bot must support useful operation without an LLM. Initial interaction can use explicit commands and guided questions.

Suggested commands: /help, /watch, /list, /stores, /sources, /pause, /resume, /remove and /status.

Example guided flow:
1. User starts /watch.
2. Bot asks for product and platform/edition.
3. Bot asks for target price and whether to alert on a new observed minimum.
4. Bot displays a summary and asks for confirmation.
5. Application validates and persists the watch.

Natural-language messages may be parsed by deterministic patterns first and an optional LLM second. Any uncertain result becomes a confirmation/clarification step. LLM output is never trusted as executable configuration.

Only configured Telegram user IDs may access the personal MVP.

## Manual source registry and adapters

A source entry has a lifecycle:
1. Registered manually with name, URL/chat and type.
2. Validated for access, terms and collection method.
3. Linked to a supported adapter.
4. Enabled and assigned a polling interval/rate limit.
5. Monitored for health and parser failures.

An entry without a working adapter is marked unsupported or pending integration. Do not silently treat it as active.

Adapter contract should expose source identity, fetch operation, parsing of candidate offers/messages, canonical evidence URL, timestamps and source-specific errors. Prefer official APIs/feeds; use website collection only where allowed. Apply per-source rate limits, caching and backoff.

## Telegram: interface vs. promotion ingestion

These are separate capabilities:
1. The user-facing bot receives private chat updates and sends alerts.
2. A Telegram source adapter collects new posts only from chats/channels where the bot has been added and has sufficient visibility. Group privacy mode/admin status affects message visibility.
3. Bot API is not an archive API; updates are retained for at most 24 hours.
4. Historical backfill may be explored later with MTProto and an explicitly authorized account that already has access. It is deferred due to account-session security, privacy and rate-limit complexity.

For MVP, collect new posts from explicitly configured chats where bot access is permitted. Historical backfill is not an MVP promise.

## Price history semantics

Every observation records provenance and timestamp. Distinguish:
- Current offer price.
- Lowest price observed by Promo Sniffer since tracking began.
- Imported historical price, with source and original date.
- External site's advertised historical minimum, with its coverage/methodology when known.

Never state "lowest ever" when only a partial observation window exists. Display the period and source coverage behind any record.

## Initial deployment shape

- One application container for Telegram polling and scheduled collection.
- SQLite database on persistent host mount.
- No Redis, message broker, Kubernetes or separate frontend initially.
- Health/status reports bot connectivity, database status and last successful source checks.
- Use SQLite online backup; do not copy a live database file with a generic tar operation.
- No public host port for long polling.
- Bounded collection concurrency and per-source timeouts to protect the small VPS.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Store markup changes | Fixture tests, parser versioning and source health |
| Unsupported registered source | Explicit pending/unsupported state |
| Wrong product match | Platform/edition/condition attributes and confidence threshold |
| Misleading historical-low claim | Provenance, coverage dates and conservative wording |
| Telegram bot cannot read old posts | Historical MTProto work deferred |
| Source blocks/rate limits | Prefer APIs/feeds, throttle, cache and back off |
| Duplicate alerts | Stable deduplication key and cooldown |
| LLM output is wrong/unavailable | Deterministic fallback, schema validation and user confirmation |
| VPS resource pressure | Single container, bounded concurrency and resource monitoring |
