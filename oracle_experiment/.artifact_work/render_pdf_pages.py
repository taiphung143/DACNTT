from __future__ import annotations

import sys
from pathlib import Path

import fitz


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: render_pdf_pages.py INPUT.pdf OUTPUT_DIR")
    pdf_path = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf_path)
    matrix = fitz.Matrix(2.0, 2.0)
    for index, page in enumerate(document, start=1):
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        pixmap.save(output_dir / f"page-{index}.png")
    print(f"pages={document.page_count}")


if __name__ == "__main__":
    main()
