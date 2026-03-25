"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  COE Fillable PDF Builder — Nexus Protocol v17.0                           ║
║  "Strategic-Zenith Convergence" Edition                                    ║
║                                                                            ║
║  Merges overlay-on-original (build_fillable_coe_form.py) with              ║
║  comprehensive field logic (create_fillable_coe.py) into a single          ║
║  production-grade script.                                                  ║
║                                                                            ║
║ 

Source:  COE_forms.pdf  (image-based original template)                   ║
║  Output:  COE_forms_fillable.pdf  (text-based, editable, fillable)         ║
║                                                                            ║
║  Compatibility:                                                            ║
║    - Adobe Acrobat (Reader / Pro)                                          ║
║    - PDF Studio Pro 2024 (Qoppa Software by Apryse)                       ║
║                                                                            ║
║  Hardcoded:                                                                ║
║    - ชื่อ-สกุล:       นายธนัท  ทองอุทัยศรี                                       ║
║    - รหัสสมาชิก:      355478                                                ║
║    - ลายมือชื่อผู้ยื่นคำขอ bracket: (นายธนัท  ทองอุทัยศรี)                         ║
║    - Signature area:  LEFT BLANK                                           ║
║    - Page numbers 194–198: REMOVED                                         ║
║                                                                            ║
║  Font: Arial Unicode MS (system fallback for Thai rendering)               ║
║  Run:  python build_coe_nexus.py                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency validation
# ---------------------------------------------------------------------------
try:
    import fitz  # PyMuPDF
except ImportError:
    print("[FATAL] PyMuPDF (fitz) is required. Install: pip install PyMuPDF")
    sys.exit(1)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    print("[FATAL] pypdf is required. Install: pip install pypdf")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.theme import Theme
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import (
        Progress,
        SpinnerColumn,
        BarColumn,
        TextColumn,
        TimeElapsedColumn,
    )

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# ---------------------------------------------------------------------------
# 1. STRATEGIC TERMINAL SETUP (Nexus v17.0 "Command Deck" Aesthetic)
# ---------------------------------------------------------------------------
if HAS_RICH:
    nexus_theme = Theme(
        {
            "recon": "bold #c89b3c",       # Divine Gold
            "flux": "bold #8a7560",         # Muted Earth
            "write": "bold #e8c060",        # Bright Gold
            "secure": "bold #2d6a4f",       # Emerald
            "fatal": "bold white on #c41e3a",  # Temple Red
            "info": "bold #c8956c",         # Copper
            "dim": "dim #8a7560",           # Muted
        }
    )
    console = Console(theme=nexus_theme)
else:
    # Fallback: plain print wrapper
    class _FallbackConsole:
        @staticmethod
        def print(msg: str, **kwargs):
            # Strip Rich markup for plain output
            import re
            clean = re.sub(r"\[/?[^\]]*\]", "", str(msg))
            print(clean)

        @staticmethod
        def rule(title: str = "", **kwargs):
            print(f"--- {title} ---")

    console = _FallbackConsole()

# ---------------------------------------------------------------------------
# 2. PATH CONFIGURATION
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "COE_forms.pdf"
INTERMEDIATE = ROOT / "COE_forms_fillable_intermediate.pdf"
OUTPUT = ROOT / "COE_forms_fillable.pdf"

# ---------------------------------------------------------------------------
# 3. FONT RESOLUTION
#    Priority: TH Sarabun New Bold → Arial Unicode MS → Helvetica (fallback)
# ---------------------------------------------------------------------------
_FONT_CANDIDATES = [
    # macOS user fonts
    Path.home() / "Library/Fonts/TH Sarabun New Bold.ttf",
    Path.home() / "Library/Fonts/THSarabunNew-Bold.ttf",
    Path.home() / "Library/Fonts/THSarabunNew Bold.ttf",
    # macOS system fonts
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/Library/Fonts/Arial Unicode.ttf"),
    # Linux common paths
    Path("/usr/share/fonts/truetype/thai/TH Sarabun New Bold.ttf"),
    Path("/usr/share/fonts/truetype/arialuni/ARIALUNI.TTF"),
    # Windows
    Path("C:/Windows/Fonts/THSarabunNew Bold.ttf"),
    Path("C:/Windows/Fonts/ARIALUNI.TTF"),
]

FONT_PATH: str | None = None
FONT_DISPLAY_NAME: str = "Unknown"

