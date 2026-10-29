"""Regenerate checked-in social artwork (optional Pillow and rsvg-convert).

Normal site builds copy the PNGs unchanged and need only Python's stdlib.
Run: python3 tools/generate_social_cards.py
"""
from pathlib import Path
import io
import math
import random
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, SCALE = 1200, 630, 2
FONTS = Path('/usr/share/fonts/TTF')


def font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size * SCALE)


def render(language):
    randomizer = random.Random(402)
    image = Image.new('RGB', (WIDTH * SCALE, HEIGHT * SCALE))
    pixels = image.load()
    assert pixels is not None
    for y in range(HEIGHT * SCALE):
        for x in range(WIDTH * SCALE):
            glow = max(0, 1 - math.hypot(x / SCALE - 980, y / SCALE - 260) / 680)
            grain = randomizer.choice((-1, 0, 0, 0, 1))
            pixels[x, y] = (int(15 + glow * 5) + grain, int(19 + glow * 5) + grain, int(25 + glow * 7) + grain)
    draw = ImageDraw.Draw(image)

    def rect(box, fill, radius=0, outline=None):
        draw.rounded_rectangle(tuple(round(v * SCALE) for v in box), radius=radius * SCALE, fill=fill, outline=outline, width=SCALE)

    def text(x, y, value, size, fill, bold=False):
        draw.text((x * SCALE, y * SCALE), value, font=font(size, bold), fill=fill, anchor='lt')

    red, white, muted = '#ef3340', '#f2f3f5', '#aab2bf'
    rect((72, 82, 101, 86), red, 2)
    eyebrow = 'INDEPENDENT COMMUNITY ARCHIVE' if language == 'en' else 'ARCHIVO COMUNITARIO INDEPENDIENTE'
    text(72, 110, eyebrow, 13, muted, True)
    # Keep the native i glyph; recolor only its separated dot.
    title_font = font(99, True)
    layer = Image.new('RGBA', image.size)
    title_draw = ImageDraw.Draw(layer)
    title_draw.text((70 * SCALE, 174 * SCALE), 'ThinkPad', font=title_font, fill=white, anchor='lt')
    dot_left = (70 + title_font.getlength('Th') / SCALE) * SCALE
    dot_right = dot_left + title_font.getlength('i')
    mask = layer.getchannel('A')
    # Follow the actual first ink component, stopping at the dot/stem gap.
    # A fixed y cutoff can include the first rows of the native i stem.
    glyph = mask.crop((int(dot_left), 160 * SCALE, int(dot_right), 225 * SCALE))
    bounds = glyph.getbbox()
    if bounds:
        dot_bottom = bounds[1]
        while dot_bottom < glyph.height and glyph.crop((0, dot_bottom, glyph.width, dot_bottom + 1)).getbbox():
            dot_bottom += 1
        alpha = Image.new('L', layer.size)
        alpha.paste(glyph.crop((0, 0, glyph.width, dot_bottom)), (int(dot_left), 160 * SCALE))
        layer.paste(Image.new('RGBA', layer.size, red), (0, 0), alpha)
    image = Image.alpha_composite(image.convert('RGBA'), layer)
    draw = ImageDraw.Draw(image)
    text(70, 285, 'Archive', 99, white, True)
    text(75, 432, 'Manuals · Software · History' if language == 'en' else 'Manuales · Software · Historia', 23, muted)

    # Subtle keyboard material, not a manufacturer product photograph.
    for row in range(4):
        for column in range(3):
            x, y = 825 + column * 98 - row * 13, 147 + row * 82
            rect((x, y, x + 82, y + 65), '#171d26', 11, '#2b3441')
            rect((x + 5, y + 4, x + 77, y + 57), '#1c2430', 8)
    cap = Image.open(io.BytesIO(subprocess.check_output([
        'rsvg-convert', '-w', str(194 * SCALE), '-h', str(194 * SCALE), str(ROOT / 'assets/favicon.svg')]))).convert('RGBA')
    image.alpha_composite(cap, (880 * SCALE, 206 * SCALE))
    draw = ImageDraw.Draw(image)
    rect((72, 525, 1128, 526), '#303844')
    text(74, 554, 'thinkpadarchive.com', 20, '#d0d5de')
    text(1078, 557, language.upper(), 15, muted, True)
    image = image.convert('RGB').resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    target = ROOT / 'assets' / ('social-' + language + '.png')
    image.save(target, optimize=True)
    print(target.name, image.size, target.stat().st_size)


if __name__ == '__main__':
    for language in ('en', 'es'):
        render(language)
