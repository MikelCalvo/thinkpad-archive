"""Public analytics body; shared navigation and document shell stay in Renderer."""
from html import escape
import json


STATS_COPY = {
    'en': {
        'title': 'Stats',
        'period': 'Period', 'all_time': 'All time', 'days': 'Last {days} days', 'refresh': 'Refresh',
        'loading': 'Loading public counts…', 'ready': 'Public counts loaded. Refreshes every minute while this page is visible.',
        'unavailable': 'Statistics are unavailable. No counts are being displayed.',
        'disabled': 'Analytics collection is disabled. No counts are being displayed.',
        'file': 'Live statistics are unavailable in a local file. Open the hosted site to read public counts.',
        'noscript': 'Live counts need JavaScript. Privacy and methodology remain readable below.',
        'initial': 'Live counts have not been loaded.', 'views': 'JavaScript page views',
        'download_total': 'Catalogue downloads',
        'download_method': 'Downloads count full ZIP responses sent by this server, separately from views and only since collection was enabled. HEAD, partial Range requests and DNT/GPC opt-outs do not count. Transfers are not unique people or proof a file was saved. Buffers used by the network or proxy can outlive a disconnect; these are not receipt acknowledgements. Failed counter writes and interrupted transfers can omit counts.',
        'window': 'UTC window', 'range': '{from} – {to}', 'daily': 'Daily views',
        'daily_table': 'Daily counts table', 'pages': 'Popular pages', 'sources': 'Referral sources',
        'devices': 'Devices', 'browsers': 'Browsers', 'systems': 'Operating systems',
        'languages': 'Page languages', 'value': 'Category', 'page': 'Page', 'day': 'UTC day',
        'count': 'Views', 'empty': 'No counts recorded.', 'privacy_title': 'Privacy & methodology',
        'privacy_short': 'Page views, not unique visitors. No cookies, identifiers, country data or cross-page visitor linkage.',
        'method': 'What is stored and what these counts mean',
        'storage': 'Only counts(day, dimension, value, count) is stored: positive daily marginal counters in SQLite, retained indefinitely as part of the archive. Total, page, source, device, browser, system and language are separate totals, never joined visitor records. ZIP downloads add a separate daily version counter without visitor categories. All retained counters are public; no private visitor records are kept.',
        'collection': 'One document load can add one view; search/filter changes do not. This dashboard does not collect. DNT and GPC opt out. No raw referrer, user agent, IP address, IP hash, cookie, identifier, fingerprint, session, duration or click recording is stored. No country or GeoIP lookup is performed.',
        'limits': 'Client-side blocking and opt-outs omit views; bots and spoofed browser/referral categories can affect counts. Categories are coarse estimates, not verified people or hardware. Marginal counts cannot link a page to a source or device. These numbers are not unique visitors.',
        'infrastructure': 'Infrastructure or reverse-proxy logs are outside this application’s analytics guarantees and may have their own policy. The analytics application does not write access/request logs.',
        'source_direct': 'Direct / no referrer', 'source_internal': 'Internal', 'source_search': 'Search engines',
        'source_github': 'GitHub', 'source_reddit': 'Reddit', 'source_hacker-news': 'Hacker News',
        'source_social': 'Social', 'source_other': 'Other', 'device_desktop': 'Desktop',
        'device_mobile': 'Mobile', 'device_tablet': 'Tablet', 'device_unknown': 'Unknown',
        'browser_firefox': 'Firefox', 'browser_chrome': 'Chrome', 'browser_safari': 'Safari',
        'browser_edge': 'Edge', 'browser_opera': 'Opera', 'browser_other': 'Other', 'browser_unknown': 'Unknown',
        'system_windows': 'Windows', 'system_macos': 'macOS', 'system_linux': 'Linux',
        'system_android': 'Android', 'system_ios': 'iOS', 'system_other': 'Other', 'system_unknown': 'Unknown',
        'language_en': 'English', 'language_es': 'Spanish',
        'traffic_method': 'HTML requests add one daily document-traffic marginal: browser, unknown, other-bot or a finite crawler name. No page, referrer or device is joined to it. Only transient User-Agent classification is used, with no IP, DNS or GeoIP verification. Earlier views are not reclassified. DNT/GPC opt-outs, HEAD, errors, dashboard, APIs, assets and downloads are excluded. Only successful full server writes count, not receipt by a person: network or proxy buffers may outlive disconnects. Counter failures and interrupted sends can omit counts. Static/offline hosting collects nothing by default.',
        'traffic_note': 'Successful HTML GETs, including clients without JavaScript. Browser-like does not mean human; crawler names are spoofable self-descriptions. This is a separate population from JavaScript views and ZIP downloads.',
        'other-bot': 'Other self-declared automation',
        'traffic_absent': 'This API does not yet provide HTML traffic counts. Earlier JavaScript views remain unclassified.',
        'requests': 'Requests',
        'traffic_daily': 'Daily HTML requests',
        'traffic_counts': 'Exact category counts',
        'traffic_crawlers': 'Declared crawlers & other automation',
        'traffic_unknown': 'Unknown',
        'traffic_bots': 'Bots / automation',
        'traffic_browser': 'Browser-like',
        'traffic': 'Document traffic · self-declared categories',
        'documents': 'HTML document requests',
    },
    'es': {
        'title': 'Estadísticas',
        'period': 'Periodo', 'all_time': 'Todo el tiempo', 'days': 'Últimos {days} días', 'refresh': 'Actualizar',
        'loading': 'Cargando recuentos públicos…', 'ready': 'Recuentos públicos cargados. Se actualizan cada minuto mientras esta página está visible.',
        'unavailable': 'Las estadísticas no están disponibles. No se muestran recuentos.',
        'disabled': 'La recopilación está desactivada. No se muestran recuentos.',
        'file': 'Las estadísticas en directo no están disponibles en un archivo local. Abre el sitio alojado para consultar los recuentos públicos.',
        'noscript': 'Los recuentos en directo necesitan JavaScript. La privacidad y la metodología siguen disponibles debajo.',
        'initial': 'No se han cargado los recuentos en directo.', 'views': 'Vistas con JavaScript',
        'download_total': 'Descargas del catálogo',
        'download_method': 'Las descargas cuentan respuestas ZIP completas enviadas por este servidor, por separado de las vistas y solo desde que se activó su recuento. No se cuentan HEAD, peticiones parciales Range ni exclusiones DNT/GPC. No son personas únicas ni prueban que se guardara el archivo. Los búferes de red o del proxy pueden sobrevivir a una desconexión; no son confirmaciones de recepción. Un fallo al guardar el contador o una transferencia interrumpida puede omitir recuentos.',
        'window': 'Intervalo UTC', 'range': '{from} – {to}', 'daily': 'Vistas diarias',
        'daily_table': 'Tabla de recuentos diarios', 'pages': 'Páginas populares', 'sources': 'Procedencia',
        'devices': 'Dispositivos', 'browsers': 'Navegadores', 'systems': 'Sistemas operativos',
        'languages': 'Idiomas de las páginas', 'value': 'Categoría', 'page': 'Página', 'day': 'Día UTC',
        'count': 'Vistas', 'empty': 'No hay recuentos registrados.', 'privacy_title': 'Privacidad y metodología',
        'privacy_short': 'Vistas de páginas, no visitantes únicos. Sin cookies, identificadores, datos de país ni vinculación de visitantes entre páginas.',
        'method': 'Qué se almacena y qué significan los recuentos',
        'storage': 'Solo se almacena counts(day, dimension, value, count): contadores marginales diarios positivos en SQLite, conservados de forma indefinida como parte del archivo. Total, página, procedencia, dispositivo, navegador, sistema e idioma son totales separados, nunca registros de visitantes combinados. Las descargas ZIP añaden un contador diario por versión sin categorías de visitantes. Todos los contadores conservados son públicos; no hay registros privados de visitantes.',
        'collection': 'Una carga de documento puede sumar una vista; los cambios de búsqueda o filtros no. Este panel no recopila datos. DNT y GPC excluyen la recopilación. No se almacenan referentes completos, agentes de usuario, direcciones IP, hashes de IP, cookies, identificadores, huellas digitales, sesiones, duraciones ni registros de clics. No se consulta el país ni GeoIP.',
        'limits': 'El bloqueo del navegador y la exclusión omiten vistas; los bots y las categorías de navegador o procedencia falseadas pueden alterar los recuentos. Las categorías son estimaciones generales, no personas ni equipos verificados. Los recuentos marginales no permiten vincular una página con una procedencia o dispositivo. No son visitantes únicos.',
        'infrastructure': 'Los registros de infraestructura o del proxy inverso quedan fuera de las garantías de este sistema de analítica y pueden tener su propia política. La aplicación de analítica no escribe registros de acceso ni peticiones.',
        'source_direct': 'Directa / sin referente', 'source_internal': 'Interna', 'source_search': 'Buscadores',
        'source_github': 'GitHub', 'source_reddit': 'Reddit', 'source_hacker-news': 'Hacker News',
        'source_social': 'Redes sociales', 'source_other': 'Otra', 'device_desktop': 'Escritorio',
        'device_mobile': 'Móvil', 'device_tablet': 'Tableta', 'device_unknown': 'Desconocido',
        'browser_firefox': 'Firefox', 'browser_chrome': 'Chrome', 'browser_safari': 'Safari',
        'browser_edge': 'Edge', 'browser_opera': 'Opera', 'browser_other': 'Otro', 'browser_unknown': 'Desconocido',
        'system_windows': 'Windows', 'system_macos': 'macOS', 'system_linux': 'Linux',
        'system_android': 'Android', 'system_ios': 'iOS', 'system_other': 'Otro', 'system_unknown': 'Desconocido',
        'language_en': 'Inglés', 'language_es': 'Español',
        'traffic_method': 'Las peticiones HTML añaden un único marginal diario document-traffic: browser, unknown, other-bot o un nombre de rastreador de una lista finita. No se combina con página, procedencia ni dispositivo. Solo se clasifica el User-Agent de forma transitoria, sin verificar IP, DNS ni GeoIP. No se reclasifican vistas anteriores. Se excluyen DNT/GPC, HEAD, errores, panel, API, recursos y descargas. Solo cuentan escrituras completas del servidor, no la recepción por una persona: los búferes de red o del proxy pueden sobrevivir a una desconexión. Los fallos de contador y envíos interrumpidos pueden omitir recuentos. El alojamiento estático y sin conexión no recopila por defecto.',
        'traffic_note': 'GET de HTML completos, incluidos clientes sin JavaScript. Parecer un navegador no implica ser humano; los nombres de rastreadores son declaraciones falseables. Esta población es distinta de las vistas con JavaScript y las descargas ZIP.',
        'other-bot': 'Otra automatización declarada',
        'traffic_absent': 'Esta API todavía no ofrece recuentos de tráfico HTML. Las vistas anteriores con JavaScript siguen sin clasificar.',
        'requests': 'Peticiones',
        'traffic_daily': 'Peticiones HTML diarias',
        'traffic_counts': 'Recuentos exactos por categoría',
        'traffic_crawlers': 'Rastreadores declarados y otra automatización',
        'traffic_unknown': 'Desconocido',
        'traffic_bots': 'Bots / automatización',
        'traffic_browser': 'Similar a un navegador',
        'traffic': 'Tráfico de documentos · categorías declaradas',
        'documents': 'Peticiones de documentos HTML',
    },
}


