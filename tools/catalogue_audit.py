"""Read-only catalogue audit and bounded source parsers (Python stdlib only).

No network, vendor-code execution or private archive access occurs at import or
in a default audit. Optional selector reconciliation reads an explicit JS path
as text; it never evaluates JavaScript. Reported counts are source identities,
not claims of distinct hardware configurations or universal support.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urljoin, urlsplit

ID = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
MATRIX = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*\Z")


def parse_selector(text):
    """Extract only literal ThinkPad/TransNote arrays, preserving row order."""
    rows, groups = [], set()
    pattern = r"\bvar\s+(l_tp_[A-Za-z0-9_]+|l_transnote)\s*=\s*new\s+Array\s*\((.*?)\)\s*;"
    for match in re.finditer(pattern, text, re.S):
        group, body = match.groups()
        if group in groups:
            raise ValueError("duplicate selector group")
        groups.add(group)
        try:
            values = json.loads("[" + body + "]")
        except json.JSONDecodeError as error:
            raise ValueError("selector array must contain JSON string literals") from error
        for value in values:
            if not isinstance(value, str) or value.count("|") != 1:
                raise ValueError("malformed selector row")
            label, matrix = value.split("|")
            if not (label.startswith("ThinkPad ") or (group == "l_transnote" and label == "TransNote")):
                raise ValueError("non-ThinkPad selector identity")
            if not MATRIX.fullmatch(matrix):
                raise ValueError("invalid matrix identifier")
            rows.append({"group": group, "label": label, "matrix": matrix})
    return rows


class _HistoryTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.cells = None
        self.cell = None
        self.href = None
        self.anchor = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.cells = []
        elif tag in ("th", "td") and self.cells is not None:
            self.cell = {"text": [], "links": []}
        elif tag == "a" and self.cell is not None:
            self.href = dict(attrs).get("href")
            self.anchor = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"].append(data)
            if self.href is not None:
                self.anchor.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.cell is not None and self.href is not None:
            self.cell["links"].append((self.href, "".join(self.anchor).strip()))
            self.href = None
        elif tag in ("th", "td") and self.cell is not None:
            self.cells.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.cells is not None:
            self.rows.append(self.cells)
            self.cells = None


def parse_early_history(text):
    """Read linked first-cell model names in explicitly dated 1992–1999 rows.

    Regional variants are included; redlinks, features, and the unbranded Palm
    Top PC110 are excluded. Dates are used only as an extraction boundary and
    are not published as launch-date claims.
    """
    parser = _HistoryTable()
    parser.feed(text)
    result, seen = [], set()
    for cells in parser.rows:
        if len(cells) < 2:
            continue
        date = "".join(cells[1]["text"])
        year = re.search(r"\b(199[2-9])\b", date)
        if not year:
            continue
        for href, name in cells[0]["links"]:
            if not href.startswith("/wiki/Category:") or name == "PC110" or name in seen:
                continue
            if not re.fullmatch(r"(?:[0-9][A-Za-z0-9]*|i Series [0-9]+)", name):
                continue
            seen.add(name)
            result.append({"name": name, "year": int(year[1]), "url": urljoin("https://www.thinkwiki.org", href)})
    return result


def parse_manual_index(text):
    """Read explicit ThinkPad family-to-PDF metadata from Lenovo's table."""
    parser = _HistoryTable()
    parser.feed(text)
    result = []
    for cells in parser.rows:
        if len(cells) != 2:
            continue
        name = " ".join("".join(cells[0]["text"]).split())
        if not (name.startswith("ThinkPad ") or name.startswith("i Series ") or name == "TransNote"):
            continue
        for url, label in cells[1]["links"]:
            parsed = urlsplit(url)
            if parsed.scheme == "https" and parsed.hostname == "download.lenovo.com" and parsed.path.lower().endswith(".pdf"):
                result.append({"name": name, "url": url})
    return result


