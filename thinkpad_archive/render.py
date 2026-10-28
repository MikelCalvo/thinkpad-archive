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
        return '<a href="' + e(url) + '" target="_blank" rel="noopener noreferrer">' + e(label) + '</a>'

    @staticmethod
    def metadata(items):
        return '<dl class="metadata">' + ''.join('<div><dt>' + e(key) + '</dt><dd>' + e(value) + '</dd></div>' for key, value in items) + '</dl>'

    def page(self, current, lang, title, body, kind="home", model_id=None, selection=None):
        t = self.locales[lang]
        nav = []
        for key, filename in (("catalogue", "index.html"), ("sources", "sources.html")):
            active = {"aria-current": "page"} if key == {"home": "catalogue", "year": "catalogue", "all": "catalogue", "sources": "sources"}.get(kind) else {}
            nav.append(self.link(current, lang + "/" + filename, t[key], **active))
        languages, alternates = [], []
        for code, translation in self.locales.items():
            target = self.year_target(code, selection) if kind in ("year", "all") else code + ("/models/" + model_id + ".html" if model_id else "/" + ("sources.html" if kind == "sources" else "index.html"))
            year_attrs = {'data-year-url':self.href(current, code + '/years/__year__.html'), 'data-all-url':self.href(current, code + '/catalogue.html')} if kind in ('home', 'year', 'all') else {}
            languages.append(self.link(current, target, translation["language_name"], hreflang=code, lang=code, **{'data-language-choice': code}, **year_attrs, **({"aria-current": "true"} if code == lang else {})))
            alternates.append('<link rel="alternate" hreflang="' + e(code) + '" href="' + e(self.href(current, target)) + '">\n')
        language_picker = ('<details id="language-picker" class="language-picker"><summary class="icon-control" aria-label="' + e(t['choose_language']) + '" title="' + e(t['choose_language']) + '">'
                           '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c-5 5-5 13 0 18M12 3c5 5 5 13 0 18"/></svg>'
                           '<span class="language-code" aria-hidden="true">' + e(lang.upper()) + '</span></summary>'
                           '<nav class="language-nav" aria-label="' + e(t['language']) + '">' + ''.join(languages) + '</nav></details>')
        home = '' if kind == 'home' else ('<a class="home-link" href="' + e(self.href(current, lang + '/index.html')) + '" aria-label="' + e(t['home_link']) + '" title="' + e(t['home_link']) + '">'
                    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 10.5 12 3l9 7.5M5.5 9v11h5v-6h3v6h5V9"/></svg></a>')
        css = self.href(current, "assets/style.css")
        script = self.href(current, "assets/search.js")
        tools = ('<div class="header-tools">' + language_picker +
                 '<button id="theme-toggle" class="icon-control" type="button" hidden aria-label="' + e(t["theme_dark"]) + '" data-light-label="' + e(t["theme_light"]) + '" data-dark-label="' + e(t["theme_dark"]) + '">'
                 '<svg class="theme-moon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20.5 13.2A8.5 8.5 0 0 1 10.8 3.5a8.5 8.5 0 1 0 9.7 9.7Z"/></svg>'
                 '<svg class="theme-sun" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg></button>'
                 '<a class="github-link icon-control" href="https://github.com/MikelCalvo/thinkpad-archive" target="_blank" rel="noopener noreferrer" aria-label="' + e(t["github_repository"]) + '" title="' + e(t["github_repository"]) + '">'
                 # Simple Icons GitHub path (CC0); attribution in sources-and-rights.md.
                 '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg></a></div>')
        return ('<!DOCTYPE html>\n<html lang="' + e(lang) + '"' + (' data-language-entry="true"' if current == 'index.html' else '') + '>\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;; style-src &#39;self&#39;; img-src &#39;self&#39;; script-src &#39;self&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;">\n'
                '<meta name="referrer" content="no-referrer">\n<title>' + e(title + " · " + t["site_name"]) + '</title>\n'
                + ''.join(alternates) + '<script src="' + e(self.href(current, "assets/language.js")) + '"></script>\n'
                '<script src="' + e(self.href(current, "assets/theme.js")) + '"></script>\n'
                '<link rel="icon" type="image/svg+xml" href="' + e(self.href(current, 'favicon.svg')) + '">\n'
                '<link rel="stylesheet" href="' + e(css) + '">\n'
                + '<script src="' + e(self.href(current, "assets/ui.js")) + '" defer></script>\n'
                + ('<script src="' + e(script) + '" defer></script>\n' if kind in ("home", "year", "all") else '') + '</head>\n<body>\n'
                '<a class="skip-link" href="#main">' + e(t["skip"]) + '</a>\n'
                '<header class="site-header"><div class="topbar">'
                '<nav class="main-nav" aria-label="' + e(t["site_name"]) + '">' + home + ''.join(nav) + '</nav>' + tools + '</div></header>\n'
                '<main id="main">' + body + '</main>\n<footer><p>' + e(t["footer"]) + '</p><p>' + e(t["created_by"]) + ' ' + self.remote('https://mikelcalvo.net/', 'Mikel Calvo') + '</p></footer>\n</body>\n</html>\n')

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

    @staticmethod
    def model_years(model):
        return sorted({r["year"] for r in model.get("introduced", [])})

    @classmethod
    def has_unknown_year(cls, model):
        return not cls.model_years(model) or bool(model.get("introduced_unknown"))

    def calendar_years(self):
        known = [year for model in self.data["models"] for year in self.model_years(model)]
        return list(range(min(known), max(known) + 1)) if known else []

    def year_target(self, lang, year):
        if year == "all":
            return lang + '/catalogue.html'
        return lang + '/years/' + str(year) + '.html'

    def timeline(self, current, lang, selected):
        t = self.locales[lang]
        years = self.calendar_years()
        counts = {year: sum(year in self.model_years(model) for model in self.data["models"]) for year in years}
        controls = '<nav class="timeline-track" aria-label="' + e(t["timeline"]) + '">'
        for year in ["all"] + years:
            label = t['all_years'] if year == 'all' else str(year)
            count = len(self.data['models']) if year == 'all' else counts[year]
            attributes = {'data-year':year, 'aria-current':'true' if str(year) == str(selected) else 'false'}
            controls += '<a href="' + e(self.href(current, self.year_target(lang, year))) + '"' + ''.join(' ' + key + '="' + e(value) + '"' for key, value in attributes.items()) + '>' + e(label) + '<span class="year-count">' + str(count) + '</span></a>'
        controls += '</nav>'
        if years:
            value = selected if type(selected) is int else years[0] - 1
            controls += '<input id="year-slider" type="range" min="' + str(years[0] - 1) + '" max="' + str(years[-1]) + '" step="1" value="' + str(value) + '" aria-label="' + e(t['choose_year']) + '" hidden>'
        label = t['unknown_year'] if selected == 'unknown' else t['all_years'] if selected == 'all' else t['introduced_in'] + ' ' + str(selected)
        return '<div id="timeline" class="timeline" data-selected-year="' + e(selected) + '" data-default-year="' + e('all') + '" data-all-value="' + e(years[0] - 1 if years else '') + '" data-all-label="' + e(t['all_years']) + '" data-unknown-label="' + e(t['unknown_year']) + '" data-year-label="' + e(t['introduced_in']) + '">' + controls + '<h2 id="selected-year" class="visually-hidden">' + e(label) + '</h2></div>'

    def home(self, current, lang, selection=None):
        t, data = self.locales[lang], self.data
        years = self.calendar_years()
        selected = selection if selection is not None else 'all'
        def selected_model(model):
            return selected == 'all' or (selected == 'unknown' and self.has_unknown_year(model)) or (type(selected) is int and selected in self.model_years(model))
        selected_count = sum(selected_model(model) for model in data['models'])
        body = '<section class="hero"><h1 class="archive-title" aria-label="ThinkPad Archive"><span class="title-word" aria-hidden="true">Th<span class="title-i">i</span>nkPad</span> <span class="archive-word" aria-hidden="true">Archive</span></h1></section>'
        body += '<section aria-label="' + e(t['catalogue']) + '">'
        body += self.timeline(current, lang, selected)
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
        body += '<div class="table-wrap" role="region" aria-labelledby="selected-year" tabindex="0"><table class="catalogue"><thead><tr>' + ''.join('<th scope="col">' + e(t[key]) + '</th>' for key in ("model", "family", "manual_availability", "driver_availability")) + '</tr></thead><tbody id="model-rows">'
        order = {key: i for i, key in enumerate(("early", "classic", "lenovo", "modern", "unknown"))}
        for model in sorted(data["models"], key=lambda m: (order[m["era"]], m["name"].casefold(), m["id"])):
            aliases = ' / '.join(model["aliases"])
            manual_presence = 'with' if model["document_ids"] else 'without'
            driver_presence = 'with' if model["driver_ids"] else 'without'
            model_path = lang + '/models/' + model["id"] + '.html'
            row_years = ' '.join(str(year) for year in self.model_years(model))
            visibility = '' if selected_model(model) else ' hidden'
            body += '<tr data-model-id="' + e(model['id']) + '" data-years="' + e(row_years) + '" data-unknown-year="' + str(self.has_unknown_year(model)).lower() + '"' + visibility + ' data-search="' + e(' '.join([model["name"], model["id"], *model["aliases"]])) + '" data-family="' + e(model["family"]) + '" data-manuals="' + manual_presence + '" data-drivers="' + driver_presence + '"><th scope="row">' + self.link(current, model_path, model["name"]) + ('<span class="alias">' + e(aliases) + '</span>' if aliases else '') + '</th><td><span class="family-code">' + e(model["family"].upper()) + '</span><span class="alias">' + e(t["era_" + model["era"]]) + '</span></td>'
            for ids, label_key in ((model["document_ids"], "manuals"), (model["driver_ids"], "drivers")):
                section = label_key
                if label_key == "drivers" and ids and all(self.drivers[key]["risk"] == "firmware" for key in ids):
                    section = "firmware"
                body += '<td>' + (self.link(current, model_path + '#' + section, str(len(ids))) if ids else '0') + '</td>'
            body += '</tr>'
        body += '</tbody></table></div><p id="empty-results" class="notice" aria-live="polite"' + (' hidden' if selected_count else '') + '>' + e(t["empty_results"]) + '</p></section>'
        kind = 'all' if selection == 'all' else 'year' if selection is not None else 'home'
        return self.page(current, lang, t["catalogue"], body, kind=kind, selection=selected)

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
        body = '<section class="model-hero"><p class="eyebrow">' + e(t["family"]) + ' ' + e(model["family"].upper()) + '</p><h1>' + e(model["name"]) + '</h1><p>' + e(t["source_listing"]) + '</p>' + self.metadata(items) + self.thinkwiki(lang, model) + '</section>'
        introductions = model.get('introduced', [])
        if introductions:
            dates = ' <span aria-hidden="true">·</span> '.join(self.remote(row['url'], str(row['year']) + ' · ' + ', '.join(row['variants'])) for row in introductions)
            label = t['documented_years'] if any('evidence' in row for row in introductions) else t['introduced_in']
            body += '<p class="introduction-references"><span class="small">' + e(label) + ': </span>' + dates + '</p>'
            for row in introductions:
                if 'evidence' in row:
                    evidence = row['evidence']
                    note = evidence['note'].get(lang, evidence['note']['en'])
                    body += '<p class="date-evidence small"><strong>' + e(str(row['year']) + ' · ' + t['evidence_' + evidence['kind']]) + ': </strong>' + e(note) + '</p>'
        else:
            body += '<p class="small">' + e(t['unknown_year']) + '</p>'
        unknown_variants = model.get('introduced_unknown', [])
        if unknown_variants:
            body += '<p class="small">' + e(t['unknown_year']) + ': ' + e(', '.join(unknown_variants)) + '</p>'
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
        body = ('<div class="sources-page"><section class="sources-intro"><h1>' + e(t['sources']) + '</h1>'
                '<p class="lede">' + e(t['sources_intro']) + '</p></section>')
        # Curated entry points use recorded identities, never guessed source URLs.
        families = (
            ('manufacturer', 'IBM / Lenovo', 'sources_docs_text', 'official',
             'M5 3h10l4 4v14H5ZM14 3v5h5M8 12h8M8 16h6',
             (('lenovo-eol-manuals', 'sources_manual_link'), ('lenovo-eol-selector', 'sources_software_link'))),
            ('specifications', 'PSREF', 'sources_specs_text', 'official',
             'M4 5h16v14H4ZM4 10h16M10 10v9',
             (('lenovo-psref', 'sources_psref_link'), ('psref-twbook', 'sources_books_link'))),
            ('community', 'ThinkWiki', 'sources_wiki_text', 'community',
             'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM3 12h18M12 3c-5 5-5 13 0 18M12 3c5 5 5 13 0 18',
             (('thinkwiki-history', 'sources_wiki_link'),)),
        )
        cards = []
        for key, title, description, kind, icon, entries in families:
            links = [self.remote(self.sources[source_id]['url'], t[label]) for source_id, label in entries
                     if source_id in self.sources and self.sources[source_id]['kind'] == kind]
            if links:
                cards.append('<article class="source-family" data-source-family="' + e(key) + '">'
                             '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="' + e(icon) + '"/></svg>'
                             '<h3>' + e(title) + '</h3><p>' + e(t[description]) + '</p>'
                             '<div class="source-entry-links">' + ''.join(links) + '</div></article>')
        if cards:
            body += ('<section aria-labelledby="sources-primary"><h2 id="sources-primary">' + e(t['sources_primary']) + '</h2>'
                     '<div class="source-families">' + ''.join(cards) + '</div></section>')
        body += ('<section aria-labelledby="sources-evidence"><h2 id="sources-evidence">' + e(t['sources_evidence_heading']) + '</h2>'
                 '<dl class="source-evidence">')
        for key in ('listing', 'readme', 'compatibility'):
            body += '<div><dt>' + e(t['sources_' + key]) + '</dt><dd>' + e(t['sources_' + key + '_text']) + '</dd></div>'
        body += ('</dl></section><aside class="source-install" aria-labelledby="sources-install"><h2 id="sources-install">' + e(t['safety_heading']) + '</h2>'
                 '<p>' + e(t['safety_text']) + '</p><p class="source-firmware"><strong>BIOS / firmware.</strong> ' + e(t['sources_firmware_text']) + '</p></aside>'
                 '<div class="source-details"><details id="source-references"><summary>' + e(t['sources_reference_heading']) + '</summary>'
                 '<div class="source-details-body"><p class="small">' + e(t['sources_reference_intro']) + '</p><div class="source-reference-groups">')
        for kind, heading in (('official', 'sources_official_heading'), ('community', 'sources_community_heading')):
            sources = [s for s in self.data['sources'] if s['kind'] == kind]
            if sources:
                body += '<div><h3>' + e(t[heading]) + '</h3><ul class="source-reference-list">'
                for source in sources:
                    body += '<li>' + self.remote(source['url'], source['title']) + '</li>'
                body += '</ul></div>'
        body += ('</div></div></details><details id="source-methodology"><summary>' + e(t['sources_method_heading']) + '</summary>'
                 '<div class="source-details-body"><p lang="' + e(scope_lang) + '">' + e(self.data['scope'][scope_lang]) + '</p>')
        for key in ('dates', 'files', 'operations'):
            body += '<p>' + e(t['sources_method_' + key]) + '</p>'
        body += '</div></details></div></div>'
        return self.page(current, lang, t["sources"], body, kind="sources")

    def render(self, default_language):
        result = {"index.html": self.home("index.html", default_language)}
        for lang in self.locales:
            for filename, method in (("index.html", self.home), ("sources.html", self.source_page)):
                current = lang + "/" + filename
                result[current] = method(current, lang)
            current = lang + '/catalogue.html'
            result[current] = self.home(current, lang, 'all')
            for year in self.calendar_years() + ['unknown']:
                current = self.year_target(lang, year)
                result[current] = self.home(current, lang, year)
            for model in self.data["models"]:
                current = lang + "/models/" + model["id"] + ".html"
                result[current] = self.model(current, lang, model)
        return result
