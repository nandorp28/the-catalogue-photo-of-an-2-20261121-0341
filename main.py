#!/usr/bin/env python3
"""The Catalogue Photo of an Impossible Gadget.

Renders, in pure Python stdlib, a studio catalogue photograph of a tin
can of DEHYDRATED WATER ("JUST ADD WATER"), with exactly one accessory:
a small glass of water standing beside it.  Everything is drawn
procedurally - gradients, metallic shading, soft shadows, a bitmap
label - and written out as a PNG with a hand-rolled encoder (zlib only,
no PIL).  Run with `python3 main.py`; it writes /output/entry.png.
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
OUT = "/output/entry.png"

# ---------------------------------------------------------------------------
# Tiny 5x7 bitmap font.  Each glyph is 7 rows of 5 bits, '#' = on.
# ---------------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    ":": ("00000", "00100", "00000", "00000", "00000", "00100", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def text_width(text, scale):
    """Pixel width of `text` rendered at `scale` (1 = 5x7 per glyph)."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


# ---------------------------------------------------------------------------
# Pixel buffer: a flat bytearray, 3 bytes per pixel (RGB).
# ---------------------------------------------------------------------------

def new_canvas():
    return bytearray(W * H * 3)


def put(buf, x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend(buf, x, y, r, g, b, a):
    """Alpha-blend a colour over the pixel at (x, y); a in 0..255."""
    if a <= 0 or not (0 <= x < W and 0 <= y < H):
        return
    if a >= 255:
        put(buf, x, y, r, g, b)
        return
    i = (y * W + x) * 3
    inv = 255 - a
    buf[i] = (r * a + buf[i] * inv) // 255
    buf[i + 1] = (g * a + buf[i + 1] * inv) // 255
    buf[i + 2] = (b * a + buf[i + 2] * inv) // 255


def fill_rect(buf, x0, y0, x1, y1, color):
    r, g, b = color
    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(W, x1)
    y1 = min(H, y1)
    for y in range(y0, y1):
        base = (y * W + x0) * 3
        for x in range(x0, x1):
            i = base + (x - x0) * 3
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b


def fill_ellipse(buf, cx, cy, rx, ry, color, alpha=255):
    """Filled ellipse, optionally translucent."""
    r, g, b = color
    for y in range(cy - ry, cy + ry + 1):
        dy = (y - cy) / ry
        if abs(dy) > 1:
            continue
        hw = int(rx * math.sqrt(1.0 - dy * dy))
        for x in range(cx - hw, cx + hw + 1):
            blend(buf, x, y, r, g, b, alpha)


def ellipse_outline(buf, cx, cy, rx, ry, color, alpha=255, thick=1):
    r, g, b = color
    for t in range(0, 720):
        ang = math.radians(t * 0.5)
        x = int(cx + rx * math.cos(ang))
        y = int(cy + ry * math.sin(ang))
        for dx in range(thick):
            for dy in range(thick):
                blend(buf, x + dx, y + dy, r, g, b, alpha)


def draw_text(buf, x, y, text, scale, color):
    """Draw `text` with its top-left corner at (x, y)."""
    r, g, b = color
    cx = x
    for ch in text:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    for sy in range(scale):
                        for sx in range(scale):
                            put(buf, cx + col * scale + sx,
                                y + row * scale + sy, r, g, b)
        cx += 6 * scale


def draw_text_centre(buf, cx, y, text, scale, color):
    draw_text(buf, cx - text_width(text, scale) // 2, y, text, scale, color)


# ---------------------------------------------------------------------------
# PNG encoder (zlib only; filter 0 on every scanline).
# ---------------------------------------------------------------------------

def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, buf):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: none
        raw += buf[y * W * 3:(y + 1) * W * 3]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)
    return len(png)

# ---------------------------------------------------------------------------
# The scene.
# ---------------------------------------------------------------------------

# Palette: matte light-grey studio, brushed silver, deep-teal label.
TEAL = (13, 79, 74)
TEAL_DARK = (9, 58, 54)
TEAL_LIGHT = (24, 105, 99)
SILVER = (198, 203, 207)
WHITE = (255, 255, 255)
INK = (38, 44, 48)
FLOOR_Y = 800

# The can: hero, slightly left of centre so the glass fits on the right.
CAN_X0, CAN_X1 = 270, 570
CAN_TOP, CAN_BOT = 225, 800
CAN_CX = (CAN_X0 + CAN_X1) // 2
CAN_RX = (CAN_X1 - CAN_X0) // 2
LABEL_Y0, LABEL_Y1 = 400, 650

