#!/usr/bin/env python3
"""Renders the front page of the world's news for Wednesday 25 November 2026
to /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png).

Pure Python standard library: no PIL, no fonts on disk. The image is a
1024x1024 RGB PNG written with zlib, every glyph from an embedded 5x7
bitmap font. Deterministic: every draw call takes fixed inputs, so two
runs write byte-identical PNGs. No network access is used; the headlines
below were gathered from BBC World RSS on the day and baked in.
"""

import os
import struct
import zlib

W = H = 1024

# Palette (a newspaper on a late-November night)
PAPER = (244, 242, 235)
INK = (24, 26, 31)
RED = (178, 34, 38)
BLUE = (32, 62, 110)
GREY = (110, 112, 118)
SLATE = (58, 64, 74)
GOLD = (176, 132, 44)

# The day's stories, in lead-first order.
# (region tag, tag colour, headline, detail, glyph key)
STORIES = [
    ("USA", RED,
     "HUAWEI VERDICT IN NEW YORK",
     "JURY CONVICTS ON STEALING TRADE SECRETS; ACQUITTED OF RACKETEERING",
     "chip"),
    ("EUROPE", BLUE,
     "SARKOZY AND BRUNI ON TRIAL",
     "FRENCH EX-PRESIDENT AND WIFE FACE COURT IN LATEST OF HIS CASES",
     "globe"),
    ("MIDEAST", GOLD,
     "HAMAS SECURITY CHIEF KILLED",
     "ISRAELI AIR STRIKE ON GAZA KILLS NAEEM ABU NAHEL, SEVEN REPORTED DEAD",
     "wave"),
    ("NATO", RED,
     "NATO VOWS SPACE DEFENCE",
     "RUTTE ACTS ON REPORTS RUSSIA PLANS A NUCLEAR-WARHEAD SATELLITE",
     "chip"),
    ("ASIA", BLUE,
     "SHANGHAI PARTY CHIEF PURGED",
     "CHINA INVESTIGATES CHEN JINING AS XI'S ANTI-GRAFT PURGES EXPAND",
     "globe"),
    ("MIDEAST", GOLD,
     "HOUTHI STRIKE HITS RIYADH",
     "ATTACK ON SKYSCRAPER IN SAUDI CAPITAL WOUNDS 11, OFFICIALS SAY",
     "wave"),
    ("AFRICA", BLUE,
     "DR CONGO JET GOES MISSING",
     "REBELS CLAIM TO DOWN MILITARY PLANE; SA PILOT, UGANDAN OFFICER ABOARD",
     "wave"),
    ("EUROPE", GREY,
     "JAPAN BACKS WAR CRIMES COURT",
     "TAKAICHI BREAKS WITH US, DEFENDS AND FUNDS THE ICC",
     "note"),
]


