import email.message
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

from scripts import probe_mercado_livre as probe


def valid_item(item_id="MLB123", price=319.9, url="https://produto.mercadolivre.com.br/MLB-123"):
    return {
        "id": item_id,
        "title": "Onimusha: Way of the Sword - PS5",
        "price": price,
        "currency_id": "BRL",
        "permalink": url,
        "thumbnail": "https://http2.mlstatic.com/thumb.jpg",
        "seller": {"id": 42},
        "condition": "new",
        "shipping": {"free_shipping": True},
        "listing_type_id": "gold_special",
        "category_id": "MLB1234",
        "catalog_product_id": "MLB999",
        "official_store_id": None,
    }


def valid_payload(items=None, total=None):
    items = [valid_item()] if items is None else items
    return {
        "site_id": "MLB",
        "paging": {"total": len(items) if total is None else total, "limit": 20, "offset": 0},
        "results": items,
    }


def response(payload):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    fake = MagicMock()
    fake.read.return_value = body
    fake.__enter__.return_value = fake
    fake.__exit__.return_value = False
    return fake


def http_error(code, body=b'{"message":"boom"}', retry_after=None):
    headers = email.message.Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(
        probe.API_URL,
        code,
        "reason",
        hdrs=headers,
        fp=io.BytesIO(body),
    )


class QueryValidationTests(unittest.TestCase):
    def test_simple_term(self):
        self.assertEqual(probe.validate_query("onimusha"), "onimusha")

    def test_product_and_model(self):
        query = "Onimusha Way of the Sword PS5"
        self.assertEqual(probe.validate_query(query), query)

    def test_accents(self):
        query = "Onimusha mídia física edição brasileira"
        self.assertEqual(probe.validate_query(query), query)

    def test_special_characters(self):
        query = "Onimusha: Way of the Sword (PS5) - R$ 250,00 + frete"
        self.assertEqual(probe.validate_query(query), query)

    def test_shell_like_characters_are_data(self):
        query = "Onimusha $(rm -rf /); echo `whoami` && \"quoted\""
        self.assertEqual(probe.validate_query(query), query)
        params = parse_qs(urlparse(probe.build_url(query, 1)).query)
        self.assertEqual(params["q"], [query])
        self.assertNotIn("$(", urlparse(probe.build_url(query, 1)).query)
        self.assertNotIn(";", urlparse(probe.build_url(query, 1)).query)

    def test_empty_query_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_query("")

    def test_whitespace_only_query_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_query("   \t  ")

    def test_query_is_stripped(self):
        self.assertEqual(probe.validate_query("  onimusha  "), "onimusha")

    def test_control_characters_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_query("onimusha\nPS5")

    def test_query_too_long_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_query("x" * (probe.MAX_QUERY_LENGTH + 1))


class LimitValidationTests(unittest.TestCase):
    def test_limits_1_20_50(self):
        for value in (1, 20, 50, "1", "20", "50"):
            with self.subTest(value=value):
                self.assertEqual(probe.validate_limit(value), int(value))

    def test_zero_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_limit(0)

    def test_negative_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_limit(-1)

    def test_above_50_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_limit(51)

    def test_text_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_limit("abc")

    def test_boolean_rejected(self):
        with self.assertRaises(probe.InvalidInputError):
            probe.validate_limit(True)


