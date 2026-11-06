# Promo Sniffer

A personal price-monitoring assistant controlled through Telegram conversations. Tell it what product to watch, which sources to use, and what price should trigger an alert.

## Product concept

Example:

> "Monitora GTA 6 para PS5. Me avisa se ficar abaixo de R$ 250 ou se aparecer pelo menor preço histórico."

Promo Sniffer keeps a watchlist, checks manually registered stores and promotion sources on a schedule, records observed prices, and sends alerts when a rule matches.

Telegram is the first interface. WhatsApp is a possible future channel, not an MVP dependency.

## Confirmed MVP decisions

- Stores and promotion sources are registered manually by the owner.
- Initial store candidates: Gamerhut, Amazon Brasil, Shopee, Mercado Livre, Netshoes, Centauro, Dafiti and Adidas Brasil.
- Telegram groups/channels will be added when the owner provides their links.
- A promotion-aggregator website is still to be selected.
- LLM interpretation is optional; deterministic commands and guided conversations must work without it.
- Initial geography/currency: Brazil / BRL.
- Personal use, restricted to authorized Telegram user IDs.
- Python modular monolith and SQLite for the initial single-instance deployment.

Registering a source does not mean it is already integrated. A source without a validated adapter must be shown as pending/unsupported, not silently monitored. See [source catalog](docs/SOURCE_CATALOG.md).

## Important Telegram limitation

The Telegram Bot API can receive new messages from chats/channels where the bot has access, but it is not an arbitrary historical archive API. Historical backfill may require a separate MTProto implementation and security review; it is outside the MVP.

## Documentation

- [Product brief](docs/PROJECT_BRIEF.md)
- [Source catalog](docs/SOURCE_CATALOG.md)
- [Architecture proposal](docs/ARCHITECTURE.md)
- [Implementation plan and PR sequence](docs/IMPLEMENTATION_PLAN.md)
- [Contribution workflow](CONTRIBUTING.md)

## Current status

- [x] Repository initialized
- [x] Product scope and architecture documented
- [x] Initial store candidates selected
- [ ] Validate canonical domains, access and collection methods
- [ ] Select a promotion-aggregator website
- [ ] Receive Telegram group/channel links
- [ ] Application skeleton and CI
- [ ] Persistence and watch management
- [ ] Telegram bot
- [ ] Source adapters, scheduler and alerts
- [ ] Docker, CI/CD and VPS deployment

## Deployment conventions

Shared VPS conventions live in [nat-rib/personal-server-tools](https://github.com/nat-rib/personal-server-tools):

- App: `/opt/personal-cloud/apps/promo-sniffer`
- Persistent data: `/opt/personal-cloud/data/promo-sniffer`
- Backups: `/opt/personal-cloud/backups/promo-sniffer`
- Bind service ports to loopback; configure Tailscale Serve separately.
- Keep secrets outside Git and use GitHub Actions secrets for CI/CD.

This repository owns its Dockerfile, tests, healthcheck, GHCR publishing, deployment workflow and application-specific rollback.
