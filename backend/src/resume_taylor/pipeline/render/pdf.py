"""PDF export. Windows drives MS Word over COM; other platforms use docx2pdf."""

import sys
from pathlib import Path


def count_pdf_pages(path: Path) -> int:
    from pypdf import PdfReader

    return len(PdfReader(str(path)).pages)


def _convert_with_word(docx_path: Path, pdf_path: Path) -> None:
    """Export through Word's COM API directly. docx2pdf does the same, but it
    reuses any Word window you have open, prints progress bars, and treats
    Word dropping the COM link on Quit() (common, and harmless once the PDF
    exists) as a failure. A private DispatchEx instance avoids all three."""
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(docx_path.resolve()), ReadOnly=True, AddToRecentFiles=False)
        try:
            doc.ExportAsFixedFormat(str(pdf_path.resolve()), 17)  # 17 = wdExportFormatPDF
        finally:
            doc.Close(False)
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def convert_to_pdf(docx_path: Path, pdf_path: Path) -> None:
    if pdf_path.exists():
        pdf_path.unlink()
    if sys.platform == "win32":
        _convert_with_word(docx_path, pdf_path)
    else:
        from docx2pdf import convert

        convert(str(docx_path), str(pdf_path))
    if not pdf_path.exists():
        raise RuntimeError("Word finished without producing a PDF")