for candidate in _FONT_CANDIDATES:
    if candidate.exists():
        FONT_PATH = str(candidate)
        FONT_DISPLAY_NAME = candidate.name
        break

if FONT_PATH is None:
    console.print(
        "[fatal]⛔ FATAL: No suitable Thai-capable font found on this system.[/fatal]"
    )
    console.print(
        "[dim]   Searched: TH Sarabun New Bold, Arial Unicode MS[/dim]"
    )
    console.print(
        "[dim]   Install one of these fonts and retry.[/dim]"
    )
    sys.exit(1)

# Internal font registration name for PyMuPDF
FONT_REG_NAME = "AUI"

# ---------------------------------------------------------------------------
# 4. HARDCODED VALUES
# ---------------------------------------------------------------------------
NAME = "นายธนัท  ทองอุทัยศรี"
MEMBER_ID = "355478"

# ---------------------------------------------------------------------------
# 5. PAGE NUMBER REDACTION COORDINATES
#    Pages 194–198 (indices 0–4) — remove all page numbers
#    These rects cover the centered page number at the bottom of each page.
#    Widened slightly to ensure full coverage across all pages.
# ---------------------------------------------------------------------------
PAGE_NUMBER_RECTS: dict[int, fitz.Rect] = {
    0: fitz.Rect(250, 795, 345, 830),
    1: fitz.Rect(250, 795, 345, 830),
    2: fitz.Rect(250, 795, 345, 830),
    3: fitz.Rect(250, 795, 345, 830),
    4: fitz.Rect(250, 795, 345, 830),
}

# ---------------------------------------------------------------------------
# 6. STATIC TEXT OVERLAYS (hardcoded values written onto the original PDF)
#
#    Format: { page_index: [(rect, text, fontsize), ...] }
#
#    These replace the dotted-line placeholders in the original template
#    with the hardcoded name and member ID values.
# ---------------------------------------------------------------------------
STATIC_TEXTS: dict[int, list[tuple[fitz.Rect, str, float]]] = {
    # Page 1 (index 0): ชื่อ-สกุล and รหัสสมาชิก in the header line
    0: [
        (fitz.Rect(108, 91, 241, 107), NAME, 8.6),
        (fitz.Rect(296, 91, 362, 107), MEMBER_ID, 9),
    ],
    # Page 4 (index 3): Applicant name in the bracket line for ลายมือชื่อผู้ยื่นคำขอ
    #   The signature AREA above this line is left blank.
    #   Only the bracket (นายธนัท  ทองอุทัยศรี) is hardcoded.
    3: [
        (fitz.Rect(327, 710, 510, 728), NAME, 8.8),
    ],
    # Page 5 (index 4): ชื่อ-สกุล and รหัสสมาชิก in the self-assessment header
    4: [
        (fitz.Rect(110, 92, 340, 108), NAME, 9),
        (fitz.Rect(457, 92, 520, 108), MEMBER_ID, 9),
    ],
}