# The glass: the one accessory, right of the can.
GLASS_X0, GLASS_X1 = 665, 795
GLASS_TOP, GLASS_BOT = 610, 800
GLASS_CX = (GLASS_X0 + GLASS_X1) // 2
WATER_Y = 655


def cylinder_light(t):
    """Brightness factor across a cylinder's width, t in 0..1.

    Dark rolled edges, bright body, one hard key-light band left of
    centre (the softbox), a faint secondary bounce on the right.
    """
    body = 0.62 + 0.38 * math.sin(math.pi * t) ** 0.9
    key = 0.34 * math.exp(-((t - 0.30) ** 2) / (2 * 0.055 ** 2))
    bounce = 0.10 * math.exp(-((t - 0.86) ** 2) / (2 * 0.07 ** 2))
    return min(1.25, body + key + bounce)


def shade(color, f):
    return (min(255, int(color[0] * f)),
            min(255, int(color[1] * f)),
            min(255, int(color[2] * f)))


def draw_backdrop(buf):
    """Seamless studio sweep: light top, slightly darker floor, a soft
    key light from the top left and a gentle fall-off at the edges."""
    for y in range(H):
        v = y / (H - 1)  # 0 top -> 1 bottom
        # Vertical sweep: bright at the top, dimmer toward the floor.
        base = 236 - 26 * v
        if y > FLOOR_Y:
            base -= 6.0 * min(1.0, (y - FLOOR_Y) / 120.0)
        for x in range(W):
            dx = (x - 300) / 520.0
            dy = (y - 170) / 520.0
            key = 16.0 * math.exp(-(dx * dx + dy * dy))
            # Mild vignette so the product sits in the light.
            ex = (x - W / 2) / (W / 2)
            ey = (y - H / 2) / (H / 2)
            vig = 10.0 * (ex * ex + ey * ey)
            val = int(max(0, min(255, base + key - vig)))
            put(buf, x, y, val, val, val + 2)


def soft_shadow(buf, cx, cy, rx, ry, strength=110):
    """A soft contact shadow: stacked ellipses, darker toward the middle."""
    for k in range(5, 0, -1):
        a = int(strength * (6 - k) / 14.0)
        fill_ellipse(buf, cx, cy, int(rx * k / 5.0), int(ry * k / 5.0),
                     (52, 52, 54), alpha=a)


def draw_can(buf):
    """Brushed-silver tin can with a lid, a rim and a teal label."""
    # Body: per-column metallic shading.
    for x in range(CAN_X0, CAN_X1 + 1):
        t = (x - CAN_X0) / (CAN_X1 - CAN_X0)
        f = cylinder_light(t)
        col = shade(SILVER, f)
        for y in range(CAN_TOP, CAN_BOT):
            put(buf, x, y, *col)
    # Faint vertical brushing: a few hairline streaks, darker and lighter.
    for k, sx in enumerate(range(CAN_X0 + 8, CAN_X1 - 4, 17)):
        tone = 118 if k % 2 == 0 else 138
        for y in range(CAN_TOP + 34, CAN_BOT - 30):
            blend(buf, sx, y, tone, tone, tone + 4, 26)
    # Top lid: silver ellipse, rolled rim, inner lid, pull tab.
    fill_ellipse(buf, CAN_CX, CAN_TOP, CAN_RX, 30, shade(SILVER, 0.82))
    ellipse_outline(buf, CAN_CX, CAN_TOP, CAN_RX - 2, 28,
                    (120, 126, 130), alpha=200, thick=2)
    fill_ellipse(buf, CAN_CX, CAN_TOP, CAN_RX - 16, 21, shade(SILVER, 1.08))
    fill_ellipse(buf, CAN_CX, CAN_TOP - 2, 8, 5, (150, 156, 160))
    fill_rect(buf, CAN_CX - 26, CAN_TOP - 7, CAN_CX + 26, CAN_TOP - 1,
              (158, 164, 168))
    fill_rect(buf, CAN_CX - 26, CAN_TOP - 7, CAN_CX - 20, CAN_TOP - 1,
              (120, 126, 130))
    # Bottom rim: a darker curve where the can meets the floor.
    fill_ellipse(buf, CAN_CX, CAN_BOT, CAN_RX, 26, shade(SILVER, 0.42))
    fill_ellipse(buf, CAN_CX, CAN_BOT - 4, CAN_RX - 6, 22,
                 shade(SILVER, 0.62))

    # ---- Label: deep teal band, shaded like the cylinder. ----
    for x in range(CAN_X0, CAN_X1 + 1):
        t = (x - CAN_X0) / (CAN_X1 - CAN_X0)
        f = 0.72 + 0.38 * math.sin(math.pi * t) ** 0.9
        f += 0.22 * math.exp(-((t - 0.30) ** 2) / (2 * 0.055 ** 2))
        col = shade(TEAL, min(1.2, f))
        for y in range(LABEL_Y0, LABEL_Y1):
            put(buf, x, y, *col)
    # Pinstripes framing the label.
    for y in (LABEL_Y0 + 4, LABEL_Y1 - 5):
        for x in range(CAN_X0 + 2, CAN_X1 - 1):
            put(buf, x, y, 214, 226, 222)
    # The joke, on the label itself - no caption anywhere else.
    draw_text_centre(buf, CAN_CX, LABEL_Y0 + 26, "DEHYDRATED", 4, WHITE)
    draw_text_centre(buf, CAN_CX, LABEL_Y0 + 62, "WATER", 6, WHITE)
    for x in range(CAN_X0 + 34, CAN_X1 - 33):
        put(buf, x, LABEL_Y0 + 122, 190, 214, 210)
    draw_text_centre(buf, CAN_CX, LABEL_Y0 + 134, "JUST ADD WATER", 3, WHITE)
    draw_text_centre(buf, CAN_CX, LABEL_Y0 + 168, "NET WT 0 G", 2, WHITE)
    draw_text_centre(buf, CAN_CX, LABEL_Y0 + 190, "INGREDIENTS: WATER", 2,
                     WHITE)
    draw_text_centre(buf, CAN_CX, LABEL_Y0 + 208, "(REMOVED)", 2, WHITE)
    # Small print on the bare metal, above and below the label.
    draw_text_centre(buf, CAN_CX, 330, "100% NOTHING INSIDE", 2, INK)
    draw_text_centre(buf, CAN_CX, 692, "SERVES 0", 2, INK)
    draw_text_centre(buf, CAN_CX, 712, "SHAKE WELL", 2, INK)


