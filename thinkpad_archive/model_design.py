"""Source-backed model dossiers used by the public catalogue builder."""
from .render import Renderer, e
from .design_samples import SAMPLES
from .profiles import format_date

COPY = {
    'en': {
        'overview': 'Overview', 'manuals': 'Manuals', 'drivers': 'Drivers & Software', 'firmware': 'BIOS & Firmware', 'sources': 'Sources',
        'launch': 'Launch', 'documented': 'Documented date', 'market': 'Markets & exclusivity', 'price': 'Period price',
        'pending': 'To be documented', 'market_pending': 'Regional availability not yet researched',
        'price_pending': 'Original price not yet researched', 'story_pending': 'The model’s story is still to be documented.',
        'story_pending_text': 'This space will bring together the original positioning, defining features and the context of its time. The next research pass will add model-specific, cited history.',
        'era_pending': 'Historical context', 'era_pending_text': 'Launch context, regional variants and period prices will be added after the design is approved.',
        'era': 'In its time', 'specs': 'At a glance', 'specs_pending': 'The technical profile will be completed from model-specific sources.',
        'read_source': 'Read the original reference', 'launch_sources': 'Date sources & variant notes', 'variant': 'Variant',
        'service': 'Maintenance', 'specification': 'Product reference', 'document': 'Document', 'open_manual': 'Open PDF',
        'reference_details': 'Reference details', 'size': 'File size', 'source': 'Source', 'digest': 'SHA-256',
        'packages': 'packages', 'documents': 'documents', 'date': 'Source date', 'version': 'Version', 'os': 'Operating systems',
        'download': 'Download', 'readme': 'Readme', 'reference': 'Reference', 'package_details': 'Source & package details',
        'source_listing': 'Manufacturer listing', 'evidence': 'Association', 'no_download': 'Download link not recorded',
        'no_readme': 'Readme not recorded', 'no_packages': 'No software linked to this exact entry yet.',
        'no_manuals': 'No manual linked to this exact entry yet.', 'no_firmware': 'No firmware linked to this exact entry yet.',
        'back': 'Back to catalogue', 'family': 'Series', 'related': 'Explore another model', 'catalogue': 'Full catalogue',
        'references': 'Research & references', 'aliases': 'Names & variants', 'country_note': 'A documented regional SKU does not establish country exclusivity.',
        'period': 'Catalogue era', 'pricing_note': 'Price source', 'sources_details': 'Identity, dates & original listings',
    },
    'es': {
        'overview': 'El ordenador', 'manuals': 'Manuales', 'drivers': 'Drivers y software', 'firmware': 'BIOS y firmware', 'sources': 'Fuentes',
        'launch': 'Lanzamiento', 'documented': 'Fecha documentada', 'market': 'Mercados y exclusividad', 'price': 'Precio de la época',
        'pending': 'Pendiente de documentar', 'market_pending': 'Distribución regional aún sin investigar',
        'price_pending': 'Precio original aún sin investigar', 'story_pending': 'La historia de este modelo está por documentar.',
        'story_pending_text': 'Aquí reuniremos su posicionamiento original, sus rasgos distintivos y el contexto de su época. La siguiente ronda de investigación añadirá historia específica del modelo y sus fuentes.',
        'era_pending': 'Contexto histórico', 'era_pending_text': 'El contexto del lanzamiento, las variantes regionales y los precios de la época se completarán tras aprobar el diseño.',
        'era': 'En su época', 'specs': 'De un vistazo', 'specs_pending': 'La ficha técnica se completará con fuentes específicas del modelo.',
        'read_source': 'Consultar la referencia original', 'launch_sources': 'Fuentes de fechas y notas de variantes', 'variant': 'Variante',
        'service': 'Mantenimiento', 'specification': 'Referencia de producto', 'document': 'Documento', 'open_manual': 'Abrir PDF',
        'reference_details': 'Detalles de la referencia', 'size': 'Tamaño del archivo', 'source': 'Fuente', 'digest': 'SHA-256',
        'packages': 'paquetes', 'documents': 'documentos', 'date': 'Fecha en la fuente', 'version': 'Versión', 'os': 'Sistemas operativos',
        'download': 'Descarga', 'readme': 'Readme', 'reference': 'Referencia', 'package_details': 'Fuente y detalles del paquete',
        'source_listing': 'Listado del fabricante', 'evidence': 'Asociación', 'no_download': 'Sin enlace de descarga registrado',
        'no_readme': 'Readme no registrado', 'no_packages': 'Aún no hay software enlazado a esta entrada exacta.',
        'no_manuals': 'Aún no hay manuales enlazados a esta entrada exacta.', 'no_firmware': 'Aún no hay firmware enlazado a esta entrada exacta.',
        'back': 'Volver al catálogo', 'family': 'Serie', 'related': 'Explorar otro modelo', 'catalogue': 'Catálogo completo',
        'references': 'Investigación y referencias', 'aliases': 'Nombres y variantes', 'country_note': 'Una configuración regional documentada no demuestra exclusividad de un país.',
        'period': 'Época del catálogo', 'pricing_note': 'Fuente del precio', 'sources_details': 'Identidad, fechas y listados originales',
    },
}


