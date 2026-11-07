#!/usr/bin/env python3
"""Read-only Mercado Livre search probe for the Promo Sniffer marketplace spike.

The probe calls the officially documented Mercado Livre item search resource
(``/sites/MLB/search``) and emits normalized observations to stdout.

Mercado Livre requires an OAuth 2.0 access token in the ``Authorization``
header for API calls. The token is read from ``MERCADO_LIVRE_ACCESS_TOKEN`` or
from the optional ``--input-json`` payload. It is never written to logs or to
the process command line of the remote execution.

The probe does not use cookies, browser automation, CAPTCHA solving, proxies or
undocumented endpoints.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import socket
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

API_URL = "https://api.mercadolibre.com/sites/MLB/search"
SITE_ID = "MLB"
SOURCE = "mercado_livre"
USER_AGENT = (
    "PromoSniffer/0.2 "
    "(+https://github.com/nat-rib/promo-sniffer; personal price research)"
)
TOKEN_ENV_VAR = "MERCADO_LIVRE_ACCESS_TOKEN"

DEFAULT_QUERY = "Onimusha Way of the Sword PS5"
DEFAULT_LIMIT = 20
MIN_LIMIT = 1
MAX_LIMIT = 50
MAX_QUERY_LENGTH = 200
DEFAULT_TIMEOUT = 20.0
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER = 60.0

EXIT_INVALID_INPUT = 2
EXIT_NETWORK = 3
EXIT_MISSING_TOKEN = 4
EXIT_API_ERROR = 5
EXIT_INVALID_RESPONSE = 6


class ProbeError(Exception):
    """Base class for expected probe failures."""

    exit_code = 1


class InvalidInputError(ProbeError):
    exit_code = EXIT_INVALID_INPUT


class NetworkError(ProbeError):
    exit_code = EXIT_NETWORK


class MissingTokenError(ProbeError):
    exit_code = EXIT_MISSING_TOKEN


class APIError(ProbeError):
    exit_code = EXIT_API_ERROR

    def __init__(self, status: int, message: str, retry_after: Optional[float] = None):
        self.status = status
        self.retry_after = retry_after
        super().__init__(message)


class ResponseError(ProbeError):
    exit_code = EXIT_INVALID_RESPONSE


def validate_query(value: Any) -> str:
    """Return a normalized query or raise InvalidInputError.

    PostgreSQL-style or shell-like characters are allowed because the query is
    data, never evaluated as code. Control characters are rejected to keep logs
    and the remote transport predictable.
    """
    if not isinstance(value, str):
        raise InvalidInputError("query must be a string")
    query = value.strip()
    if not query:
        raise InvalidInputError("query must not be empty or contain only whitespace")
    if len(query) > MAX_QUERY_LENGTH:
        raise InvalidInputError(
            f"query must be at most {MAX_QUERY_LENGTH} characters (got {len(query)})"
        )
    if any(ord(char) < 32 or ord(char) == 127 for char in query):
        raise InvalidInputError("query must not contain control characters")
    return query


def validate_limit(value: Any) -> int:
    """Return an integer limit between 1 and 50 or raise InvalidInputError."""
    if isinstance(value, bool):
        raise InvalidInputError("limit must be an integer between 1 and 50")
    if isinstance(value, int):
        limit = value
    elif isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()):
        limit = int(value.strip())
    else:
        raise InvalidInputError("limit must be an integer between 1 and 50")
    if not MIN_LIMIT <= limit <= MAX_LIMIT:
        raise InvalidInputError(
            f"limit must be between {MIN_LIMIT} and {MAX_LIMIT} (got {limit})"
        )
    return limit


def build_url(query: str, limit: int) -> str:
    """Build the search URL with every user value percent-encoded."""
    return f"{API_URL}?{urlencode({'q': query, 'limit': limit})}"


def build_headers(access_token: str) -> Dict[str, str]:
    if not isinstance(access_token, str) or not access_token.strip():
        raise MissingTokenError(
            f"{TOKEN_ENV_VAR} is not set; the Mercado Livre API requires an "
            "OAuth 2.0 access token"
        )
    return {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {access_token.strip()}",
    }


def validate_payload(payload: Any) -> Dict[str, Any]:
    """Validate the top-level API response before processing results."""
    if not isinstance(payload, dict):
        raise ResponseError("Mercado Livre response must be a JSON object")

    results = payload.get("results")
    if results is None:
        raise ResponseError("Mercado Livre response is missing the 'results' list")
    if not isinstance(results, list):
        raise ResponseError("Mercado Livre response field 'results' must be a list")

    paging = payload.get("paging")
    if paging is not None and not isinstance(paging, dict):
        raise ResponseError("Mercado Livre response field 'paging' must be an object")

    return payload


def _as_string(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value else None


def _as_price(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


def _as_optional_bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _valid_url(value: Any) -> Optional[str]:
    if not isinstance(value, str) or not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value


def normalize_results(payload: Dict[str, Any], query: str, limit: int) -> Dict[str, Any]:
    """Normalize API results into the internal observation model.

    An observation is only emitted when it has a valid price and URL. Optional
    fields are always present (as ``None`` when missing). Duplicate item IDs or
    URLs are dropped and counted in ``skipped``.
    """
    validate_payload(payload)

    observations: List[Dict[str, Any]] = []
    skipped = {
        "invalid_item": 0,
        "missing_price": 0,
        "missing_url": 0,
        "duplicate": 0,
    }
    seen_ids = set()
    seen_urls = set()

    for item in payload.get("results", []):
        if not isinstance(item, dict):
            skipped["invalid_item"] += 1
            continue

        price = _as_price(item.get("price"))
        if price is None:
            skipped["missing_price"] += 1
            continue

        item_url = _valid_url(item.get("permalink"))
        if item_url is None:
            skipped["missing_url"] += 1
            continue

        item_id = _as_string(item.get("id"))
        if (item_id and item_id in seen_ids) or item_url in seen_urls:
            skipped["duplicate"] += 1
            continue
        if item_id:
            seen_ids.add(item_id)
        seen_urls.add(item_url)

        shipping = item.get("shipping")
        if not isinstance(shipping, dict):
            shipping = {}
        seller = item.get("seller")
        if not isinstance(seller, dict):
            seller = {}

        observations.append(
            {
                "source": SOURCE,
                "source_item_id": item_id,
                "title": _as_string(item.get("title")),
                "price": price,
                "currency": _as_string(item.get("currency_id")),
                "url": item_url,
                "thumbnail": _as_string(item.get("thumbnail")),
                "seller_id": seller.get("id"),
                "condition": _as_string(item.get("condition")),
                "free_shipping": _as_optional_bool(shipping.get("free_shipping")),
                "listing_type": _as_string(item.get("listing_type_id")),
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "raw_attributes": {
                    "category_id": _as_string(item.get("category_id")),
                    "catalog_product_id": _as_string(item.get("catalog_product_id")),
                    "official_store_id": item.get("official_store_id"),
                },
            }
        )

    paging = payload.get("paging") if isinstance(payload.get("paging"), dict) else {}
    total = paging.get("total")
    if isinstance(total, bool) or not isinstance(total, int):
        total = None

    return {
        "source": SOURCE,
        "query": query,
        "site_id": _as_string(payload.get("site_id")) or SITE_ID,
        "limit": limit,
        "total": total,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "observations": observations,
        "skipped": skipped,
        "skipped_count": sum(skipped.values()),
    }


def _server_message(exc: HTTPError, access_token: str) -> str:
    """Read a short, safe error message from the response body.

    The raw body is never logged. Any accidental token echo is redacted.
    """
    message = ""
    try:
        raw = exc.read(4096)
        data = json.loads(raw)
        if isinstance(data, dict):
            for key in ("message", "error", "error_description", "description"):
                value = data.get(key)
                if isinstance(value, str) and value:
                    message = value
                    break
    except Exception:
        message = ""

    message = re.sub(r"\s+", " ", message).strip()[:200]
    if access_token:
        message = message.replace(access_token, "[redacted]")
    return message


def _retry_after_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    value = value.strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        seconds = (retry_at - datetime.now(timezone.utc)).total_seconds()
    if seconds < 0:
        return 0.0
    return seconds


def _backoff_seconds(attempt: int) -> float:
    # attempt is 1-based; cap the deterministic part and add jitter.
    return min(2.0 ** (attempt - 1), 8.0) + random.uniform(0.0, 0.5)


def _error_for_status(
    exc: HTTPError,
    access_token: str,
    attempt: int,
    retry_after: Optional[float],
) -> APIError:
    detail = _server_message(exc, access_token)
    guidance = {
        400: "check the query and limit parameters",
        401: "the access token is missing, invalid or expired",
        403: (
            "access denied; verify the token scopes, application status and "
            "allowed IPs in the Mercado Livre developer panel"
        ),
        404: "the search endpoint was not found; the API may have changed",
        429: "rate limited by Mercado Livre",
    }.get(exc.code, "unexpected Mercado Livre API error")

    message = f"Mercado Livre API returned HTTP {exc.code} ({guidance})"
    if detail and detail.lower() not in {"forbidden", "unauthorized"}:
        message = f"{message}: {detail}"
    if retry_after is not None:
        message = f"{message} [Retry-After={retry_after:g}s]"
    if attempt > 1:
        message = f"{message} after {attempt} attempts"
    return APIError(exc.code, message, retry_after=retry_after)


def request_payload(
    url: str,
    headers: Dict[str, str],
    timeout: float = DEFAULT_TIMEOUT,
    max_attempts: int = MAX_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Fetch and decode JSON, retrying only transient failures.

    429 responses respect ``Retry-After`` when present. 5xx and transport
    errors use bounded exponential backoff with jitter. 400/401/403/404 and
    invalid JSON are never retried.
    """
    access_token = ""
    authorization = headers.get("Authorization", "")
    if authorization.startswith("Bearer "):
        access_token = authorization[len("Bearer ") :]

    for attempt in range(1, max_attempts + 1):
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ResponseError(
                    "Mercado Livre returned a response that is not valid JSON"
                ) from exc
        except HTTPError as exc:
            retry_after = _retry_after_seconds(
                exc.headers.get("Retry-After") if exc.headers else None
            )
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if retryable and attempt < max_attempts:
                if exc.code == 429 and retry_after is not None:
                    if retry_after > MAX_RETRY_AFTER:
                        raise _error_for_status(
                            exc, access_token, attempt, retry_after
                        ) from exc
                    delay = retry_after
                else:
                    delay = _backoff_seconds(attempt)
                sleep(delay)
                continue
            raise _error_for_status(exc, access_token, attempt, retry_after) from exc
        except (TimeoutError, socket.timeout, URLError, ConnectionError) as exc:
            if attempt < max_attempts:
                sleep(_backoff_seconds(attempt))
                continue
            reason = getattr(exc, "reason", None) or exc
            raise NetworkError(
                f"could not reach the Mercado Livre API after {attempt} attempts: {reason}"
            ) from exc

    raise NetworkError("could not reach the Mercado Livre API")


