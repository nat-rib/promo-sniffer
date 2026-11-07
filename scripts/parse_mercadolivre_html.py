#!/usr/bin/env python3
"""Parse a manually saved Mercado Livre HTML page.

This utility is intentionally offline: it reads an HTML file that the user
saved from their own browser and extracts JSON-LD and the
``window.__PRELOADED_STATE__`` payload. It does not fetch pages, use cookies,
spoof a browser identity or bypass any access control.

Usage:
    python3 scripts/parse_mercadolivre_html.py --input ~/Downloads/page.html
    python3 scripts/parse_mercadolivre_html.py --input page.html --state-keys-only
"""
from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional


class _JsonLdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.blocks: List[str] = []
        self._inside = False
        self._buffer: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Any]) -> None:
        if tag.lower() != "script":
            return
        attributes = {str(key).lower(): value for key, value in attrs}
        script_type = (attributes.get("type") or "").lower()
        if script_type == "application/ld+json":
            self._inside = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._inside:
            self.blocks.append("".join(self._buffer))
            self._inside = False
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._inside:
            self._buffer.append(data)


def extract_json_ld(html: str) -> List[Any]:
    """Return every valid JSON-LD document found in the saved page."""
    collector = _JsonLdCollector()
    collector.feed(html)
    documents: List[Any] = []
    for block in collector.blocks:
        try:
            documents.append(json.loads(block))
        except json.JSONDecodeError:
            continue
    return documents


def extract_preloaded_state(html: str) -> Optional[Any]:
    """Extract ``window.__PRELOADED_STATE__ = {...};`` with balanced braces."""
    marker = "window.__PRELOADED_STATE__"
    marker_index = html.find(marker)
    if marker_index == -1:
        return None

    start = html.find("{", marker_index)
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(html)):
        char = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start : index + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _as_name(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        name = value.get("name")
        return name if isinstance(name, str) else None
    return None


def _first_offer(document: Dict[str, Any]) -> Dict[str, Any]:
    offers = document.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        return {}
    return offers


def summarize_json_ld(documents: List[Any]) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for document in documents:
        entries = document if isinstance(document, list) else [document]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            offer = _first_offer(entry)
            summaries.append(
                {
                    "@type": entry.get("@type"),
                    "name": entry.get("name"),
                    "sku": entry.get("sku"),
                    "url": entry.get("url"),
                    "brand": _as_name(entry.get("brand")),
                    "price": offer.get("price"),
                    "priceCurrency": offer.get("priceCurrency"),
                    "availability": offer.get("availability"),
                    "seller": _as_name(offer.get("seller")),
                }
            )
    return summaries


def parse_saved_html(html: str, include_state_keys: bool = True) -> Dict[str, Any]:
    json_ld_documents = extract_json_ld(html)
    state = extract_preloaded_state(html)

    result: Dict[str, Any] = {
        "source": "saved_html",
        "json_ld_blocks_found": len(json_ld_documents),
        "json_ld": summarize_json_ld(json_ld_documents),
        "preloaded_state_found": state is not None,
    }
    if include_state_keys:
        result["preloaded_state_keys"] = (
            sorted(state.keys()) if isinstance(state, dict) else None
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Offline parser for a manually saved Mercado Livre HTML page. "
            "It never fetches network resources."
        )
    )
    parser.add_argument("--input", required=True, help="saved HTML file path")
    parser.add_argument(
        "--state-keys-only",
        action="store_true",
        help="omit the list of top-level __PRELOADED_STATE__ keys",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        with open(args.input, "r", encoding="utf-8", errors="replace") as handle:
            html = handle.read()
    except OSError as exc:
        print(f"Could not read saved HTML: {exc}", file=sys.stderr)
        return 2

    result = parse_saved_html(html, include_state_keys=not args.state_keys_only)
    if not result["json_ld_blocks_found"] and not result["preloaded_state_found"]:
        print(
            "No JSON-LD or __PRELOADED_STATE__ found in the saved page. "
            "Make sure you saved the product page, not the verification page.",
            file=sys.stderr,
        )
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
