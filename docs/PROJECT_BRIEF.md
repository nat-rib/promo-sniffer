# Promo Sniffer — project brief

This document is the source of truth for product decisions. Confirmed direction is recorded; unresolved implementation choices remain explicit.

## Product purpose

A personal price-monitoring assistant controlled through a messaging app. The user describes products and alert rules in natural language. The service monitors configured stores and promotion communities, builds its own evidence-backed price history, and sends an alert when a target price or a verified historical low is found.

Example: "Monitora GTA 6 para PS5. Me avisa se ficar abaixo de R$ 250 ou se aparecer pelo menor preço histórico."

## Users and primary use cases

- Create a watch by describing a product, platform/edition, target price and optional sources.
- Ask which products are being monitored and inspect their current status.
- Change a target price, pause/resume a watch, or remove it.
- Receive alerts with product, store/community, current price, shipping/coupon caveats when available, observed date and evidence link.
- Ask for a product's recorded price history and the basis for a historical-low claim.

## Messaging interface

- **MVP: Telegram bot.** The official Telegram Bot API is free and supports private bot conversations, commands and updates.
- WhatsApp is deferred. The official WhatsApp Business Platform has category- and market-based message pricing and additional setup requirements.
- Keep messaging behind an adapter/interface so another channel can be added later.
- Only the bot owner/authorized Telegram user IDs may create or modify watches in the personal MVP.

## Promotion sources

- Initial geography/currency: Brazil / BRL.
- Sources are pluggable adapters: store APIs, affiliate/product feeds where available, permitted website collection, and Telegram channels/groups explicitly configured by the owner.
- Maintain a registry of sources with enabled state, polling interval, rate limits, parser version and last successful check.
- Do not assume every store or Telegram community is accessible or permits automated collection.
- Start with a small, explicitly selected set of sources; expand after reliability and terms are validated.

### Telegram source limitations

The Telegram Bot API is suitable for the user-facing bot and for collecting new messages from channels where the bot is a member. In groups, the bot generally needs admin access or privacy mode disabled to receive all relevant messages. It cannot be treated as an API for downloading arbitrary old group/channel history. Bot updates are retained by Telegram for no more than 24 hours.

Historical backfill from public channels may be evaluated separately using Telegram's MTProto client API with an explicitly authorized user account that has access to those channels. This introduces session-secret, account-security, privacy, rate-limit and operational concerns; it is not part of the initial MVP. Never ask the user to provide their Telegram password or login code to the bot.

## Product identity and monitoring rules

- A watch should identify the product precisely: title/query, platform, edition, region and relevant SKU/GTIN when available.
- Avoid merging different editions, platforms, bundles, used/refurbished items or regional versions.
- A watch can have a target price, a historical-low alert, or both.
- Allow source-level exclusions and optional filters (new/used, seller, shipping, coupon requirement).
- Natural-language parsing must produce a reviewable watch summary; ask for clarification when product identity or price conditions are ambiguous.
- LLM use, if any, is an optional parser layer. Core rules and price calculations must be deterministic and testable.

## Price history and evidence

Store each observation with product/watch identity, source, seller, observed price, currency, shipping/coupon context when known, availability, URL, timestamp and extraction metadata.

- Preserve raw source evidence or a compact source snapshot when legally and operationally appropriate.
- Deduplicate repeated observations without losing meaningful price changes.
- Keep historical coverage start date and source provenance visible.
- Distinguish "lowest price observed by Promo Sniffer" from "lowest price ever". Never claim an all-time low without adequate external evidence and coverage.
- Importing historical Telegram posts or third-party price-history pages is a separate ingestion path; validate dates, product identity, price context and source reliability.
- Normalize prices to BRL only when conversion is explicit; retain original currency and exchange-rate metadata.

## Detection and delivery

- Scheduled checks run per source with configurable intervals, backoff and rate limits.
- Alert on target-price threshold crossing and on a new verified minimum in the stored observation history.
- Avoid repeated alerts for the same unchanged offer; support cooldowns and recovery notifications.
- Alert payload includes why it fired and a link to the evidence.

## Non-functional requirements

- Personal, low-volume service sized for the existing small Hetzner VPS; measure CPU, memory and storage before adding infrastructure.
- Respect source terms, robots policies where applicable, API limits and privacy.
- Secrets and Telegram tokens remain outside Git and container images.
- Backups must cover persistent price/watch data and be restorable.
- Observability: structured logs, source health, last successful collection and failed parser counts.

## Technical direction (proposal, to validate in implementation PR)

| Area | Direction |
|---|---|
| Language | Python |
| Architecture | Modular monolith with source adapters |
| Messaging | Telegram Bot API first |
| Database | SQLite for initial single-instance MVP; evaluate PostgreSQL only if concurrency/scale requires it |
| Scheduling | In-process scheduler initially; durable job strategy if reliability needs justify it |
| Product parsing | Deterministic command/schema validation; optional LLM adapter for natural language |
| Deployment | Docker Compose, GHCR and GitHub Actions |
| Hosting | Existing Hetzner VPS, subject to resource validation |
| Private access | No public web UI required for MVP; Telegram is the interface |

## Delivery milestones

1. Select first stores and Telegram promotion channels.
2. Validate access, terms, product matching and price extraction on real examples.
3. Implement Telegram bot and watchlist CRUD.
4. Implement one store adapter and price observation/history.
5. Add scheduler, deduplication, threshold and historical-low alerts.
6. Add Telegram source ingestion for newly arriving posts in configured chats.
7. Add tests, Docker healthcheck, GHCR and deployment workflow.
8. Evaluate historical backfill and additional sources as a separate milestone.
