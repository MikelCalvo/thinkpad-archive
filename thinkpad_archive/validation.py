"""Strict public metadata and locale validation, with no network access."""
from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

ID = re.compile(r"[a-z0-9][a-z0-9-]*\Z", re.ASCII)
LANG = re.compile(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})*\Z", re.ASCII)
LOCALE_KEYS = frozenset("language_name site_name catalogue sources skip language browse_categories category_audio category_graphics category_network category_bluetooth category_chipset category_power category_input category_storage category_optical category_usb category_security category_camera category_expansion category_updates category_utilities category_recovery category_diagnostics category_bios category_other scope_heading model_count driver_count manual_count browse_heading search search_hint family all_families all_entries driver_availability manual_availability with_drivers without_drivers with_manuals without_manuals model aliases era source_listing source_unavailable matching reset empty_results manuals no_manuals official community remote metadata_only document_note digest bytes not_recorded model_hint utilities utilities_note diagnostic_description reference_description sources_intro safety_heading safety_text source_kind matrix back_catalogue footer legacy_note era_early era_classic era_lenovo era_modern era_unknown drivers no_drivers firmware no_firmware firmware_warning firmware_warning_text category version operating_systems released download readme reference source_url evidence manufacturer_listing readme_model_list availability_note driver_note missing_download missing_readme no_package_links source_digest".split())
MAX_INPUT = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def no_symlinks(path):
    """Reject symlinks at any input/output path component."""
    path = Path(os.path.abspath(path))
    require(not any(part.is_symlink() for part in (path, *path.parents)), "Symlink paths are not allowed")
    return path


def read_bytes(path, limit=MAX_INPUT):
    path = no_symlinks(path)
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            require(stat.S_ISREG(info.st_mode), "Input must be a regular file")
            require(info.st_size <= limit, "Input exceeds size limit")
            body = stream.read(limit + 1)
            require(len(body) <= limit, "Input exceeds size limit")
            return body
    except OSError:
        raise ValueError("Input file cannot be read") from None


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON keys are not allowed")
        result[key] = value
    return result


