#!/usr/bin/env python3
"""Generate the paper index and source-backed statistics using only Python."""

import json
import re
from collections import Counter
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
HIGHLIGHT_CLASSES = {
    "dim-method": "method", "hl-method": "method",
    "dim-concept": "concept", "hl-term": "concept",
    "dim-evidence": "evidence", "hl-evidence": "evidence",
    "dim-thesis": "thesis", "hl-thesis": "thesis",
    "dim-response": "response", "hl-concession": "response",
}


def clean_text(value):
    return " ".join(value.split())


class PaperMetadata(HTMLParser):
    """Read explicitly marked source units, never translated duplicates."""

    def __init__(self):
        super().__init__()
        self.stack = []
        self.heading = []
        self.heading_seen = False
        self.capture_heading = False
        self.page_title = []
        self.description = ""
        self.keywords = ""
        self.image = ""
        self.author_text = []
        self.author_line_seen = False
        self.author_line_ended = False
        self.meta_authors = []
        self.year = None
        self.arxiv_id = ""
        self.counts = Counter()
        self.highlight_counts = dict.fromkeys(HIGHLIGHT_CLASSES.values(), 0)
        self.recognized_highlights = False
        self.bibliography = []
        self.current_reference = None
        self.row_kinds = Counter()
        self.has_typed_rows = False
        self.has_units = False
        self.has_legacy_rows = False

    def ancestor(self, *, tag=None, cls=None):
        return any((tag is None or item[0] == tag) and (cls is None or cls in item[1]) for item in self.stack)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        if tag == "h1" and not self.heading_seen:
            self.heading_seen = True
            self.capture_heading = True
        if tag == "meta":
            name = attrs.get("name", "").lower()
            content = attrs.get("content", "")
            if name == "description":
                self.description = content
            elif name == "keywords":
                self.keywords = content
            elif name == "citation_author":
                self.meta_authors.append(content)
            elif name in {"citation_publication_date", "citation_date", "dc.date"}:
                match = re.match(r"((?:19|20)\d{2})(?:\D|$)", content)
                if match:
                    self.year = int(match[1])
        elif tag == "a" and not self.arxiv_id and (
            self.ancestor(tag="header") or self.ancestor(cls="source-line") or self.ancestor(cls="source-note")
        ):
            match = re.search(r"https?://arxiv\.org/abs/(\d{4}\.\d{4,5})(?:v\d+)?(?:$|[?#])", attrs.get("href", ""))
            if match:
                self.arxiv_id = match[1]
                if self.year is None:
                    year = int(self.arxiv_id[:2])
                    self.year = 2000 + year if year < 91 else 1900 + year
        elif tag == "img" and not self.image:
            source = attrs.get("src", "")
            if re.fullmatch(r"data:image/(png|jpeg|webp|gif);base64,[\s\S]+", source):
                self.image = source
        if "author-line" in classes and not self.author_line_seen:
            self.author_line_seen = True
        if tag == "br" and self.ancestor(cls="author-line"):
            self.author_line_ended = True
        if "reading-row" in classes:
            kind = attrs.get("data-kind")
            if kind:
                self.has_typed_rows = True
                self.row_kinds[kind] += 1
            else:
                self.has_legacy_rows = True
        if "unit" in classes:
            self.has_units = True
            if "paragraph" in classes:
                self.counts["unit_paragraphs"] += 1
            if "figure" in classes:
                self.counts["unit_figures"] += 1
        if tag == "p" and "ltx_p" in classes and self.ancestor(cls="english"):
            self.counts["english_paragraphs"] += 1
        if "ltx_tag_figure" in classes and self.ancestor(cls="english"):
            self.counts["english_figures"] += 1
        if tag == "li" and "ltx_bibitem" in classes:
            self.counts["references"] += 1
            self.current_reference = {"anchor": attrs.get("id", ""), "parts": []}
            self.bibliography.append(self.current_reference)
        if tag == "mark":
            for cls in classes:
                if cls in HIGHLIGHT_CLASSES:
                    self.recognized_highlights = True
                    self.highlight_counts[HIGHLIGHT_CLASSES[cls]] += 1
                    break
        if tag not in VOID_TAGS:
            self.stack.append((tag, classes))

    def handle_endtag(self, tag):
        if tag == "h1":
            self.capture_heading = False
        if tag == "li" and self.current_reference is not None:
            self.current_reference = None
        for position in range(len(self.stack) - 1, -1, -1):
            if self.stack[position][0] == tag:
                del self.stack[position:]
                break

    def handle_data(self, data):
        if self.capture_heading and self.ancestor(tag="h1"):
            self.heading.append(data)
        if self.ancestor(tag="title"):
            self.page_title.append(data)
        if self.ancestor(cls="author-line") and not self.author_line_ended:
            self.author_text.append(data)
        if self.current_reference is not None:
            self.current_reference["parts"].append(data)

    @property
    def authors(self):
        values = self.meta_authors or re.split(r"\s*[·；;]\s*", clean_text("".join(self.author_text)))
        return [re.sub(r"[*†‡]+$", "", clean_text(value)).strip() for value in values if clean_text(value)]

    @property
    def highlights(self):
        recognized_layout = self.has_typed_rows or self.has_units or (
            self.has_legacy_rows and self.counts["english_paragraphs"]
        )
        if recognized_layout or self.recognized_highlights:
            return self.highlight_counts.copy()
        return dict.fromkeys(self.highlight_counts, None)

    def measured(self, field):
        if field == "references":
            return self.counts["references"] if self.counts["references"] else None
        if self.has_typed_rows:
            return self.row_kinds["paragraph" if field == "paragraphs" else "figure"]
        if self.has_units:
            return self.counts["unit_" + field]
        if self.has_legacy_rows and self.counts["english_paragraphs"]:
            return self.counts["english_" + field]
        return None


