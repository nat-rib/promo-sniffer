#!/usr/bin/env python3
"""Read-only Mercado Livre search probe for the Promo Sniffer marketplace spike.

Uses the public site search endpoint and writes normalized observations to stdout.
No credentials, cookies, browser automation, or page scraping are used.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "https://api.mercadolibre.com/sites/MLB/search"


def search(query: str, limit: int) -> dict:
    url = f"{API_URL}?{urlencode({'q': query, 'limit': limit})}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "PromoSniffer/0.1 (personal price research; contact: repo owner)",
        },
    )
    with urlopen(request, timeout=20) as response:
        payload = json.load(response)

    observations = []
    for item in payload.get("results", []):
        shipping = item.get("shipping") or {}
        seller = item.get("seller") or {}
        observations.append(
            {
                "source": "mercado_livre",
                "source_item_id": item.get("id"),
                "title": item.get("title"),
                "price": item.get("price"),
                "currency": item.get("currency_id"),
                "url": item.get("permalink"),
                "thumbnail": item.get("thumbnail"),
                "seller_id": seller.get("id"),
                "condition": item.get("condition"),
                "free_shipping": shipping.get("free_shipping"),
                "listing_type": item.get("listing_type_id"),
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "raw_attributes": {
                    "category_id": item.get("category_id"),
                    "catalog_product_id": item.get("catalog_product_id"),
                    "official_store_id": item.get("official_store_id"),
                },
            }
        )

    return {
        "source": "mercado_livre",
        "query": query,
        "site_id": payload.get("site_id"),
        "total": (payload.get("paging") or {}).get("total"),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "observations": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query",
        default="Onimusha Way of the Sword PS5",
        help="Search phrase (default: Onimusha Way of the Sword PS5)",
    )
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 51))
    args = parser.parse_args()

    try:
        result = search(args.query, args.limit)
    except HTTPError as exc:
        print(f"Mercado Livre API returned HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        return 2
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"Could not query Mercado Livre API: {exc}", file=sys.stderr)
        return 3

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
