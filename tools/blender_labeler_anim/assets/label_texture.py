"""Generate a placeholder label texture PNG."""
import struct
import zlib
from pathlib import Path


def create_label_png(path, width=512, height=256):
    """Create a simple label texture with colored bands and text-like patterns."""
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            # White background
            r, g, b = 240, 240, 235

            # Top and bottom borders
            if y < 8 or y >= height - 8:
                r, g, b = 60, 100, 160
            # Left and right borders
            elif x < 8 or x >= width - 8:
                r, g, b = 60, 100, 160
            # Center band (simulates text area)
            elif height // 3 < y < 2 * height // 3:
                # Fake text lines
                line_y = (y - height // 3) % 20
                if line_y < 3 and 40 < x < width - 40:
                    r, g, b = 40, 40, 50
            # Top accent stripe
            elif 15 < y < 25:
                r, g, b = 200, 50, 50

            row.extend([r, g, b])
        pixels.append(bytes(row))

    # Write minimal PNG
    def write_png(path, width, height, rows):
        def chunk(chunk_type, data):
            c = chunk_type + data
            return (len(data)).to_bytes(4, 'big') + c + zlib.crc32(c).to_bytes(4, 'big')

        header = b'\x89PNG\r\n\x1a\n'
        ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
        raw = b''
        for row in rows:
            raw += b'\x00' + row  # filter byte 0 (none)

        with open(path, 'wb') as f:
            f.write(header)
            f.write(chunk(b'IHDR', ihdr))
            f.write(chunk(b'IDAT', zlib.compress(raw)))
            f.write(chunk(b'IEND', b''))

    write_png(path, width, height, pixels)
    print(f"Generated label texture: {path}")


if __name__ == '__main__':
    out = Path(__file__).parent / 'label_texture.png'
    create_label_png(str(out))
