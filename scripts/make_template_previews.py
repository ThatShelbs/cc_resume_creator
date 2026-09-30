"""
Render the three resume templates with the fictional demo persona and save
the top of page one as PNG thumbnails for the template picker
(frontend/public/templates/<key>.png). Needs Microsoft Word (for the
PDF) plus pypdfium2 and Pillow (the backend[dev] extra). Re-run after changing
TEMPLATES in resume_taylor/pipeline/render/templates.py.
"""

import copy
import tempfile
from pathlib import Path

import pypdfium2 as pdfium

from resume_taylor.layout import FRONTEND_DIR, REPO_ROOT
from resume_taylor.pipeline.render.docx_builder import build_docx
from resume_taylor.pipeline.render.pdf import convert_to_pdf
from resume_taylor.pipeline.render.templates import TEMPLATES
from resume_taylor.pipeline.result import result_to_docx_data
from resume_taylor.sample_data.demo_data import DEMO_RESULT

OUT = FRONTEND_DIR / "public" / "templates"
WIDTH = 640  # px; the picker shows these at ~300px, so this stays crisp on HiDPI
CROP = 0.62  # keep the top of the page, where the templates differ most


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for key in TEMPLATES:
            result = copy.deepcopy(DEMO_RESULT)
            docx_path = Path(tmp) / f"{key}.docx"
            pdf_path = Path(tmp) / f"{key}.pdf"
            build_docx(result_to_docx_data(result), docx_path, key)
            convert_to_pdf(docx_path, pdf_path)
            pdf = pdfium.PdfDocument(str(pdf_path))
            try:
                page = pdf[0]
                image = page.render(scale=WIDTH / page.get_width()).to_pil()
            finally:
                pdf.close()  # Windows won't delete a file pdfium still has open
            image = image.crop((0, 0, image.width, int(image.height * CROP)))
            image.save(OUT / f"{key}.png", optimize=True)
            print(f"Wrote {(OUT / f'{key}.png').relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