def load_json(path):
    try:
        return json.loads(read_bytes(path).decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid JSON number")))
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("Input must be valid UTF-8 JSON") from None


def fields(record, keys):
    require(type(record) is dict and set(record) == set(keys.split()), "Unexpected or missing metadata fields")


def text(value, *, empty=False):
    require(type(value) is str and (empty or bool(value.strip())), "Expected text")
    require(len(value) <= 20000 and all(ord(c) >= 32 and ord(c) != 127 for c in value), "Invalid text characters")
    require(not re.search(r"(?:file:/{1,3}|/(?:home|Users|root|mnt|media|run/user|tmp|var/tmp)/|(?<![A-Za-z])[A-Za-z]:[\\/])", value, re.I), "Host paths are not metadata")
    return value


def identifier(value):
    require(type(value) is str and ID.fullmatch(value) is not None and len(value) <= 128, "Invalid identifier")
    return value


def url(value):
    text(value)
    require(not any(c.isspace() for c in value) and "\\" not in value, "Invalid source URL")
    require(re.search(r"%(?![0-9a-f]{2})", value, re.I) is None, "Malformed URL escape")
    require(not re.search(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", value, re.I), "Invalid encoded URL control")
    try:
        parts = urlsplit(value)
        require(parts.scheme == "https" and bool(parts.hostname) and parts.username is None and parts.password is None, "Source URLs must use HTTPS without userinfo")
        require(parts.port is None or 1 <= parts.port <= 65535, "Invalid URL port")
        host = parts.hostname
        if ":" in host:
            ipaddress.IPv6Address(host)
        else:
            require(re.fullmatch(r"[A-Za-z0-9.-]+", host) is not None, "Invalid URL host")
            require(not host.startswith(".") and ".." not in host, "Invalid URL host")
        require("%" not in parts.netloc, "Invalid URL host")
    except ValueError:
        raise ValueError("Invalid source URL") from None
    return value


def string_list(value, validator=text):
    require(type(value) is list, "Expected a list")
    for item in value:
        validator(item)
    require(len(value) == len(set(value)), "Repeated list values")


def records(payload, name):
    fields(payload, "schema_version " + name + (" scope sources" if name == "models" else ""))
    require(type(payload["schema_version"]) is int and payload["schema_version"] == 2, "Unsupported schema version")
    require(type(payload[name]) is list, "Expected metadata list")
    return payload[name]


def unique(items):
    require(len(items) == len({item["id"] for item in items}), "Repeated metadata identifiers")


def digest(value):
    require(value is None or (type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None), "Invalid source digest")


def localized_text(value):
    require(type(value) is dict and {"en", "es"} <= set(value), "Localized text needs English and Spanish")
    for code, body in value.items():
        require(type(code) is str and LANG.fullmatch(code) is not None, "Invalid text language")
        text(body)


def load_catalogue(directory):
    directory = Path(directory)
    data = {name: load_json(directory / (name + ".json")) for name in ("models", "documents", "utilities", "drivers")}
    models, docs, utilities, drivers = (records(data[name], name) for name in ("models", "documents", "utilities", "drivers"))
    localized_text(data["models"]["scope"])
    sources = data["models"]["sources"]
    require(type(sources) is list and sources, "Sources are required")
    for source in sources:
        fields(source, "id title url kind")
        identifier(source["id"])
        text(source["title"])
        url(source["url"])
        require(source["kind"] in ("official", "community"), "Invalid source kind")
    for doc in docs:
        fields(doc, "id title url source_kind sha256 bytes model_hint")
        identifier(doc["id"])
        text(doc["title"])
        url(doc["url"])
        text(doc["model_hint"], empty=True)
        require(doc["source_kind"] in ("official", "community"), "Invalid document source kind")
        digest(doc["sha256"])
        require(doc["bytes"] is None or (type(doc["bytes"]) is int and doc["bytes"] >= 0), "Invalid document size")
    for utility in utilities:
        fields(utility, "id title url category")
        identifier(utility["id"])
        text(utility["title"])
        url(utility["url"])
        require(utility["category"] in ("diagnostic", "reference"), "Invalid utility category")
    for driver in drivers:
        fields(driver, "id title category version operating_systems released links source_url evidence risk source_sha256")
        identifier(driver["id"])
        text(driver["title"])
        text(driver["category"])
        for key in ("version", "released"):
            if driver[key] is not None:
                text(driver[key])
        string_list(driver["operating_systems"])
        require(type(driver["links"]) is list, "Expected package links")
        for link in driver["links"]:
            fields(link, "url kind")
            url(link["url"])
            require(link["kind"] in ("download", "readme", "reference"), "Invalid package link kind")
        require(len(driver["links"]) == len({(link["url"], link["kind"]) for link in driver["links"]}), "Repeated package links")
        url(driver["source_url"])
        require(driver["evidence"] in ("manufacturer_listing", "readme_model_list"), "Invalid evidence level")
        require(driver["risk"] in ("firmware", "software"), "Invalid package risk")
        digest(driver["source_sha256"])
    source_ids, doc_ids, driver_ids = ({item["id"] for item in rows} for rows in (sources, docs, drivers))
    for model in models:
        fields(model, "id name aliases family era sources matrix_url document_ids driver_ids")
        identifier(model["id"])
        identifier(model["family"])
        text(model["name"])
        string_list(model["aliases"])
        require(model["era"] in ("early", "classic", "lenovo", "modern", "unknown"), "Invalid era")
        string_list(model["sources"], identifier)
        string_list(model["document_ids"], identifier)
        string_list(model["driver_ids"], identifier)
        require(bool(model["sources"]) and set(model["sources"]) <= source_ids, "Unknown source reference")
        require(set(model["document_ids"]) <= doc_ids, "Unknown document reference")
        require(set(model["driver_ids"]) <= driver_ids, "Unknown driver reference")
        if model["matrix_url"] is not None:
            url(model["matrix_url"])
    for items in (sources, models, docs, utilities, drivers):
        unique(items)
    return {"models": models, "documents": docs, "utilities": utilities, "drivers": drivers, "sources": sources, "scope": data["models"]["scope"]}


def load_locales(directory):
    directory = no_symlinks(directory)
    require(directory.is_dir(), "Locales directory is missing")
    result = {}
    for path in sorted(directory.glob("*.json")):
        code = path.stem
        require(LANG.fullmatch(code) is not None, "Invalid locale filename")
        payload = load_json(path)
        require(type(payload) is dict and set(payload) == LOCALE_KEYS, "Translation keyset mismatch")
        for value in payload.values():
            text(value)
        result[code] = payload
    require({"en", "es"} <= set(result), "English and Spanish translations are required")
    return result
