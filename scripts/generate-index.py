#!/usr/bin/env python3
"""Generate the root paper index using only Python."""

import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent


class PaperMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading = []
        self.page_title = []
        self.description = ""
        self.keywords = ""
        self.image = ""
        self.capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1" and not self.heading:
            self.capture = self.heading
        elif tag == "title":
            self.capture = self.page_title
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "description":
                self.description = attrs.get("content", "")
            elif name == "keywords":
                self.keywords = attrs.get("content", "")
        elif tag == "img" and not self.image:
            source = attrs.get("src", "")
            if re.fullmatch(r"data:image/(png|jpeg|webp|gif);base64,[\s\S]+", source):
                self.image = source

    def handle_endtag(self, tag):
        if tag in {"h1", "title"}:
            self.capture = None

    def handle_data(self, data):
        if self.capture is not None:
            self.capture.append(data)


def paper_card(paper, overrides):
    metadata = PaperMetadata()
    metadata.feed(paper.read_text(encoding="utf-8"))
    title = " ".join("".join(metadata.heading or metadata.page_title).split()) or paper.stem
    description = overrides.get("description", metadata.description)
    tag = overrides.get("tag", "HTML 阅读笔记")
    cover = ""

    # A matching asset overrides the first embedded figure, as in the original cards.
    for extension in ("png", "jpg", "jpeg", "webp", "gif"):
        asset = ROOT / "assets" / f"{paper.stem.lower()}.{extension}"
        if asset.is_file():
            cover = "./" + quote(asset.relative_to(ROOT).as_posix())
            break

    if not cover:
        cover = metadata.image

    cover_html = ""
    if cover:
        cover_html = f'<img class="cover" src="{escape(cover)}" alt="">'
    description_html = f"<p>{escape(description)}</p>" if description else ""
    keywords = escape(metadata.keywords)
    href = escape(quote(paper.relative_to(ROOT).as_posix()))
    card = f"""      <li data-keywords="{keywords}">
        <a class="card" href="./{href}">
          {cover_html}
          <div class="card-body">
            <h2>{escape(title)}</h2>
            {description_html}
            <div class="card-footer">
              <span class="tag">{escape(tag)}</span>
              <span class="open">阅读批注 <span aria-hidden="true">→</span></span>
            </div>
          </div>
        </a>
      </li>"""
    return title, card


def build():
    papers = sorted(
        paper for paper in (ROOT / "paper").rglob("*")
        if paper.is_file() and paper.suffix.lower() == ".html"
    )
    metadata_file = ROOT / "papers.json"
    overrides = json.loads(metadata_file.read_text(encoding="utf-8")) if metadata_file.is_file() else {}
    cards = []
    for paper in papers:
        cards.append(paper_card(paper, overrides.get(paper.name, {})))
    cards.sort(key=lambda item: item[0].casefold())

    template = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    index = template.replace("{{paper_cards}}", "\n".join(card for _, card in cards))
    index = index.replace("{{paper_count}}", str(len(cards)))
    (ROOT / "index.html").write_text(index, encoding="utf-8")
    print(f"Generated index.html with {len(cards)} papers")
    for title, _ in cards:
        print(f"  {title}")


if __name__ == "__main__":
    build()