def normalize_matrix_row(row, source_url, source_sha256=None):
    """Project a retained manufacturer row into concise public metadata."""
    _url(source_url)
    description = " ".join(row["description"].split())
    title, separator, tail = description.partition(" Version:")
    # The retained parser flattened the heading, version and anchor labels.
    # Strip only observed labels, never publish the flattened vendor row body.
    offsets = [tail.find(link["label"]) for link in row["links"] if link.get("label") and tail.find(link["label"]) >= 0]
    version = (tail[:min(offsets)] if offsets else tail).strip() if separator else None
    links = set()
    for link in row["links"]:
        url = link["url"]
        _url(url)
        suffix = PurePosixPath(urlsplit(url).path).suffix.lower()
        kind = "readme" if suffix == ".txt" else ("download" if suffix in {".exe", ".zip", ".iso", ".cab", ".tgz", ".gz", ".dmg", ".img", ".imz", ".vbs", ".bat", ".msi", ".rpm", ".sh", ".sys", ".inf", ".tvt", ".mdm", ".ini", ".reg", ".vxd", ".cmd", ".shar"} else "reference")
        links.add((url, kind))
    if not links:
        links.add((source_url, "reference"))
    operating_systems = sorted(set(filter(None, (part.strip() for part in re.split(
        r"\s+(?=Windows\b|OS/2\b|DOS(?:/Windows)?\b|Linux\b|OS Independent\b|All operating systems listed\b)", row.get("os", ""))))))
    category = " ".join(row["category"].split())
    risk = "firmware" if re.search(r"bios|uefi|firmware|embedded controller", category + " " + title, re.I) else "software"
    released = row.get("released")
    # This literal is an inherited parser fallback, never a source date.
    if released == "No indicada en la matriz":
        released = None
    result = {"title": title.strip(), "category": category, "version": version or None,
              "operating_systems": operating_systems, "released": released or None,
              "links": [{"url": url, "kind": kind} for url, kind in sorted(links)],
              "source_url": source_url, "evidence": "manufacturer_listing", "risk": risk}
    identity = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"id": "driver-" + hashlib.sha256(identity.encode()).hexdigest()[:24], **result,
            "source_sha256": source_sha256}


def _url(value):
    if not isinstance(value, str) or any(ord(c) < 33 for c in value) or "\\" in value:
        raise ValueError("invalid public URL")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("public URLs must use HTTPS without credentials")


def _fields(row, fields):
    if not isinstance(row, dict) or set(row) != set(fields.split()):
        raise ValueError("unexpected or missing metadata fields")


def _text(value):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError("metadata text must be nonempty single-line text")
    if any(marker in value for marker in ("/home/", "/tmp/", "file://", "C:\\", "verbatim_header", "\\r\\n")):
        raise ValueError("private path or captured source body in metadata")


def _rows(data, key, fields):
    rows = data[key]
    if not isinstance(rows, list):
        raise ValueError("metadata collection must be an array")
    seen = set()
    for row in rows:
        optional = ""
        if key == "models" and isinstance(row, dict):
            optional = ''.join(' ' + field for field in ('thinkwiki', 'introduced', 'introduced_unknown') if field in row)
        _fields(row, fields + optional)
        if key == "models" and isinstance(row, dict) and "introduced_unknown" in row:
            variants = row["introduced_unknown"]
            if not isinstance(variants, list):
                raise ValueError("invalid undated variants")
            for variant in variants:
                _text(variant)
            if len(set(variants)) != len(variants):
                raise ValueError("repeated undated variants")
        if key == "models" and isinstance(row, dict) and "introduced" in row:
            introductions = row["introduced"]
            if not isinstance(introductions, list):
                raise ValueError("invalid introduction references")
            seen_dates = set()
            for introduction in introductions:
                _fields(introduction, "year variants url")
                if type(introduction["year"]) is not int or not 1992 <= introduction["year"] <= 2100:
                    raise ValueError("invalid introduction year")
                variants = introduction["variants"]
                if not isinstance(variants, list) or not variants:
                    raise ValueError("introduction needs explicit variants")
                for variant in variants:
                    _text(variant)
                if len(set(variants)) != len(variants):
                    raise ValueError("repeated introduction variants")
                _url(introduction["url"])
                identity = (introduction["year"], introduction["url"])
                if identity in seen_dates:
                    raise ValueError("repeated introduction reference")
                seen_dates.add(identity)
        if key == "models" and isinstance(row, dict) and "thinkwiki" in row:
            references = row["thinkwiki"]
            if not isinstance(references, list):
                raise ValueError("invalid ThinkWiki references")
            for reference in references:
                _fields(reference, "title url")
                _text(reference["title"])
                _url(reference["url"])
                parts = urlsplit(reference["url"])
                if parts.netloc != "www.thinkwiki.org" or not parts.path.startswith("/wiki/Category:") or not parts.path.removeprefix("/wiki/Category:") or parts.query or parts.fragment:
                    raise ValueError("invalid ThinkWiki category URL")
            if len(references) != len({r["url"] for r in references}):
                raise ValueError("repeated ThinkWiki references")
        identifier = row["id"]
        if not isinstance(identifier, str) or not ID.fullmatch(identifier) or identifier in seen:
            raise ValueError("invalid or duplicate identifier")
        seen.add(identifier)
    return rows, seen