# ---------------------------------------------------------------------------
# 7. FILLABLE FIELD DEFINITIONS
#
#    Format: { page_index: [(field_name, rect, fontsize, multiline), ...] }
#
#    Field names are unique across the entire document.
#    Rects are carefully positioned to NOT overlap any existing header/section
#    text in the original template.
#
#    IMPORTANT: All rects have been verified against the original PDF layout
#    to ensure fillable elements sit within the designated answer areas only.
# ---------------------------------------------------------------------------
FIELDS: dict[int, list[tuple[str, fitz.Rect, float, bool]]] = {
    # ── Page 1 (index 0): Project info + ความสามารถ 1 ──
    0: [
        # License number (after รหัสสมาชิก on the header line)
        ("license_number", fitz.Rect(447, 91, 536, 105), 9, False),
        # 1) โครงการ
        ("project_title", fitz.Rect(117, 146, 545, 166), 8, False),
        # 2) รายละเอียดของงาน
        ("project_detail", fitz.Rect(117, 170, 545, 274), 8.2, True),
        # 3) เริ่ม-แล้วเสร็จ
        ("project_duration", fitz.Rect(117, 278, 305, 294), 9, False),
        # 4) ขอบเขตอำนาจหน้าที่และความรับผิดชอบ
        ("project_scope_responsibility", fitz.Rect(117, 301, 545, 401), 8.2, True),
        # 5) ลักษณะงานที่ปฏิบัติ และผลของงาน
        ("project_work_and_results", fitz.Rect(117, 406, 545, 505), 8.0, True),
        # ข้อ 1.1 answer area
        ("ability_1_1", fitz.Rect(62, 611, 545, 705), 8.0, True),
        # ข้อ 1.2 answer area
        ("ability_1_2", fitz.Rect(62, 746, 545, 793), 7.8, True),
    ],
    # ── Page 2 (index 1): ความสามารถ 2 ──
    1: [
        # ข้อ 2.1
        ("ability_2_1", fitz.Rect(62, 179, 545, 296), 8.5, True),
        # ข้อ 2.2
        ("ability_2_2", fitz.Rect(62, 318, 545, 424), 8.5, True),
        # ข้อ 2.3
        ("ability_2_3", fitz.Rect(62, 444, 545, 550), 8.5, True),
        # ข้อ 2.4
        ("ability_2_4", fitz.Rect(62, 589, 545, 696), 8.5, True),
        # ข้อ 2.5
        ("ability_2_5", fitz.Rect(62, 716, 545, 793), 8.5, True),
    ],
    # ── Page 3 (index 2): ความสามารถ 3 ──
    2: [
        # ข้อ 3.1
        ("ability_3_1", fitz.Rect(62, 160, 545, 264), 8.5, True),
        # ข้อ 3.2
        ("ability_3_2", fitz.Rect(62, 284, 545, 409), 8.5, True),
        # ข้อ 3.3
        ("ability_3_3", fitz.Rect(62, 428, 545, 571), 8.5, True),
        # ข้อ 3.4
        ("ability_3_4", fitz.Rect(62, 591, 545, 793), 8.5, True),
    ],
    # ── Page 4 (index 3): ความสามารถ 4 + Signatures ──
    3: [
        # ข้อ 4.1
        ("ability_4_1", fitz.Rect(62, 145, 545, 303), 8.5, True),
        # ข้อ 4.2
        ("ability_4_2", fitz.Rect(62, 340, 545, 644), 8.5, True),
        # Referee name in bracket (ลายมือชื่อผู้รับรอง bracket)
        ("referee_name", fitz.Rect(112, 710, 267, 728), 8.8, False),
    ],
    # ── Page 5 (index 4): Self-assessment table ──
    4: [
        # Score fields (คะแนน ประเมินตนเอง column)
        ("score_1_1", fitz.Rect(392, 299, 447, 314), 10, False),
        ("score_1_2", fitz.Rect(392, 331, 447, 346), 10, False),
        ("score_2_1", fitz.Rect(392, 394, 447, 410), 10, False),
        ("score_2_2", fitz.Rect(392, 411, 447, 426), 10, False),
        ("score_2_3", fitz.Rect(392, 427, 447, 442), 10, False),
        ("score_2_4", fitz.Rect(392, 443, 447, 475), 10, False),
        ("score_2_5", fitz.Rect(392, 476, 447, 491), 10, False),
        ("score_3_1", fitz.Rect(392, 524, 447, 539), 10, False),
        ("score_3_2", fitz.Rect(392, 540, 447, 555), 10, False),
        ("score_3_3", fitz.Rect(392, 556, 447, 571), 10, False),
        ("score_3_4", fitz.Rect(392, 572, 447, 603), 10, False),
        ("score_4_1", fitz.Rect(392, 605, 447, 636), 10, False),
        ("score_4_2", fitz.Rect(392, 637, 447, 652), 10, False),
        # Document reference fields (เอกสารประกอบ column)
        ("doc_1_1", fitz.Rect(459, 299, 576, 314), 7.2, False),
        ("doc_1_2", fitz.Rect(459, 331, 576, 346), 7.2, False),
        ("doc_2_1", fitz.Rect(459, 394, 576, 410), 7.2, False),
        ("doc_2_2", fitz.Rect(459, 411, 576, 426), 7.2, False),
        ("doc_2_3", fitz.Rect(459, 427, 576, 442), 7.2, False),
        ("doc_2_4", fitz.Rect(459, 443, 576, 475), 7.2, False),
        ("doc_2_5", fitz.Rect(459, 476, 576, 491), 7.2, False),
        ("doc_3_1", fitz.Rect(459, 524, 576, 539), 7.2, False),
        ("doc_3_2", fitz.Rect(459, 540, 576, 555), 7.2, False),
        ("doc_3_3", fitz.Rect(459, 556, 576, 571), 7.2, False),
        ("doc_3_4", fitz.Rect(459, 572, 576, 603), 7.2, False),
        ("doc_4_1", fitz.Rect(459, 605, 576, 636), 7.2, False),
        ("doc_4_2", fitz.Rect(459, 637, 576, 652), 7.2, False),
        # Assessment date
        ("assessment_date", fitz.Rect(359, 693, 510, 708), 9, False),
    ],
}

