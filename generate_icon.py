"""Generate a DiskDuran app icon (icon.ico) using only standard library."""
import struct, zlib, io

def create_ico():
    sizes = [256, 48, 32, 16]
    images = []
    for s in sizes:
        images.append(create_png(s))

    # ICO header: reserved(2) + type(2) + count(2)
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for i, png_data in enumerate(images):
        s = sizes[i]
        w = 0 if s == 256 else s
        h = 0 if s == 256 else s
        entries += struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png_data), offset)
        offset += len(png_data)

    with open("icon.ico", "wb") as f:
        f.write(header + entries)
        for png_data in images:
            f.write(png_data)

def create_png(size):
    pixels = []
    cx, cy = size / 2, size / 2
    r_outer = size * 0.42
    r_inner = size * 0.12
    r_ring = size * 0.28

    for y in range(size):
        row = []
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist = (dx*dx + dy*dy) ** 0.5

            if dist <= r_inner:
                row.extend([220, 220, 225, 255])  # center hole - light gray
            elif dist <= r_inner + 1.5:
                row.extend([0, 122, 255, 255])  # inner ring - blue
            elif dist <= r_ring:
                t = (dist - r_inner) / (r_ring - r_inner)
                r = int(0 + t * 90)
                g = int(122 - t * 30)
                b = int(255 - t * 60)
                row.extend([r, g, b, 255])  # gradient blue to indigo
            elif dist <= r_ring + 1.5:
                row.extend([88, 86, 214, 255])  # mid ring - indigo
            elif dist <= r_outer:
                t = (dist - r_ring) / (r_outer - r_ring)
                r = int(88 - t * 40)
                g = int(86 + t * 100)
                b = int(214 - t * 20)
                row.extend([r, g, b, 255])  # gradient indigo to teal
            elif dist <= r_outer + 2:
                a = max(0, int(255 * (1 - (dist - r_outer) / 2)))
                row.extend([90, 180, 200, a])  # anti-aliased edge
            else:
                row.extend([0, 0, 0, 0])  # transparent
        pixels.append(bytes(row))

    return encode_png(size, size, pixels)

def encode_png(w, h, rows):
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    raw = b""
    for row in rows:
        raw += b"\x00" + row  # filter byte 0 (none)

    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    out += chunk(b"IDAT", zlib.compress(raw, 9))
    out += chunk(b"IEND", b"")
    return out

if __name__ == "__main__":
    create_ico()
    print("icon.ico generado")
