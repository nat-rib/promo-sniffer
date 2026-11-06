# Architecture proposal

## Goals

Build a low-maintenance personal service that turns chat instructions into durable price watches, checks multiple sources, records evidence-backed observations and sends actionable alerts. Start small enough for a 1 vCPU / 4 GB VPS.

## High-level design

```text
Telegram user
    |
    v
Telegram Bot Adapter ----> Conversation / Command Service
                                  |
                                  v
                            Watch Service
                                  |
                 +----------------+----------------+
                 |                |                |
                 v                v                v
             Watch DB       Scheduler        Alert Rules
                 |                |                |
                 |                v                |
                 |         Collection Runner       |
                 |                |                |
                 |        +-------+-------+        |
                 |        |       |       |        |
                 |        v       v       v        |
                 |      Store   Deal    Telegram   |
                 |     adapters feeds   adapters  |
                 |        |       |       |        |
                 +--------+-------+-------+--------+
                                  |
                                  v
                         Price Observations
                                  |
                                  v
                           Alert Dispatcher
                                  |
                                  v
                            Telegram user
```

## Suggested modules

- `bot/`: Telegram transport, authorization, commands, callback buttons and message formatting. Keep Telegram SDK types out of domain logic.
- `application/`: use cases for create/list/update/pause/delete watches, ingest observations and dispatch alerts.
- `domain/`: watch rules, product identity, offer, price observation and alert decisions.
- `sources/`: common adapter contract plus store, feed, website and Telegram-chat implementations.
- `collector/`: scheduler, polling, retry/backoff, concurrency limits and source health.
- `persistence/`: repositories and migrations.
- `config/`: validated environment configuration.
- `tests/`: unit tests, adapter contract tests and fixture-based parser tests.

A modular monolith is preferred over microservices: one deployable container initially, with clear internal boundaries.

## Core data model

- `products`: canonical product identity and normalized attributes (title, platform, edition, region, identifiers).
- `watches`: user query, canonical product, target price, currency, condition flags, status and cooldown.
- `sources`: source type, name, configuration reference, enabled state, polling policy and health metadata.
- `offers`: source listing identity, seller, URL, availability and product match confidence.
- `price_observations`: offer, observed price, currency, shipping/coupon context, timestamp and evidence metadata.
- `alerts`: triggering observation, rule type, delivery state and deduplication key.
- `ingestion_checkpoints`: last processed message/item/cursor per source.

Store secrets in environment variables or mounted secret files, never in source configuration or database exports intended for Git.

## Conversation behavior

The bot should support natural-language requests, but never silently create a materially ambiguous watch. Parse a message into a structured proposal and ask the user to confirm it.

Example:

User: "Monitora GTA 6 para PS5 abaixo de R$ 250."

Bot: "Vou monitorar Grand Theft Auto VI para PS5, mídia física ou digital ainda não especificada, e avisar abaixo de R$ 250. Está correto?"

After confirmation, persist the watch and reply with its identifier. Also support deterministic commands such as `/list`, `/watch`, `/pause`, `/resume`, `/remove` and `/help`.

Only allow configured Telegram user IDs in the personal MVP. Unknown users receive no access to watch data.

## Collection and source adapters

Every adapter should expose a small contract: identify source, fetch candidate offers/messages, parse product and price, provide canonical URL/evidence, and report source-specific errors. Keep parsing separate from orchestration.

- Prefer official APIs and feeds.
- Use HTML collection only where allowed, with conservative request rates, caching and clear user-agent identification.
- Keep source-specific rate limits and retry/backoff.
- Store parser version and raw evidence reference to help debug extraction changes.
- Never interpret a coupon-dependent, membership-only, installment or shipping-exclusive price as a normal final price without labeling it.

Product matching should consider platform, edition, condition, seller and identifiers. Low-confidence matches should be excluded from automatic alerts or sent for user confirmation.

## Telegram: interface vs. promotion ingestion

These are separate capabilities:

1. The user-facing bot receives private chat updates and sends alerts.
2. A Telegram source adapter collects new posts only from chats/channels where the bot has been added and has sufficient visibility. In groups, privacy mode/admin status affects which messages are visible.
3. Bot API updates are not an archive API and are retained for at most 24 hours. Do not design historical backfill around Bot API polling.
4. Historical channel backfill can be explored with MTProto and an explicitly authorized user account that is already a member. This is deferred because it needs a user session credential, careful secret handling, access checks and rate-limit controls. It must not scrape private communities without permission.

For MVP, support new posts from a short list of configured public channels that explicitly allow the bot to join, plus manually supplied historical URLs or trusted price-history sources where available.

## Price history semantics

A historical low is only meaningful relative to a defined dataset. Every UI/alert should distinguish:
- Current offer price.
- Lowest price Promo Sniffer has observed since tracking began.
- Imported historical price, including its source and original date.
- External site's advertised historical minimum, including its coverage/methodology when known.

Do not state "lowest ever" when only a partial observation window exists. Show the period and source coverage used to calculate a record.

## Initial deployment shape

- One application container running bot polling and scheduled collection tasks.
- SQLite database on the persistent host mount for a single instance.
- No Redis, message broker, Kubernetes or separate frontend in the first version.
- Health/status command reports bot connectivity, database status and last successful source checks.
- Docker healthcheck should validate process/application health, not merely that the container is running.
- Back up the database using SQLite's online backup mechanism; do not rely on copying a live SQLite file with a generic tar archive.
- Keep host port exposure disabled unless a future webhook or admin endpoint actually needs it. Telegram long polling avoids requiring a public inbound endpoint.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Store markup changes | Fixture tests, parser versioning, source health and failure alerts |
| Wrong product match | Platform/edition/condition attributes and confidence threshold |
| Misleading historical-low claim | Provenance, coverage dates and conservative wording |
| Telegram bot cannot read old posts | Separate MTProto backfill milestone |
| Source blocks/rate limits | Prefer APIs/feeds, throttle, cache and back off |
| Duplicate alerts | Stable offer/rule deduplication key and cooldown |
| VPS resource pressure | Single process/container initially, bounded concurrency and resource monitoring |
