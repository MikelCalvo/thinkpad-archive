"""Small source-backed content samples for a local design preview only.

Not a catalogue backfill. Unresearched fields stay absent. Reference rows are
from the retained IBM PSREF books, not inferred from package/manual dates.
"""
SAMPLES = {
    't30': {
        'maker': 'IBM',
        'release': {'en': '23 April 2002', 'es': '23 de abril de 2002'},
        'release_scope': {'en': 'US model announcement · available May 2002', 'es': 'Anuncio de modelos en EE. UU. · disponibles en mayo de 2002'},
        'price': None,
        'description': {
            'en': 'Performance for the working day, with room to adapt.',
            'es': 'Rendimiento para trabajar, con espacio para adaptarse.'},
        'story': {
            'en': 'A 14.1-inch business notebook built around the mobile Pentium 4-M. The removable Ultrabay 2000 drive, optional docking solutions and replaceable memory put expansion at the heart of the design.',
            'es': 'Un portátil de trabajo de 14,1 pulgadas construido alrededor del Pentium 4-M. La unidad extraíble Ultrabay 2000, las bases opcionales y la memoria ampliable sitúan la expansión en el centro del diseño.'},
        'era_title': {'en': 'The wired desk meets wireless', 'es': 'Del escritorio cableado a la conexión inalámbrica'},
        'era_story': {
            'en': 'The original configurations pair Windows XP Professional with Ethernet, an optical drive and serial and parallel ports. Wi-Fi and Bluetooth depend on the configuration: a snapshot of a machine that could serve both the office desk and the journey between offices.',
            'es': 'Las configuraciones originales combinan Windows XP Professional con Ethernet, unidad óptica y puertos serie y paralelo. Wi-Fi y Bluetooth dependen de la configuración: una fotografía de un equipo preparado tanto para la mesa de oficina como para el viaje entre oficinas.'},
        'specs': [
            ('Processor', 'Procesador', 'Pentium 4-M', '1.6 / 1.8 GHz'),
            ('Display', 'Pantalla', '14.1″ TFT', 'XGA / SXGA+'),
            ('Memory', 'Memoria', '256 MB DDR', '1 GB max.'),
            ('Weight', 'Peso', '2.42–2.57 kg', '2,42–2,57 kg'),
        ],
        'spec_note': {'en': 'Type 2366 US configurations, May 2002 · specifications vary by model.', 'es': 'Configuraciones 2366 de EE. UU., mayo de 2002 · las características varían según el modelo.'},
        'reference': 'https://psrefstuff.lenovo.com/syspool/Sys/PDF/withdrawnbook/tawbook.pdf#page=41',
        'reference_title': 'IBM PSREF · T30 · p. 41',
    },
    '700c': {
        'maker': 'IBM',
        'release': {'en': 'October 1992', 'es': 'Octubre de 1992'},
        'release_scope': {'en': 'Availability recorded in IBM PSREF', 'es': 'Disponibilidad recogida en IBM PSREF'},
        'price': {'value': '$4,350 USD', 'es_value': '4.350 USD',
                  'en': 'Retail price in IBM’s May 1994 catalogue, for 9552-30B. Not a confirmed launch price.',
                  'es': 'Precio de catálogo IBM de mayo de 1994 para el 9552-30B. No es un precio de lanzamiento confirmado.'},
        'description': {
            'en': 'Colour on the road, at the beginning of the ThinkPad story.',
            'es': 'Color para llevar, al principio de la historia ThinkPad.'},
        'story': {
            'en': 'A 10.4-inch active-matrix colour display, a 25 MHz 486SLC processor and the TrackPoint II. The documented 9552-30B configuration combines a 120 MB hard disk with 4 MB of memory in a black portable computer.',
            'es': 'Pantalla de color de matriz activa de 10,4 pulgadas, procesador 486SLC a 25 MHz y TrackPoint II. La configuración documentada 9552-30B combina un disco de 120 MB con 4 MB de memoria en un portátil de acabado negro.'},
        'era_title': {'en': 'A different scale of portable computing', 'es': 'Otra escala para la informática portátil'},
        'era_story': {
            'en': 'The IBM reference lists DOS 5.02, a 1.44 MB floppy drive and a battery-equipped weight of 7.6 lb. A removable disk and optional docking station show the balance between mobility and a fully equipped desk in this early ThinkPad.',
            'es': 'La referencia de IBM recoge DOS 5.02, una disquetera de 1,44 MB y un peso de 7,6 libras con batería. El disco extraíble y la base opcional muestran el equilibrio entre movilidad y escritorio en este primer ThinkPad.'},
        'specs': [
            ('Processor', 'Procesador', '486SLC', '25 MHz'),
            ('Display', 'Pantalla', '10.4″ TFT', '640 × 480'),
            ('Memory', 'Memoria', '4 MB', '16 MB max.'),
            ('Storage', 'Almacenamiento', '120 MB', '9552-30B'),
        ],
        'spec_note': {'en': '9552-30B configuration · IBM withdrawn reference.', 'es': 'Configuración 9552-30B · referencia histórica de IBM.'},
        'reference': 'https://psrefstuff.lenovo.com/syspool/Sys/PDF/withdrawnbook/twbook.pdf#page=4',
        'reference_title': 'IBM PSREF · 700C · p. 4',
    },
}
