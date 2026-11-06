# Marketplace collection spike — Onimusha PS5

Date: 2026-11-05  
Status: **technical validation in progress**. Neither marketplace is enabled for scheduled collection yet.

## Test product identity

Use one canonical watch target for the spike:

- Product: **Onimusha: Way of the Sword**
- Platform: PlayStation 5
- Edition: Standard
- Media: physical copy preferred; digital offers must be classified separately
- Condition: new only for the primary comparison
- Market: Brazil
- Currency: BRL

Do not merge Nintendo Switch 2, Steelbook, imported/international, used/refurbished, digital-license or accessory/manual listings into the primary PS5 standard-edition price series.

## Initial public-web observations

These are manual search observations, not Promo Sniffer collector output and not a durable price history.

| Source | Observation | Caveat |
|---|---:|---|
| Mercado Livre | R$ 315,27 Pix in one listing | Search result showed 7% Pix discount, free shipping and 1,000+ sales. Preserve both Pix and regular price when available. |
| Shopee | R$ 358,15 Pix in one listing | Listing was marked international; shipping coupon and import taxes may change the landed cost. |
| Mercado Livre deal aggregator | R$ 283 with coupon | Coupon-dependent offer; must be stored as a conditional price, not the unconditional base price. |

References checked during research:
- Mercado Livre official developer docs: https://developers.mercadolivre.com.br/pt_br/itens-e-buscas
- Mercado Livre search results: https://lista.mercadolivre.com.br/onimusha
- Shopee listing sample: https://shopee.com.br/-PS5-Onimusha-Way-of-the-Sword-i.1625435036.58267545974
- Shopee affiliate API documentation surfaced at https://www.affiliateshopee.com.br/documentacao; confirm current API terms and access with Shopee before production use.

## Mercado Livre — first collector probe

The official developer documentation describes the `/sites/{SITE_ID}/search` resource and item lookup resources. For Brazil, the search site identifier is `MLB`. The probe in `scripts/probe_mercado_livre.py` performs a read-only search and emits normalized JSON observations.

Run locally:

```bash
python3 scripts/probe_mercado_livre.py
python3 scripts/probe_mercado_livre.py --query "Onimusha Way of the Sword PS5" --limit 30
```

Fields captured when present:
- item ID, title, price and currency
- canonical listing URL and thumbnail
- seller ID, condition and listing type
- free-shipping flag
- category/catalog identifiers as raw attributes
- collection timestamp

The probe intentionally does not claim the result is a valid match. A later matching stage must classify platform, edition, media, condition, region/import status, seller, shipping and coupons. The first pass should retain uncertain listings for review rather than silently discard or merge them.

Before scheduled production use, verify current API authentication/rate-limit requirements, item-detail fields, seller reputation lookup and platform terms. Handle 401/403/429 as source-health states, not as reasons to fall back to scraping.

## Shopee — access gate

The research found a Shopee Affiliate Open API surface, including a GraphQL product-offer search, but it is credentialed and affiliate-oriented. It is not evidence of unrestricted marketplace search access or complete coverage of all listings.

Next steps:
1. Confirm the owner has an active Shopee Affiliate account and can request/activate API credentials.
2. Confirm that the API terms allow this personal price-monitoring use case.
3. Obtain credentials through Shopee's official process; keep App ID/secret in environment secrets, never in Git or chat.
4. Test whether `productOfferV2` can find the target item and determine which listing fields, seller identity, currency, price range, shipping and promotion conditions are returned.
5. If access is unavailable or coverage is insufficient, mark Shopee as **blocked/unsupported pending approved access**. Do not bypass login, CAPTCHA, anti-bot controls or use undocumented private endpoints.

No Shopee adapter is implemented until this gate passes.

## Price observation model implications

A marketplace observation must not be represented by one ambiguous `price` field alone. Preserve at least:
- displayed/base price and currency
- Pix/instant-payment price, if distinct
- coupon/voucher amount and eligibility text, if known
- shipping amount and free-shipping flag, when available
- landed/estimated total only when its components are known
- seller ID/name and seller reputation snapshot, when available
- item condition, platform, edition, media type, region/import status
- listing URL, source item ID, timestamp and raw source payload

A conditional coupon price must never be compared as if every user could obtain it. Historical-low alerts should say **lowest observed by Promo Sniffer since tracking began**, and compare like-for-like product variants and price conditions.

## Acceptance criteria for this spike

- [ ] Mercado Livre probe returns valid JSON or records a clear API access/rate-limit error.
- [ ] At least one returned listing is manually checked against the canonical PS5 standard physical product.
- [ ] Pix, coupon and shipping conditions are not collapsed into a single unconditional price.
- [ ] Shopee API eligibility and credentials are confirmed by the owner.
- [ ] No source is marked enabled until access, terms, adapter tests and product matching are validated.


## Run the probe from the Hetzner VPS through GitHub Actions

The repository now contains a manual workflow at `.github/workflows/vps-marketplace-probe.yml`. It connects a GitHub-hosted runner to the tailnet, copies the probe to `/tmp` on the VPS and executes it there as the configured SSH user. This is a diagnostic run only: it does not deploy the application, change Compose services, touch persistent app data or restart containers.

Configure these repository Actions secrets before running it:

| Secret | Value |
|---|---|
| `TS_AUTHKEY` | Tailscale auth key for a short-lived GitHub Actions runner, tagged/authorized by your tailnet ACL |
| `VPS_TAILSCALE_IP` | Tailscale IPv4 address of the Hetzner VPS |
| `VPS_SSH_USER` | VPS SSH account (expected: `deploy`) |
| `VPS_SSH_PRIVATE_KEY` | Dedicated private key for GitHub Actions; its public key must be in the VPS user's `~/.ssh/authorized_keys` |
| `VPS_SSH_KNOWN_HOSTS` | Verified known_hosts entry for the VPS Tailscale address |

Do not reuse the VPS-to-GitHub read-only deploy key for this direction. Generate a separate key pair for GitHub Actions and add only its public key to the VPS. Do not commit any key or Tailscale auth key.

After adding secrets, open **Actions → VPS marketplace probe → Run workflow**, select branch `feat/marketplace-collection-spike`, and keep the default Onimusha query. The output is the response observed from the VPS network, with no browser cookies or logged-in marketplace session.

The workflow has not been executed yet because the required repository secrets and VPS-side SSH authorization must be configured by the owner. A successful run proves outbound API access from the VPS; it does not by itself approve scheduled production collection or establish Shopee access.
