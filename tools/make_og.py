"""Regenerates site/assets/og.png (1200x630). Needs Pillow; run by hand, not in CI."""
import pathlib
from PIL import Image, ImageDraw, ImageFont
ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H = 1200, 630
im = Image.new("RGB", (W, H), "#0b0e14"); d = ImageDraw.Draw(im)
for r in range(420, 0, -6):  # soft glow
    a = int(40 * (1 - r / 420)); d.ellipse((150 - r, -60 - r, 150 + r, -60 + r), fill=(11 + a // 3, 14 + a // 2, 20 + a))
def font(size, w=800):
    for p in ["/usr/share/fonts/truetype/sand-box/google/Inter/Inter-VariableFont_opsz,wght.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try:
            f = ImageFont.truetype(p, size)
            try: f.set_variation_by_axes([size if size < 32 else 32, w])
            except Exception: pass
            return f
        except Exception: continue
    return ImageFont.load_default()
cx, cy = 1000, 315
for i, rr in enumerate((210, 150, 90)):
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline="#4d8dff", width=4 if i else 6)
d.pieslice((cx - 210, cy - 210, cx + 210, cy + 210), -90, -30, fill="#ffc53d")
d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill="#ffc53d")
d.rounded_rectangle((80, 92, 104, 116), 12, fill="#ffc53d")
d.text((122, 84), "Frontlineradar", font=font(36), fill="#e8edf5")
d.text((80, 190), "Ukraine war", font=font(84), fill="#e8edf5")
d.text((80, 290), "daily radar", font=font(84), fill="#ffc53d")
d.text((80, 420), "Headlines · ISW assessments · Drone & missile strike data", font=font(28, 500), fill="#8f9bb0")
d.text((80, 520), "frontlineradar.org", font=font(30, 700), fill="#4d8dff")
im.save(ROOT / "site/assets/og.png", optimize=True)
print("wrote site/assets/og.png")
