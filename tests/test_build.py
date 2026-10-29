"""Public v2 contract tests using original, synthetic source metadata only."""
from __future__ import annotations

import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def fixture_data():
    return {
        "models": {"schema_version": 2, "scope": {"en": "Synthetic source scope.", "es": "Alcance sintético de las fuentes."}, "sources": [{"id": "maker", "title": "Maker reference", "url": "https://example.org/catalogue?a=1&b=2", "kind": "official"}], "models": [
            {"id": "700c", "name": "ThinkPad 700C", "aliases": ["700 C"], "family": "700", "era": "early", "sources": ["maker"], "matrix_url": "https://example.org/700c", "document_ids": ["manual"], "driver_ids": ["audio", "bios"]},
            {"id": "x230-tablet", "name": "ThinkPad X230 Tablet", "aliases": ["X230t"], "family": "x", "era": "lenovo", "sources": ["maker"], "matrix_url": None, "document_ids": [], "driver_ids": ["tablet"]},
            {"id": "700cs", "name": "ThinkPad 700CS", "aliases": [], "family": "700", "era": "early", "sources": ["maker"], "matrix_url": None, "document_ids": [], "driver_ids": []},
        ]},
        "documents": {"schema_version": 2, "documents": [{"id": "manual", "title": "Hardware Maintenance Manual", "url": "https://example.org/manual.pdf", "source_kind": "official", "sha256": "a" * 64, "bytes": 1234, "model_hint": "700C"}]},
        "utilities": {"schema_version": 2, "utilities": [{"id": "diagnostic", "title": "PC Doctor", "url": "https://example.org/notes.txt", "category": "diagnostic"}, {"id": "reference", "title": "Configuration Utility", "url": "https://example.org/reference.txt", "category": "reference"}]},
        "drivers": {"schema_version": 2, "drivers": [
            {"id": "audio", "title": "Audio Features", "category": "Audio", "version": "1.23", "operating_systems": ["Windows 95", "OS/2"], "released": "1998-01-02", "links": [{"url": "https://example.org/audio.exe", "kind": "download"}, {"url": "https://example.org/audio.txt", "kind": "readme"}], "source_url": "https://example.org/700c", "evidence": "manufacturer_listing", "risk": "software", "source_sha256": "b" * 64},
            {"id": "bios", "title": "System Program", "category": "BIOS", "version": None, "operating_systems": [], "released": None, "links": [{"url": "https://example.org/bios", "kind": "reference"}], "source_url": "https://example.org/700c", "evidence": "manufacturer_listing", "risk": "firmware", "source_sha256": None},
            {"id": "tablet", "title": "Tablet Button Driver", "category": "Input", "version": "2.0", "operating_systems": ["Windows 7"], "released": None, "links": [{"url": "https://example.org/tablet.txt", "kind": "readme"}], "source_url": "https://example.org/tablet", "evidence": "readme_model_list", "risk": "software", "source_sha256": "c" * 64},
            {"id": "unassociated", "title": "Unassociated source metadata", "category": "Other", "version": None, "operating_systems": [], "released": None, "links": [], "source_url": "https://example.org/other", "evidence": "manufacturer_listing", "risk": "software", "source_sha256": None},
        ]},
    }