def search(
    query: str,
    limit: int,
    access_token: str,
    timeout: float = DEFAULT_TIMEOUT,
    max_attempts: int = MAX_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> Dict[str, Any]:
    """Validate inputs, call the API and return normalized observations."""
    normalized_query = validate_query(query)
    normalized_limit = validate_limit(limit)
    headers = build_headers(access_token)
    payload = request_payload(
        build_url(normalized_query, normalized_limit),
        headers,
        timeout=timeout,
        max_attempts=max_attempts,
        sleep=sleep,
    )
    return normalize_results(payload, normalized_query, normalized_limit)


def require_access_token(explicit: Optional[str] = None) -> str:
    token = explicit if explicit is not None else os.environ.get(TOKEN_ENV_VAR, "")
    if not isinstance(token, str) or not token.strip():
        raise MissingTokenError(
            f"{TOKEN_ENV_VAR} is not set; the Mercado Livre API requires an "
            "OAuth 2.0 access token. See docs/MARKETPLACE_COLLECTION_SPIKE.md"
        )
    return token.strip()


def _read_input_json(path: str) -> Dict[str, Any]:
    try:
        if path == "-":
            raw = sys.stdin.read()
        else:
            with open(path, "r", encoding="utf-8") as handle:
                raw = handle.read()
    except OSError as exc:
        raise InvalidInputError(f"could not read input JSON: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidInputError("input JSON is not valid JSON") from exc
    if not isinstance(data, dict):
        raise InvalidInputError("input JSON must be an object")
    return data


def _resolve_inputs(args: argparse.Namespace) -> Tuple[str, int, Optional[str]]:
    if args.input_json:
        data = _read_input_json(args.input_json)
        if "query" not in data or "limit" not in data:
            raise InvalidInputError(
                "input JSON must contain 'query' and 'limit' fields"
            )
        query = validate_query(data["query"])
        limit = validate_limit(data["limit"])
        token = data.get("access_token")
        if token is not None and not isinstance(token, str):
            raise InvalidInputError("input JSON field 'access_token' must be a string")
        return query, limit, token

    query = validate_query(args.query if args.query is not None else DEFAULT_QUERY)
    limit = validate_limit(args.limit if args.limit is not None else DEFAULT_LIMIT)
    return query, limit, None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Mercado Livre search probe. Requires an OAuth 2.0 access "
            f"token in {TOKEN_ENV_VAR}."
        )
    )
    parser.add_argument(
        "--query",
        default=None,
        help=f"search phrase (default: {DEFAULT_QUERY})",
    )
    parser.add_argument(
        "--limit",
        default=None,
        help=f"maximum listings, {MIN_LIMIT}-{MAX_LIMIT} (default: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--input-json",
        default=None,
        metavar="PATH",
        help=(
            "read {'query', 'limit', 'access_token'} from a JSON file, or '-' "
            "for stdin; values replace --query/--limit"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"request timeout in seconds (default: {DEFAULT_TIMEOUT:g})",
    )
    parser.add_argument(
        "--check-inputs",
        action="store_true",
        help="validate inputs and exit without calling the API or needing a token",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        query, limit, input_token = _resolve_inputs(args)
        if args.check_inputs:
            print(json.dumps({"valid": True, "query_length": len(query), "limit": limit}))
            return 0

        if args.timeout <= 0:
            raise InvalidInputError("timeout must be greater than zero")

        access_token = require_access_token(input_token)
        print(
            f"Probe: searching Mercado Livre site {SITE_ID} "
            f"(limit={limit}, query_length={len(query)})",
            file=sys.stderr,
        )
        result = search(
            query,
            limit,
            access_token,
            timeout=args.timeout,
        )
    except ProbeError as exc:
        print(f"Probe error: {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive boundary
        print(f"Probe error: unexpected failure ({type(exc).__name__})", file=sys.stderr)
        return 1

    print(
        f"Probe: {len(result['observations'])} observation(s) normalized, "
        f"{result['skipped_count']} skipped",
        file=sys.stderr,
    )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