class NormalizationTests(unittest.TestCase):
    def test_multiple_listings_are_normalized(self):
        payload = valid_payload(
            [
                valid_item("MLB1", 319.9, "https://produto.mercadolivre.com.br/MLB-1"),
                valid_item("MLB2", 289.0, "https://produto.mercadolivre.com.br/MLB-2"),
            ]
        )
        result = probe.normalize_results(payload, "onimusha", 20)

        self.assertEqual(result["source"], "mercado_livre")
        self.assertEqual(result["query"], "onimusha")
        self.assertEqual(result["site_id"], "MLB")
        self.assertEqual(result["limit"], 20)
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["observations"]), 2)
        self.assertEqual(result["skipped_count"], 0)
        first = result["observations"][0]
        self.assertEqual(first["source_item_id"], "MLB1")
        self.assertEqual(first["price"], 319.9)
        self.assertEqual(first["currency"], "BRL")
        self.assertEqual(first["seller_id"], 42)
        self.assertTrue(first["free_shipping"])
        self.assertEqual(first["raw_attributes"]["catalog_product_id"], "MLB999")
        self.assertTrue(first["collected_at"].endswith("+00:00"))

    def test_empty_results_is_success(self):
        result = probe.normalize_results(valid_payload([], total=0), "nada", 20)
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["skipped_count"], 0)

    def test_optional_fields_missing(self):
        item = {
            "id": "MLB1",
            "price": 100,
            "permalink": "https://produto.mercadolivre.com.br/MLB-1",
        }
        result = probe.normalize_results(valid_payload([item]), "x", 1)
        observation = result["observations"][0]

        self.assertIsNone(observation["title"])
        self.assertIsNone(observation["currency"])
        self.assertIsNone(observation["thumbnail"])
        self.assertIsNone(observation["seller_id"])
        self.assertIsNone(observation["condition"])
        self.assertIsNone(observation["free_shipping"])
        self.assertIsNone(observation["listing_type"])
        self.assertEqual(
            observation["raw_attributes"],
            {
                "category_id": None,
                "catalog_product_id": None,
                "official_store_id": None,
            },
        )

    def test_item_without_price_is_skipped(self):
        item = valid_item("MLB1")
        item.pop("price")
        result = probe.normalize_results(valid_payload([item]), "x", 1)
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["skipped"]["missing_price"], 1)

    def test_item_without_url_is_skipped(self):
        item = valid_item("MLB1")
        item.pop("permalink")
        result = probe.normalize_results(valid_payload([item]), "x", 1)
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["skipped"]["missing_url"], 1)

    def test_duplicate_items_are_deduplicated(self):
        first = valid_item("MLB1", 100, "https://produto.mercadolivre.com.br/MLB-1")
        duplicate_id = valid_item("MLB1", 101, "https://produto.mercadolivre.com.br/MLB-999")
        duplicate_url = valid_item("MLB2", 102, "https://produto.mercadolivre.com.br/MLB-1")
        result = probe.normalize_results(
            valid_payload([first, duplicate_id, duplicate_url]), "x", 3
        )
        self.assertEqual(len(result["observations"]), 1)
        self.assertEqual(result["skipped"]["duplicate"], 2)

    def test_non_object_item_is_skipped(self):
        result = probe.normalize_results(
            {"site_id": "MLB", "paging": {}, "results": ["not-an-object"]}, "x", 1
        )
        self.assertEqual(result["skipped"]["invalid_item"], 1)

    def test_unexpected_top_level_structure_is_rejected(self):
        with self.assertRaises(probe.ResponseError):
            probe.normalize_results([], "x", 1)  # type: ignore[arg-type]
        with self.assertRaises(probe.ResponseError):
            probe.normalize_results({}, "x", 1)
        with self.assertRaises(probe.ResponseError):
            probe.normalize_results({"results": "nope"}, "x", 1)
        with self.assertRaises(probe.ResponseError):
            probe.normalize_results({"results": [], "paging": []}, "x", 1)


