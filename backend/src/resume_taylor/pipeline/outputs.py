"""Writing a finished run: archiving superseded outputs, then the .docx/.pdf files and
the tailoring report."""

import re
import shutil
from datetime import datetime
from pathlib import Path

from ..config import ARCHIVE_DIR, CREATE_DIR, EFFORT, MODEL
from ..layout import REPO_ROOT
from .render.docx_builder import build_cover_letter_docx, build_docx
from .render.pdf import convert_to_pdf, count_pdf_pages
from .report import write_report
from .result import result_bullets_by_company, result_citations, result_to_docx_data
from .runtime import WARNINGS, stage, warn


def slugify_name(first: str, last: str) -> str:
    def clean(part: str) -> str:
        part = part.strip().lower()
        part = re.sub(r"[^a-z0-9]+", "-", part)
        return part.strip("-")

    return f"{clean(first)}-{clean(last)}"


OUTPUT_PREFIXES = ("out_resume_", "out_cover_letter_")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def archive_existing_outputs(create_dir: Path | None = None, archive_dir: Path | None = None) -> None:
    create_dir = create_dir or CREATE_DIR
    archive_dir = archive_dir or ARCHIVE_DIR
    archive_dir.mkdir(parents=True, exist_ok=True)
    create_dir.mkdir(parents=True, exist_ok=True)

    archive_time = datetime.now().strftime("%H-%M-%S")
    for prefix in OUTPUT_PREFIXES:
        for docx_file in create_dir.glob(f"{prefix}*.docx"):
            archived_name = f"{docx_file.stem}-{archive_time}{docx_file.suffix}"
            shutil.move(str(docx_file), str(archive_dir / archived_name))
            print(f"Archived {docx_file.name} -> {archive_dir.name}/{archived_name}")

        for report_file in create_dir.glob(f"{prefix}*_report.md"):
            base = report_file.name[: -len("_report.md")]
            archived_name = f"{base}-{archive_time}_report.md"
            shutil.move(str(report_file), str(archive_dir / archived_name))
            print(f"Archived {report_file.name} -> {archive_dir.name}/{archived_name}")

        for pdf_file in create_dir.glob(f"{prefix}*.pdf"):
            pdf_file.unlink()
            print(f"Removed superseded {pdf_file.name} (only .docx versions are archived)")


def write_outputs(
    result: dict,
    out_dir: Path,
    archive_dir: Path | None,
    template: str,
    no_pdf: bool,
    fact_bank: dict | None = None,
) -> Path:
    """Archive whatever is in out_dir, then write the resume (and cover letter)
    .docx/.pdf plus the tailoring report. Returns the report path."""
    data = result_to_docx_data(result)
    today = datetime.now().strftime("%Y-%m-%d")
    slug = slugify_name(data["first_name"], data["last_name"])
    base_name = f"out_resume_{slug}_{today}"
    cl_base_name = f"out_cover_letter_{slug}_{today}"
    page_count = None

    archive_existing_outputs(out_dir, archive_dir)
    stage("rendering")
    outputs = [(base_name, lambda path: build_docx(data, path, template))]
    if result.get("cover_letter"):
        paragraphs = [p["text"] for p in result["cover_letter"]]
        outputs.append((cl_base_name, lambda path: build_cover_letter_docx(data, paragraphs, path, template)))
    for name, build in outputs:
        docx_path = out_dir / f"{name}.docx"
        pdf_path = out_dir / f"{name}.pdf"
        build(docx_path)
        print(f"Wrote {display_path(docx_path)}")
        if no_pdf:
            continue
        stage("pdf")
        try:
            convert_to_pdf(docx_path, pdf_path)
            print(f"Wrote {display_path(pdf_path)}")
        except Exception as exc:  # docx2pdf requires MS Word via COM automation
            warn(f"could not generate {pdf_path.name} ({exc}). The .docx was still created.")
            continue
        pages = count_pdf_pages(pdf_path)
        if name == base_name:
            page_count = pages
            print(f"Resume length: {pages} page(s)")
            if pages > 2:
                warn(f"the resume runs {pages} pages; consider cutting the weakest bullets.")
        elif pages > 1:
            warn(f"the cover letter runs {pages} pages; it should fit on one.")

    result["page_count"] = page_count
    result["template"] = template
    report_path = out_dir / f"{base_name}_report.md"
    coverage = result.get("coverage") or {}
    write_report(
        report_path,
        result.get("inputs") or {},
        result.get("model", MODEL),
        result.get("effort", EFFORT),
        WARNINGS,
        (coverage.get("covered", []), coverage.get("missing", [])),
        result_bullets_by_company(result),
        result_citations(result),
        fact_bank,
        result.get("draft", ""),
        cover_letter=[(p["text"], p.get("ids") or []) for p in result.get("cover_letter") or []] or None,
        page_count=page_count,
    )
    return report_path
