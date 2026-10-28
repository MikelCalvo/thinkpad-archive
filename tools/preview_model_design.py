"""Build model dossiers, optionally with an alternate validated profile file.

Run from the repository root:
    python3 tools/preview_model_design.py --output build/model-preview
The output parent must exist and the destination must be new.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thinkpad_archive import build_site
from thinkpad_archive.model_design import ModelDesignRenderer
from thinkpad_archive.profiles import load_profiles
from thinkpad_archive.validation import load_catalogue, load_locales


def build_preview(output, *, profiles_path=None):
    data, locales = load_catalogue(ROOT/'data'), load_locales(ROOT/'locales')
    candidate = profiles_path if profiles_path is not None else ROOT/'data/profiles.json'
    profiles = load_profiles(candidate, {m['id'] for m in data['models']}) if profiles_path is not None or candidate.exists() else None
    destination = build_site(output)
    renderer = ModelDesignRenderer(data, locales, profiles=profiles)
    generated = []
    for lang in locales:
        for model in data['models']:
            current = lang+'/models/'+model['id']+'.html'
            (destination/current).write_text(renderer.model(current, lang, model), encoding='utf-8')
            generated.append(current)
    assert len(generated) == len(set(generated)) == len(data['models'])*len(locales)
    css = destination/'assets/style.css'
    detail_css = (ROOT/'assets/model-design.css').read_bytes()
    if not css.read_bytes().endswith(detail_css):
        css.write_bytes(css.read_bytes()+b'\n'+detail_css)
    return destination, generated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--profiles', type=Path, help='Validated factual-profile JSON; defaults to data/profiles.json when present')
    args = parser.parse_args()
    output, generated = build_preview(args.output, profiles_path=args.profiles)
    print(json.dumps({'preview':str(output),'model_pages':len(generated),'models':len(generated)//2,
                      'style_sha256':hashlib.sha256((output/'assets/style.css').read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
