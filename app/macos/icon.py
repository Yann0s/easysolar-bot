"""Icône EasySolar : carré arrondi bleu Victron, soleil orange, panneau solaire blanc."""
import sys
from PIL import Image, ImageDraw

N = 1024
img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((100, 100, 924, 924), radius=185, fill=(0, 76, 151))
d.ellipse((560, 190, 800, 430), fill=(243, 146, 0))
panel = [(220, 820), (380, 470), (760, 470), (840, 820)]
d.polygon(panel, fill=(255, 255, 255))
blue = (0, 76, 151)
for i in range(1, 4):
    t = i / 4
    y = 470 + t * 350
    d.line([(380 - t * 160, y), (760 + t * 80, y)], fill=blue, width=14)
for i in range(1, 3):
    t = i / 3
    d.line([(380 + t * 380, 470), (220 + t * 620, 820)], fill=blue, width=14)
img.save(sys.argv[1])
