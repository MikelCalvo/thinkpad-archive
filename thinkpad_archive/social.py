"""Static sharing metadata for the official ThinkPad Archive site."""
from html import escape

SITE_ORIGIN = 'https://thinkpadarchive.com'


def page_metadata(current, lang, title, kind, selection, translations):
    """One title/description/canonical source for HTML, sharing and Schema.org."""
    t = translations
    if kind == 'model':
        heading = title + ' · ' + t['site_name']
        description = t['social_model_description'].format(model=title)
    elif kind == 'sources':
        heading = t['sources'] + ' · ' + t['site_name']
        description = t['social_sources_description']
    elif kind == 'year':
        if selection == 'unknown':
            heading = t['social_unknown_title'] + ' · ' + t['site_name']
            description = t['social_unknown_description']
        else:
            heading = t['social_year_title'].format(year=selection) + ' · ' + t['site_name']
            description = t['social_year_description'].format(year=selection)
    elif kind == 'stats':
        spanish = lang == 'es'
        heading = ('Estadísticas públicas' if spanish else 'Public statistics') + ' · ' + t['site_name']
        description = ('Contadores diarios agregados de páginas de ThinkPad Archive, sin identificadores de visitantes.' if spanish else
                       'Daily aggregate page-view counters for ThinkPad Archive, without visitor identifiers.')
    else:
        heading = t['site_name'] + (' · Manuales, drivers e historia' if lang == 'es' else ' · Manuals, drivers and history')
        description = t['social_home_description']
    canonical = SITE_ORIGIN + ('/' + lang + '/' if kind in ('home', 'all') else '/' + current)
    return heading, description, canonical


def sharing_head(current, lang, title, kind, selection, translations):
    """Emit crawler-readable tags without depending on scripts or page state."""
    t = translations
    heading, description, canonical = page_metadata(current, lang, title, kind, selection, t)
    # Other installed locales receive the English artwork, not a broken image URL.
    image_language = lang if lang in ('en', 'es') else 'en'
    image = SITE_ORIGIN + '/assets/social-' + image_language + '.png'
    tags = [('name', 'description', description),
            ('property', 'og:type', 'website'),
            ('property', 'og:site_name', t['site_name']),
            ('property', 'og:title', heading),
            ('property', 'og:description', description),
            ('property', 'og:url', canonical),
            ('property', 'og:locale', t['social_locale']),
            ('property', 'og:image', image),
            ('property', 'og:image:secure_url', image),
            ('property', 'og:image:type', 'image/png'),
            ('property', 'og:image:width', '1200'),
            ('property', 'og:image:height', '630'),
            ('property', 'og:image:alt', t['social_image_alt']),
            ('name', 'twitter:card', 'summary_large_image'),
            ('name', 'twitter:title', heading),
            ('name', 'twitter:description', description),
            ('name', 'twitter:image', image),
            ('name', 'twitter:image:alt', t['social_image_alt'])]
    return ('<link rel="canonical" href="' + escape(canonical, quote=True) + '">\n' +
            ''.join('<meta ' + attribute + '="' + key + '" content="' + escape(value, quote=True) + '">\n'
                    for attribute, key, value in tags))
