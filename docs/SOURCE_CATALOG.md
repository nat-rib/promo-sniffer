# Initial source catalog

This is the owner-selected candidate list for the first source feasibility spike. Entries are candidates only: none is considered monitored until its access method is reviewed, an adapter is implemented and tests pass.

## Games and electronics

| Source | Type | Status | Validation notes |
|---|---|---|---|
| Gamerhut | Store | Candidate | Canonical URL confirmed by owner: https://www.gamerhut.com.br/. Validate product-page format and collection method. |
| Amazon Brasil | Marketplace | Candidate | Capture seller, condition, shipping, coupon and Prime/member conditions. |
| Shopee | Marketplace | Candidate | Capture seller, condition, shipping, vouchers and platform coupon context. |
| Mercado Livre | Marketplace | Candidate | Capture seller reputation, condition, shipping and coupon context. |

## Clothing and sneakers

| Source | Type | Status | Validation notes |
|---|---|---|---|
| Netshoes | Store/marketplace | Candidate | Distinguish first-party offers from marketplace sellers where applicable. |
| Centauro | Store/marketplace | Candidate | Distinguish first-party offers from marketplace sellers where applicable. |
| Dafiti | Store/marketplace | Candidate | Capture seller, size, color, shipping and coupon context. |
| Adidas Brasil | Brand store | Candidate | Capture size, color, model and member/coupon conditions. |

## Promotion websites — selected shortlist

These are the three recommended promotion communities/sites for the initial evaluation. They are not yet approved technical ingestion sources.

| Site | Best fit | Status | Validation notes |
|---|---|---|---|
| [Pelando](https://www.pelando.com.br/) | Broad community deals, user voting and discussion | Candidate | Validate public page/feed availability, terms, rate limits and stable offer URLs. |
| [Promobit](https://www.promobit.com.br/) | Curated offers, coupons and community submissions | Candidate | Validate public page/feed availability, terms, rate limits and stable offer URLs. |
| [Gatry](https://www.gatry.com.br/) | Community deals with comments and store/product context | Candidate | Validate public page/feed availability, terms, rate limits and stable offer URLs. |

Selection rationale: the three cover complementary Brazilian deal-community experiences (community voting/discussion, editorial/moderated curation and active deal threads). This is a practical shortlist, not an objective universal ranking. Do not assume they provide an official API or permit automated scraping.

## Telegram promotion channels

| Channel | Scope | Status | Validation notes |
|---|---|---|---|
| [Ofertas Nintendo BR](https://t.me/ofertasnintendobr) | Nintendo games, consoles and collectibles | Candidate — access pending | Public channel supplied by owner. Channel description says suggestions are submitted via ofertasnintendo.com.br and excludes links, stores, banks, apps, used products and foreign eShops. Confirm whether the channel owner permits bot membership/collection; do not post suggestions or messages. Bot API can only collect new posts after the bot is added with sufficient visibility. |

The Ofertas Nintendo website explains that its Telegram channel publishes promotions first, retains prior posts and supports reactions/comments. This is useful for human review, but it does not grant Promo Sniffer permission to ingest the channel. Historical backfill is not part of the Bot API MVP.

## Still pending

| Source category | Status | Next action |
|---|---|---|
| Additional Telegram groups/channels | Awaiting owner | Owner may provide more links later; verify access and permissions individually. |
| Technical permission for Ofertas Nintendo BR | Pending | Obtain channel-owner approval/add the bot if allowed; otherwise leave as reference-only. |

## Source lifecycle

1. **Candidate** — name selected by owner.
2. **Validated** — canonical URL, access method, terms/policy review and sample evidence documented.
3. **Adapter implemented** — collector and fixture tests pass.
4. **Enabled** — source is actively scheduled for collection.
5. **Paused/unsupported** — collection is stopped or not technically/policy feasible.

A source may not skip from Candidate to Enabled. Never imply that a candidate store, promotion site or Telegram channel is already being monitored.
