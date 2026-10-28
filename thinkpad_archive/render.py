"""Original static HTML renderer; every text and attribute operand is escaped."""
from __future__ import annotations

from html import escape
from pathlib import PurePosixPath
from urllib.parse import quote, urlencode
import posixpath


# Presentation groups do not alter source categories or model associations.
CATEGORIES = (
    ("audio", "♫", ("audio",)),
    ("graphics", "▣", ("display and video graphics", "multimedia")),
    ("network", "⇄", ("networking", "networking: lan (ethernet)", "networking: wireless lan", "networking: wireless wan")),
    ("bluetooth", "⌁", ("bluetooth and modem",)),
    ("chipset", "▦", ("chipset", "memory")),
    ("power", "ϟ", ("power management",)),
    ("input", "⌨", ("mouse and keyboard", "input")),
    ("storage", "▤", ("storage", "accessories : storage (hdd / ssd / dvd / blu-ray / usb / card reader)", "diskette drive")),
    ("optical", "◎", ("optical drive", "cd and dvd drives")),
    ("usb", "⌘", ("usb device, firewire, ieee 1394",)),
    ("security", "◇", ("security", "fingerprint reader")),
    ("camera", "◉", ("camera and card reader",)),
    ("expansion", "⊞", ("pcmcia (pc card)", "docking station and port replicator")),
    ("updates", "↻", ("windows update", "patch", "operating system installation and update")),
    ("utilities", "⚙", ("thinkvantage technology", "software and utility", "software and utilities", "utility", "enterprise management", "software installation/configuration", "preloaded software", "data migration", "installation and user guide")),
    ("recovery", "↶", ("recovery",)),
    ("diagnostics", "+", ("diagnostic",)),
    ("bios", "▧", ("bios", "bios/uefi")),
    ("other", "⋯", ()),
)


def category_key(source_category):
    normalized = source_category.strip().casefold()
    return next((key for key, _, names in CATEGORIES if normalized in names), "other")


def e(value):
    return escape(str(value), quote=True)


