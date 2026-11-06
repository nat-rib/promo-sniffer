# Promo Sniffer

A personal price-monitoring assistant controlled through Telegram conversations. Tell it what product to watch, where to look, and what price should trigger an alert.

## Product concept

Example:

> "Monitora GTA 6 para PS5. Me avisa se ficar abaixo de R$ 250 ou se aparecer pelo menor preço histórico."

Promo Sniffer keeps a watchlist, checks configured stores and promotion sources on a schedule, records observed prices, and sends alerts when a rule matches.

Telegram is the first interface because its official Bot API is free and straightforward to operate. WhatsApp is a possible future channel, not an MVP dependency.

## MVP scope

- Telegram bot for natural-language watchlist management and alerts.
- Product watch entries with target price, currency, platform/edition and source preferences.
- Configurable store and promotion-source adapters.
- Scheduled price checks with deduplication and rate limits.
- Internal price history with source, timestamp and evidence URL.
- Alerts for target-price hits and observed historical lows.
- Commands to list, inspect, pause, update and remove watches.

Historical prices must be evidence-based. The bot API does not provide arbitrary historical chat export: it receives updates and messages from chats/channels where the bot has access. Backfilling channel history may require a separately authorized Telegram client using MTProto, and is intentionally outside the first MVP. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Current status

- [x] Repository initialized
- [x] Product concept and MVP documented
- [x] Architecture direction documented
- [ ] Confirm initial stores and promotion channels
- [ ] Implement Telegram conversation flow
- [ ] Implement price-source adapters and history
- [ ] Tests, Docker image and CI/CD
- [ ] VPS deployment

## Documentation

- [Product brief](docs/PROJECT_BRIEF.md)
- [Architecture proposal](docs/ARCHITECTURE.md)
- [Contribution workflow](CONTRIBUTING.md)

## Development

The proposed baseline is Python with a modular-monolith architecture. The runtime, libraries and database will be finalized with the first implementation PR, after source selection and a thin technical spike.

## Deployment conventions

The shared conventions live in [nat-rib/personal-server-tools](https://github.com/nat-rib/personal-server-tools):

- Compose: `/opt/personal-cloud/apps/promo-sniffer`
- Persistent data: `/opt/personal-cloud/data/promo-sniffer`
- Local backups: `/opt/personal-cloud/backups/promo-sniffer`
- Bind service ports to loopback; configure Tailscale Serve separately.
- Keep secrets outside Git and use GitHub Actions secrets for CI/CD.

This repository owns its Dockerfile, tests, healthcheck, GHCR publishing, deployment workflow and application-specific rollback.
