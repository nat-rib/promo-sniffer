# Initial source catalog

This is the owner-selected candidate list for the first source feasibility spike. Entries are candidates only: none is considered monitored until its access method is reviewed, an adapter is implemented and tests pass.

## Games and electronics

| Source | Type | Status | Validation notes |
|---|---|---|---|
| Gamerhut | Store | Candidate | Confirm exact canonical domain and product-page format. |
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

## Pending sources

| Source category | Status | Next action |
|---|---|---|
| Telegram promotion groups/channels | Awaiting owner | Owner will provide links; verify bot access and permissions. |
| Promotion-aggregator websites | Not selected | Select at least one site, then validate terms and extraction method. |

## Source lifecycle

1. **Candidate** — name selected by owner.
2. **Validated** — canonical URL, access method, terms/policy review and sample evidence documented.
3. **Adapter implemented** — collector and fixture tests pass.
4. **Enabled** — source is actively scheduled for collection.
5. **Paused/unsupported** — collection is stopped or not technically/policy feasible.

A source may not skip from Candidate to Enabled. Never imply that a candidate store is already being monitored.
