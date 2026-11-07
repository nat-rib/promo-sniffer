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

### API authentication finding (2026-11-06)

The first remote run failed with HTTP 403. Direct checks from the development machine and from the VPS produced the same result:

- `GET https://api.mercadolibre.com/sites/MLB/search?q=...` without credentials returned `403` with body `{"message":"forbidden","error":"forbidden","status":403}`.
- Even the baseline resource `GET https://api.mercadolibre.com/sites/MLB` returned `403` and the policy headers `x-policy-agent-block-code: PA_UNAUTHORIZED_RESULT_FROM_POLICIES` and `x-policy-agent-block-reason: At least one policy returned UNAUTHORIZED`.
- A deliberately invalid bearer token also returned the same policy 403.

The official Mercado Livre documentation now states that API calls must send an OAuth 2.0 access token in the `Authorization: Bearer ...` header ([Autenticação e Autorização](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao)). The probe was calling the correct item-search resource, but it did not send any token. **The 403 was an authentication/policy rejection, not a CAPTCHA, bot challenge or missing endpoint.**

The corrected probe reads `MERCADO_LIVRE_ACCESS_TOKEN` (or an `access_token` field in the stdin JSON payload), sends it only in the HTTP header, and never logs it. If the token is absent, invalid, expired, blocked or lacks the required scope, the probe fails explicitly with a source-health error. It does not retry permanent 401/403 responses and does not fall back to scraping, cookies, proxies or undocumented endpoints.

`/sites/MLB/search` is the official item-search resource used by the probe. The current documentation page highlights seller/nickname/category examples; the free-text `q` filter is the traditional search parameter for the same resource. If Mercado Livre removes `q`, the documented alternative is the catalog product search (`/products/search?status=active&site_id=MLB&q=...`) followed by item lookups for the returned product IDs. That fallback is more expensive and is not implemented until a valid token confirms the need.

Mercado Livre access tokens expire (the authorization-code flow documents a 6-hour lifetime, with a rotating refresh token). For this diagnostic spike, the owner must place a currently valid access token in the repository secret before each run. A production collector will need a durable, rotated-token strategy; that is out of scope until source access is confirmed.

### Diagnostic token setup

Use the official Mercado Livre OAuth 2.0 authorization-code flow. Do not paste the client secret or the access token into chat, source files or workflow logs.

1. Create or select an application in the Mercado Livre developer center: <https://developers.mercadolivre.com.br/devcenter>.
2. Register an exact redirect URI (for example `https://localhost/callback`) and request read access.
3. Open the authorization URL for Brazil, sign in with the application owner account and authorize it:
   `https://auth.mercadolivre.com.br/authorization?response_type=code&client_id=APP_ID&redirect_uri=REDIRECT_URI`
4. Exchange the returned `code` for an access token using `POST https://api.mercadolibre.com/oauth/token` with `grant_type=authorization_code`, `client_id`, `client_secret`, `code` and `redirect_uri`, as documented in [Autenticação e Autorização](https://developers.mercadolivre.com.br/pt_br/autenticacao-e-autorizacao).
5. Store the resulting `access_token` directly in GitHub, without writing it to a file or shell history:

   ```bash
   gh secret set MERCADO_LIVRE_ACCESS_TOKEN --repo nat-rib/promo-sniffer
   ```

6. Run the workflow promptly. If the token expires, repeat the authorization flow; the probe will report HTTP 401/403 rather than retrying or bypassing the control.

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
| `TS_OIDC_CLIENT_ID` | Tailscale OIDC client ID used by `tailscale/github-action` with GitHub Workload Identity Federation |
| `TS_OIDC_AUDIENCE` | Tailscale OIDC audience for the GitHub Actions provider |
| `MERCADO_LIVRE_ACCESS_TOKEN` | Valid Mercado Livre OAuth 2.0 access token with read access. Short-lived; update it before a diagnostic run if it expired |
| `VPS_TAILSCALE_IP` | Tailscale IPv4 address of the Hetzner VPS |
| `VPS_SSH_USER` | VPS SSH account (expected: `deploy`) |
| `VPS_SSH_PRIVATE_KEY` | Dedicated private key for GitHub Actions; its public key must be in the VPS user's `~/.ssh/authorized_keys` |
| `VPS_SSH_KNOWN_HOSTS` | Verified known_hosts entry for the VPS Tailscale address |

Do not reuse the VPS-to-GitHub read-only deploy key for this direction. Generate a separate key pair for GitHub Actions and add only its public key to the VPS. Do not commit any key, Tailscale credential or Mercado Livre token.

The workflow validates `query` (non-empty, at most 200 characters, no control characters) and `limit` (integer from 1 to 50) before connecting to the tailnet. It then sends the query, limit and access token to the VPS as a JSON payload over the SSH stdin stream. The values are never interpolated into a remote shell command, so shell metacharacters in the query remain data. The token is not passed as a command-line argument and is not printed.

To run it, open **Actions → VPS marketplace probe → Run workflow**, select branch `feat/marketplace-collection-spike`, and keep the default Onimusha query. Alternatively, use `gh workflow run vps-marketplace-probe.yml --repo nat-rib/promo-sniffer --ref feat/marketplace-collection-spike -f query="Onimusha Way of the Sword PS5" -f limit=20`.

A successful run proves both outbound API access from the VPS and a valid authenticated Mercado Livre response. It does not by itself approve scheduled production collection or establish Shopee access.

Local checks do not need a network call:

```bash
python3 -m pytest -q tests/test_probe_mercado_livre.py
python3 scripts/probe_mercado_livre.py --check-inputs --query "Onimusha PS5" --limit 20
```
