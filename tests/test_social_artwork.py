"""Raster regression: only the native i dot is red, never its stem.

Decode the checked-in RGB PNGs using stdlib so Docker/test builds need no
artwork-generation dependencies. Geometry is pinned to the accepted wordmark.
"""
from pathlib import Path
import struct
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[1]


def rgb_png(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset, compressed = 8, bytearray()
    width = height = 0
    while offset < len(data):
        length = struct.unpack('>I', data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        body = data[offset + 8:offset + 8 + length]
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', body)
            assert (depth, color, compression, filtering, interlace) == (8, 2, 0, 0, 0)
        elif kind == b'IDAT':
            compressed.extend(body)
        offset += length + 12
    raw = zlib.decompress(compressed)
    stride = width * 3
    assert len(raw) == height * (stride + 1)
    previous, rows = bytearray(stride), []
    for y in range(height):
        start = y * (stride + 1)
        method = raw[start]
        row = bytearray(raw[start + 1:start + 1 + stride])
        assert method in range(5)
        for x in range(stride):
            left = row[x - 3] if x >= 3 else 0
            up = previous[x]
            upper_left = previous[x - 3] if x >= 3 else 0
            if method == 1:
                predictor = left
            elif method == 2:
                predictor = up
            elif method == 3:
                predictor = (left + up) // 2
            elif method == 4:
                estimate = left + up - upper_left
                distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
                predictor = (left, up, upper_left)[distances.index(min(distances))]
            else:
                predictor = 0
            row[x] = (row[x] + predictor) % 256
        rows.append(row)
        previous = row
    return lambda x, y: tuple(rows[y][x * 3:x * 3 + 3])


class SocialArtwork(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards = {lang: rgb_png(ROOT / 'assets' / ('social-' + lang + '.png')) for lang in ('en', 'es')}

    def test_i_stem_is_white_including_its_top_edge(self):
        for lang, pixel in self.cards.items():
            for y in range(196, 247):
                for x in range(218, 231):
                    with self.subTest(language=lang, x=x, y=y):
                        red, green, blue = pixel(x, y)
                        self.assertGreater(min(red, green, blue), 210)
                        self.assertLess(max(red, green, blue) - min(red, green, blue), 16)

    def test_i_dot_stays_red_and_gap_stays_empty(self):
        for lang, pixel in self.cards.items():
            with self.subTest(language=lang):
                for y in range(176, 185):
                    red, green, blue = pixel(225, y)
                    self.assertGreater(red, 200)
                    self.assertLess(green, 90)
                    self.assertLess(blue, 100)
                for y in range(190, 193):
                    self.assertLess(max(pixel(225, y)), 40)
