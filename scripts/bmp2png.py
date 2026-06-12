import struct
import zlib
import os

def bmp_to_png(bmp_path, png_path):
    with open(bmp_path, "rb") as f:
        # Read BMP header
        sig = f.read(2)
        assert sig == b"BM"
        file_size = struct.unpack("<I", f.read(4))[0]
        f.read(4)  # reserved
        offset = struct.unpack("<I", f.read(4))[0]
        
        # DIB header
        dib_size = struct.unpack("<I", f.read(4))[0]
        w = struct.unpack("<i", f.read(4))[0]
        h = struct.unpack("<i", f.read(4))[0]
        planes = struct.unpack("<H", f.read(2))[0]
        bpp = struct.unpack("<H", f.read(2))[0]
        
        # Skip rest of DIB header
        f.read(dib_size - 16)
        
        # Read pixel data (BGR, bottom-up)
        row_size = w * 3
        padding = (4 - (row_size % 4)) % 4
        
        rows = []
        for y in range(abs(h)):
            row = f.read(row_size)
            f.read(padding)
            # Convert BGR to RGB
            rgb = bytearray()
            for i in range(0, len(row), 3):
                rgb.append(row[i+2])  # R
                rgb.append(row[i+1])  # G
                rgb.append(row[i])    # B
            rows.append(bytes(rgb))
        
        if h < 0:
            rows = rows[::-1]
        
        img_data = b""
        for row in rows:
            img_data += b"\x00" + row  # filter byte (None) + pixel data
        
        # PNG file
        def make_chunk(chunk_type, data):
            c = chunk_type + data
            crc = zlib.crc32(c) & 0xffffffff
            return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)
        
        ihdr = struct.pack(">IIBBBBB", w, abs(h), 8, 2, 0, 0, 0)
        compressed = zlib.compress(img_data)
        
        with open(png_path, "wb") as out:
            out.write(b"\x89PNG\r\n\x1a\n")
            out.write(make_chunk(b"IHDR", ihdr))
            out.write(make_chunk(b"IDAT", compressed))
            out.write(make_chunk(b"IEND", b""))

src = "/workspace/screenshots"
dst = "/workspace/screenshots"

for name in ["final_layout", "floorplan", "placement", "routing", "cts"]:
    bmp = os.path.join(src, f"{name}.bmp")
    png = os.path.join(dst, f"{name}.png")
    if os.path.exists(bmp):
        bmp_to_png(bmp, png)
        sz = os.path.getsize(png)
        print(f"Converted {name}.bmp -> {name}.png ({sz} bytes)")