# ---------------------------------------------------------------- bitmap font
# Classic 5x7 glyphs, one string of 7 rows per glyph, each row 5 bits.
FONT5x7 = {
    'A': ("01110","10001","10001","11111","10001","10001","10001"),
    'B': ("11110","10001","10001","11110","10001","10001","11110"),
    'C': ("01110","10001","10000","10000","10000","10001","01110"),
    'D': ("11110","10001","10001","10001","10001","10001","11110"),
    'E': ("11111","10000","10000","11110","10000","10000","11111"),
    'F': ("11111","10000","10000","11110","10000","10000","10000"),
    'G': ("01110","10001","10000","10111","10001","10001","01111"),
    'H': ("10001","10001","10001","11111","10001","10001","10001"),
    'I': ("11111","00100","00100","00100","00100","00100","11111"),
    'J': ("00111","00010","00010","00010","00010","10010","01100"),
    'K': ("10001","10010","10100","11000","10100","10010","10001"),
    'L': ("10000","10000","10000","10000","10000","10000","11111"),
    'M': ("10001","11011","10101","10101","10001","10001","10001"),
    'N': ("10001","11001","10101","10011","10001","10001","10001"),
    'O': ("01110","10001","10001","10001","10001","10001","01110"),
    'P': ("11110","10001","10001","11110","10000","10000","10000"),
    'Q': ("01110","10001","10001","10001","10101","10010","01101"),
    'R': ("11110","10001","10001","11110","10100","10010","10001"),
    'S': ("01111","10000","10000","01110","00001","00001","11110"),
    'T': ("11111","00100","00100","00100","00100","00100","00100"),
    'U': ("10001","10001","10001","10001","10001","10001","01110"),
    'V': ("10001","10001","10001","10001","10001","01010","00100"),
    'W': ("10001","10001","10001","10101","10101","11011","10001"),
    'X': ("10001","10001","01010","00100","01010","10001","10001"),
    'Y': ("10001","10001","01010","00100","00100","00100","00100"),
    'Z': ("11111","00001","00010","00100","01000","10000","11111"),
    '0': ("01110","10001","10011","10101","11001","10001","01110"),
    '1': ("00100","01100","00100","00100","00100","00100","01110"),
    '2': ("01110","10001","00001","00110","01000","10000","11111"),
    '3': ("11110","00001","00001","01110","00001","00001","11110"),
    '4': ("00010","00110","01010","10010","11111","00010","00010"),
    '5': ("11111","10000","11110","00001","00001","10001","01110"),
    '6': ("00110","01000","10000","11110","10001","10001","01110"),
    '7': ("11111","00001","00010","00100","01000","01000","01000"),
    '8': ("01110","10001","10001","01110","10001","10001","01110"),
    '9': ("01110","10001","10001","01111","00001","00010","01100"),
    ' ': ("00000","00000","00000","00000","00000","00000","00000"),
    '.': ("00000","00000","00000","00000","00000","00100","00100"),
    ',': ("00000","00000","00000","00000","00100","00100","01000"),
    ':': ("00000","00100","00100","00000","00100","00100","00000"),
    ';': ("00000","00100","00100","00000","00100","00100","01000"),
    '!': ("00100","00100","00100","00100","00100","00000","00100"),
    '?': ("01110","10001","00001","00110","00100","00000","00100"),
    "'": ("00100","00100","01000","00000","00000","00000","00000"),
    '"': ("01010","01010","00000","00000","00000","00000","00000"),
    '-': ("00000","00000","00000","01110","00000","00000","00000"),
    '|': ("00100","00100","00100","00100","00100","00100","00100"),
    '(': ("00010","00100","01000","01000","01000","00100","00010"),
    ')': ("01000","00100","00010","00010","00010","00100","01000"),
    '/': ("00001","00010","00010","00100","01000","01000","10000"),
    '$': ("00100","01111","10100","01110","00101","11110","00100"),
    '&': ("01100","10010","01100","10101","10010","01101","10010"),
    '+': ("00000","00100","00100","11111","00100","00100","00000"),
    '%': ("11001","11010","00010","00100","01000","01011","10011"),
    '#': ("01010","11111","01010","01010","01010","11111","01010"),
}

# ---------------------------------------------------------------- raster core
PIX = bytearray()  # row-major RGB

def _at(x, y):
    o = (y * W + x) * 3
    return PIX[o], PIX[o + 1], PIX[o + 2]


def fill_rect(x0, y0, x1, y1, colour):
    for y in range(max(0, y0), min(H, y1 + 1)):
        base = y * W
        for x in range(max(0, x0), min(W, x1 + 1)):
            o = (base + x) * 3
            PIX[o] = colour[0]
            PIX[o + 1] = colour[1]
            PIX[o + 2] = colour[2]


def hline(x0, x1, y, colour, w=1):
    for k in range(w):
        fill_rect(x0, y + k, x1, y + k, colour)


def vline(x, y0, y1, colour, w=1):
    for k in range(w):
        fill_rect(x + k, y0, x + k, y1, colour)


def box(x0, y0, x1, y1, colour, w=1):
    hline(x0, x1, y0, colour, w)
    hline(x0, x1, y1 - w + 1, colour, w)
    vline(x0, y0, y1, colour, w)
    vline(x1 - w + 1, y0, y1, colour, w)


def text(x, y, s, colour, scale=2):
    cx = x
    for ch in s.upper():
        rows = FONT5x7.get(ch, FONT5x7['?'])
        for ry, row in enumerate(rows):
            for rx in range(5):
                if row[rx] == '1':
                    fill_rect(cx + rx * scale, y + ry * scale,
                              cx + rx * scale + scale - 1,
                              y + ry * scale + scale - 1, colour)
        cx += 6 * scale
    return cx


def text_w(s, scale=2):
    return 6 * scale * len(s) - scale