def load_paper(paper, overrides):
    metadata = PaperMetadata()
    metadata.feed(paper.read_text(encoding="utf-8"))
    title = clean_text("".join(metadata.heading or metadata.page_title)) or paper.stem
    relative = paper.relative_to(ROOT)
    record = {
        "id": relative.relative_to("paper").with_suffix("").as_posix(),
        "href": "./" + quote(relative.as_posix()),
        "title": title,
        "short_title": overrides.get("short_title", title.split(":", 1)[0]),
        "description": overrides.get("description", metadata.description),
        "tag": overrides.get("tag", "HTML 阅读笔记"),
        "keywords": metadata.keywords,
        "authors": overrides.get("authors", metadata.authors),
        "year": overrides.get("year", metadata.year),
        "paragraphs": metadata.measured("paragraphs"),
        "references": metadata.measured("references"),
        "figures": metadata.measured("figures"),
        "topics": overrides.get("topics", []),
        "highlights": metadata.highlights,
        "citations": [],
        "arxiv_id": metadata.arxiv_id,
    }
    cover = ""
    for extension in ("png", "jpg", "jpeg", "webp", "gif"):
        asset = ROOT / "assets" / f"{paper.stem.lower()}.{extension}"
        if asset.is_file():
            cover = "./" + quote(asset.relative_to(ROOT).as_posix())
            break
    record["cover"] = cover or metadata.image
    return record, metadata.bibliography


def connect_citations(records, bibliographies):
    """Only direct bibliography matches count; text mentions are not citations."""
    for source in records:
        for target in records:
            if source["id"] == target["id"]:
                continue
            for reference in bibliographies[source["id"]]:
                text = clean_text("".join(reference["parts"]))
                arxiv_match = bool(target["arxiv_id"] and re.search(r"(?<!\d)" + re.escape(target["arxiv_id"]) + r"(?!\d)", text))
                title = target["title"].casefold().rstrip(".")
                title_match = len(title) >= 6 and bool(re.search(r"(?<!\w)" + re.escape(title) + r"(?!\w)", text.casefold()))
                if (arxiv_match or title_match) and reference["anchor"]:
                    number = re.match(r"\[(\d+)\]", text)
                    source["citations"].append({
                        "target": target["id"],
                        "anchor": reference["anchor"],
                        "label": f"参考文献 [{number[1]}]" if number else "参考文献原条目",
                    })
                    break


def paper_card(paper):
    if paper["cover"]:
        cover_html = f'<img class="cover" src="{escape(paper["cover"])}" alt="" loading="lazy" decoding="async">'
    else:
        cover_html = f'<div class="cover-fallback" aria-hidden="true">{escape(paper["short_title"])}</div>'
    meta = " · ".join(str(value) for value in [paper["year"], f'{len(paper["authors"])} 位作者' if paper["authors"] else ""] if value)
    description_html = f'<p class="paper-summary">{escape(paper["description"])}</p>' if paper["description"] else ""
    subtitle = f'<p class="paper-subtitle" lang="en">{escape(paper["title"])}</p>' if paper["title"] != paper["short_title"] else ""
    stats = " · ".join(f"{value} {label}" for value, label in [(paper["paragraphs"], "段正文"), (paper["figures"], "张图")] if value is not None)
    keywords = " ".join([paper["keywords"], *paper["authors"], *paper["topics"]])
    return f'''      <li data-paper-id="{escape(paper["id"])}" data-keywords="{escape(keywords)}">
        <a class="card" href="{escape(paper["href"])}">
          {cover_html}
          <div class="card-body">
            <p class="paper-meta" title="{escape(' · '.join(paper['authors']))}">{escape(meta)}</p>
            <h3 class="paper-title">{escape(paper["short_title"])}</h3>
            {subtitle}
            {description_html}
            <p class="paper-stats">{escape(stats)}</p>
            <div class="card-footer">
              <span class="tag">{escape(paper["tag"])}</span>
              <span class="open">阅读批注 <span aria-hidden="true">↗</span></span>
            </div>
          </div>
        </a>
      </li>'''


def read_library():
    metadata_file = ROOT / "papers.json"
    overrides = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.is_file() else {}
    records, bibliographies = [], {}
    for path in sorted((ROOT / "paper").rglob("*")):
        if path.is_file() and path.suffix.lower() == ".html":
            override = overrides.get(path.relative_to(ROOT / "paper").as_posix(), overrides.get(path.name, {}))
            record, references = load_paper(path, override)
            records.append(record)
            bibliographies[record["id"]] = references
    records.sort(key=lambda item: item["title"].casefold())
    connect_citations(records, bibliographies)
    return records


def render_index(template, records):
    # Covers live in static cards; do not duplicate large embedded images in JSON.
    data = [{key: value for key, value in record.items() if key != "cover"} for record in records]
    replacements = {
        "paper_cards": "\n".join(paper_card(paper) for paper in records),
        "paper_data": json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c"),
        "paper_count": len(records),
        "author_count": len({author.casefold() for paper in records for author in paper["authors"]}),
        "paragraph_count": sum(paper["paragraphs"] or 0 for paper in records),
        "reference_count": sum(paper["references"] or 0 for paper in records),
        "highlight_count": sum(sum(value or 0 for value in paper["highlights"].values()) for paper in records),
    }
    for key, value in replacements.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def build():
    records = read_library()
    template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    (ROOT / "index.html").write_text(render_index(template, records), encoding="utf-8")
    print(f"Generated index.html with {len(records)} papers")
    for paper in records:
        print(f'  {paper["short_title"]}: {len(paper["authors"])} authors, {paper["paragraphs"]} paragraphs, {paper["references"]} references')


if __name__ == "__main__":
    build()
