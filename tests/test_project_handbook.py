"""The interview handbook must remain a complete, offline-safe single HTML file."""

import re
from html.parser import HTMLParser
from pathlib import Path


HANDBOOK = Path(__file__).resolve().parents[1] / "docs" / "PROJECT_DEEP_DIVE.html"


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.svgs = 0
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.links.append(attrs["href"][1:])
        if tag == "svg":
            self.svgs += 1
        if tag == "script":
            self.scripts.append(attrs)


def test_handbook_is_offline_complete_and_has_interview_depth():
    html = HANDBOOK.read_text(encoding="utf-8")
    page = _Page()
    page.feed(html)
    assert len(page.links) >= 16
    assert all(target in page.ids for target in page.links)
    assert page.svgs >= 3
    assert len(re.findall(r'^\["[^\n]+', html, flags=re.MULTILINE)) >= 60
    assert all("src" not in script for script in page.scripts)
    assert not re.search(r"\bsk-[A-Za-z0-9]{16,}\b", html)
    assert "https://fonts.googleapis.com" not in html
