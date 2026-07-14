#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera semaforo.ico (ícone do executável) — só biblioteca padrão.

Desenha um semáforo com as três luzes acesas, em 16/32/48 px, e grava
no formato ICO (BMP de 32 bits com canal alfa embutido).
"""

import os
import struct

RED, YELLOW, GREEN = (224, 24, 24), (242, 182, 13), (23, 201, 58)
BODY, RIM = (24, 26, 28), (70, 74, 78)


def draw(size):
    """Matriz size x size de pixels RGBA (topo para baixo)."""
    px = [[(0, 0, 0, 0)] * size for _ in range(size)]
    x1, x2 = round(size * 0.30), round(size * 0.70)
    for y in range(size):
        for x in range(x1, x2):
            edge = y in (0, size - 1) or x in (x1, x2 - 1)
            px[y][x] = (RIM if edge else BODY) + (255,)
    r = max(2, round(size * 0.14))
    cx = size // 2
    for color, fy in ((RED, 0.19), (YELLOW, 0.5), (GREEN, 0.81)):
        cy = round(size * fy)
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r and 0 <= cy + dy < size:
                    px[cy + dy][cx + dx] = color + (255,)
    return px


def encode_bmp(px):
    """Codifica os pixels como BMP-em-ICO (BITMAPINFOHEADER + BGRA + máscara AND)."""
    size = len(px)
    xor_rows = b""
    for row in reversed(px):  # BMP é de baixo para cima
        xor_rows += b"".join(bytes((b, g, r, a)) for (r, g, b, a) in row)
    and_stride = ((size + 31) // 32) * 4
    and_rows = bytes(and_stride * size)  # alfa embutido; máscara zerada
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0,
                         len(xor_rows) + len(and_rows), 0, 0, 0, 0)
    return header + xor_rows + and_rows


def main():
    sizes = (16, 32, 48)
    images = [encode_bmp(draw(s)) for s in sizes]
    out = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    for size, img in zip(sizes, images):
        out += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32,
                           len(img), offset)
        offset += len(img)
    out += b"".join(images)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "semaforo.ico")
    with open(path, "wb") as fh:
        fh.write(out)
    print("gerado:", path, "(%d bytes)" % len(out))


if __name__ == "__main__":
    main()