def glyph_chip(x, y, key, colour):
    """A small 26x26 pictogram, drawn with primitives only."""
    box(x, y, x + 25, y + 25, colour, 2)
    cx = x + 9
    if key == "chip":
        box(cx, y + 8, cx + 8, y + 16, colour, 1)
        for i in (0, 3, 6):
            vline(cx + i, y + 3, y + 7, colour)
            vline(cx + i, y + 17, y + 21, colour)
    elif key == "wave":
        for k in range(3):
            yy = y + 6 + k * 6
            fill_rect(x + 5, yy, x + 20, yy, colour)
            fill_rect(x + 7, yy - 1, x + 9, yy - 1, colour)
            fill_rect(x + 16, yy - 1, x + 18, yy - 1, colour)
    elif key == "globe":
        box(x + 5, y + 5, x + 20, y + 20, colour, 1)
        hline(x + 5, x + 20, y + 12, colour)
        vline(x + 12, y + 5, y + 20, colour)
    elif key == "note":
        vline(x + 11, y + 6, y + 16, colour)
        fill_rect(x + 6, y + 15, x + 10, y + 19, colour)
        fill_rect(x + 12, y + 6, x + 16, y + 8, colour)


# ---------------------------------------------------------------- the page
def render():
    PIX.clear()
    PIX.extend(bytes(W * H * 3))
    fill_rect(0, 0, W - 1, H - 1, PAPER)

    # Masthead band: a fixed night-to-dawn gradient
    for top in range(118):
        t = top / 118.0
        c = (int(20 + 190 * t), int(24 + 175 * t), int(40 + 160 * t))
        hline(0, W - 1, top, c)

    mast = "THE WORLD IN ONE DAY"
    s = 7  # 42 px tall caps
    text((W - text_w(mast, s)) // 2, 14, mast, (250, 248, 240), s)
    date = "WEDNESDAY 25 NOVEMBER 2026"
    s = 4
    text((W - text_w(date, s)) // 2, 80, date, GOLD, s)
    text(24, 92, "WORLD EDITION", (230, 232, 238), 2)
    sub = "EIGHT STORIES THAT MOVED THE PLANET, AS REPORTED ON THE DAY"
    s = 2
    text((W - text_w(sub, s)) // 2, 122, sub, GREY, s)
    hline(24, W - 24, 146, INK, 3)

    # Lead story
    region, colour, head, detail, gkey = STORIES[0]
    y = 162
    fill_rect(24, y, 24 + text_w("LEAD | " + region, 2) + 14, y + 24, colour)
    text(34, y + 6, "LEAD | " + region, PAPER, 2)
    glyph_chip(W - 60, y + 2, gkey, colour)
    text(24, y + 36, head, INK, 5)
    # wrap the lead detail within the page width
    words = detail.split()
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_w(trial, 3) <= W - 48:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    for li, ln in enumerate(lines):
        text(24, y + 36 + 44 + li * 24, ln, SLATE, 3)
    hline(24, W - 24, y + 36 + 44 + 24 * len(lines) + 8, GREY, 2)

    # Remaining stories in a two-column grid
    y0 = y + 36 + 44 + 24 * len(lines) + 26
    col_w = 488
    row_h = 168
    for i, (region, colour, head, detail, gkey) in enumerate(STORIES[1:]):
        col = i % 2
        row = i // 2
        x = 24 + col * (col_w + 24)
        y = y0 + row * row_h
        fill_rect(x, y, x + text_w(region, 2) + 14, y + 20, colour)
        text(x + 7, y + 4, region, PAPER, 2)
        glyph_chip(x + col_w - 34, y, gkey, colour)
        text(x, y + 30, head, INK, 3)
        # wrap the detail line into the column
        words = detail.split()
        lines, cur = [], ""
        for wd in words:
            trial = (cur + " " + wd).strip()
            if text_w(trial, 2) <= col_w - 40:
                cur = trial
            else:
                lines.append(cur)
                cur = wd
        if cur:
            lines.append(cur)
        for li, ln in enumerate(lines[:3]):
            text(x, y + 62 + li * 22, ln, SLATE, 2)
        hline(x, x + col_w - 16, y + row_h - 18, (200, 198, 190), 2)

    # Footer: the day's date again, so the image names its day even cropped
    fill_rect(0, H - 44, W - 1, H - 1, INK)
    foot = "25 NOVEMBER 2026 | THE DAY THE WORLD MADE HEADLINES"
    s = 3
    text((W - text_w(foot, s)) // 2, H - 36, foot, PAPER, s)


def write_png(path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter type 0
        raw += PIX[y * stride:(y + 1) * stride]
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def main():
    render()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    write_png(os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
