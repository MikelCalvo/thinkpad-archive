"""Offline catalogue integrity checks and finite selector-parser regressions."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "tools" / "catalogue_audit.py"


def audit_module():
    if not AUDIT_PATH.is_file():
        raise AssertionError("catalogue audit API is missing")
    spec = importlib.util.spec_from_file_location("catalogue_audit", AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SelectorTests(unittest.TestCase):
    def test_only_thinkpad_rows_preserve_grouped_identity(self):
        text = '''var l_lnv_g = new Array("Lenovo G400|G400");
var l_tp_700 = new Array("ThinkPad 701C, 701CS|701c");
var l_tp_t = new Array("ThinkPad T40|T40", "ThinkPad T40p|T40");
var l_transnote = new Array("TransNote|Transnote");'''
        self.assertEqual(audit_module().parse_selector(text), [
            {"group": "l_tp_700", "label": "ThinkPad 701C, 701CS", "matrix": "701c"},
            {"group": "l_tp_t", "label": "ThinkPad T40", "matrix": "T40"},
            {"group": "l_tp_t", "label": "ThinkPad T40p", "matrix": "T40"},
            {"group": "l_transnote", "label": "TransNote", "matrix": "Transnote"},
        ])

    def test_selector_rejects_malformed_rows_without_execution(self):
        module = audit_module()
        for text in (
            'var l_tp_x = new Array("ThinkPad X20");',
            'var l_tp_x = new Array("IdeaPad X20|X20");',
            'var l_tp_x = new Array("ThinkPad X20|../secret");',
            'var l_tp_x = new Array(doSomething());',
            'var l_tp_x = new Array("ThinkPad X20|X20"); var l_tp_x = new Array("ThinkPad X21|X21");',
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                module.parse_selector(text)


class HistoryTests(unittest.TestCase):
    def test_history_reads_only_dated_model_cells_and_deduplicates(self):
        html = '''<table><tr><th>1992</th></tr><tr><td><a href="/wiki/Category:700">700</a>, <a href="/wiki/Category:700C">700C</a></td><td>Oct 1992</td><td><a href="/wiki/Category:NotAModel">feature</a></td></tr><tr><th>1995</th></tr><tr><td><a href="/wiki/Category:PC110">PC110</a>, <a href="/w/index.php?redlink=1">Template:Missing</a></td><td>Sep 1995</td></tr><tr><td><a href="/wiki/Category:700">700</a></td><td>Oct 1995</td></tr><tr><th>2000</th></tr><tr><td><a href="/wiki/Category:X20">X20</a></td><td>Sep 2000</td></tr></table>'''
        self.assertEqual(audit_module().parse_early_history(html), [
            {"name": "700", "year": 1992, "url": "https://www.thinkwiki.org/wiki/Category:700"},
            {"name": "700C", "year": 1992, "url": "https://www.thinkwiki.org/wiki/Category:700C"},
        ])


class ManualIndexTests(unittest.TestCase):
    def test_manual_index_keeps_thinkpad_rows_and_real_https_pdf_links(self):
        html = '''<table><tr><th>Family</th><th>Download Link</th></tr><tr><td>ThinkPad T400, R400</td><td><a href="https://download.lenovo.com/pccbbs/mobiles_pdf/hmm.pdf"><img></a></td></tr><tr><td>Lenovo G400</td><td><a href="https://download.lenovo.com/g400.pdf">PDF</a></td></tr><tr><td>TransNote</td><td><a href="http://bad.example/hmm.pdf">PDF</a></td></tr><tr><td>i Series 1200, 1300, ThinkPad 130</td><td><a href="https://download.lenovo.com/i.pdf">PDF</a></td></tr></table>'''
        self.assertEqual(audit_module().parse_manual_index(html), [
            {"name": "ThinkPad T400, R400", "url": "https://download.lenovo.com/pccbbs/mobiles_pdf/hmm.pdf"},
            {"name": "i Series 1200, 1300, ThinkPad 130", "url": "https://download.lenovo.com/i.pdf"},
        ])


class MatrixMetadataTests(unittest.TestCase):
    def fixture_row(self):
        return {"category": "Audio", "description": "Audio driver for Windows XP - ThinkPad Version: 1.20 Audio Software Read me", "os": "Windows XP Windows 2000 Windows XP", "released": "09 Dec 2000", "links": [{"url": "https://download.lenovo.com/a.exe", "label": "Audio Software"}, {"url": "https://download.lenovo.com/a.txt", "label": "Read me"}]}

    def test_matrix_row_projects_facts_not_captured_description(self):
        module = audit_module()
        self.assertTrue(hasattr(module, "normalize_matrix_row"), "v2 matrix projection API is missing")
        actual = module.normalize_matrix_row(self.fixture_row(), "https://download.lenovo.com/lenovo/content/ddfm/X20.html", "a" * 64)
        self.assertEqual({k: v for k, v in actual.items() if k != "id"}, {
            "title": "Audio driver for Windows XP - ThinkPad", "category": "Audio", "version": "1.20",
            "operating_systems": ["Windows 2000", "Windows XP"], "released": "09 Dec 2000",
            "links": [{"url": "https://download.lenovo.com/a.exe", "kind": "download"}, {"url": "https://download.lenovo.com/a.txt", "kind": "readme"}],
            "source_url": "https://download.lenovo.com/lenovo/content/ddfm/X20.html", "evidence": "manufacturer_listing", "risk": "software", "source_sha256": "a" * 64,
        })

    def test_identity_preserves_os_version_route_not_link_order(self):
        module = audit_module()
        self.assertTrue(hasattr(module, "normalize_matrix_row"), "v2 matrix projection API is missing")
        row, url = self.fixture_row(), "https://download.lenovo.com/lenovo/content/ddfm/X20.html"
        original = module.normalize_matrix_row(row, url)
        row["links"].reverse()
        self.assertEqual(original, module.normalize_matrix_row(row, url))
        self.assertEqual(original["id"], module.normalize_matrix_row(row, url, "b" * 64)["id"])
        for field, value in (("os", "Windows 7"), ("description", row["description"].replace("1.20", "1.21"))):
            changed = self.fixture_row()
            changed[field] = value
            self.assertNotEqual(original["id"], module.normalize_matrix_row(changed, url)["id"])
        self.assertNotEqual(original["id"], module.normalize_matrix_row(row, url.replace("X20", "X21"))["id"])

    def test_linkless_listing_stays_reference_only_and_missing_version_stays_unknown(self):
        module = audit_module()
        row = self.fixture_row()
        row.update(description="Audio driver Version: 1.20", links=[])
        self.assertEqual(module.normalize_matrix_row(row, "https://download.lenovo.com/matrix.html")["links"], [{"url": "https://download.lenovo.com/matrix.html", "kind": "reference"}])
        row.update(description="Audio driver", links=self.fixture_row()["links"])
        self.assertIsNone(module.normalize_matrix_row(row, "https://download.lenovo.com/matrix.html")["version"])

    def test_download_link_roles_preserve_installer_formats(self):
        module = audit_module()
        row = self.fixture_row()
        row["links"] = [{"url": "https://download.lenovo.com/a" + suffix, "label": "file"} for suffix in (".msi", ".rpm", ".sh", ".sys", ".inf", ".tvt", ".pdf", ".md5")]
        result = module.normalize_matrix_row(row, "https://download.lenovo.com/matrix.html")
        roles = {Path(link["url"]).suffix: link["kind"] for link in result["links"]}
        self.assertEqual(roles, {".msi": "download", ".rpm": "download", ".sh": "download", ".sys": "download", ".inf": "download", ".tvt": "download", ".pdf": "reference", ".md5": "reference"})

    def test_firmware_risk_and_readme_only_are_not_installation_evidence(self):
        module = audit_module()
        self.assertTrue(hasattr(module, "normalize_matrix_row"), "v2 matrix projection API is missing")
        for title, category in (("BIOS update", "BIOS"), ("Embedded Controller Program", "Utility"), ("Hard drive firmware update", "Storage")):
            row = self.fixture_row()
            row.update(description=title + " Version: 2.0 Read me", category=category, os="", released="", links=[row["links"][1]])
            result = module.normalize_matrix_row(row, "https://download.lenovo.com/matrix.html")
            self.assertEqual((result["risk"], result["evidence"], result["version"], result["released"], result["operating_systems"]), ("firmware", "manufacturer_listing", "2.0", None, []))
            self.assertEqual([link["kind"] for link in result["links"]], ["readme"])


class AuditTests(unittest.TestCase):
    def fixture(self):
        return {
            "models": {"schema_version": 2, "scope": {"en": "Selected metadata only", "es": "Solo metadatos seleccionados"}, "sources": [
                {"id": "vendor", "title": "Source", "url": "https://example.org/source", "kind": "official"}
            ], "models": [{"id": "x20", "name": "ThinkPad X20", "aliases": [], "family": "x", "era": "classic", "sources": ["vendor"], "matrix_url": None, "document_ids": ["hmm"], "driver_ids": ["audio"]}]},
            "documents": {"schema_version": 2, "documents": [{"id": "hmm", "title": "HMM", "url": "https://example.org/hmm.pdf", "source_kind": "official", "sha256": None, "bytes": None, "model_hint": "X20"}]},
            "utilities": {"schema_version": 2, "utilities": [{"id": "config", "title": "ThinkPad Configuration", "url": "https://example.org/config.txt", "category": "reference"}]},
            "drivers": {"schema_version": 2, "drivers": [{"id": "audio", "title": "Audio driver", "category": "Audio", "version": "1.0", "operating_systems": ["Windows XP"], "released": "09 Dec 2000", "links": [{"url": "https://download.lenovo.com/audio.exe", "kind": "download"}, {"url": "https://download.lenovo.com/audio.txt", "kind": "readme"}], "source_url": "https://download.lenovo.com/lenovo/content/ddfm/X20.html", "evidence": "manufacturer_listing", "risk": "software", "source_sha256": None}]},
        }

    def run_fixture(self, fixture):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            for name, payload in fixture.items():
                (root / "data" / (name + ".json")).write_text(json.dumps(payload), encoding="utf-8")
            return audit_module().audit_catalogue(root)

    def test_valid_metadata_counts_are_computed(self):
        self.assertEqual(self.run_fixture(self.fixture()), {
            "models": 1, "sources": 1, "documents": 1, "utilities": 1, "driver_metadata_entries": 1,
            "models_with_documents": 1, "models_with_driver_metadata": 1, "selector_models": 0,
            "matrix_routes": 0, "driver_source_routes": 1, "unique_download_urls": 1, "unique_readme_urls": 1,
            "firmware_metadata_entries": 0, "manufacturer_listing_entries": 1, "readme_model_list_entries": 0,
        })

    def test_selector_cli_reconciles_rows_without_merging_matrices(self):
        fixture = self.fixture()
        fixture["models"]["sources"][0]["id"] = "lenovo-eol-selector"
        fixture["models"]["models"][0]["sources"] = ["lenovo-eol-selector"]
        fixture["models"]["models"][0]["matrix_url"] = "https://download.lenovo.com/lenovo/content/ddfm/X20.html"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "data").mkdir()
            for name, payload in fixture.items():
                (root / "data" / (name + ".json")).write_text(json.dumps(payload), encoding="utf-8")
            selector = root / "selector.js"
            selector.write_text('var l_tp_x = new Array("ThinkPad X20|X20");', encoding="utf-8")
            command = [sys.executable, str(AUDIT_PATH), "--root", str(root), "--selector", str(selector)]
            accepted = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            self.assertEqual(json.loads(accepted.stdout)["selector_reconciled"], 1)
            selector.write_text('var l_tp_x = new Array("ThinkPad X21|X20");', encoding="utf-8")
            rejected = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(rejected.returncode, 1)
            self.assertIn("selector identities differ", rejected.stderr)

    def test_broken_references_rejected(self):
        for field, value in (("sources", ["missing"]), ("document_ids", ["missing"]), ("driver_ids", ["missing"])):
            data = self.fixture()
            data["models"]["models"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_fixture(data)

    def test_invalid_urls_traversal_and_duplicate_ids_rejected(self):
        cases = [("url", "http://example.org/hmm.pdf"), ("url", "https://user:password@example.org/hmm.pdf"), ("sha256", "bad"), ("bytes", -1)]
        for field, value in cases:
            data = self.fixture()
            data["documents"]["documents"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.run_fixture(data)
        data = self.fixture()
        data["models"]["models"] *= 2
        with self.assertRaises(ValueError):
            self.run_fixture(data)

    def test_private_paths_and_unknown_fields_rejected(self):
        for field, value in (("title", "/home/example/private"), ("source_body", "captured source text")):
            data = self.fixture()
            data["documents"]["documents"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_fixture(data)


    def test_extra_data_file_rejected_and_metadata_namespace_is_closed(self):
        data = self.fixture()
        data["unexpected"] = {"schema_version": 2, "unrelated": []}
        with self.assertRaisesRegex(ValueError, "data files"):
            self.run_fixture(data)

    def test_v2_driver_dedup_counts_and_evidence_levels(self):
        import copy
        data = self.fixture()
        duplicate = copy.deepcopy(data["drivers"]["drivers"][0])
        duplicate.update(id="audio-second", source_url="https://download.lenovo.com/lenovo/content/ddfm/X21.html")
        data["drivers"]["drivers"].append(duplicate)
        data["models"]["models"][0]["driver_ids"].append("audio-second")
        counts = self.run_fixture(data)
        self.assertEqual((counts["driver_metadata_entries"], counts["unique_download_urls"], counts["unique_readme_urls"]), (2, 1, 1))
        duplicate.update(source_url=data["drivers"]["drivers"][0]["source_url"])
        with self.assertRaisesRegex(ValueError, "duplicate driver metadata"):
            self.run_fixture(data)
        duplicate.update(evidence="readme_model_list", source_url="https://download.lenovo.com/audio.txt", source_sha256="a" * 64)
        duplicate["links"] = [{"url": "https://download.lenovo.com/audio.txt", "kind": "readme"}]
        self.assertEqual(self.run_fixture(data)["readme_model_list_entries"], 1)

    def test_driver_invalid_enums_links_types_and_body_rejected(self):
        for field, value in (("evidence", "installation_tested"), ("risk", "safe"), ("source_sha256", "bad"), ("operating_systems", "Windows XP"), ("version", 3), ("released", False), ("links", []), ("links", [{"url": "http://example.org/bad", "kind": "readme"}]), ("links", [{"url": "https://example.org/good", "kind": "installer"}]), ("title", "captured\nbody"), ("title", "x" * 401)):
            data = self.fixture()
            data["drivers"]["drivers"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_fixture(data)
        data = self.fixture()
        data["drivers"]["drivers"][0].update(evidence="readme_model_list")
        with self.assertRaisesRegex(ValueError, "readme evidence"):
            self.run_fixture(data)

    def test_schema_v2_localized_scope_exact_fields_and_source_kind(self):
        for location, field, value in (("models", "schema_version", 1), ("models", "scope", "English only"), ("models", "scope", {"en": "English"})):
            data = self.fixture()
            data[location][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.run_fixture(data)
        data = self.fixture()
        data["models"]["sources"][0]["kind"] = "unverified"
        with self.assertRaises(ValueError):
            self.run_fixture(data)
        data = self.fixture()
        data["documents"]["documents"][0]["extra_field"] = "not public metadata"
        with self.assertRaises(ValueError):
            self.run_fixture(data)


class LiveCatalogueTests(unittest.TestCase):
    def test_live_catalogue_schema_and_scope(self):
        counts = audit_module().audit_catalogue(ROOT)
        self.assertEqual(counts["models"], 250)
        self.assertEqual(counts["documents"], 88)
        self.assertEqual(counts["utilities"], 10)
        self.assertGreater(counts["driver_metadata_entries"], 1000)
        self.assertGreater(counts["models_with_driver_metadata"], 110)
        self.assertEqual(counts["selector_models"], 161)
        data = json.loads((ROOT / "data" / "models.json").read_text(encoding="utf-8"))
        names = {item["name"] for item in data["models"]}
        self.assertTrue({"ThinkPad 300", "ThinkPad 700", "ThinkPad 700C", "ThinkPad 700T"} <= names)
        self.assertTrue({"ThinkPad X200", "ThinkPad X200s", "ThinkPad X200si", "ThinkPad X200 Tablet", "ThinkPad X201", "ThinkPad X201i", "ThinkPad X201s", "ThinkPad X201 Tablet", "ThinkPad X201i Tablet", "ThinkPad X220", "ThinkPad X220i", "ThinkPad X220 Tablet", "ThinkPad X220i Tablet", "ThinkPad X230", "ThinkPad X230i", "ThinkPad X230 Tablet", "ThinkPad X230i Tablet"} <= names)
        self.assertIn("ThinkPad 701C, 701CS", names)

    def test_exact_variant_associations_and_finite_counts(self):
        payloads = {name: json.loads((ROOT / "data" / (name + ".json")).read_text(encoding="utf-8")) for name in ("models", "documents", "utilities", "drivers")}
        self.assertEqual(len(payloads["models"]["models"]), 250)
        self.assertEqual(len(payloads["documents"]["documents"]), 88)
        self.assertEqual(len(payloads["models"]["sources"]), 20)
        models = {row["name"]: row for row in payloads["models"]["models"]}
        self.assertEqual(len(models), 250)
        for name in ("ThinkPad 300C", "ThinkPad 750CE", "ThinkPad X201i Tablet", "ThinkPad X201si", "ThinkPad X230s"):
            self.assertEqual(models[name]["document_ids"], [], name)
        self.assertNotEqual(models["ThinkPad T40"]["id"], models["ThinkPad T40p"]["id"])
        self.assertEqual(models["ThinkPad T40"]["matrix_url"], models["ThinkPad T40p"]["matrix_url"])
        self.assertEqual(models["ThinkPad 1400, 1500 (Type 2611)"]["aliases"], ["ThinkPad 1400 (Type 2611)", "ThinkPad 1500 (Type 2611)"])
        self.assertNotIn("ThinkPad 860", models)
        self.assertNotIn("ThinkPad 800", models)
        documents = payloads["documents"]["documents"]
        self.assertEqual(len({row["url"] for row in documents}), 88)
        self.assertEqual(sum(row["sha256"] is not None for row in documents), 49)
        for utility in payloads["utilities"]["utilities"]:
            self.assertLess(len(utility["title"]), 100)
            self.assertNotIn("verbatim", utility["title"])

    def test_public_v2_metadata_only_and_localization_boundaries(self):
        self.assertEqual({p.name for p in (ROOT / "data").iterdir()}, {"models.json", "documents.json", "utilities.json", "drivers.json"})
        data = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "data").glob("*.json")}
        for payload in data.values():
            self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(set(data["models"]["scope"]), {"en", "es"})
        self.assertNotEqual(data["models"]["scope"]["en"], data["models"]["scope"]["es"])
        for row in data["models"]["models"]:
            optional = {key for key in ('introduced_unknown',) if key in row}
            self.assertEqual(set(row), set("id name aliases family era sources matrix_url document_ids driver_ids thinkwiki introduced".split()) | optional)
        for row in data["documents"]["documents"]:
            self.assertEqual(set(row), set("id title url source_kind sha256 bytes model_hint".split()))
            self.assertNotIn(";", row["model_hint"])
        for row in data["utilities"]["utilities"]:
            self.assertEqual(set(row), set("id title url category".split()))
            for qualifier in ("historical README only", "— reference", "legacy branch", "first Lenovo branch"):
                self.assertNotIn(qualifier, row["title"])
        for payload in data.values():
            serialized = json.dumps(payload).lower()
            for marker in ("/home/", "file://", "verbatim_header", "source_body", "recording_status", "collection_volume", "disc_path", "external_source_root"):
                self.assertNotIn(marker, serialized)

    def test_newer_exact_associations_do_not_inherit_variant_routes(self):
        models = {row["id"]: row for row in json.loads((ROOT / "data/models.json").read_text())["models"]}
        self.assertTrue((ROOT / "data/drivers.json").is_file(), "v2 driver metadata missing")
        drivers = {row["id"]: row for row in json.loads((ROOT / "data/drivers.json").read_text())["drivers"]}
        for identifier in ("x220", "x230", "x230s"):
            self.assertTrue(models[identifier]["driver_ids"])
        for identifier in ("x201si", "x230s", "x220i", "x230i", "x230-tablet", "x230i-tablet"):
            self.assertIsNone(models[identifier]["matrix_url"])
            self.assertTrue(all(drivers[d]["evidence"] == "readme_model_list" for d in models[identifier]["driver_ids"]))
        for identifier in ("x200si", "x201i-tablet"):
            self.assertTrue(models[identifier]["driver_ids"])
        self.assertTrue(any(drivers[d]["evidence"] == "manufacturer_listing" for d in models["x230"]["driver_ids"]))
        self.assertTrue(any(drivers[d]["evidence"] == "readme_model_list" for d in models["x230s"]["driver_ids"]))
        self.assertFalse(models["t14-gen-5-amd"]["driver_ids"])

    def test_audit_cli(self):
        completed = subprocess.run([sys.executable, str(AUDIT_PATH), "--root", str(ROOT)], text=True, capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["selector_models"], 161)


if __name__ == "__main__":
    unittest.main()