class Renderer:
    def __init__(self, data, locales):
        self.data, self.locales = data, locales
        self.docs = {row["id"]: row for row in data["documents"]}
        self.drivers = {row["id"]: row for row in data["drivers"]}
        self.sources = {row["id"]: row for row in data["sources"]}

    @staticmethod
    def href(current, target):
        return posixpath.relpath(target, str(PurePosixPath(current).parent))

    def link(self, current, target, label, **attrs):
        extra = "".join(' ' + key + '="' + e(value) + '"' for key, value in attrs.items())
        return '<a href="' + e(self.href(current, target)) + '"' + extra + '>' + e(label) + '</a>'

    @staticmethod
    def remote(url, label):
        return '<a href="' + e(url) + '" rel="noreferrer">' + e(label) + '</a>'

    @staticmethod
    def metadata(items):
        return '<dl class="metadata">' + ''.join('<div><dt>' + e(key) + '</dt><dd>' + e(value) + '</dd></div>' for key, value in items) + '</dl>'

    def page(self, current, lang, title, body, kind="home", model_id=None):
        t = self.locales[lang]
        nav = []
        for key, filename in (("catalogue", "index.html"), ("sources", "sources.html")):
            active = {"aria-current": "page"} if key == {"home": "catalogue", "sources": "sources"}.get(kind) else {}
            nav.append(self.link(current, lang + "/" + filename, t[key], **active))
        languages = []
        for code, translation in self.locales.items():
            target = code + ("/models/" + model_id + ".html" if model_id else "/" + ("sources.html" if kind == "sources" else "index.html"))
            languages.append(self.link(current, target, translation["language_name"], hreflang=code, lang=code, **({"aria-current": "true"} if code == lang else {})))
        css = self.href(current, "assets/style.css")
        script = self.href(current, "assets/search.js")
        return ('<!DOCTYPE html>\n<html lang="' + e(lang) + '">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;self&#39;; script-src &#39;self&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;">\n'
                '<meta name="referrer" content="no-referrer">\n<title>' + e(title + " · " + t["site_name"]) + '</title>\n'
                '<link rel="stylesheet" href="' + e(css) + '">\n'
                + '<script src="' + e(self.href(current, "assets/ui.js")) + '" defer></script>\n'
                + ('<script src="' + e(script) + '" defer></script>\n' if kind == "home" else '') + '</head>\n<body>\n'
                '<a class="skip-link" href="#main">' + e(t["skip"]) + '</a>\n'
                '<header class="site-header"><div class="topbar">'
                '<nav class="language-nav" aria-label="' + e(t["language"]) + '">' + ' '.join(languages) + '</nav>'
                '<nav class="main-nav" aria-label="' + e(t["site_name"]) + '">' + ''.join(nav) + '</nav></div></header>\n'
                '<main id="main">' + body + '</main>\n<footer><p>' + e(t["footer"]) + '</p><p>' + e(t["legacy_note"]) + '</p></footer>\n</body>\n</html>\n')

    def document(self, current, lang, doc):
        t = self.locales[lang]
        items = [(t["source_kind"], t[doc["source_kind"]]), (t["model_hint"], doc["model_hint"] or t["not_recorded"]), (t["bytes"], doc["bytes"] if doc["bytes"] is not None else t["not_recorded"])]
        return ('<article class="document"><h3>' + e(doc["title"]) + '</h3><p>' + self.remote(doc["url"], t["remote"]) + '</p><p class="small">' + e(t["metadata_only"]) + '</p>' + self.metadata(items) + '<dl class="metadata"><div class="digest"><dt>' + e(t["digest"]) + '</dt><dd><code>' + e(doc["sha256"] or t["not_recorded"]) + '</code></dd></div></dl></article>')

    def driver(self, lang, driver):
        t = self.locales[lang]
        items = [(t["category"], driver["category"]), (t["version"], driver["version"] or t["not_recorded"]), (t["operating_systems"], ' / '.join(driver["operating_systems"]) or t["not_recorded"]), (t["released"], driver["released"] or t["not_recorded"]), (t["evidence"], t[driver["evidence"]])]
        links = ' <span aria-hidden="true">·</span> '.join(self.remote(link["url"], t[link["kind"]]) for link in driver["links"])
        body = '<article class="driver"><h3>' + e(driver["title"]) + '</h3>' + self.metadata(items)
        body += '<p class="package-links">' + links + '</p>' if links else '<p>' + e(t["no_package_links"]) + '</p>'
        kinds = {link["kind"] for link in driver["links"]}
        for kind in ("download", "readme"):
            if kind not in kinds:
                body += '<p class="small">' + e(t["missing_" + kind]) + '</p>'
        body += '<p>' + self.remote(driver["source_url"], t["source_url"]) + '</p><p class="small">' + e(t["availability_note"]) + '</p>'
        body += '<dl class="metadata"><div class="digest"><dt>' + e(t["source_digest"]) + '</dt><dd><code>' + e(driver["source_sha256"] or t["not_recorded"]) + '</code></dd></div></dl></article>'
        return body

    def home(self, current, lang):
        t, data = self.locales[lang], self.data
        body = '<section class="hero"><h1 class="archive-title" aria-label="ThinkPad Archive"><span class="title-word" aria-hidden="true">Th<span class="title-i">i</span>nkPad</span> <span class="archive-word" aria-hidden="true">Archive</span></h1><dl class="stats">'
        for key, count in (("model_count", len(data["models"])), ("manual_count", len(data["documents"])), ("driver_count", len(data["drivers"]))):
            body += '<div><dt>' + e(t[key]) + '</dt><dd>' + str(count) + '</dd></div>'
        body += '</dl></section>'
        body += '<section aria-labelledby="catalogue-heading"><div class="section-heading"><span class="section-number" aria-hidden="true">01</span><h2 id="catalogue-heading">' + e(t["browse_heading"]) + '</h2></div>'
        body += '<form id="filters" class="filters" hidden><div class="search-field"><label for="model-search">' + e(t["search"]) + '</label><input type="search" id="model-search" placeholder="' + e(t["search_hint"]) + '" autocomplete="off"></div>'
        body += '<div><label for="family-filter">' + e(t["family"]) + '</label><select id="family-filter"><option value="">' + e(t["all_families"]) + '</option>'
        for family in sorted({m["family"] for m in data["models"]}):
            body += '<option value="' + e(family) + '">' + e(family.upper()) + '</option>'
        body += '</select></div>'
        for control, key, singular in (("driver", "driver_availability", "drivers"), ("manual", "manual_availability", "manuals")):
            body += '<div><label for="' + control + '-filter">' + e(t[key]) + '</label><select id="' + control + '-filter"><option value="">' + e(t["all_entries"]) + '</option>'
            for presence in ("with", "without"):
                body += '<option value="' + presence + '">' + e(t[presence + '_' + singular]) + '</option>'
            body += '</select></div>'
        body += '<button type="reset">' + e(t["reset"]) + '</button></form>'
        body += '<p class="result-count" aria-live="polite" aria-atomic="true">' + e(t["matching"]) + ': <span id="result-count">' + str(len(data["models"])) + '</span> / ' + str(len(data["models"])) + '</p>'
        body += '<div class="table-wrap" role="region" aria-labelledby="catalogue-heading" tabindex="0"><table class="catalogue"><thead><tr>' + ''.join('<th scope="col">' + e(t[key]) + '</th>' for key in ("model", "family", "manual_availability", "driver_availability")) + '</tr></thead><tbody id="model-rows">'
        order = {key: i for i, key in enumerate(("early", "classic", "lenovo", "modern", "unknown"))}
        for model in sorted(data["models"], key=lambda m: (order[m["era"]], m["name"].casefold(), m["id"])):
            aliases = ' / '.join(model["aliases"])
            manual_presence = 'with' if model["document_ids"] else 'without'
            driver_presence = 'with' if model["driver_ids"] else 'without'
            model_path = lang + '/models/' + model["id"] + '.html'
            body += '<tr data-search="' + e(' '.join([model["name"], model["id"], *model["aliases"]])) + '" data-family="' + e(model["family"]) + '" data-manuals="' + manual_presence + '" data-drivers="' + driver_presence + '"><th scope="row">' + self.link(current, model_path, model["name"]) + ('<span class="alias">' + e(aliases) + '</span>' if aliases else '') + '</th><td><span class="family-code">' + e(model["family"].upper()) + '</span><span class="alias">' + e(t["era_" + model["era"]]) + '</span></td>'
            for ids, label_key, presence in ((model["document_ids"], "manuals", manual_presence), (model["driver_ids"], "drivers", driver_presence)):
                section = label_key
                if label_key == "drivers" and ids and all(self.drivers[key]["risk"] == "firmware" for key in ids):
                    section = "firmware"
                body += '<td>' + (self.link(current, model_path + '#' + section, str(len(ids))) if ids else '0') + '<span class="alias">' + e(t[presence + '_' + label_key]) + '</span></td>'
            body += '</tr>'
        body += '</tbody></table></div><p id="empty-results" class="notice" hidden>' + e(t["empty_results"]) + '</p></section>'
        body += '<section aria-labelledby="manuals-heading"><div class="section-heading"><span class="section-number" aria-hidden="true">02</span><h2 id="manuals-heading">' + e(t["manuals"]) + '</h2></div><p>' + e(t["document_note"]) + '</p><div class="document-grid">'
        body += ''.join(self.document(current, lang, doc) for doc in data["documents"])
        body += '</div></section><section aria-labelledby="utilities-heading"><div class="section-heading"><span class="section-number" aria-hidden="true">03</span><h2 id="utilities-heading">' + e(t["utilities"]) + '</h2></div><p>' + e(t["utilities_note"]) + '</p><div class="utility-grid">'
        for utility in data["utilities"]:
            body += '<article class="utility"><h3>' + e(utility["title"]) + '</h3><p>' + e(t[utility["category"] + "_description"]) + '</p><p>' + self.remote(utility["url"], t["remote"]) + '</p></article>'
        return self.page(current, lang, t["catalogue"], body + '</div></section>')

    def driver_categories(self, current, lang, drivers, prefix):
        t = self.locales[lang]
        grouped = {}
        for driver in drivers:
            grouped.setdefault(category_key(driver["category"]), []).append(driver)
        navigation, sections = [], []
        for key, icon, _ in CATEGORIES:
            if key not in grouped:
                continue
            packages = sorted(grouped[key], key=lambda row: (row["title"].casefold(), row["version"] or "", row["id"]))
            target = prefix + '-cat-' + key
            label = t['category_' + key]
            content = ('<span class="category-icon" aria-hidden="true">' + e(icon) + '</span><span>' + e(label) + '</span><span class="category-count">' + str(len(packages)) + '</span>')
            navigation.append('<a href="#' + e(target) + '" data-category-target="' + e(target) + '">' + content + '</a>')
            sections.append('<details class="driver-category" id="' + e(target) + '"><summary>' + content + '</summary><div class="driver-grid">' + ''.join(self.driver(lang, row) for row in packages) + '</div></details>')
        return ('<nav class="category-nav" aria-label="' + e(t['browse_categories']) + '">' + ''.join(navigation) + '</nav><div class="category-groups">' + ''.join(sections) + '</div>')

    def thinkwiki(self, lang, model):
        t = self.locales[lang]
        references = model.get("thinkwiki", [])
        if references:
            links = ' <span aria-hidden="true">·</span> '.join(self.remote(r["url"], 'ThinkWiki: ' + r["title"]) for r in references)
            return '<p class="model-references">' + links + ' <span class="small">(' + e(t["community"]) + ')</span></p>'
        search = 'https://www.thinkwiki.org/w/index.php?' + urlencode({"search": model["name"].removeprefix('ThinkPad ')}, quote_via=quote)
        return '<p class="model-references">' + self.remote(search, t["thinkwiki_search"]) + ' <span class="small">' + e(t["thinkwiki_missing"]) + '</span></p>'

    def model(self, current, lang, model):
        t = self.locales[lang]
        items = [(t["aliases"], ' / '.join(model["aliases"]) or t["not_recorded"]), (t["era"], t["era_" + model["era"]])]
        body = '<p class="breadcrumb">' + self.link(current, lang + "/index.html", t["back_catalogue"]) + '</p><section class="model-hero"><p class="eyebrow">' + e(t["family"]) + ' ' + e(model["family"].upper()) + '</p><h1>' + e(model["name"]) + '</h1><p>' + e(t["source_listing"]) + '</p>' + self.metadata(items) + self.thinkwiki(lang, model) + '</section>'
        body += '<section id="manuals"><h2>' + e(t["manuals"]) + '</h2><p>' + e(t["document_note"]) + '</p>'
        if model["document_ids"]:
            body += '<div class="document-grid">' + ''.join(self.document(current, lang, self.docs[doc]) for doc in model["document_ids"]) + '</div>'
        else:
            body += '<p>' + e(t["no_manuals"]) + '</p>'
        linked_drivers = [self.drivers[driver_id] for driver_id in model["driver_ids"]]
        software = [driver for driver in linked_drivers if driver["risk"] == "software"]
        firmware = [driver for driver in linked_drivers if driver["risk"] == "firmware"]
        body += '</section><section id="drivers"><h2>' + e(t["drivers"]) + '</h2><p>' + e(t["driver_note"]) + '</p>'
        if software:
            body += self.driver_categories(current, lang, software, 'drivers')
        elif firmware:
            body += '<p>' + self.link(current, current + '#firmware', t["firmware"]) + '</p>'
        else:
            body += '<p>' + e(t["no_drivers"]) + '</p>'
        body += '</section><section id="firmware"><h2>' + e(t["firmware"]) + '</h2>'
        if firmware:
            body += '<aside class="firmware-warning"><h3>' + e(t["firmware_warning"]) + '</h3><p>' + e(t["firmware_warning_text"]) + '</p></aside>'
            body += self.driver_categories(current, lang, firmware, 'firmware')
        else:
            body += '<p>' + e(t["no_firmware"]) + '</p>'
        body += '</section>'
        body += '<section><h2>' + e(t["sources"]) + '</h2><ul class="source-list">'
        for source_id in model["sources"]:
            source = self.sources[source_id]
            body += '<li>' + self.remote(source["url"], source["title"]) + ' <span class="small">— ' + e(t[source["kind"]]) + '</span></li>'
        body += '</ul><p>' + (self.remote(model["matrix_url"], t["matrix"]) if model["matrix_url"] else e(t["source_unavailable"])) + '</p></section>'
        return self.page(current, lang, model["name"], body, kind="model", model_id=model["id"])

    def source_page(self, current, lang):
        t = self.locales[lang]
        scope_lang = lang if lang in self.data["scope"] else "en"
        body = '<section class="page-intro"><p class="eyebrow">' + e(t["site_name"]) + '</p><h1>' + e(t["sources"]) + '</h1><p class="lede">' + e(t["sources_intro"]) + '</p></section><section><h2>' + e(t["scope_heading"]) + '</h2><p lang="' + e(scope_lang) + '">' + e(self.data["scope"][scope_lang]) + '</p><ul class="source-list">'
        for source in self.data["sources"]:
            body += '<li>' + self.remote(source["url"], source["title"]) + '<p class="small">' + e(t["source_kind"]) + ': ' + e(t[source["kind"]]) + '</p></li>'
        body += '</ul></section><section><h2>' + e(t["safety_heading"]) + '</h2><p>' + e(t["safety_text"]) + '</p></section>'
        return self.page(current, lang, t["sources"], body, kind="sources")

    def render(self, default_language):
        result = {"index.html": self.home("index.html", default_language)}
        for lang in self.locales:
            for filename, method in (("index.html", self.home), ("sources.html", self.source_page)):
                current = lang + "/" + filename
                result[current] = method(current, lang)
            for model in self.data["models"]:
                current = lang + "/models/" + model["id"] + ".html"
                result[current] = self.model(current, lang, model)
        return result