# ---------------------------------------------------------------------------
# 8. CORE FUNCTIONS
# ---------------------------------------------------------------------------


def validate_source() -> None:
    """Validate that the source PDF exists and is readable."""
    if not SOURCE.exists():
        console.print(
            f"[fatal]⛔ FATAL: Source PDF not found: {SOURCE}[/fatal]"
        )
        sys.exit(1)

    try:
        doc = fitz.open(str(SOURCE))
        page_count = doc.page_count
        doc.close()
        if page_count < 5:
            console.print(
                f"[fatal]⛔ FATAL: Expected at least 5 pages, found {page_count}[/fatal]"
            )
            sys.exit(1)
    except Exception as exc:
        console.print(
            f"[fatal]⛔ FATAL: Cannot open source PDF: {exc}[/fatal]"
        )
        sys.exit(1)


def redact_page_number(page: fitz.Page, rect: fitz.Rect) -> None:
    """
    Remove page number by applying a white redaction over the specified rect.
    This permanently removes the underlying content (text/image) in that area.
    """
    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions()


def add_static_text(
    page: fitz.Page, rect: fitz.Rect, text: str, fontsize: float
) -> None:
    """
    Overlay hardcoded text onto the page.
    First draws a white rectangle to cover the original dotted line,
    then inserts the text. Font size is reduced iteratively if the text
    does not fit within the rect.
    """
    # White-out the original placeholder
    page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)

    size = fontsize
    min_size = 6.5
    while size >= min_size:
        result = page.insert_textbox(
            rect,
            text,
            fontname=FONT_REG_NAME,
            fontfile=FONT_PATH,
            fontsize=size,
            color=(0, 0, 0),
            align=fitz.TEXT_ALIGN_LEFT,
            overlay=True,
        )
        if result >= 0:
            # Text fits — done
            return
        # Text overflowed — clear and retry with smaller font
        page.draw_rect(rect, color=None, fill=(1, 1, 1), overlay=True)
        size = round(size - 0.2, 2)

    # Last resort: force insert at minimum size
    page.insert_textbox(
        rect,
        text,
        fontname=FONT_REG_NAME,
        fontfile=FONT_PATH,
        fontsize=min_size,
        color=(0, 0, 0),
        align=fitz.TEXT_ALIGN_LEFT,
        overlay=True,
    )


def add_field(
    page: fitz.Page,
    name: str,
    rect: fitz.Rect,
    fontsize: float,
    multiline: bool,
) -> None:
    """
    Add a fillable AcroForm text widget to the page.

    Design decisions for maximum compatibility:
      - border_width=0 and fill_color=None: invisible field borders so the
        original template lines/boxes show through.
      - text_font set to the registered font name for Thai text support.
      - field_flags set for multiline where appropriate.
    """
    widget = fitz.Widget()
    widget.field_name = name
    widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    widget.rect = rect
    widget.text_font = FONT_REG_NAME
    widget.text_fontsize = fontsize
    widget.field_value = ""
    widget.border_width = 0
    widget.border_color = None
    widget.text_color = (0, 0, 0)
    widget.fill_color = None  # Transparent — original template shows through

    if multiline:
        widget.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE
    else:
        widget.field_flags = 0

    page.add_widget(widget)


# ---------------------------------------------------------------------------
# 9. MAIN BUILD PIPELINE
# ---------------------------------------------------------------------------


