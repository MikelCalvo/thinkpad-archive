"""Static, offline-readable ThinkPad catalogue builder (Python stdlib only)."""
from __future__ import annotations

from pathlib import Path

from .render import Renderer
from .validation import LANG, load_catalogue, load_locales, no_symlinks, read_bytes, require

ROOT = Path(__file__).resolve().parents[1]


def build_site(output, *, data_dir=None, locales_dir=None, default_language=None):
    """Validate public metadata, locales and assets, then create a fresh output.

    English is the default. Returns the output Path. No network, manufacturer
    originals, archived software or devices are consumed by this builder.
    """
    try:
        destination = no_symlinks(output)
        require(not destination.exists(), "Output must be a new directory")
        source_data = no_symlinks(data_dir if data_dir is not None else ROOT / "data")
        source_locales = no_symlinks(locales_dir if locales_dir is not None else ROOT / "locales")
        # An output inside source inputs makes later builds self-consuming.
        require(not any(destination == p or destination.is_relative_to(p) for p in (source_data, source_locales, ROOT / "assets", ROOT / "thinkpad_archive")), "Output cannot be inside source input directories")
        require(destination.parent.is_dir(), "Output parent directory must exist")
        data = load_catalogue(source_data)
        locales = load_locales(source_locales)
        language = default_language if default_language is not None else "en"
        require(type(language) is str and LANG.fullmatch(language) is not None and language in locales, "Unknown default language")
        pages = Renderer(data, locales).render(language)
        assets = {"assets/" + name: read_bytes(ROOT / "assets" / name) for name in ("style.css", "search.js", "ui.js", "theme.js")}
        payload = {name: text.encode("utf-8") for name, text in pages.items()}
        payload.update(assets)
        try:
            destination.mkdir(mode=0o755)
        except FileExistsError:
            raise ValueError("Output must be a new directory") from None
        for member, body in payload.items():
            target = destination / member
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(body)
        return destination
    except OSError:
        # Paths in exceptions are private input, not CLI diagnostics.
        raise ValueError("Build could not read input or write the new output") from None