def badge(text, kind=''):
    return '<span class="design-tag ' + e(kind) + '">' + e(text) + '</span>'


FACT_LABELS = {
    'processor': ('Processor', 'Procesador'), 'display': ('Display', 'Pantalla'),
    'memory': ('Memory', 'Memoria'), 'storage': ('Storage', 'Almacenamiento'),
    'graphics': ('Graphics', 'Gráficos'), 'weight': ('Weight', 'Peso'),
    'dimensions': ('Dimensions', 'Dimensiones'), 'ports': ('Ports', 'Puertos'),
    'connectivity': ('Connectivity', 'Conectividad'), 'battery': ('Battery', 'Batería'),
    'operating_system': ('Original systems', 'Sistemas originales'),
    'positioning': ('Positioning', 'Posicionamiento'), 'features': ('Features', 'Características'),
}
DATE_LABELS = {
    'announcement': ('Announcement', 'Anuncio'), 'availability': ('Availability', 'Disponibilidad'),
    'sku_announcement': ('SKU announcement', 'Anuncio de configuración'),
    'documented_by': ('Documented by', 'Documentado en'),
}
PRICE_LABELS = {'launch': ('Launch price', 'Precio de lanzamiento'),
                'catalogue': ('Catalogue price', 'Precio de catálogo'),
                'contemporary_review': ('Period review price', 'Precio en análisis de la época')}

SPEC_GROUPS = (
    ('performance', ('Platform & performance', 'Plataforma y rendimiento'),
     ('Processor, memory, graphics and storage', 'Procesador, memoria, gráficos y almacenamiento'),
     ('processor', 'memory', 'graphics', 'storage')),
    ('design', ('Display & design', 'Pantalla y diseño'),
     ('Panel, dimensions and weight', 'Panel, dimensiones y peso'),
     ('display', 'dimensions', 'weight')),
    ('connections', ('Connections & power', 'Conexiones y autonomía'),
     ('Ports, networks and battery', 'Puertos, redes y batería'),
     ('ports', 'connectivity', 'battery')),
    ('equipment', ('Systems & equipment', 'Sistemas y equipamiento'),
     ('Original software and other features', 'Software original y otras características'),
     ('operating_system', 'positioning', 'features')),
)


