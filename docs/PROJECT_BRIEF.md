# Promo Sniffer — project brief

This document is the source of truth for product decisions. Confirmed decisions and deferred capabilities are explicit.

## Product purpose

A personal price-monitoring assistant controlled through Telegram. The user describes products and alert rules; Promo Sniffer checks configured sources, records evidence-backed prices and sends alerts.

Example: "Monitora GTA 6 para PS5. Me avisa se ficar abaixo de R$ 250 ou se aparecer pelo menor preço histórico."

## Confirmed product decisions

- Stores: manual registration by the owner; no broad preloaded store catalog.
- Promotion sources: Telegram groups/channels, promotion websites and store websites.
- Initial candidate stores are listed in [SOURCE_CATALOG.md](SOURCE_CATALOG.md).
- Telegram promotion groups/channels will be supplied by the owner later; none are selected yet.
- No promotion-aggregator website has been selected yet; this remains an open Phase 0 item.
- Interpretation: LLM is optional. Deterministic commands, guided prompts and schema validation must support the complete MVP without an LLM.
- Initial geography/currency: Brazil / BRL.
- Messaging: Telegram Bot API first; WhatsApp deferred.
- Operation: personal service; only explicitly authorized Telegram user IDs can access it.

## Primary use cases

- Register, enable, disable and inspect stores and promotion sources.
- Create a watch by describing a product, platform/edition and price condition.
- List, inspect, update, pause/resume and remove watches.
- Receive alerts with product, seller/source, price, shipping/coupon caveats, observation date and evidence URL.
- Inspect recorded price history and the coverage behind a historical-low claim.

## Messaging and interpretation

- MVP interface: Telegram bot. The official Bot API supports private conversations, commands and updates.
- WhatsApp is deferred; it adds separate setup and messaging costs.
- Keep messaging behind an adapter so another channel can be added later.
- Deterministic commands and guided conversation are the baseline. Natural-language parsing may use an optional LLM provider behind an interface, but it must never be required for core operation.
- An LLM may propose structured fields; application validation and user confirmation remain authoritative. Never let model output directly trigger collection or alerts without validation.
- Ask clarifying questions when product identity or price conditions are ambiguous.

## Store and promotion-source registry

The owner manually registers each store or promotion source. A registry entry should include:

- Display name and source type (store website, promotion website, Telegram channel/group).
- Canonical URL or Telegram chat identifier, where applicable.
- Enabled/disabled state.
- Adapter type and configuration reference (never credentials in plaintext).
- Polling interval, rate-limit policy and last successful check.
- Terms/access review status and operational notes.

Registration is separate from integration availability: a source can be registered but remain not yet supported until a compatible adapter is implemented and tested. The bot must communicate this clearly instead of implying it is monitoring a source it cannot collect from.

## Initial candidate store groups

### Games and electronics

- Gamerhut
- Amazon Brasil
- Shopee
- Mercado Livre

### Clothing and sneakers

- Netshoes
- Centauro
- Dafiti
- Adidas Brasil

These are owner-selected candidates, not yet validated integrations. Confirm canonical domains, access method, terms, product-page patterns, seller/condition handling and rate limits during Phase 0. Amazon, Shopee and Mercado Livre are marketplaces: seller identity, new/used condition, shipping and coupon requirements must be captured separately from the platform name.

## Source policy and Telegram limitations

- Prefer official APIs, feeds and affiliate/product feeds where available.
- Website collection is permitted only where the site's terms, access controls and applicable policies allow it. Use conservative rates, caching and backoff.
- Do not assume all stores or Telegram communities are accessible or permit automated collection.
- The Telegram Bot API can collect new messages from channels where the bot is a member. In groups, privacy mode/admin status affects visibility.
- Bot API is not an arbitrary history-export API; updates are retained for no more than 24 hours.
- Historical Telegram backfill may later be evaluated through MTProto with an explicitly authorized user account that has access. This is outside the MVP and requires separate security, privacy and rate-limit review. Never ask users to provide their Telegram password or login code to the bot.

## Product identity and monitoring rules

- Identify products precisely: title/query, platform, edition, region and SKU/GTIN when available.
- Do not merge different editions, platforms, bundles, used/refurbished items or regional versions.
- A watch may have a target price, a historical-low alert, or both.
- Support optional filters for condition, seller, shipping and coupon requirements.
- Low-confidence product matches require clarification or confirmation.

## Price history and evidence

Store each observation with product identity, source, seller, observed price, currency, shipping/coupon context when known, availability, URL, timestamp and extraction metadata.

- Deduplicate repeated observations without losing meaningful price changes.
- Preserve source provenance and tracking coverage start date.
- Distinguish "lowest price observed by Promo Sniffer" from "lowest price ever". Never claim an all-time low without adequate evidence and coverage.
- Imported historical prices must retain their original source/date and be marked as imported, not observed live by the service.
- Normalize to BRL only when conversion is explicit; retain original currency and exchange-rate metadata.

## Detection and delivery

- Scheduled checks run per source with configurable intervals, backoff and rate limits.
- Alert on target-price threshold crossing and on a new minimum in the stored observation history.
- Avoid repeated alerts for unchanged offers; support cooldowns.
- Include why the alert fired and a link to evidence.

## Non-functional requirements

- Personal, low-volume service sized for the existing small Hetzner VPS.
- Respect source terms, robots policies where applicable, API limits and privacy.
- Secrets and Telegram tokens remain outside Git and container images.
- Backups must cover persistent watch and price data and be restorable.
- Structured logs, source health, last successful collection and parser failure counts.

## Technical direction

| Area | Direction |
|---|---|
| Language | Python |
| Architecture | Modular monolith |
| Messaging | Telegram Bot API |
| Database | SQLite for the single-instance MVP |
| Scheduling | In-process scheduler initially |
| Interpretation | Deterministic command/guided flow; optional LLM adapter |
| Sources | Manually registered, pluggable store/site/Telegram adapters |
| Deployment | Docker Compose, GHCR and GitHub Actions |
| Hosting | Existing Hetzner VPS, subject to resource validation |
| Access | Telegram only; no public web UI required |

## Delivery milestones

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for phases, acceptance criteria and the proposed PR sequence.
