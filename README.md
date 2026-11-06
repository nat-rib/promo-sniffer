# Promo Sniffer

A personal price-monitoring assistant controlled through Telegram conversations. Tell it what product to watch, which sources to use, and what price should trigger an alert.

## Product concept

> "Monitora GTA 6 para PS5. Me avisa se ficar abaixo de R$ 250 ou se aparecer pelo menor preço histórico."

Promo Sniffer keeps a watchlist, checks manually registered stores and promotion sources on a schedule, records observed prices, and sends alerts when a rule matches.

## Confirmed MVP decisions

- Stores and promotion sources are registered manually by the owner.
- Initial store candidates: Gamerhut, Amazon Brasil, Shopee, Mercado Livre, Netshoes, Centauro, Dafiti and Adidas Brasil.
- Promotion-site shortlist: Pelando, Promobit and Gatry.
- First Telegram channel candidate: Ofertas Nintendo BR (@ofertasnintendobr), pending permission and bot visibility.
- LLM interpretation is optional; deterministic commands and guided conversations must work without it.
- Initial geography/currency: Brazil / BRL.
- Personal use, restricted to authorized Telegram user IDs.
- Python modular monolith and SQLite for the initial single-instance deployment.

Registering a source does not mean it is integrated or monitored. See [source catalog](docs/SOURCE_CATALOG.md).

## Important Telegram limitation

The Telegram Bot API can receive new messages from chats/channels where the bot has access, but it is not an arbitrary historical archive API. Historical backfill may require a separate MTProto implementation and security review; it is outside the MVP.

## Documentation

- [Product brief](docs/PROJECT_BRIEF.md)
- [Source catalog](docs/SOURCE_CATALOG.md)
- [Architecture proposal](docs/ARCHITECTURE.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Contribution workflow](CONTRIBUTING.md)

## Deployment conventions

Shared VPS conventions live in [nat-rib/personal-server-tools](https://github.com/nat-rib/personal-server-tools):
- App: `/opt/personal-cloud/apps/promo-sniffer`
- Data: `/opt/personal-cloud/data/promo-sniffer`
- Backups: `/opt/personal-cloud/backups/promo-sniffer`

Keep secrets outside Git. This repository owns its Dockerfile, tests, healthcheck, GHCR publishing, deployment workflow and application-specific rollback.
