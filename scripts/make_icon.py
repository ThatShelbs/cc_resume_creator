"""Draw the Resume Studio app icon (the same design as the web app's
favicon.svg) as a multi-size .ico for the desktop shortcut. Needs Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "webapp" / "assets" / "resume-studio.ico"
S = 256  # draw large, let the .ico writer downscale


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def main() -> None:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    # Indigo to violet diagonal gradient, clipped to a rounded square.
    grad = Image.new("RGBA", (S, S))
    px = grad.load()
    for y in range(S):
        for x in range(S):
            px[x, y] = lerp((99, 102, 241), (139, 92, 246), (x + y) / (2 * S)) + (255,)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=60, fill=255)
    img.paste(grad, (0, 0), mask)

    d = ImageDraw.Draw(img)
    u = S / 64  # favicon.svg units
    d.rounded_rectangle((17 * u, 12 * u, 47 * u, 52 * u), radius=4 * u, fill=(255, 255, 255, 245))
    d.rounded_rectangle((22 * u, 19 * u, 36 * u, 22 * u), radius=1.5 * u, fill=(99, 102, 241))
    for top, right in ((26, 42), (31, 42), (36, 35)):
        d.rounded_rectangle((22 * u, top * u, right * u, (top + 2.4) * u), radius=1.2 * u, fill=(199, 210, 254))
    sparkle = [(44.5, 38.5), (46.5, 42.8), (50.8, 44.8), (46.5, 46.8), (44.5, 51.1), (42.5, 46.8), (38.2, 44.8), (42.5, 42.8)]
    d.polygon([(x * u, y * u) for x, y in sparkle], fill=(251, 191, 36))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
