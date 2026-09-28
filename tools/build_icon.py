"""Generate the application icon files from one simple geometric design."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#176f80"/>
      <stop offset="1" stop-color="#102d49"/>
    </linearGradient>
  </defs>
  <rect x="24" y="24" width="464" height="464" rx="108" fill="url(#bg)"/>
  <circle cx="221" cy="220" r="123" fill="none" stroke="#f8fbfb" stroke-width="36"/>
  <path d="M311 311 397 397" fill="none" stroke="#f8fbfb" stroke-width="46" stroke-linecap="round"/>
  <path d="m221 154-94 48 94 48 94-48z" fill="#f4c766"/>
  <path d="M164 224v43c35 28 79 28 114 0v-43l-57 29z" fill="#e8af48"/>
  <path d="M315 204v73" fill="none" stroke="#f4c766" stroke-width="10" stroke-linecap="round"/>
  <circle cx="315" cy="279" r="11" fill="#f4c766"/>
</svg>
"""


def make_png() -> Image.Image:
    scale = 4
    size = 512 * scale
    mask = Image.new("L", (size, size))
    m = ImageDraw.Draw(mask)
    left, top, right, bottom, radius = (value * scale for value in (24, 24, 488, 488, 108))
    m.rectangle((left + radius, top, right - radius, bottom), fill=255)
    m.rectangle((left, top + radius, right, bottom - radius), fill=255)
    for x in (left, right - 2 * radius):
        for y in (top, bottom - 2 * radius):
            m.ellipse((x, y, x + 2 * radius, y + 2 * radius), fill=255)

    gradient = Image.new("RGBA", (size, size))
    pixels = gradient.load()
    for y in range(size):
        for x in range(size):
            t = min(1, (x + y) / (2 * size))
            pixels[x, y] = (
                round(23 + (16 - 23) * t),
                round(111 + (45 - 111) * t),
                round(128 + (73 - 128) * t),
                255,
            )
    image = Image.new("RGBA", (size, size))
    image.paste(gradient, (0, 0), mask)
    d = ImageDraw.Draw(image)

    def p(*coords):
        return tuple(round(value * scale) for value in coords)

    white = "#f8fbfb"
    gold = "#f4c766"
    d.ellipse(p(98, 97, 344, 343), outline=white, width=36 * scale)
    d.line([p(311, 311), p(397, 397)], fill=white, width=46 * scale, joint="curve")
    d.ellipse(p(374, 374, 420, 420), fill=white)
    d.polygon([p(221, 154), p(127, 202), p(221, 250), p(315, 202)], fill=gold)
    d.polygon([p(164, 224), p(221, 253), p(278, 224), p(278, 267), p(260, 279), p(240, 286), p(221, 288), p(202, 286), p(182, 279), p(164, 267)], fill="#e8af48")
    d.line([p(315, 204), p(315, 277)], fill=gold, width=10 * scale)
    d.ellipse(p(304, 268, 326, 290), fill=gold)
    return image.resize((512, 512), Image.LANCZOS)


def main() -> None:
    (ASSETS / "app-icon.svg").write_text(SVG, encoding="utf-8")
    image = make_png()
    image.save(ASSETS / "app-icon.png")
    image.save(
        ASSETS / "app-icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