class RequestTests(unittest.TestCase):
    def test_authorization_header_is_sent(self):
        with patch.object(probe, "urlopen", return_value=response(valid_payload())) as mocked:
            probe.search("onimusha", 1, "secret-token", sleep=MagicMock())

        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertIn("PromoSniffer", request.get_header("User-agent"))

    def test_missing_token_is_explicit(self):
        with self.assertRaises(probe.MissingTokenError):
            probe.search("onimusha", 1, "")

    def test_transient_500_is_retried(self):
        sleeper = MagicMock()
        with patch.object(
            probe,
            "urlopen",
            side_effect=[http_error(500), http_error(500), response(valid_payload())],
        ) as mocked:
            result = probe.search("onimusha", 1, "token", sleep=sleeper)

        self.assertEqual(len(result["observations"]), 1)
        self.assertEqual(mocked.call_count, 3)
        self.assertEqual(sleeper.call_count, 2)

    def test_persistent_500_fails_after_bounded_retries(self):
        sleeper = MagicMock()
        with patch.object(
            probe, "urlopen", side_effect=[http_error(500), http_error(500), http_error(500)]
        ):
            with self.assertRaises(probe.APIError) as raised:
                probe.search("onimusha", 1, "token", sleep=sleeper)
        self.assertEqual(raised.exception.status, 500)
        self.assertEqual(sleeper.call_count, 2)

    def test_429_respects_retry_after(self):
        sleeper = MagicMock()
        with patch.object(
            probe,
            "urlopen",
            side_effect=[
                http_error(429, retry_after="2"),
                response(valid_payload()),
            ],
        ):
            result = probe.search("onimusha", 1, "token", sleep=sleeper)

        self.assertEqual(len(result["observations"]), 1)
        sleeper.assert_called_once_with(2.0)

    def test_persistent_429_reports_rate_limit(self):
        with patch.object(
            probe,
            "urlopen",
            side_effect=[http_error(429, retry_after="0")] * 3,
        ):
            with self.assertRaises(probe.APIError) as raised:
                probe.search("onimusha", 1, "token", sleep=MagicMock())
        self.assertEqual(raised.exception.status, 429)
        self.assertIn("rate limited", str(raised.exception))

    def test_permanent_4xx_is_not_retried(self):
        for status in (400, 401, 403, 404):
            with self.subTest(status=status):
                sleeper = MagicMock()
                with patch.object(probe, "urlopen", side_effect=[http_error(status)]) as mocked:
                    with self.assertRaises(probe.APIError) as raised:
                        probe.search("onimusha", 1, "token", sleep=sleeper)
                self.assertEqual(raised.exception.status, status)
                self.assertEqual(mocked.call_count, 1)
                sleeper.assert_not_called()

    def test_403_guidance_does_not_suggest_bypass(self):
        with patch.object(probe, "urlopen", side_effect=[http_error(403)]):
            with self.assertRaises(probe.APIError) as raised:
                probe.search("onimusha", 1, "token", sleep=MagicMock())
        message = str(raised.exception).lower()
        self.assertIn("scopes", message)
        self.assertNotIn("scrap", message)
        self.assertNotIn("proxy", message)

    def test_timeout_retries_then_fails(self):
        sleeper = MagicMock()
        with patch.object(
            probe, "urlopen", side_effect=[TimeoutError("timed out")] * 3
        ) as mocked:
            with self.assertRaises(probe.NetworkError):
                probe.search("onimusha", 1, "token", sleep=sleeper)
        self.assertEqual(mocked.call_count, 3)
        self.assertEqual(sleeper.call_count, 2)

    def test_timeout_can_recover(self):
        with patch.object(
            probe, "urlopen", side_effect=[TimeoutError("timed out"), response(valid_payload())]
        ):
            result = probe.search("onimusha", 1, "token", sleep=MagicMock())
        self.assertEqual(len(result["observations"]), 1)

    def test_socket_timeout_is_retried(self):
        import socket

        with patch.object(
            probe,
            "urlopen",
            side_effect=[socket.timeout("timed out"), response(valid_payload())],
        ):
            result = probe.search("onimusha", 1, "token", sleep=MagicMock())
        self.assertEqual(len(result["observations"]), 1)

    def test_invalid_json_is_not_retried(self):
        with patch.object(probe, "urlopen", side_effect=[response(b"not json")]) as mocked:
            with self.assertRaises(probe.ResponseError):
                probe.search("onimusha", 1, "token", sleep=MagicMock())
        self.assertEqual(mocked.call_count, 1)

    def test_token_is_redacted_from_api_error(self):
        secret = "APP_USR-super-secret-token"
        body = json.dumps({"message": f"invalid token {secret}"}).encode("utf-8")
        with patch.object(probe, "urlopen", side_effect=[http_error(403, body=body)]):
            with self.assertRaises(probe.APIError) as raised:
                probe.search("onimusha", 1, secret, sleep=MagicMock())
        self.assertNotIn(secret, str(raised.exception))
        self.assertIn("[redacted]", str(raised.exception))


