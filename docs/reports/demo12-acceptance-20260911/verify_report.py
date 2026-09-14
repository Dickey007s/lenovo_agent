"""Check report structure/assets; this is not browser or business verification."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if "id" in values:
            self.ids.append(values["id"])
        for name in ("href", "src"):
            if name in values:
                self.links.append(values[name])
        if tag == "img":
            assert values.get("alt"), "Images require descriptive alt text"
            self.images.append(values["src"])
        assert tag not in {"script", "iframe"}, "Report must remain offline and inert"


root = Path(__file__).resolve().parent
parser = ReportParser()
parser.feed((root / "index.html").read_text(encoding="utf-8"))
assert len(parser.ids) == len(set(parser.ids)), "Duplicate IDs"
for link in parser.links:
    parsed = urlsplit(link)
    if not parsed.scheme and parsed.path:
        assert (root / unquote(parsed.path)).is_file(), link
for relative in parser.images:
    data = (root / relative).read_bytes()
    assert data[:3] == b"\xff\xd8\xff" and data[-2:] == b"\xff\xd9", relative
    assert len(data) > 10_000, relative
print(f"PASS: {len(parser.ids)} unique IDs, {len(parser.links)} links, {len(parser.images)} JPEG assets.")
print("Scope: offline source/assets only; no browser, model or Runtime call.")