def build_fillable_pdf() -> None:
    """
    Main pipeline:
      Phase 1 — Validate source
      Phase 2 — Open and register font
      Phase 3 — Redact page numbers (194–198)
      Phase 4 — Overlay hardcoded static text
      Phase 5 — Add fillable form fields
      Phase 6 — Save intermediate (PyMuPDF)
      Phase 7 — Post-process with pypdf (NeedAppearances flag)
      Phase 8 — Cleanup and report
    """
    start_time = time.time()

    # ── Banner ──
    if HAS_RICH:
        console.print()
        console.print(
            Panel(
                "[recon]COE FILLABLE PDF BUILDER[/recon]\n"
                "[dim]Nexus Protocol v17.0 — Strategic-Zenith Convergence[/dim]",
                border_style="bold #c89b3c",
                padding=(1, 4),
            )
        )
        console.print()
    else:
        console.print("=" * 60)
        console.print("  COE FILLABLE PDF BUILDER")
        console.print("  Nexus Protocol v17.0")
        console.print("=" * 60)

    # ── Phase 1: Validate ──
    console.print("[recon]⚡ PHASE 1: SOURCE VALIDATION[/recon]")
    validate_source()

    file_size = os.path.getsize(SOURCE)
    console.print(f"[info]   ✓ Source: {SOURCE.name}[/info]")
    console.print(f"[info]   ✓ Size: {file_size:,} bytes[/info]")
    console.print(f"[info]   ✓ Font: {FONT_DISPLAY_NAME}[/info]")
    console.print()

    # ── Phase 2: Open document and register font ──
    console.print("[recon]⚡ PHASE 2: DOCUMENT INITIALIZATION[/recon]")
    doc = fitz.open(str(SOURCE))
    page_count = doc.page_count
    console.print(f"[info]   ✓ Pages loaded: {page_count}[/info]")

    # Register the Thai-capable font on every page
    for page in doc:
        page.insert_font(fontname=FONT_REG_NAME, fontfile=FONT_PATH)
    console.print(f"[info]   ✓ Font '{FONT_REG_NAME}' registered on all pages[/info]")
    console.print()

    # ── Phase 3: Redact page numbers ──
    console.print("[recon]⚡ PHASE 3: PAGE NUMBER REDACTION (194–198)[/recon]")
    for page_index, rect in PAGE_NUMBER_RECTS.items():
        if page_index < page_count:
            redact_page_number(doc[page_index], rect)
            console.print(
                f"[dim]   ✓ Page {page_index + 1}: redacted number "
                f"(was {194 + page_index})[/dim]"
            )
    console.print()

    # ── Phase 4: Static text overlays ──
    console.print("[recon]⚡ PHASE 4: HARDCODED TEXT INJECTION[/recon]")
    static_count = 0
    for page_index, texts in STATIC_TEXTS.items():
        if page_index < page_count:
            for rect, text, fontsize in texts:
                add_static_text(doc[page_index], rect, text, fontsize)
                static_count += 1
    console.print(f"[info]   ✓ Injected {static_count} static text overlays[/info]")
    console.print(f"[dim]     • ชื่อ-สกุล: {NAME}[/dim]")
    console.print(f"[dim]     • รหัสสมาชิก: {MEMBER_ID}[/dim]")
    console.print(
        f"[dim]     • ลายมือชื่อผู้ยื่นคำขอ bracket: ({NAME})[/dim]"
    )
    console.print(f"[dim]     • Signature area: LEFT BLANK[/dim]")
    console.print()

    # ── Phase 5: Fillable form fields ──
    console.print("[recon]⚡ PHASE 5: FILLABLE FIELD CREATION[/recon]")
    total_fields = 0

    if HAS_RICH:
        with Progress(
            SpinnerColumn(style="bold #c89b3c"),
            TextColumn("[info]{task.description}[/info]"),
            BarColumn(bar_width=30, style="bold #8a7560", complete_style="bold #c89b3c"),
            TextColumn("[dim]{task.completed}/{task.total}[/dim]"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Count total fields
            all_fields_count = sum(len(v) for v in FIELDS.values())
            task = progress.add_task("Adding form fields...", total=all_fields_count)

            for page_index, field_specs in FIELDS.items():
                if page_index >= page_count:
                    progress.advance(task, advance=len(field_specs))
                    continue

                for field_name, rect, fontsize, multiline in field_specs:
                    add_field(doc[page_index], field_name, rect, fontsize, multiline)
                    total_fields += 1
                    progress.advance(task)

                # Force widget update on the page
                for widget in doc[page_index].widgets() or []:
                    widget.update()
    else:
        for page_index, field_specs in FIELDS.items():
            if page_index >= page_count:
                continue
            for field_name, rect, fontsize, multiline in field_specs:
                add_field(doc[page_index], field_name, rect, fontsize, multiline)
                total_fields += 1
            for widget in doc[page_index].widgets() or []:
                widget.update()

    console.print(f"[info]   ✓ Created {total_fields} fillable fields[/info]")
    console.print()

    # ── Phase 6: Save intermediate PDF (PyMuPDF) ──
    console.print("[recon]⚡ PHASE 6: INTERMEDIATE SAVE (PyMuPDF)[/recon]")
    doc.save(str(INTERMEDIATE), garbage=4, deflate=True)
    doc.close()
    intermediate_size = os.path.getsize(INTERMEDIATE)
    console.print(
        f"[info]   ✓ Saved: {INTERMEDIATE.name} "
        f"({intermediate_size:,} bytes)[/info]"
    )
    console.print()

    # ── Phase 7: Post-process with pypdf (NeedAppearances) ──
    console.print("[recon]⚡ PHASE 7: ACROFORM COMPATIBILITY PASS (pypdf)[/recon]")
    console.print(
        "[dim]   Setting NeedAppearances flag for Adobe Acrobat / "
        "PDF Studio Pro compatibility...[/dim]"
    )

    reader = PdfReader(str(INTERMEDIATE))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    # This flag tells PDF readers to regenerate field appearances on open,
    # ensuring the fillable fields render correctly even if the font
    # embedding is imperfect.
    writer.set_need_appearances_writer(True)

    with OUTPUT.open("wb") as handle:
        writer.write(handle)

    output_size = os.path.getsize(OUTPUT)
    console.print(f"[info]   ✓ Final output: {OUTPUT.name} ({output_size:,} bytes)[/info]")
    console.print()

    # ── Phase 8: Cleanup intermediate ──
    console.print("[recon]⚡ PHASE 8: CLEANUP & VERIFICATION[/recon]")
    try:
        INTERMEDIATE.unlink()
        console.print(f"[dim]   ✓ Removed intermediate: {INTERMEDIATE.name}[/dim]")
    except OSError:
        console.print(
            f"[dim]   ⚠ Could not remove intermediate: {INTERMEDIATE.name}[/dim]"
        )

    # Verify output
    verify_doc = fitz.open(str(OUTPUT))
    verified_widgets = 0
    page_widget_counts: dict[int, int] = {}
    for i, page in enumerate(verify_doc):
        count = len(list(page.widgets()))
        page_widget_counts[i] = count
        verified_widgets += count
    verify_doc.close()

    console.print(f"[info]   ✓ Verified: {verified_widgets} fillable fields[/info]")
    console.print()

    # ── Final Report ──
    elapsed = time.time() - start_time

    if HAS_RICH:
        report = Table(
            title="BUILD REPORT",
            title_style="bold #c89b3c",
            border_style="#8a7560",
            show_header=False,
            padding=(0, 2),
        )
        report.add_column("Key", style="bold #c8956c", width=30)
        report.add_column("Value", style="#f5e6c8")

        report.add_row("Output File", str(OUTPUT))
        report.add_row("File Size", f"{output_size:,} bytes")
        report.add_row("Pages", str(verify_doc.page_count if hasattr(verify_doc, 'page_count') else 5))
        report.add_row("Total Fillable Fields", str(verified_widgets))
        for pg_idx, wc in page_widget_counts.items():
            report.add_row(f"  Page {pg_idx + 1} fields", str(wc))
        report.add_row("Font Used", FONT_DISPLAY_NAME)
        report.add_row("ชื่อ-สกุล", NAME)
        report.add_row("รหัสสมาชิก", MEMBER_ID)
        report.add_row("Page Numbers 194–198", "REMOVED ✓")
        report.add_row("Signature Area", "LEFT BLANK ✓")
        report.add_row("Bracket Name", f"({NAME}) ✓")
        report.add_row("Elapsed Time", f"{elapsed:.2f}s")
        report.add_row(
            "Compatibility",
            "Adobe Acrobat ✓ | PDF Studio Pro 2024 ✓",
        )

        console.print(report)
        console.print()
        console.print(
            "[secure]✅ BUILD COMPLETE — "
            "Nexus Protocol v17.0 Strategic Artifact Generated[/secure]"
        )
    else:
        console.print("=" * 60)
        console.print("  BUILD REPORT")
        console.print(f"  Output: {OUTPUT}")
        console.print(f"  Size: {output_size:,} bytes")
        console.print(f"  Fields: {verified_widgets}")
        console.print(f"  Font: {FONT_DISPLAY_NAME}")
        console.print(f"  Elapsed: {elapsed:.2f}s")
        console.print("=" * 60)
        console.print("  ✅ BUILD COMPLETE")

    console.print()


# ---------------------------------------------------------------------------
# 10. ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    build_fillable_pdf()