class CliTests(unittest.TestCase):
    def test_check_inputs_does_not_need_token(self):
        stdout = io.StringIO()
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout", stdout):
            code = probe.main(["--check-inputs", "--query", "onimusha", "--limit", "1"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["limit"], 1)

    def test_empty_query_exits_with_input_error(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stderr", io.StringIO()):
            code = probe.main(["--check-inputs", "--query", "   ", "--limit", "20"])
        self.assertEqual(code, probe.EXIT_INVALID_INPUT)

    def test_invalid_limit_exits_with_input_error(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stderr", io.StringIO()):
            code = probe.main(["--check-inputs", "--query", "x", "--limit", "51"])
        self.assertEqual(code, probe.EXIT_INVALID_INPUT)

    def test_missing_token_exits_with_token_error(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stderr", io.StringIO()):
            code = probe.main(["--query", "x", "--limit", "1"])
        self.assertEqual(code, probe.EXIT_MISSING_TOKEN)

    def test_input_json_payload(self):
        payload = {
            "query": "Onimusha PS5",
            "limit": 1,
            "access_token": "secret-token",
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            json.dump(payload, handle)
            handle.flush()
            stdout = io.StringIO()
            with patch.object(probe, "urlopen", return_value=response(valid_payload())), patch(
                "sys.stdout", stdout
            ), patch("sys.stderr", io.StringIO()):
                code = probe.main(["--input-json", handle.name])

        self.assertEqual(code, 0)
        output = json.loads(stdout.getvalue())
        self.assertEqual(output["query"], "Onimusha PS5")
        self.assertEqual(output["limit"], 1)

    def test_input_json_missing_field(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json") as handle:
            json.dump({"query": "x"}, handle)
            handle.flush()
            with patch("sys.stderr", io.StringIO()):
                code = probe.main(["--input-json", handle.name])
        self.assertEqual(code, probe.EXIT_INVALID_INPUT)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[1]
        self.workflow = (root / ".github/workflows/vps-marketplace-probe.yml").read_text()

    def test_token_secret_is_required(self):
        self.assertIn("secrets.MERCADO_LIVRE_ACCESS_TOKEN", self.workflow)
        self.assertIn("Require Mercado Livre access token", self.workflow)

    def test_remote_payload_uses_stdin_json(self):
        self.assertIn("--input-json -", self.workflow)
        self.assertNotIn("QUERY_B64", self.workflow)
        self.assertNotIn('--query "$QUERY" --limit "$LIMIT"\'"', self.workflow)

    def test_inputs_are_validated_before_remote_execution(self):
        self.assertIn("--check-inputs", self.workflow)
        self.assertIn("Validate probe inputs", self.workflow)

    def test_still_restricted_to_work_branch(self):
        self.assertIn(
            "github.ref == 'refs/heads/feat/marketplace-collection-spike'",
            self.workflow,
        )

    def test_remote_command_does_not_interpolate_query(self):
        for line in self.workflow.splitlines():
            if "ssh " in line or "exec python3" in line:
                self.assertNotIn("$QUERY", line)
                self.assertNotIn("$MERCADO_LIVRE_ACCESS_TOKEN", line)


if __name__ == "__main__":
    unittest.main()