def draw_glass(buf):
    """One accessory: a small glass of water, standing beside the can."""
    top_w = (GLASS_X1 - GLASS_X0) // 2
    bot_w = 56
    # Glass body: faint translucent sides, slightly tapered.
    for y in range(GLASS_TOP, GLASS_BOT):
        v = (y - GLASS_TOP) / (GLASS_BOT - GLASS_TOP)
        hw = int(top_w + (bot_w - top_w) * v)
        for x in range(GLASS_CX - hw, GLASS_CX + hw + 1):
            blend(buf, x, y, 226, 234, 236, 46)
    # The water inside: pale blue, up to the water line.
    for y in range(WATER_Y, GLASS_BOT - 6):
        v = (y - GLASS_TOP) / (GLASS_BOT - GLASS_TOP)
        hw = int(top_w + (bot_w - top_w) * v) - 4
        for x in range(GLASS_CX - hw, GLASS_CX + hw + 1):
            blend(buf, x, y, 138, 196, 214, 118)
    # Water surface: a bright meniscus line, slightly curved.
    fill_ellipse(buf, GLASS_CX, WATER_Y, top_w - 8, 7, (196, 228, 238),
                 alpha=200)
    # Glass walls and rim, drawn as thin outlines.
    for y in range(GLASS_TOP, GLASS_BOT):
        v = (y - GLASS_TOP) / (GLASS_BOT - GLASS_TOP)
        hw = int(top_w + (bot_w - top_w) * v)
        blend(buf, GLASS_CX - hw, y, 120, 132, 136, 170)
        blend(buf, GLASS_CX + hw, y, 120, 132, 136, 170)
    ellipse_outline(buf, GLASS_CX, GLASS_TOP, top_w, 9,
                    (150, 164, 168), alpha=220, thick=2)
    fill_ellipse(buf, GLASS_CX, GLASS_BOT, bot_w + 2, 8, (168, 174, 178),
                 alpha=210)
    # A hard vertical highlight: the glass catching the key light.
    for y in range(GLASS_TOP + 14, WATER_Y + 40):
        for dx in range(5):
            blend(buf, GLASS_CX - top_w + 14 + dx, y, 255, 255, 255,
                  120 - dx * 18)


def render():
    buf = new_canvas()
    draw_backdrop(buf)
    soft_shadow(buf, CAN_CX, FLOOR_Y + 6, 215, 26, strength=155)
    soft_shadow(buf, GLASS_CX, FLOOR_Y + 6, 96, 15, strength=125)
    draw_can(buf)
    draw_glass(buf)
    return buf


def main():
    buf = render()
    try:
        os.makedirs("/output", exist_ok=True)
        path = OUT
    except OSError:
        os.makedirs("output", exist_ok=True)
        path = os.path.join("output", "entry.png")
    size = write_png(path, buf)
    print(f"wrote {path}: {W}x{H}, {size} bytes")


if __name__ == "__main__":
    main()
