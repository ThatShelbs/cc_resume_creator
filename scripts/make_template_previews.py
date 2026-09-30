"""
Render the three resume templates with the fictional demo persona and save
the top of page one as PNG thumbnails for the template picker
(webapp/frontend/public/templates/<key>.png). Needs Microsoft Word (for the
PDF) plus pypdfium2 and Pillow (requirements-dev.txt). Re-run after changing
TEMPLATES in generate_resume.py.
"""

import copy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))

import pypdfium2 as pdfium  # noqa: E402

import generate_resume as g  # noqa: E402
from demo_data import DEMO_RESULT  # noqa: E402

OUT = ROOT / "webapp" / "frontend" / "public" / "templates"
WIDTH = 640  # px; the picker shows these at ~300px, so this stays crisp on HiDPI
CROP = 0.62  # keep the top of the page, where the templates differ most


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for key in g.TEMPLATES:
            result = copy.deepcopy(DEMO_RESULT)
            docx_path = Path(tmp) / f"{key}.docx"
            pdf_path = Path(tmp) / f"{key}.pdf"
            g.build_docx(g.result_to_docx_data(result), docx_path, key)
            g.convert_to_pdf(docx_path, pdf_path)
            pdf = pdfium.PdfDocument(str(pdf_path))
            try:
                page = pdf[0]
                image = page.render(scale=WIDTH / page.get_width()).to_pil()
            finally:
                pdf.close()  # Windows won't delete a file pdfium still has open
            image = image.crop((0, 0, image.width, int(image.height * CROP)))
            image.save(OUT / f"{key}.png", optimize=True)
            print(f"Wrote {(OUT / f'{key}.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
