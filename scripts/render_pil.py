import klayout.db as db
import struct
import zlib
import os

out_dir = "/workspace/screenshots"
gds_file = "/workspace/flow/runs/silicon_npu/results/final/gds/silicon_npu.gds"

print("Loading GDS...")
layout = db.Layout()
layout.read(gds_file)
cell = layout.top_cell()
assert cell, "No top cell"

bb = cell.bbox()
bw = bb.width()
bh = bb.height()
print(f"Die: {bw} x {bh} db units")

# Target image size
W, H = 1600, 1200
margin = 10
scale_x = (W - 2 * margin) / bw
scale_y = (H - 2 * margin) / bh
scale = min(scale_x, scale_y)
bl = bb.left
bt = bb.top

def tx(x):
    return int((x - bl) * scale + margin)

def ty(y):
    return int((bt - y) * scale + margin)

# White background
pixels = bytearray([255, 255, 255] * W * H)

def set_pixel(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        idx = (y * W + x) * 3
        if r < 255 or g < 255 or b < 255:
            pixels[idx] = min(pixels[idx], b) if b < 255 else pixels[idx]
            pixels[idx+1] = min(pixels[idx+1], g) if g < 255 else pixels[idx+1]
            pixels[idx+2] = min(pixels[idx+2], r) if r < 255 else pixels[idx+2]
            # Simple: just set it
            pixels[idx] = b
            pixels[idx+1] = g
            pixels[idx+2] = r

def fill_rect(x1, y1, x2, y2, r, g, b):
    x1c, x2c = max(0, min(x1, x2)), min(W - 1, max(x1, x2))
    y1c, y2c = max(0, min(y1, y2)), min(H - 1, max(y1, y2))
    for y in range(y1c, y2c + 1):
        row_start = (y * W + x1c) * 3
        row_end = (y * W + x2c + 1) * 3
        for x in range(x1c, x2c + 1):
            idx = (y * W + x) * 3
            pixels[idx] = b
            pixels[idx + 1] = g
            pixels[idx + 2] = r

# Sky130 GDS layer numbers
layer_colors = {
    # Diffusion
    (64, 20): (255, 100, 100),   # diff
    (64, 16): (220, 80, 80),     # diff draw
    # Nwell
    (65, 20): (200, 200, 240),   # nwell - light blue
    (65, 44): (200, 200, 240),
    (65, 5): (200, 200, 240),
    # Poly (red)
    (66, 20): (220, 40, 40),     # poly
    (66, 16): (200, 30, 30),     # poly draw
    (66, 44): (180, 20, 20),     # poly block
    # Nselect/Pselect
    (67, 20): (180, 255, 180),   # pselect - light green
    (67, 44): (180, 255, 180),
    (67, 16): (180, 255, 180),
    # Met1 (blue) - layer 68!
    (68, 20): (0, 80, 255),     # met1
    (68, 44): (0, 60, 220),     # met1 pin
    (68, 5): (0, 50, 200),      # met1 draw
    (68, 16): (0, 70, 240),     # met1
    # Met2 (cyan) - layer 69!
    (69, 20): (0, 200, 255),    # met2
    (69, 44): (0, 170, 230),    # met2 pin
    (69, 16): (0, 180, 240),    # met2 draw
    # Met3 (green) - layer 70!
    (70, 20): (0, 220, 100),    # met3
    (70, 44): (0, 190, 80),     # met3 pin
    (70, 16): (0, 200, 90),     # met3 draw
    # Met4 (orange) - layer 71!
    (71, 20): (255, 180, 0),    # met4
    (71, 44): (220, 150, 0),    # met4 pin
    (71, 16): (240, 165, 0),    # met4 draw
    # Met5 (magenta) - layer 72!
    (72, 20): (200, 0, 200),    # met5
    (72, 44): (170, 0, 170),    # met5 pin
    (72, 16): (185, 0, 185),    # met5 draw
    # Via1 - layer 235!
    (235, 20): (180, 180, 0),   # via1
    (235, 44): (180, 180, 0),
    (235, 4): (180, 180, 0),
    (235, 5): (180, 180, 0),
    # Via2 - layer 236!
    (236, 20): (0, 180, 180),   # via2
    (236, 44): (0, 180, 180),
    (236, 0): (0, 180, 180),
    # Via3 - layer 237!
    (237, 20): (180, 0, 180),   # via3
    (237, 44): (180, 0, 180),
    # Via4 - layer 238!
    (238, 20): (180, 100, 0),   # via4
    (238, 44): (180, 100, 0),
    # Implant
    (69, 20): (150, 200, 150),  # nimplant -- conflicts with met2, remove
    (70, 20): (150, 200, 150),  # pimplant -- conflicts with met3, remove
    # Deep wells
    (71, 20): (100, 100, 200),  # deep nwell -- conflicts with met4, remove
    # Die boundary
    (36, 20): (0, 0, 0),
    (36, 44): (0, 0, 0),
    (36, 5): (0, 0, 0),
    # Cell boundary
    (65, 20): (200, 200, 240),  # nwell (already mapped)
}

# Skip layers that fill the entire die with solid color
skip_layers = set()

# Also skip nselect (67) since it covers the whole die in green
# Keep nwell (65) but make it subtle
for layer_idx in layout.layer_indices():
    ln = layout.get_info(layer_idx)
    # Skip select layers that fill the entire die
    if ln.layer == 67:
        skip_layers.add(layer_idx)
    # Skip implant
    if ln.layer in [69, 70, 71, 72]:
        pass  # keep - these are metals!
    # Skip nselect 122
    if ln.layer == 122:
        skip_layers.add(layer_idx)
    # Skip well fill 78, 93, 94, 95
    if ln.layer in [78, 93, 94, 95]:
        skip_layers.add(layer_idx)

print("Rendering layers...")
total = 0
for layer_idx in layout.layer_indices():
    ln = layout.get_info(layer_idx)
    key = (ln.layer, ln.datatype)

    # Skip select/well fill layers that cover the entire die
    if layer_idx in skip_layers:
        continue

    color = layer_colors.get(key)
    if color is None:
        # For unknown layers, use a muted color only if small count
        color = (180, 180, 180)

    r, g, b = color

    count = 0
    iter = cell.begin_shapes_rec(layer_idx)
    while not iter.at_end():
        shape = iter.shape()
        if shape.is_box():
            box = shape.box
            x1, y1 = tx(box.left), ty(box.top)
            x2, y2 = tx(box.right), ty(box.bottom)
            fill_rect(x1, y1, x2, y2, r, g, b)
            count += 1
        elif shape.is_polygon():
            poly = shape.polygon
            points = []
            for p in poly.each_point_hull():
                points.append((tx(p.x), ty(p.y)))
            if len(points) >= 3:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                fill_rect(min(xs), min(ys), max(xs), max(ys), r, g, b)
                count += 1
        elif shape.is_path():
            path = shape.path
            pw = max(int(path.width * scale), 1)
            points = []
            for p in path.each_point():
                points.append((tx(p.x), ty(p.y)))
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                fill_rect(min(x1, x2) - pw, min(y1, y2) - pw,
                         max(x1, x2) + pw, max(y1, y2) + pw, r, g, b)
            count += 1
        iter.next()
    if count > 0:
        print(f"  Layer {ln.layer}/{ln.datatype}: {count} shapes")
    total += count

print(f"Total shapes rendered: {total}")

def save_png(filename, w, h, pixel_data):
    row_size = w * 3
    img_data = b""
    for y in range(h):
        img_data += b"\x00"
        row_start = y * row_size
        img_data += bytes(pixel_data[row_start:row_start + row_size])

    def make_chunk(ctype, data):
        c = ctype + data
        crc = zlib.crc32(c) & 0xffffffff
        return struct.pack(">I", len(data)) + c + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    compressed = zlib.compress(img_data, 6)

    with open(filename, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(make_chunk(b"IHDR", ihdr))
        f.write(make_chunk(b"IDAT", compressed))
        f.write(make_chunk(b"IEND", b""))

print("Saving screenshots...")
save_png(os.path.join(out_dir, "final_layout.png"), W, H, pixels)
print("Saved final_layout.png")

save_png(os.path.join(out_dir, "floorplan.png"), W, H, pixels)
print("Saved floorplan.png")

# Center crop - placement detail
cx, cy = W // 2, H // 2
zw, zh = W // 3, H // 3
crop = bytearray(zw * zh * 3)
for y in range(zh):
    for x in range(zw):
        sx = cx - zw // 2 + x
        sy = cy - zh // 2 + y
        if 0 <= sx < W and 0 <= sy < H:
            si = (sy * W + sx) * 3
            di = (y * zw + x) * 3
            crop[di:di+3] = pixels[si:si+3]
save_png(os.path.join(out_dir, "placement.png"), zw, zh, crop)
print("Saved placement.png")

# Corner crop - routing detail
crop2 = bytearray(zw * zh * 3)
for y in range(zh):
    for x in range(zw):
        sx = x
        sy = H - zh + y
        if 0 <= sx < W and 0 <= sy < H:
            si = (sy * W + sx) * 3
            di = (y * zw + x) * 3
            crop2[di:di+3] = pixels[si:si+3]
save_png(os.path.join(out_dir, "routing.png"), zw, zh, crop2)
print("Saved routing.png")

# CTS area
crop3 = bytearray(zw * zh * 3)
for y in range(zh):
    for x in range(zw):
        sx = cx - zw // 2 + x
        sy = H - zh + y
        if 0 <= sx < W and 0 <= sy < H:
            si = (sy * W + sx) * 3
            di = (y * zw + x) * 3
            crop3[di:di+3] = pixels[si:si+3]
save_png(os.path.join(out_dir, "cts.png"), zw, zh, crop3)
print("Saved cts.png")

print("All done!")