def _refs(values, allowed):
    if not isinstance(values, list) or len(values) != len(set(values)) or not set(values) <= allowed:
        raise ValueError("missing or duplicate cross-reference")


def audit_catalogue(root):
    """Validate the exact public schema and return computed counts or fail."""
    root = Path(root)
    data = {}
    expected = {"models": "schema_version scope sources models", "documents": "schema_version documents",
                "utilities": "schema_version utilities", "drivers": "schema_version drivers"}
    if {p.name for p in (root / "data").iterdir()} != {name + ".json" for name in expected}:
        raise ValueError("unexpected or missing public data files")
    for name, keys in expected.items():
        data[name] = json.loads((root / "data" / (name + ".json")).read_text(encoding="utf-8"))
        _fields(data[name], keys)
        if type(data[name]["schema_version"]) is not int or data[name]["schema_version"] != 2:
            raise ValueError("unsupported schema version")
    _fields(data["models"]["scope"], "en es")
    for value in data["models"]["scope"].values():
        _text(value)
    sources, source_ids = _rows(data["models"], "sources", "id title url kind")
    models, model_ids = _rows(data["models"], "models", "id name aliases family era sources matrix_url document_ids driver_ids")
    documents, document_ids = _rows(data["documents"], "documents", "id title url source_kind sha256 bytes model_hint")
    utilities, utility_ids = _rows(data["utilities"], "utilities", "id title url category")
    drivers, driver_ids = _rows(data["drivers"], "drivers", "id title category version operating_systems released links source_url evidence risk source_sha256")
    for source in sources:
        _text(source["title"])
        if source["kind"] not in ("official", "community"):
            raise ValueError("invalid source kind")
        _url(source["url"])
    for model in models:
        _text(model["name"])
        if not (model["name"].startswith("ThinkPad ") or model["name"] == "TransNote"):
            raise ValueError("non-ThinkPad model")
        if not isinstance(model["family"], str) or not ID.fullmatch(model["family"]):
            raise ValueError("invalid machine-independent family")
        if model["era"] not in ("early", "classic", "lenovo", "modern", "unknown"):
            raise ValueError("invalid era")
        if not isinstance(model["aliases"], list) or len(set(model["aliases"])) != len(model["aliases"]):
            raise ValueError("invalid aliases")
        for alias in model["aliases"]:
            _text(alias)
        _refs(model["sources"], source_ids)
        if not model["sources"]:
            raise ValueError("model requires provenance")
        _refs(model["document_ids"], document_ids)
        _refs(model["driver_ids"], driver_ids)
        if model["matrix_url"] is not None:
            _url(model["matrix_url"])
    for row in documents + utilities:
        _text(row["title"])
        _url(row["url"])
    for row in documents:
        _text(row["model_hint"])
        if row["source_kind"] not in ("official", "community"):
            raise ValueError("invalid document source kind")
        if row["sha256"] is not None and (not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])):
            raise ValueError("invalid SHA256")
        if row["bytes"] is not None and (type(row["bytes"]) is not int or row["bytes"] <= 0):
            raise ValueError("invalid byte count")
    for row in utilities:
        if row["category"] not in ("diagnostic", "reference"):
            raise ValueError("invalid utility category")
    metadata_seen, urls = set(), {"download": set(), "readme": set()}
    for row in drivers:
        for key in ("title", "category"):
            _text(row[key])
            if len(row[key]) > 400:
                raise ValueError("driver metadata must be concise")
        for key in ("version", "released"):
            if row[key] is not None:
                _text(row[key])
        systems = row["operating_systems"]
        if not isinstance(systems, list) or any(not isinstance(v, str) for v in systems) or len(set(systems)) != len(systems):
            raise ValueError("invalid advertised operating systems")
        for value in systems:
            _text(value)
        _url(row["source_url"])
        if row["evidence"] not in ("manufacturer_listing", "readme_model_list") or row["risk"] not in ("software", "firmware"):
            raise ValueError("invalid driver evidence or risk")
        if row["source_sha256"] is not None and (not isinstance(row["source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["source_sha256"])):
            raise ValueError("invalid source SHA256")
        if not isinstance(row["links"], list) or not row["links"]:
            raise ValueError("driver links must be a nonempty array")
        link_pairs = set()
        for link in row["links"]:
            _fields(link, "url kind")
            _url(link["url"])
            if link["kind"] not in ("download", "readme", "reference") or (link["url"], link["kind"]) in link_pairs:
                raise ValueError("invalid or duplicate driver link")
            link_pairs.add((link["url"], link["kind"]))
            if link["kind"] in urls:
                urls[link["kind"]].add(link["url"])
        if row["evidence"] == "readme_model_list" and (row["source_sha256"] is None or (row["source_url"], "readme") not in link_pairs):
            raise ValueError("readme evidence requires the fingerprinted source readme link")
        identity = {k: v for k, v in row.items() if k not in ("id", "source_sha256")}
        identity["links"] = sorted(link_pairs)
        identity["operating_systems"] = sorted(systems)
        serialized = json.dumps(identity, sort_keys=True)
        if serialized in metadata_seen:
            raise ValueError("duplicate driver metadata")
        metadata_seen.add(serialized)
    return {"models": len(models), "sources": len(sources), "documents": len(documents),
            "utilities": len(utilities), "driver_metadata_entries": len(drivers),
            "models_with_documents": sum(bool(row["document_ids"]) for row in models),
            "models_with_driver_metadata": sum(bool(row["driver_ids"]) for row in models),
            "selector_models": sum("lenovo-eol-selector" in row["sources"] for row in models),
            "matrix_routes": len({row["matrix_url"] for row in models if row["matrix_url"]}),
            "driver_source_routes": len({row["source_url"] for row in drivers}),
            "unique_download_urls": len(urls["download"]), "unique_readme_urls": len(urls["readme"]),
            "firmware_metadata_entries": sum(row["risk"] == "firmware" for row in drivers),
            "manufacturer_listing_entries": sum(row["evidence"] == "manufacturer_listing" for row in drivers),
            "readme_model_list_entries": sum(row["evidence"] == "readme_model_list" for row in drivers)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--selector", type=Path, help="read explicit selector text and reconcile exact row identities")
    args = parser.parse_args(argv)
    try:
        result = audit_catalogue(args.root)
        if args.selector is not None:
            original = parse_selector(args.selector.read_text(encoding="utf-8"))
            catalogue = json.loads((args.root / "data" / "models.json").read_text(encoding="utf-8"))
            selected = [row for row in catalogue["models"] if "lenovo-eol-selector" in row["sources"]]
            identities = {(row["name"], row["matrix_url"]) for row in selected}
            # Exact observed label+route pairs only. See docs/data-quality.md;
            # the raw parser remains unchanged, and unknown drift still fails.
            corrections = {
                ('ThinkPad 750, 750CSE, 750CS, 755C, 755CS', '750'):
                    'ThinkPad 750, 750CS, 755C, 755CS',
                ('ThinkPad A21e (Type 2632)', 'A21e-2632'):
                    'ThinkPad i Series 1800 (Type 2632)',
                ('ThinkPad A22m (Type 2629, 2633)', 'A22m-2629'):
                    'ThinkPad A22m (Type 2633)',
                ('ThinkPad 1400, 1500 (Type 2621, 2651)', '1500-2621'):
                    'ThinkPad 1400 (Type 2621), 1500 (Type 2621, 2651)',
                ('ThinkPad S51', 'S51'): None,
            }
            normalized = []
            excluded = 0
            for row in original:
                label = corrections.get((row['label'], row['matrix']), row['label'])
                if label is None:
                    excluded += 1
                else:
                    normalized.append((label, 'https://download.lenovo.com/lenovo/content/ddfm/' + row['matrix'] + '.html'))
            expected = set(normalized)
            if len(selected) != len(normalized) or len(expected) != len(normalized) or identities != expected:
                raise ValueError("selector identities differ from catalogue")
            result["selector_reconciled"] = len(normalized)
            if excluded:
                result['selector_excluded'] = excluded
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, "catalogue audit failed: " + str(error) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
