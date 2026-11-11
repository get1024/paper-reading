"""Check extraction boundaries and safe embedding, using small independent fixtures."""

import importlib.util
import json
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("generate_index", Path(__file__).with_name("generate-index.py"))
index = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(index)


class IndexMetadataTests(unittest.TestCase):
    def parse(self, html):
        metadata = index.PaperMetadata()
        metadata.feed(html)
        return metadata

    def test_authors_stop_before_affiliation_and_year_comes_from_source(self):
        metadata = self.parse('''<header><h1>A <em>paper</em></h1>
          <div class="author-line">Alice* · Bob†<br>University · Lab</div>
          <a href="https://arxiv.org/abs/2601.12345v2">source</a></header>
          <p>Study date: 2027</p>''')
        self.assertEqual(metadata.authors, ["Alice", "Bob"])
        self.assertEqual(metadata.year, 2026)
        self.assertEqual(index.clean_text("".join(metadata.heading)), "A paper")

    def test_only_explicit_source_units_are_measured(self):
        metadata = self.parse('''<div class="reading-row" data-kind="paragraph">
          <div class="english"><p>Source.</p></div><p class="translation">译文</p></div>
          <div class="reading-row" data-kind="figure"><img src="image.png"></div>
          <li class="ltx_bibitem" id="ref1">A reference.</li>
          <span class="dim-method">Legend</span><mark class="dim-method">Method</mark>
          <mark class="hl-concession">Boundary</mark>''')
        self.assertEqual(metadata.measured("paragraphs"), 1)
        self.assertEqual(metadata.measured("figures"), 1)
        self.assertEqual(metadata.measured("references"), 1)
        self.assertEqual(metadata.highlights["method"], 1)
        self.assertEqual(metadata.highlights["response"], 1)

    def test_only_first_h1_is_the_title(self):
        metadata = self.parse('''<title>Browser title</title>
          <h1>First <em>paper title</em></h1><h1>Second section heading</h1>''')
        self.assertEqual(index.clean_text("".join(metadata.heading)), "First paper title")

    def test_unknown_layout_has_unknown_counts_and_no_bibliography_year(self):
        metadata = self.parse('''<h1>New paper</h1><p>Unmarked prose.</p>
          <a href="https://arxiv.org/abs/2101.12345">An unrelated cited paper</a>''')
        self.assertIsNone(metadata.measured("paragraphs"))
        self.assertIsNone(metadata.measured("references"))
        self.assertIsNone(metadata.year)
        self.assertEqual(metadata.authors, [])
        self.assertTrue(all(value is None for value in metadata.highlights.values()))

    def test_recognized_layout_without_marks_has_known_zero_highlights(self):
        metadata = self.parse('<article class="unit paragraph">Source, translation and annotation.</article>')
        self.assertTrue(all(value == 0 for value in metadata.highlights.values()))

    def test_citation_requires_target_match_and_real_anchor(self):
        records = [
            {"id": "a", "title": "A", "arxiv_id": "2601.12345", "citations": []},
            {"id": "b", "title": "A long target title", "arxiv_id": "2602.23456", "citations": []},
        ]
        index.connect_citations(records, {
            "a": [{"anchor": "reference-7", "parts": ["[7] A paper. arXiv:2602.23456."]}], "b": [],
        })
        self.assertEqual(records[0]["citations"], [{"target": "b", "anchor": "reference-7", "label": "参考文献 [7]"}])
        self.assertEqual(records[1]["citations"], [])

    def test_json_script_cannot_close_itself_and_does_not_duplicate_cover(self):
        record = {
            "id": "a", "title": "</script><script>alert(1)</script>", "short_title": "A",
            "href": "./paper/a.html", "authors": [], "year": None, "cover": "data:image/png;base64,AA==",
            "description": "", "tag": "test", "keywords": "", "topics": [],
            "paragraphs": None, "figures": None, "references": None, "highlights": {},
        }
        encoded = index.render_index("{{paper_data}}", [record])
        self.assertNotIn("</script>", encoded)
        self.assertNotIn("base64", encoded)
        self.assertEqual(json.loads(encoded)[0]["title"], record["title"])


if __name__ == "__main__":
    unittest.main()