def write_fixture(directory, records=None):
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in (records or fixture_data()).items():
        (directory / (name + ".json")).write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.tags = [], [], []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        self.tags.append((tag, attr))
        if "id" in attr:
            self.ids.append(attr["id"])
        for key in ("href", "src"):
            if key in attr:
                self.links.append(attr[key])


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tp-web-", dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / "data"
        write_fixture(self.data)
        self.locales = self.base / "locales"
        shutil.copytree(ROOT / "locales", self.locales)
        self.output = self.base / "site"

    def engine(self):
        self.assertIsNotNone(importlib.util.find_spec("thinkpad_archive"))
        import thinkpad_archive
        self.assertTrue(callable(getattr(thinkpad_archive, "build_site", None)))
        return thinkpad_archive

    def build(self, **kwargs):
        return self.engine().build_site(self.output, data_dir=self.data, locales_dir=self.locales, **kwargs)

    def change(self, table, edit):
        path = self.data / (table + ".json")
        obj = json.loads(path.read_text(encoding="utf-8"))
        edit(obj)
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def text(self, page="en/index.html"):
        return (self.output / page).read_text(encoding="utf-8")

    def test_api_is_public_only(self):
        self.assertEqual(list(inspect.signature(self.engine().build_site).parameters), ["output", "data_dir", "locales_dir", "default_language", "stats_enabled", "offline_download"])
        import thinkpad_archive.validation as validation
        self.assertFalse(hasattr(validation, "private_bindings"))
        self.assertFalse(hasattr(validation, "VOLUME_IDS"))

    def test_v2_build_has_no_collection_dependency_pages_or_controls(self):
        self.assertEqual(set(p.name for p in self.data.iterdir()), {"models.json", "documents.json", "drivers.json", "utilities.json"})
        self.build()
        for path in self.output.rglob("*"):
            if path.is_file() and path.suffix not in ('.png', '.zip'):
                content = path.read_text(encoding="utf-8").lower()
                for removed in ("volumes.html", "private-map", "cd-r", "dvd-r", "recorded selection", "volúmenes", "colección"):
                    self.assertNotIn(removed, content, str(path.relative_to(self.output)))
        self.assertFalse(any(self.output.rglob("volumes.html")))
        self.assertEqual({p.relative_to(self.output).as_posix() for p in self.output.rglob('*') if p.is_file() and p.suffix in ('.txt', '.xml')}, {'robots.txt', 'sitemap.xml'})
        self.assertEqual({p.suffix for p in self.output.rglob("*") if p.is_file()}, {".html", ".css", ".js", ".svg", ".png", ".txt", ".xml", ".zip", ".sha256"})

    def test_complete_bilingual_tree_same_model_links_and_local_assets(self):
        self.build()
        self.assertIn('<html lang="en" data-language-entry="true">', self.text("index.html"))
        for lang in ("en", "es"):
            for page in ("index.html", "sources.html", "models/700c.html", "models/x230-tablet.html", "models/700cs.html"):
                self.assertTrue((self.output / lang / page).is_file())
            model = self.text(lang + "/models/700c.html")
            self.assertIn(f'../../{"es" if lang == "en" else "en"}/models/700c.html', model)
            self.assertIn('href="https://example.org/manual.pdf"', model)
        for path in self.output.rglob("*.html"):
            parser = Links()
            parser.feed(path.read_text())
            self.assertEqual(len(parser.ids), len(set(parser.ids)))
            self.assertNotIn("fetch(", path.read_text())
            for tag, attrs in parser.tags:
                if tag in ("script", "link", "img") and attrs.get('rel') not in ('canonical', 'alternate'):
                    self.assertFalse(urlsplit(attrs.get("src", attrs.get("href", ""))).scheme)
                if attrs.get('rel') == 'alternate':
                    self.assertEqual(urlsplit(attrs['href']).scheme, 'https')
                    self.assertEqual(urlsplit(attrs['href']).netloc, 'thinkpadarchive.com')
                    self.assertIn(attrs['hreflang'], ('en', 'es', 'x-default'))
            for href in parser.links:
                parts = urlsplit(href)
                if parts.scheme:
                    self.assertEqual(parts.scheme, "https")
                    continue
                self.assertFalse(parts.netloc)
                target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
                self.assertTrue(target.is_relative_to(self.output.resolve()))
                self.assertTrue(target.is_file(), href)
                if parts.fragment:
                    linked = Links()
                    linked.feed(target.read_text())
                    self.assertIn(parts.fragment, linked.ids)

    def test_no_script_rows_and_useful_metadata_availability_controls(self):
        self.build()
        parser = Links()
        parser.feed(self.text())
        rows = [attrs for tag, attrs in parser.tags if tag == "tr" and "data-search" in attrs]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all("hidden" not in row for row in rows))
        self.assertEqual([(r["data-drivers"], r["data-manuals"]) for r in rows], [("with", "with"), ("without", "without"), ("with", "without")])
        selects = {attrs.get("id") for tag, attrs in parser.tags if tag == "select"}
        self.assertEqual(selects, {"family-filter", "driver-filter", "manual-filter"})
        self.assertIn('type="search"', self.text())
        empty = next(attrs for tag, attrs in parser.tags if attrs.get('id') == 'empty-results')
        self.assertEqual(empty.get('aria-live'), 'polite')
        self.assertIn('id="filters" class="filters" hidden', self.text())
        self.assertNotIn('class="stats"', self.text())
        self.assertNotIn('Manual references</dt><dd>1</dd>', self.text())
        self.assertNotIn('Model entries</dt><dd>3</dd>', self.text())
        self.assertNotIn("PC Doctor", self.text())
        self.assertIn("700 C", self.text("en/models/700c.html"))

    def test_driver_details_links_evidence_and_separate_firmware_warning(self):
        self.build()
        text = self.text("en/models/700c.html")
        for value in ("Audio Features", "Audio", "1.23", "Windows 95", "OS/2", "1998-01-02", "https://example.org/audio.exe", "https://example.org/audio.txt", "https://example.org/700c", "b" * 64, "Manufacturer listing only", "Download", "Readme", "Source listing", "Not recorded", "availability", "installation"):
            self.assertIn(value, text)
        self.assertIn('<section id="firmware"', text)
        self.assertIn('class="firmware-warning"', text)
        self.assertGreater(text.index("System Program"), text.index('<section id="firmware"'))
        self.assertLess(text.index("Audio Features"), text.index('<section id="firmware"'))
        self.assertIn("Readme names this model", self.text("en/models/x230-tablet.html"))
        self.assertNotIn("Manufacturer listing only", self.text("en/models/x230-tablet.html"))

    def test_firmware_only_entry_is_not_reported_as_missing_driver_metadata(self):
        self.change("models", lambda d: d["models"][0].update(driver_ids=["bios"]))
        self.build()
        for lang in ("en", "es"):
            model = self.text(lang + "/models/700c.html")
            translations = json.loads((self.locales / (lang + ".json")).read_text())
            self.assertNotIn(translations["no_drivers"], model)
            self.assertIn(translations["firmware_warning"], model)
            self.assertIn("System Program", model)
        self.assertIn('href="models/700c.html#firmware"', self.text())

    def test_explicit_missing_download_and_source_digest_are_readable(self):
        self.change("models", lambda d: d["models"][2].update(driver_ids=["unassociated"]))
        self.build()
        for lang in ("en", "es"):
            model = self.text(lang + "/models/700cs.html")
            translations = json.loads((self.locales / (lang + ".json")).read_text())
            self.assertIn(translations["no_package_links"], model)
            self.assertIn(translations["availability_note"], model)
            self.assertIn(translations["not_recorded"], model)
            self.assertIn('href="https://example.org/other"', model)

    def test_spanish_model_applicability_remains_without_landing_library(self):
        self.build()
        model = self.text("es/models/700c.html")
        home = self.text("es/index.html")
        self.assertIn("no es necesariamente un manual de servicio", model)
        self.assertIn("tipo de máquina y la variante exactos", model)
        self.assertNotIn('reference-library', home)
        self.assertNotIn('class="utility"', home)
        self.assertNotIn("Selected document reference", model)
        self.assertNotIn("PC Doctor", home)

    def test_each_absent_download_or_readme_is_explicit_in_both_languages(self):
        self.build()
        expected = {"en": ("No download URL recorded; availability unknown.", "No readme URL recorded; model applicability unverified."), "es": ("No consta una URL de descarga; disponibilidad desconocida.", "No consta una URL de readme; aplicación al modelo sin verificar.")}
        for lang in ("en", "es"):
            translations = json.loads((self.locales / (lang + ".json")).read_text())
            bios = self.text(lang + "/models/700c.html").split('<section id="firmware"', 1)[1]
            self.assertIn(expected[lang][0], bios)
            self.assertIn(expected[lang][1], bios)
            self.assertEqual(translations["missing_download"], expected[lang][0])
            self.assertEqual(translations["missing_readme"], expected[lang][1])
            tablet = self.text(lang + "/models/x230-tablet.html")
            self.assertIn(translations["missing_download"], tablet)
            self.assertNotIn(translations["missing_readme"], tablet)

    def test_exact_driver_ids_no_implicit_family_matching_or_fake_model_route(self):
        self.build()
        variant = self.text("en/models/700cs.html")
        self.assertNotIn("Audio Features", variant)
        self.assertNotIn("System Program", variant)
        self.assertNotIn("https://example.org/700c", variant)
        self.assertNotIn("Unassociated source metadata", self.text("en/models/700c.html"))
        self.assertIn("No driver metadata linked", variant)
        self.assertIn("No manual linked", variant)
        self.assertIn("https://example.org/catalogue?a=1&amp;b=2", variant)
        self.assertIn("No model-specific matrix", variant)

    def test_complete_spanish_ui_scope_evidence_warning_and_metadata_caveats(self):
        self.build(default_language="es")
        self.assertIn('<html lang="es" data-language-entry="true">', self.text("index.html"))
        es = self.text("es/models/700c.html")
        for value in ("Controladores", "Versión", "Sistemas operativos anunciados", "Fecha", "Descarga", "Listado del fabricante", "Solo listado del fabricante", "Advertencia de firmware", "instalación", "disponibilidad"):
            self.assertIn(value, es)
        self.assertIn("El readme nombra este modelo", self.text("es/models/x230-tablet.html"))
        source = self.text("es/sources.html")
        self.assertIn("Alcance sintético de las fuentes.", source)
        self.assertNotIn("Synthetic source scope.", source)
        for page in ("es/index.html", "es/models/700c.html", "es/sources.html"):
            for english in ("Manufacturer listing only", "No driver metadata linked", "Readme names this model", "Before using", "Reference metadata only"):
                self.assertNotIn(english, self.text(page))
        self.assertIn("Hardware Maintenance Manual", es)
        self.assertIn("Windows 95", es)

    def test_escape_every_metadata_context_including_driver_fields(self):
        bad = '\"><script>alert(1)</script>&'
        self.change("models", lambda d: d["models"][0].update(name=bad, aliases=[bad]))
        self.change("models", lambda d: d["sources"][0].update(title=bad))
        self.change("models", lambda d: d["scope"].update(en=bad))
        self.change("documents", lambda d: d["documents"][0].update(title=bad, model_hint=bad))
        self.change("utilities", lambda d: d["utilities"][0].update(title=bad))
        self.change("drivers", lambda d: d["drivers"][0].update(title=bad, category=bad, version=bad, operating_systems=[bad], released=bad))
        self.build()
        for path in self.output.rglob("*.html"):
            self.assertNotIn(bad, path.read_text())
            self.assertNotIn("<script>alert", path.read_text())
        self.assertIn("&lt;script&gt;", self.text("en/models/700c.html"))

    def test_additional_locale_same_model_and_explicit_scope_fallback(self):
        other = json.loads((self.locales / "en.json").read_text())
        other.update(language_name="Français", catalogue="Catalogue de test")
        (self.locales / "fr.json").write_text(json.dumps(other))
        self.build(default_language="fr")
        self.assertIn('<html lang="fr" data-language-entry="true">', self.text("index.html"))
        self.assertIn("Catalogue de test", self.text("fr/index.html"))
        self.assertIn("../../fr/models/700c.html", self.text("en/models/700c.html"))
        self.assertIn('<p lang="en">Synthetic source scope.</p>', self.text("fr/sources.html"))

    def test_future_locale_localized_scope_used_when_supplied(self):
        other = json.loads((self.locales / "en.json").read_text())
        (self.locales / "fr.json").write_text(json.dumps(other))
        self.change("models", lambda d: d["scope"].update(fr="Portée originale."))
        self.build()
        self.assertIn('<p lang="fr">Portée originale.</p>', self.text("fr/sources.html"))

    def test_existing_output_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep"
        marker.write_bytes(b"unchanged")
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(marker.read_bytes(), b"unchanged")
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_invalid_v2_metadata_rejected_before_output(self):
        cases = [
            ("models", lambda d: d["models"][0].update(id="../escape")),
            ("models", lambda d: d["models"][0].update(family="../escape")),
            ("models", lambda d: d["models"][0].update(document_ids=["unknown"])),
            ("models", lambda d: d["models"][0].update(driver_ids=["unknown"])),
            ("models", lambda d: d["models"][0].update(driver_ids=["audio", "audio"])),
            ("models", lambda d: d["models"][0].update(sources=["unknown"])),
            ("models", lambda d: d["models"][0].update(era=[])),
            ("models", lambda d: d["sources"][0].update(kind={})),
            ("models", lambda d: d["models"].append(d["models"][0].copy())),
            ("models", lambda d: d.update(schema_version=True)),
            ("models", lambda d: d.update(scope="untranslated project description")),
            ("models", lambda d: d["scope"].pop("es")),
            ("models", lambda d: d["scope"].update(es={"bad": "text"})),
            ("models", lambda d: d["scope"].update(bad_code="text")),
            ("documents", lambda d: d["documents"][0].update(bytes=True)),
            ("documents", lambda d: d["documents"][0].update(sha256="incorrect")),
            ("documents", lambda d: d["documents"][0].update(source_kind=[])),
            ("utilities", lambda d: d["utilities"][0].update(category={})),
            ("drivers", lambda d: d["drivers"][0].update(evidence="installation_tested")),
            ("drivers", lambda d: d["drivers"][0].update(risk=[])),
            ("drivers", lambda d: d["drivers"][0].update(source_sha256="incorrect")),
            ("drivers", lambda d: d["drivers"][0].update(operating_systems="Windows")),
            ("drivers", lambda d: d["drivers"][0].update(operating_systems=[{}])),
            ("drivers", lambda d: d["drivers"][0].update(version=1.2)),
            ("drivers", lambda d: d["drivers"][0].update(released=123)),
            ("drivers", lambda d: d["drivers"][0].update(links=[{"url": "https://example.org/a", "kind": "execute"}])),
            ("drivers", lambda d: d["drivers"][0].update(links=[{}])),
            ("drivers", lambda d: d["drivers"][0].update(links={})),
            ("drivers", lambda d: d["drivers"][0].update(links=[d["drivers"][0]["links"][0]] * 2)),
            ("drivers", lambda d: d["drivers"].append(d["drivers"][0].copy())),
            ("drivers", lambda d: d.update(schema_version=1)),
        ]
        for index, (table, edit) in enumerate(cases):
            with self.subTest(case=index, table=table):
                write_fixture(self.data)
                self.change(table, edit)
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse(self.output.exists())

    def test_old_schema_fields_are_not_part_of_public_contract(self):
        cases = [
            ("models", lambda d: d["models"][0].update(collection_volume="700")),
            ("documents", lambda d: d["documents"][0].update(local_name="manuals/manual.pdf")),
            ("utilities", lambda d: d["utilities"][0].update(local_name="references/notes.txt")),
        ]
        for index, (table, edit) in enumerate(cases):
            with self.subTest(case=index):
                write_fixture(self.data)
                self.change(table, edit)
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse(self.output.exists())

    def test_every_url_boundary_refuses_unsafe_urls(self):
        unsafe = ("http://example.org/", "javascript:alert(1)", "https://user:pass@example.org/", "https://example.org/\nunsafe", "https://example.org/%0aunsafe", "https://example.org/%zz", "https://example.org/%", "https://example.org:0/", "https://example.org:70000/", "https://example.org:<script>/", "https://bad<host>.org/", 'https://bad"host.org/', "https://example.org%40attacker.org/")
        edits = (
            ("models", lambda d, u: d["models"][0].update(matrix_url=u)),
            ("models", lambda d, u: d["sources"][0].update(url=u)),
            ("documents", lambda d, u: d["documents"][0].update(url=u)),
            ("utilities", lambda d, u: d["utilities"][0].update(url=u)),
            ("drivers", lambda d, u: d["drivers"][0].update(source_url=u)),
            ("drivers", lambda d, u: d["drivers"][0]["links"][0].update(url=u)),
        )
        for index, url in enumerate(unsafe):
            for table, edit in edits:
                with self.subTest(case=index, table=table):
                    write_fixture(self.data)
                    self.change(table, lambda d: edit(d, url))
                    with self.assertRaises(ValueError):
                        self.build()
                    self.assertFalse(self.output.exists())

    def test_locale_validation_missing_unknown_nontext_unsafe_and_empty(self):
        original = (self.locales / "es.json").read_bytes()
        for mode in ("missing", "extra", "nontext", "unsafe", "empty"):
            with self.subTest(mode=mode):
                data = json.loads(original)
                if mode == "missing":
                    data.pop("catalogue")
                elif mode == "extra":
                    data["unrecognized"] = "not supported"
                elif mode == "nontext":
                    data["catalogue"] = {"bad": "value"}
                elif mode == "empty":
                    data["catalogue"] = ""
                else:
                    (self.locales / "bad_code.json").write_text(json.dumps(data))
                (self.locales / "es.json").write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse(self.output.exists())
        (self.locales / "bad_code.json").unlink()

    def test_unknown_default_language_rejected(self):
        with self.assertRaises(ValueError):
            self.build(default_language="zz")
        self.assertFalse(self.output.exists())

    def test_output_and_input_symlink_ancestors_refused(self):
        alias = self.base / "alias"
        alias.symlink_to(self.data, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.engine().build_site(self.output, data_dir=alias)
        parent = self.base / "outside"
        parent.mkdir()
        linked = self.base / "linked"
        linked.symlink_to(parent, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.engine().build_site(linked / "site", data_dir=self.data)
        self.assertFalse((parent / "site").exists())

    def test_duplicate_json_keys_rejected(self):
        (self.data / "models.json").write_text('{"schema_version":2,"schema_version":2}')
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(shutil.which("node"), "Node is optional JS verification tooling")
    def test_search_availability_composition_alias_reset_and_empty(self):
        # Exercise the shipped JS, not a reimplementation of its predicates.
        script = r'''
const assert = require('node:assert/strict');
const listeners = new Map();
function element(value = '') {return {value, hidden:true, textContent:'', addEventListener(k,f){listeners.set(this.id+':'+k,f);}};}
const ids = ['filters','model-search','family-filter','driver-filter','manual-filter','empty-results','model-rows'];
const elements = Object.fromEntries(ids.map(id => [id, Object.assign(element(), {id})]));
const rows = [
  {'data-search':'ThinkPad 700C 700 C','data-family':'700','data-drivers':'with','data-manuals':'with'},
  {'data-search':'ThinkPad 700CS','data-family':'700','data-drivers':'without','data-manuals':'without'},
  {'data-search':'ThinkPad X230 Tablet X230t','data-family':'x','data-drivers':'with','data-manuals':'without'}
].map(data => ({hidden:false,getAttribute:k => data[k]}));
elements['model-rows'].getElementsByTagName = () => rows;
global.document = {getElementById:id => elements[id]};
global.window = {setTimeout:f => f()};
require(process.argv[1]);
function fire(id, event, value) {elements[id].value=value;listeners.get(id+':'+event)({preventDefault(){}});}
function visible(expected) {assert.deepEqual(rows.map((r,i)=>r.hidden ? null : i).filter(i=>i!==null), expected);assert.equal(elements['empty-results'].hidden,expected.length!==0);}
assert.equal(elements.filters.hidden,false);visible([0,1,2]);
fire('driver-filter','change','without');visible([1]);
fire('driver-filter','change','with');visible([0,2]);
fire('manual-filter','change','with');visible([0]);
fire('family-filter','change','x');visible([]);
for (const id of ['model-search','family-filter','driver-filter','manual-filter']) elements[id].value='';
listeners.get('filters:reset')();visible([0,1,2]);
fire('model-search','input','X230t');visible([2]);
fire('model-search','input','700 c');visible([0,1]);
fire('family-filter','change','x');visible([]);
listeners.get('filters:submit')({preventDefault(){}});
console.log('search composition passed');
'''
        result = subprocess.run(["node", "-e", script, str(ROOT / "assets/search.js")], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("search composition passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