def stats_body(lang):
    """Return a self-contained escaped body fragment; unsupported locales use EN."""
    t = STATS_COPY.get(lang, STATS_COPY['en'])
    e = lambda key: escape(t[key.replace('traffic-counts', 'traffic_counts').replace('traffic-crawlers', 'traffic_crawlers')], quote=True)

    def table(name, first='value', count='count'):
        return ('<div class="stats-table-scroll" role="region" aria-label="' + e(name) + '" tabindex="0">'
                '<table><caption class="visually-hidden">' + e(name) + '</caption><thead><tr>'
                '<th scope="col">' + e(first) + '</th><th scope="col">' + e(count) + '</th>'
                '</tr></thead><tbody id="stats-' + name + '"></tbody></table></div>')

    title = e('title')
    if lang == 'es':
        title = 'Estadíst<span class="title-i">i</span>cas'

    body = ('<div id="stats-dashboard" class="stats-dashboard" data-stats-copy="' +
            escape(json.dumps(t, ensure_ascii=False), quote=True) + '">'
            '<header class="stats-heading"><h1>' + title + '</h1></header>'
            '<div id="stats-controls" class="stats-controls" hidden><div><label for="stats-days">' + e('period') + '</label>'
            '<select id="stats-days">')
    for days in (7, 30, 90, 365):
        body += ('<option value="' + str(days) + '"' + (' selected' if days == 30 else '') + '>' +
                 escape(t['days'].replace('{days}', str(days))) + '</option>')
    body += '<option value="all">' + e('all_time') + '</option>'
    body += ('</select></div><button id="stats-refresh" type="button" aria-label="' + e('refresh') + '" title="' + e('refresh') + '">'
             '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
             '<path d="M20 4v6h-6M4 20v-6h6"/><path d="M6.1 7a7 7 0 0 1 11.6-1L20 10M4 14l2.3 4A7 7 0 0 0 17.9 17"/>'
             '</svg></button></div>'
             '<p id="stats-status" class="stats-status" role="status" aria-live="polite" aria-atomic="true">' + e('initial') + '</p>'
             '<noscript><p>' + e('noscript') + '</p></noscript>'
             '<div id="stats-results" hidden><dl class="stats-overview"><div><dt>' + e('views') + '</dt>'
             '<dd id="stats-total">—</dd></div><div><dt>' + e('download_total') + '</dt><dd id="stats-download-total">—</dd></div><div><dt>' + e('documents') + '</dt><dd id="stats-document-total">—</dd></div><div><dt>' + e('window') + '</dt><dd id="stats-window">—</dd></div></dl>'
             '<section id="stats-traffic" class="stats-panel stats-traffic" aria-labelledby="stats-traffic-title">'
             '<h2 id="stats-traffic-title">' + e('traffic') + '</h2><p class="stats-traffic-note">' + e('traffic_note') + '</p>'
             '<p id="stats-traffic-status" role="status"></p>'
             '<svg id="stats-traffic-chart" class="stats-chart stats-traffic-chart" viewBox="0 0 600 240" role="img" aria-label="' + e('traffic') + '"></svg>'
             + table('traffic-counts', count='requests') +
             '<details><summary>' + e('traffic_crawlers') + '</summary>' + table('traffic-crawlers', count='requests') + '</details>'
             '<details><summary>' + e('traffic_daily') + '</summary>'
             '<div class="stats-table-scroll" role="region" aria-label="' + e('traffic_daily') + '" tabindex="0"><table>'
             '<caption class="visually-hidden">' + e('traffic_daily') + '</caption><thead><tr>'
             '<th scope="col">' + e('day') + '</th>' +
             ''.join('<th scope="col">' + e(key) + '</th>' for key in ('requests', 'traffic_browser', 'traffic_bots', 'traffic_unknown')) +
             '</tr></thead><tbody id="stats-traffic-daily"></tbody></table></div></details></section>'
             '<section class="stats-panel stats-daily" aria-labelledby="stats-daily-title"><h2 id="stats-daily-title">' + e('daily') + '</h2>'
             '<svg id="stats-chart" class="stats-chart" viewBox="0 0 1000 180" role="img" aria-label="' + e('daily') + '"></svg>'
             '<details><summary>' + e('daily_table') + '</summary>' + table('daily', 'day') + '</details></section>'
             '<div class="stats-grid">')
    for name in ('pages', 'sources', 'devices', 'browsers', 'systems', 'languages'):
        body += ('<section class="stats-panel" aria-labelledby="stats-' + name + '-title">'
                 '<h2 id="stats-' + name + '-title">' + e(name) + '</h2>' + table(name, 'page' if name == 'pages' else 'value') + '</section>')
    body += ('</div></div><section class="stats-privacy" aria-labelledby="stats-privacy-title">'
             '<h2 id="stats-privacy-title">' + e('privacy_title') + '</h2><p>' + e('privacy_short') + '</p>'
             '<details><summary>' + e('method') + '</summary>')
    body += ''.join('<p>' + e(key) + '</p>' for key in ('storage', 'collection', 'traffic_method', 'download_method', 'limits', 'infrastructure'))
    return body + '</details></section></div>'
