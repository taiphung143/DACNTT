from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    pages = sorted(source.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
    scale = 0.35
    for start in range(0, len(pages), 4):
        chunk = pages[start : start + 4]
        first = Image.open(chunk[0]).convert("RGB")
        tile = (int(first.width * scale), int(first.height * scale))
        sheet = Image.new("RGB", (tile[0] * 2 + 60, tile[1] * 2 + 90), "#d8d8d8")
        draw = ImageDraw.Draw(sheet)
        for offset, path in enumerate(chunk):
            page = Image.open(path).convert("RGB")
            page.thumbnail(tile, Image.Resampling.LANCZOS)
            x = 20 + (offset % 2) * (tile[0] + 20)
            y = 35 + (offset // 2) * (tile[1] + 20)
            draw.text((x, y - 25), f"Page {path.stem.split('-')[-1]}", fill="black")
            sheet.paste(page, (x, y))
        end = start + len(chunk)
        sheet.save(output / f"contact-{start + 1:02d}-{end:02d}.png")


if __name__ == "__main__":
    main()
