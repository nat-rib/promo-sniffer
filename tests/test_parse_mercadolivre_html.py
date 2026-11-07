import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from scripts import parse_mercadolivre_html as parser


SAVED_HTML = """
<html>
  <head>
    <script type="application/ld+json">
      {
        "@type": "Product",
        "name": "Onimusha: Way of the Sword",
        "sku": "MLB76247569",
        "url": "https://www.mercadolivre.com.br/onimusha-way-of-the-sword-ps5/p/MLB76247569",
        "brand": {"name": "Capcom"},
        "offers": {
          "price": "319.90",
          "priceCurrency": "BRL",
          "availability": "https://schema.org/InStock",
          "seller": {"name": "Loja Exemplo"}
        }
      }
    </script>
    <script type="application/ld+json">this is not json</script>
  </head>
  <body>
    <script>
      window.__PRELOADED_STATE__ = {
        "product": {"id": "MLB76247569"},
        "nested": {"text": "a } brace and a \\" quote", "list": [1, 2, 3]},
        "price": 319.9
      };
    </script>
  </body>
</html>
"""


class JsonLdTests(unittest.TestCase):
    def test_extracts_valid_blocks_and_skips_invalid(self):
        documents = parser.extract_json_ld(SAVED_HTML)
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["name"], "Onimusha: Way of the Sword")

    def test_summarizes_product_offer(self):
        summary = parser.summarize_json_ld(parser.extract_json_ld(SAVED_HTML))
        self.assertEqual(summary[0]["sku"], "MLB76247569")
        self.assertEqual(summary[0]["price"], "319.90")
        self.assertEqual(summary[0]["priceCurrency"], "BRL")
        self.assertEqual(summary[0]["seller"], "Loja Exemplo")
        self.assertEqual(summary[0]["brand"], "Capcom")

    def test_json_ld_list_document(self):
        html = '<script type="application/ld+json">[{"name": "A"}, {"name": "B"}]</script>'
        summary = parser.summarize_json_ld(parser.extract_json_ld(html))
        self.assertEqual([item["name"] for item in summary], ["A", "B"])

    def test_missing_json_ld(self):
        self.assertEqual(parser.extract_json_ld("<html></html>"), [])


class PreloadedStateTests(unittest.TestCase):
    def test_extracts_nested_state_with_braces_in_strings(self):
        state = parser.extract_preloaded_state(SAVED_HTML)
        self.assertIsNotNone(state)
        self.assertEqual(state["product"]["id"], "MLB76247569")
        self.assertEqual(state["nested"]["text"], 'a } brace and a " quote')
        self.assertEqual(state["nested"]["list"], [1, 2, 3])

    def test_missing_state(self):
        self.assertIsNone(parser.extract_preloaded_state("<html></html>"))

    def test_invalid_state_returns_none(self):
        html = "window.__PRELOADED_STATE__ = {broken};"
        self.assertIsNone(parser.extract_preloaded_state(html))


class ParseSavedHtmlTests(unittest.TestCase):
    def test_full_result(self):
        result = parser.parse_saved_html(SAVED_HTML)
        self.assertEqual(result["source"], "saved_html")
        self.assertEqual(result["json_ld_blocks_found"], 1)
        self.assertTrue(result["preloaded_state_found"])
        self.assertIn("product", result["preloaded_state_keys"])

    def test_state_keys_can_be_omitted(self):
        result = parser.parse_saved_html(SAVED_HTML, include_state_keys=False)
        self.assertNotIn("preloaded_state_keys", result)


class CliTests(unittest.TestCase):
    def _write(self, content):
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".html", delete=False
        )
        handle.write(content)
        handle.close()
        self.addCleanup(lambda: __import__("os").unlink(handle.name))
        return handle.name

    def test_cli_outputs_json(self):
        path = self._write(SAVED_HTML)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = parser.main(["--input", path])
        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["json_ld"][0]["name"], "Onimusha: Way of the Sword")

    def test_cli_rejects_page_without_supported_data(self):
        path = self._write("<html><body>verification page</body></html>")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = parser.main(["--input", path])
        self.assertEqual(code, 1)
        self.assertIn("No JSON-LD", stderr.getvalue())

    def test_cli_reports_missing_file(self):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = parser.main(["--input", "/path/does/not/exist.html"])
        self.assertEqual(code, 2)
        self.assertIn("Could not read", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
