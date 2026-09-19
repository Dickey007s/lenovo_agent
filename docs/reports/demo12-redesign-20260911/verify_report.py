"""Validate the offline report's syntax and local assets, not browser rendering."""

from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
from urllib.parse import unquote, urlsplit


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []
        self.scripts = []
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if "id" in attributes:
            self.ids.append(attributes["id"])
        for name in ("href", "src"):
            if name in attributes:
                self.links.append(attributes[name])
        if tag == "script":
            self.in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if self.in_script:
            self.scripts.append(data)


root = Path(__file__).resolve().parent
parser = ReportParser()
parser.feed((root / "index.html").read_text(encoding="utf-8"))
assert len(parser.ids) == len(set(parser.ids)), "Duplicate HTML IDs"
for link in parser.links:
    parsed = urlsplit(link)
    if not parsed.scheme and parsed.path:
        assert (root / unquote(parsed.path)).is_file(), link
for view in ("progress", "record", "collaboration", "evidence"):
    for relative in (f"references/{view}.png", f"screenshots/{view}-1672.png"):
        data = (root / relative).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", relative
        assert int.from_bytes(data[16:20], "big") == 1672, relative
        expected_height = 941 if relative.startswith("references/") else 940
        assert int.from_bytes(data[20:24], "big") == expected_height, relative
node = shutil.which("node")
assert node, "Node is required for JavaScript syntax checks"
subprocess.run([node, "--check"], input="\n".join(parser.scripts), text=True, check=True)
print(f"PASS: unique IDs, {len(parser.links)} links, 8 PNG dimensions, JavaScript syntax.")
print("Scope: source and assets only; no browser, Provider or Runtime call.")