class ModelDesignRenderer(Renderer):
    def __init__(self, data, locales, *, profiles=None):
        super().__init__(data, locales)
        self.profiles = profiles or {}

    def profile_sample(self, profile):
        # Adapt factual records to the accepted layout; no new historical inference.
        events = [row for row in profile['dates'] if row['kind'] != 'documented_by']
        priority = {'announcement':0,'sku_announcement':1,'availability':2,'documented_by':3}
        dates = sorted(events or profile['dates'], key=lambda row: (row['date'], priority[row['kind']]))
        chosen = dates[0] if dates else None
        price = profile['prices'][0] if profile['prices'] else None
        converted_price = None
        if price:
            from decimal import Decimal
            amount = format(Decimal(price['amount']), ',f').rstrip('0').rstrip('.') if '.' in price['amount'] else format(Decimal(price['amount']), ',f')
            es_amount = amount.replace(',', '_').replace('.', ',').replace('_', '.')
            converted_price = {'value': amount+' '+price['currency'], 'es_value': es_amount+' '+price['currency']}
            for code, index in (('en',0),('es',1)):
                converted_price[code] = PRICE_LABELS[price['kind']][index]+' · '+format_date(price['date'],code)+' · '+self.local(price['scope'],code)
        return {
            'maker': 'ThinkPad',
            'release': {code:format_date(chosen['date'],code) for code in ('en','es')} if chosen else None,
            'release_scope': {code:DATE_LABELS[chosen['kind']][index]+' · '+self.local(chosen['scope'],code) for code,index in (('en',0),('es',1))} if chosen else None,
            'price': converted_price,
            'story': profile['summary'], 'era_story': profile['context'],
            'era_title': {'en':'Historical perspective', 'es':'Perspectiva histórica'},
            'spec_note': {'en':'Specifications and equipment depend on the configurations described in the cited sources.', 'es':'Las características y el equipamiento dependen de las configuraciones descritas en las fuentes citadas.'},
        }

    def header_facts(self, lang, model, profile, sample):
        """A wrapping metadata line, not fixed slots for unconfirmed fields."""
        index = 1 if lang == 'es' else 0
        items = []
        selected_date = None
        def add(key, label, value):
            items.append('<div data-header-fact="'+key+'"><dt>'+e(label)+'</dt><dd>'+e(value)+'</dd></div>')
        if profile and profile['dates']:
            events = [r for r in profile['dates'] if r['kind'] != 'documented_by']
            priority = {'announcement':0,'sku_announcement':1,'availability':2,'documented_by':3}
            row = min(events or profile['dates'], key=lambda r:(r['date'],priority[r['kind']]))
            selected_date = row['date']
            add('date', DATE_LABELS[row['kind']][index], format_date(row['date'],lang))
        elif sample and sample['release']:
            add('date', self.words(lang)['documented'], self.local(sample['release'],lang))
        else:
            years = self.model_years(model)
            if years:
                add('date', self.words(lang)['documented'], ' / '.join(str(y)for y in years))
        add('series', self.words(lang)['family'], model['family'].upper())
        if profile and profile['prices']:
            row = profile['prices'][0]
            label = PRICE_LABELS[row['kind']][index]
            amount = sample['price']['es_value' if lang=='es' else 'value']
            scope = self.local(row['scope'],lang).lower()
            if (any(s in scope for s in ('desde','precio inicial','precio de partida')) if lang=='es' else any(s in scope for s in ('starting at','starting price','starts at','from '))):
                amount = ('Desde ' if lang=='es' else 'From ') + amount
            if any(s in scope for s in ('aproximado','approximate')):
                amount = '≈ ' + amount
            dated = row['kind'] != 'launch' or row['date'] != selected_date
            add('price',label,amount+(' · '+format_date(row['date'],lang) if dated else ''))
        elif profile is None and sample and sample.get('price'):
            price = sample['price']
            add('price',self.words(lang)['price'],price.get('es_value',price['value'])if lang=='es'else price['value'])
        # A source's regional SKU/listing is not evidence of exclusivity.
        exclusive = [r for r in profile['markets'] if r['exclusive'] is True] if profile else []
        if exclusive:
            import re
            scopes = ' '.join(r['scope']['en'] for r in exclusive)
            regions = [names[index] for pattern,names in (
                (r'\bJapan\b',('Japan','Japón')), (r'\bChina\b',('China','China')))
                if re.search(pattern,scopes,re.I)]
            if regions:
                value = ('Exclusivo de ' if lang=='es'else'Exclusive to ')+' / '.join(regions)
                # Prefer idiomatic English for the known single-market case.
                if lang=='en' and len(regions)==1:value=regions[0]+' exclusive'
            else:
                value = 'Exclusividad regional documentada' if lang=='es'else'Documented regional exclusivity'
            add('market','Mercado'if lang=='es'else'Market',value)
        return '<dl class="model-meta">'+''.join(items)+'</dl>'

    def specifications(self, lang, profile, sample):
        index = 1 if lang == 'es' else 0
        if profile is not None:
            rows = {f['key']:self.local(f['value'],lang)for f in profile['facts']}
        elif sample:
            labels = {names[0]:key for key,names in FACT_LABELS.items()}
            rows = {labels[en]:(detail if en=='Weight'and lang=='es'else value+(' · '+detail if detail and en!='Weight'else''))
                    for en,es,value,detail in sample['specs'] if en in labels}
        else:
            rows = {}
        if not rows:return ''
        title = 'Especificaciones' if lang=='es'else'Specifications'
        body = '<section id="specifications" class="model-specifications" aria-label="'+title+'"><div class="section-heading"><h2>'+title+'</h2></div><div class="spec-groups">'
        for key,names,descriptions,keys in SPEC_GROUPS:
            selected = [k for k in keys if k in rows]
            if not selected:continue
            body += '<details class="spec-group" id="spec-'+key+'"><summary><span class="spec-group-title">'+e(names[index])+'</span><span class="spec-group-hint">'+e(descriptions[index])+'</span><span class="spec-group-count">'+str(len(selected))+'</span></summary><dl class="key-specs">'
            for fact_key in selected:
                body += '<div data-fact-key="'+fact_key+'"><dt>'+e(FACT_LABELS[fact_key][index])+'</dt><dd>'+e(rows[fact_key])+'</dd></div>'
            body += '</dl></details>'
        return body+'</div></section>'

    def profile_references(self, lang, profile):
        index = 1 if lang == 'es' else 0
        rows = []
        refs = {r['id']:r for r in profile['references']}
        label = 'Fuentes de la ficha' if lang == 'es' else 'Profile sources'
        for collection in ('facts','dates','prices','markets'):
            for row in profile[collection]:
                if collection == 'facts':
                    heading = FACT_LABELS[row['key']][index] + ': ' + self.local(row['value'],lang)
                elif collection == 'dates':
                    heading = DATE_LABELS[row['kind']][index] + ': ' + format_date(row['date'],lang)
                elif collection == 'prices':
                    heading = PRICE_LABELS[row['kind']][index] + ': ' + row['amount'] + ' ' + row['currency']
                else:
                    heading = 'Distribución' if lang == 'es' else 'Markets'
                links = ' · '.join(self.remote(refs[key]['url'],refs[key]['title']+' · '+refs[key]['locator']) for key in row['sources'])
                rows.append('<li><strong>'+e(heading)+'</strong><p>'+e(self.local(row['scope'],lang))+'</p>'+links+'</li>')
        used = {key for collection in ('facts','dates','prices','markets') for row in profile[collection] for key in row['sources']}
        rows.extend('<li>'+self.remote(r['url'],r['title']+' · '+r['locator'])+'</li>'
                    for r in profile['references'] if r['id'] not in used)
        return ('<details class="reference-details profile-sources"><summary>'+label+'</summary><ul class="source-list">'+''.join(rows)+'</ul></details>') if rows else ''

    def words(self, lang):
        return COPY.get(lang, COPY['en'])

    @staticmethod
    def local(value, lang):
        return value.get(lang, value['en'])

    def compact_document(self, lang, doc):
        t, words = self.locales[lang], self.words(lang)
        title = doc['title']
        service = 'maintenance' in title.lower()
        specification = 'reference' in title.lower() or 'specifications' in title.lower()
        kind = words['service'] if service else words['specification'] if specification else words['document']
        display = title
        for prefix in ('ThinkPad ', 'IBM Personal Systems Reference: ', 'IBM Mobile Systems '):
            if display.startswith(prefix):
                display = display[len(prefix):]
                break
        symbol = '<svg viewBox="0 0 32 36" aria-hidden="true"><path d="M6 2h13l7 7v25H6zM19 2v8h7M11 17h10M11 22h10M11 27h7"/></svg>'
        details = self.metadata([(words['source'], t[doc['source_kind']]), (t['model_hint'], doc['model_hint'] or t['not_recorded']),
                                 (words['size'], self.file_size(doc['bytes']) if doc['bytes'] else t['not_recorded'])])
        details += '<p class="reference-hash"><span>' + e(words['digest']) + '</span><code>' + e(doc['sha256'] or t['not_recorded']) + '</code></p>'
        return ('<article class="manual-card"><div class="manual-icon">' + symbol + '</div><div class="manual-body">'
                + '<div class="card-tags">' + badge(kind, 'red' if service else '') + badge('PDF') + '</div><h3>' + e(display) + '</h3>'
                + '<p class="manual-origin">' + e(t[doc['source_kind']]) + (' · ' + e(self.file_size(doc['bytes'])) if doc['bytes'] else '') + '</p>'
                + '<a class="document-action" href="' + e(doc['url']) + '" target="_blank" rel="noopener noreferrer">' + e(words['open_manual']) + ' <span aria-hidden="true">↗</span></a>'
                + '<details class="reference-details"><summary>' + e(words['reference_details']) + '</summary>' + details + '</details></div></article>')

    @staticmethod
    def file_size(size):
        return ('%.1f MB' % (size / 1000000)) if size >= 1000000 else ('%.0f KB' % (size / 1000))

    def driver(self, lang, driver):
        t, words = self.locales[lang], self.words(lang)
        actions = []
        for link in driver['links']:
            actions.append('<a class="package-action ' + ('download-action' if link['kind'] == 'download' else '') + '" href="' + e(link['url']) + '" target="_blank" rel="noopener noreferrer">' + e(words.get(link['kind'], t[link['kind']])) + (' <span aria-hidden="true">↓</span>' if link['kind'] == 'download' else '') + '</a>')
        information = [(words['version'], driver['version'] or t['not_recorded']),
                       (words['os'], ' / '.join(driver['operating_systems']) or t['not_recorded']),
                       (words['date'], driver['released'] or t['not_recorded'])]
        meta = self.metadata(information)
        source = '<p>' + self.remote(driver['source_url'], words['source_listing']) + '</p>'
        source += self.metadata([(words['evidence'], t[driver['evidence']]), (t['category'], driver['category'])])
        source += '<code>' + e(driver['source_sha256'] or t['not_recorded']) + '</code>'
        kinds = {link['kind'] for link in driver['links']}
        missing = ''.join('<span class="missing-link">' + e(words[key]) + '</span>' for kind,key in [('download','no_download'),('readme','no_readme')] if kind not in kinds)
        return ('<article class="package-row" data-package-id="' + e(driver['id']) + '"><div class="package-main"><h3>' + e(driver['title']) + '</h3>' + meta
                + '<details class="reference-details package-reference"><summary>' + e(words['package_details']) + '</summary>' + source + '</details>'
                + missing + '</div><div class="package-actions">' + ''.join(actions) + '</div></article>')

    def driver_categories(self, current, lang, drivers, prefix):
        # Retain the native category lists without repeating them as shortcuts.
        markup = super().driver_categories(current, lang, drivers, prefix)
        return '<div class="category-groups">' + markup.partition('<div class="category-groups">')[2]

    def dates(self, lang, model):
        t, words = self.locales[lang], self.words(lang)
        dates = model.get('introduced', [])
        if not dates and not model.get('introduced_unknown'):
            return ''
        body = '<details class="launch-details"><summary>' + e(words['launch_sources']) + '</summary>'
        for row in dates:
            body += '<div class="launch-record">' + self.remote(row['url'], str(row['year']) + ' · ' + ', '.join(row['variants']))
            if 'evidence' in row:
                evidence = row['evidence']
                body += '<p class="date-evidence"><strong>' + e(t['evidence_' + evidence['kind']]) + '</strong> · ' + e(self.local(evidence['note'], lang)) + '</p>'
            body += '</div>'
        if model.get('introduced_unknown'):
            body += '<p>' + e(t['unknown_year']) + ': ' + e(', '.join(model['introduced_unknown'])) + '</p>'
        return body + '</details>'

    def model(self, current, lang, model):
        t, w = self.locales[lang], dict(self.words(lang))
        profile = self.profiles.get(model['id'])
        if profile is not None:
            if lang == 'es':
                w.update(market_pending='No se ha confirmado una fuente suficiente sobre la distribución regional.',
                         price_pending='No se ha confirmado una fuente suficiente para el precio original.',
                         story_pending_text='No se ha confirmado una fuente suficiente para redactar una descripción histórica de esta identidad exacta.',
                         era_pending_text='No se ha confirmado una fuente suficiente sobre su contexto histórico.',
                         specs_pending='No se ha confirmado una fuente suficiente para ampliar la ficha técnica.')
            else:
                w.update(market_pending='No source confirmed with sufficient evidence for regional distribution.',
                         price_pending='No source confirmed with sufficient evidence for the original price.',
                         story_pending_text='No source confirmed with sufficient evidence for the historical description of this exact identity.',
                         era_pending_text='No source confirmed with sufficient evidence for its historical context.',
                         specs_pending='No source confirmed with sufficient evidence to expand the technical profile.')
        sample = self.profile_sample(profile) if profile else SAMPLES.get(model['id'])
        software = [self.drivers[key] for key in model['driver_ids'] if self.drivers[key]['risk'] == 'software']
        firmware = [self.drivers[key] for key in model['driver_ids'] if self.drivers[key]['risk'] == 'firmware']
        name = model['name']
        if name.startswith('ThinkPad '):
            title = '<span class="brand-word">Th<span class="title-i">i</span>nkPad</span> ' + e(name[len('ThinkPad '):])
        else:
            title = e(name)
        body = '<div class="model-design">'
        body += '<header class="dossier-hero"><h1>' + title + '</h1></header>'
        body += '<section id="overview" class="model-overview" aria-label="' + e(w['overview']) + '">'
        body += self.header_facts(lang, model, profile, sample)
        body += '<div class="model-story"><h2 class="visually-hidden">' + e(w['overview']) + '</h2><p class="model-lead">' + e(self.local(sample['story'],lang) if sample and sample['story'] else w['story_pending_text']) + '</p></div>'
        if sample and sample['era_story']:
            body += '<details class="era-story"><summary>' + e(w['era_pending']) + '</summary><p>' + e(self.local(sample['era_story'],lang)) + '</p></details>'
        if sample and not profile:
            body += '<p class="context-reference">' + self.remote(sample['reference'],sample['reference_title']+' ↗') + '</p>'
        body += '</section>' + self.specifications(lang, profile, sample)
        body += '<section id="manuals" class="dossier-section"><div class="section-heading"><h2>'+e(w['manuals'])+'</h2><span>'+str(len(model['document_ids']))+' '+e(w['documents'])+'</span></div>'
        body += ('<div class="manual-cards">'+''.join(self.compact_document(lang,self.docs[key]) for key in model['document_ids'])+'</div>') if model['document_ids'] else '<p class="design-empty">'+e(w['no_manuals'])+'</p>'
        body += '</section><section id="drivers" class="dossier-section"><div class="section-heading"><h2>'+e(w['drivers'])+'</h2><span>'+str(len(software))+' '+e(w['packages'])+'</span></div>'
        body += self.driver_categories(current,lang,software,'drivers') if software else '<p class="design-empty">'+e(w['no_packages'])+'</p>'
        body += '</section><section id="firmware" class="dossier-section"><div class="section-heading"><h2>'+e(w['firmware'])+'</h2><span>'+str(len(firmware))+' '+e(w['packages'])+'</span></div>'
        if firmware:
            body += '<aside class="firmware-warning"><h3>'+e(t['firmware_warning'])+'</h3><p>'+e(t['firmware_warning_text'])+'</p></aside>'+self.driver_categories(current,lang,firmware,'firmware')
        else:
            body += '<p class="design-empty">'+e(w['no_firmware'])+'</p>'
        body += '</section><section id="sources" class="dossier-references"><h2>'+e(w['references'])+'</h2>'+self.thinkwiki(lang,model)
        body += self.dates(lang,model)
        if profile:
            body += self.profile_references(lang,profile)
        body += '<details class="reference-details source-drawer"><summary>'+e(w['sources_details'])+'</summary>'
        if model['aliases']:
            body += '<p>'+e(w['aliases'])+': '+e(' / '.join(model['aliases']))+'</p>'
        body += '<ul class="source-list">'
        for source_id in model['sources']:
            source=self.sources[source_id]
            body += '<li>'+self.remote(source['url'],source['title'])+' <span class="small">'+e(t[source['kind']])+'</span></li>'
        if sample and not profile:
            body += '<li>'+self.remote(sample['reference'],sample['reference_title'])+'</li>'
            if sample.get('release_scope'):
                body += '<li>'+e(self.local(sample['release_scope'],lang))+'</li>'
            if sample.get('price'):
                body += '<li>'+e(self.local(sample['price'],lang))+'</li>'
            if sample.get('spec_note'):
                body += '<li>'+e(self.local(sample['spec_note'],lang))+'</li>'
        body += '</ul>'
        if model['matrix_url']:
            body += '<p>'+self.remote(model['matrix_url'],t['matrix'])+'</p>'
        body += '</details></section></div>'
        page=self.page(current,lang,name,body,kind='model',model_id=model['id'])
        return page.replace('<body>','<body class="model-design-page">')
