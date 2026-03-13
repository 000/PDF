from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, asdict
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageStat
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
WATERMARKED_ROOT = OUTPUT_DIR / "watermarked_pdfs"
CATALOG_DIR = OUTPUT_DIR / "catalog"
ASSET_DIR = OUTPUT_DIR / "assets"
EXCLUDED_TOP_LEVEL_DIRS = {"output", ".venv", ".git", "__pycache__", "scripts"}

FONT_REGULAR = Path("/System/Library/Fonts/Supplemental/Tahoma.ttf")
FONT_BOLD = Path("/System/Library/Fonts/Supplemental/Tahoma Bold.ttf")
WATERMARK_IMAGE_NAME = "watermark_recreated.png"
PREFERRED_WATERMARKS = (
    "watermarking_truecopy_March10th_transparent copy.png",
    WATERMARK_IMAGE_NAME,
)

ANALYSIS_RENDER_SCALE = 1.35
OCCUPANCY_THRESHOLD = 22
CLEAR_REGION_THRESHOLD = 0.003
ADAPTIVE_SCALE_FACTORS = (1.0, 0.92, 0.84)

DESCRIPTIONS_TH = {
    "NCSA_Submission_Cert/CCSKv5.pdf": (
        "ใบประกาศนียบัตรจาก Cloud Security Alliance ระบุการผ่านหลักสูตร "
        "Certificate of Cloud Security Knowledge (CCSK) v5 ของนายธนัท"
    ),
    "NCSA_Submission_Cert/CISSP_TOEIC.pdf": (
        "ไฟล์รวม 2 หน้า ประกอบด้วยใบรับรอง CISSP ของ ISC2 และรายงานผลสอบ "
        "TOEIC Listening & Reading"
    ),
    "NCSA_Submission_Cert/CompTIA Cloud+ ce certificate.pdf": (
        "ใบรับรอง CompTIA Cloud+ ของนายธนัท ระบุวันรับรอง 5 มกราคม 2026 "
        "และวันหมดอายุ 5 มกราคม 2029"
    ),
    "NCSA_Submission_Cert/ECC-CEH-Certificate.pdf": (
        "ใบประกาศนียบัตร EC-Council Certified Ethical Hacker (CEH) "
        "ของนายธนัท พร้อมวันออกและวันต่ออายุใบรับรอง"
    ),
    "NCSA_Submission_Cert/ECC-CHFI-Certificate-ANSI.pdf": (
        "ใบประกาศนียบัตร EC-Council Computer Hacking Forensic Investigator "
        "(CHFI) ของนายธนัท พร้อมวันออกและวันต่ออายุใบรับรอง"
    ),
    "NCSA_submission_employment/20201116 Services Agreement - WIMT UK - Tanat Tonguthaisri - signed.pdf": (
        "สัญญา Services Agreement ระหว่าง WhereIsMyTransport Ltd "
        "กับ Tanat Tonguthaisri ลงวันที่ 12 พฤศจิกายน 2020"
    ),
    "NCSA_submission_employment/20201116 Work Order - WIMT UK - Tanat Tonguthaisri - signed.pdf": (
        "เอกสาร Work Order ของ WhereIsMyTransport สำหรับโครงการ Bangkok City Two "
        "ระบุขอบเขตงานวิเคราะห์ข้อมูลจราจร ระยะเวลา และค่าตอบแทน"
    ),
    "NCSA_submission_employment/Contract-Tanat-SLF-Jan2029.pdf": (
        "สัญญาจ้างพนักงานสัญญาจ้างกับกองทุนเงินให้กู้ยืมเพื่อการศึกษา "
        "กำหนดช่วงสัญญาจ้างถึง 31 มกราคม 2572"
    ),
    "NCSA_submission_employment/Tanat-ETDA-AugDec2022.pdf": (
        "เอกสาร TOR/ขอบเขตงานจ้างเหมาของ ETDA เกี่ยวกับการทบทวนนโยบายและแนวปฏิบัติ "
        "การออกใบรับรองอิเล็กทรอนิกส์ CP/CPS State จาก WebTrust"
    ),
    "NCSA_submission_employment/Tanat_TPQI_employment.pdf": (
        "หนังสือรับรองจากสถาบันคุณวุฒิวิชาชีพ (องค์การมหาชน) "
        "รับรองการปฏิบัติงานของนายธนัทในตำแหน่งเจ้าหน้าที่ทดสอบ"
    ),
    "NCSA_submission_employment/หนังสือรับรองการทำงาน ๓ รายการ.pdf": (
        "แฟ้มรวมหนังสือรับรองและคำสั่งเกี่ยวกับประวัติการทำงานจากหลายหน่วยงาน "
        "เช่น ARQ Group ศูนย์ไซเบอร์กองทัพบก และ สวทช."
    ),
    "consent_forms/ncsa_consent_form_tanat.pdf": (
        "หนังสือแสดงความยินยอมให้ NCSA ตรวจสอบประวัติการใช้โซเชียลมีเดีย "
        "ของนายธนัท พร้อมรายการบัญชีโซเชียลมีเดียที่ใช้งาน"
    ),
    "consent_forms/ncsa_consent_form_tanat_slf.pdf": (
        "หนังสือแสดงความยินยอมให้ NCSA ตรวจสอบประวัติการใช้โซเชียลมีเดีย "
        "ฉบับระบุตำแหน่งงานที่กองทุนเงินให้กู้ยืมเพื่อการศึกษา"
    ),
    "consent_forms/signed_consent_forms.pdf": (
        "ชุดเอกสารลงนาม 2 หน้า ประกอบด้วยหนังสือยินยอมให้เก็บรวบรวม/เปิดเผยข้อมูลส่วนบุคคล "
        "และหนังสือยินยอมให้ตรวจสอบประวัติบุคคลสำหรับการสมัครงานกับ NCSA"
    ),
}


@dataclass
class PdfRecord:
    relative_path: str
    filename: str
    pages: int
    file_size_bytes: int
    description_th: str
    output_relative_path: str


@dataclass(frozen=True)
class Placement:
    x_pt: float
    y_pt: float
    width_pt: float
    height_pt: float
    occupancy_ratio: float
    moved: bool


def ensure_dirs() -> None:
    for path in (OUTPUT_DIR, WATERMARKED_ROOT, CATALOG_DIR, ASSET_DIR):
        path.mkdir(parents=True, exist_ok=True)


def iter_source_pdfs() -> list[Path]:
    pdfs: list[Path] = []
    for pattern in ("*.pdf", "*.PDF"):
        for path in ROOT.rglob(pattern):
            rel = path.relative_to(ROOT)
            if rel.parts and rel.parts[0] in EXCLUDED_TOP_LEVEL_DIRS:
                continue
            pdfs.append(path)
    return sorted(set(pdfs))


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = FONT_BOLD if bold else FONT_REGULAR
    if font_path.exists():
        return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def draw_text_with_glow(
    base: Image.Image,
    text: str,
    position: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int, int],
    glow_fill: tuple[int, int, int, int],
    glow_radius: int,
) -> None:
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_glow = ImageDraw.Draw(glow)
    draw_glow.text(position, text, font=font, fill=glow_fill)
    glow = glow.filter(ImageFilter.GaussianBlur(glow_radius))
    base.alpha_composite(glow)
    draw = ImageDraw.Draw(base)
    draw.text(position, text, font=font, fill=fill)


def draw_signature(base: Image.Image) -> None:
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw_glow = ImageDraw.Draw(glow)
    draw = ImageDraw.Draw(base)

    segments = [
        [(240, 520), (340, 455), (540, 470), (700, 500), (740, 540), (610, 525), (410, 600), (520, 725), (690, 785)],
        [(860, 555), (930, 520), (1000, 610), (950, 740), (1115, 730), (1330, 695), (1440, 650), (1305, 575)],
        [(1225, 430), (1290, 390), (1400, 382), (1575, 392)],
        [(1410, 555), (1450, 645), (1525, 690), (1620, 650), (1715, 740)],
        [(1225, 430), (1245, 505), (1280, 620), (1298, 675)],
    ]

    for points in segments:
        draw_glow.line(points, fill=(108, 150, 255, 188), width=34, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    base.alpha_composite(glow)

    for points in segments:
        draw.line(points, fill=(48, 102, 245, 208), width=11, joint="curve")


def create_watermark_image(path: Path) -> tuple[int, int]:
    size = (1800, 1200)
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    title_font = load_font(178, bold=False)
    date_font = load_font(120, bold=True)
    meta_font = load_font(112, bold=True)

    draw_text_with_glow(
        image,
        "สำเนาถูกต้อง",
        (290, 48),
        title_font,
        (22, 22, 22, 186),
        (0, 0, 0, 55),
        8,
    )
    draw_signature(image)

    draw_text_with_glow(
        image,
        "10 มีนาคม 2569",
        (575, 790),
        date_font,
        (47, 89, 224, 185),
        (108, 150, 255, 155),
        18,
    )

    draw = ImageDraw.Draw(image)
    draw.line([(255, 975), (1585, 975)], fill=(47, 89, 224, 170), width=8)

    draw_text_with_glow(
        image,
        "เลขประจำตัวสอบ: 01007",
        (255, 1040),
        meta_font,
        (47, 89, 224, 185),
        (108, 150, 255, 155),
        18,
    )

    image.save(path)
    return size


def resolve_watermark_asset(explicit_path: Path | None) -> tuple[Path, tuple[int, int]]:
    candidates: list[Path] = []
    if explicit_path is not None:
        candidates.append(explicit_path if explicit_path.is_absolute() else ROOT / explicit_path)
    candidates.extend(ASSET_DIR / name for name in PREFERRED_WATERMARKS)

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            with Image.open(candidate) as watermark:
                return candidate, watermark.size

    fallback = ASSET_DIR / WATERMARK_IMAGE_NAME
    return fallback, create_watermark_image(fallback)


def get_base_watermark_width(page_width: float, page_height: float) -> float:
    target_width = max(150.0, min(page_width * 0.28, 220.0))
    if page_width > page_height:
        target_width = max(170.0, min(page_width * 0.24, 235.0))
    return target_width


def render_analysis_image(page: fitz.Page) -> Image.Image:
    pixmap = page.get_pixmap(matrix=fitz.Matrix(ANALYSIS_RENDER_SCALE, ANALYSIS_RENDER_SCALE), alpha=False)
    mode = "RGB" if pixmap.n < 4 else "RGBA"
    return Image.frombytes(mode, (pixmap.width, pixmap.height), pixmap.samples).convert("RGB")


def build_content_mask(page_image: Image.Image) -> Image.Image:
    white_bg = Image.new("RGB", page_image.size, (255, 255, 255))
    diff = ImageChops.difference(page_image, white_bg).convert("L")
    mask = diff.point(lambda value: 255 if value >= OCCUPANCY_THRESHOLD else 0)
    return mask.filter(ImageFilter.MaxFilter(5))


def iter_candidate_offsets(max_left_px: int, max_down_px: int, step_x: int, step_y: int) -> list[tuple[int, int]]:
    offsets: list[tuple[int, int]] = []
    for dy in range(0, max_down_px + 1, step_y):
        for dx in range(0, max_left_px + 1, step_x):
            offsets.append((dx, dy))
    offsets.sort(key=lambda pair: (pair[0] + pair[1], pair[1], pair[0]))
    return offsets


def compute_occupancy(mask: Image.Image, x_px: int, y_px: int, width_px: int, height_px: int) -> float:
    pad = max(4, round(min(width_px, height_px) * 0.05))
    left = max(0, x_px - pad)
    top = max(0, y_px - pad)
    right = min(mask.width, x_px + width_px + pad)
    bottom = min(mask.height, y_px + height_px + pad)
    region = mask.crop((left, top, right, bottom))
    area = max(1, region.width * region.height)
    ink_pixels = ImageStat.Stat(region).sum[0] / 255.0
    return ink_pixels / area


def default_placement(page_width: float, page_height: float, watermark_size: tuple[int, int]) -> Placement:
    wm_width, wm_height = watermark_size
    aspect_ratio = wm_width / wm_height
    width_pt = get_base_watermark_width(page_width, page_height)
    height_pt = width_pt / aspect_ratio
    margin_pt = max(12.0, min(page_width, page_height) * 0.02)
    x_pt = page_width - width_pt - margin_pt
    y_pt = page_height - height_pt - margin_pt
    return Placement(x_pt=x_pt, y_pt=y_pt, width_pt=width_pt, height_pt=height_pt, occupancy_ratio=1.0, moved=False)


def choose_watermark_placement(
    page_width: float,
    page_height: float,
    watermark_size: tuple[int, int],
    page_image: Image.Image,
) -> Placement:
    wm_width, wm_height = watermark_size
    aspect_ratio = wm_width / wm_height
    base_width_pt = get_base_watermark_width(page_width, page_height)
    margin_pt = max(12.0, min(page_width, page_height) * 0.02)
    mask = build_content_mask(page_image)
    x_scale = mask.width / page_width
    y_scale = mask.height / page_height

    best: Placement | None = None
    best_score: float | None = None

    for scale_factor in ADAPTIVE_SCALE_FACTORS:
        width_pt = base_width_pt * scale_factor
        height_pt = width_pt / aspect_ratio
        width_px = max(8, round(width_pt * x_scale))
        height_px = max(8, round(height_pt * y_scale))
        margin_x_px = max(4, round(margin_pt * x_scale))
        margin_y_px = max(4, round(margin_pt * y_scale))
        max_left_px = max(0, round(min(page_width * 0.32, width_pt * 1.8 + 28.0) * x_scale))
        max_down_px = max(0, round(min(page_height * 0.34, height_pt * 1.9 + 40.0) * y_scale))
        step_x = max(8, width_px // 10)
        step_y = max(8, height_px // 10)

        for dx_px, dy_px in iter_candidate_offsets(max_left_px, max_down_px, step_x, step_y):
            x_px = mask.width - width_px - margin_x_px - dx_px
            y_px = margin_y_px + dy_px
            if x_px < margin_x_px:
                continue
            if y_px + height_px > mask.height - margin_y_px:
                continue

            occupancy_ratio = compute_occupancy(mask, x_px, y_px, width_px, height_px)
            x_pt = x_px / x_scale
            y_top_pt = y_px / y_scale
            y_pt = page_height - y_top_pt - height_pt
            moved = dx_px > 0 or dy_px > 0 or scale_factor < 1.0
            placement = Placement(
                x_pt=x_pt,
                y_pt=y_pt,
                width_pt=width_pt,
                height_pt=height_pt,
                occupancy_ratio=occupancy_ratio,
                moved=moved,
            )

            if occupancy_ratio <= CLEAR_REGION_THRESHOLD:
                return placement

            distance_score = (dx_px / max(1, max_left_px + step_x)) + (dy_px / max(1, max_down_px + step_y))
            size_penalty = (1.0 - scale_factor) * 0.35
            score = occupancy_ratio * 1000.0 + distance_score + size_penalty
            if best_score is None or score < best_score:
                best = placement
                best_score = score

    return best or default_placement(page_width, page_height, watermark_size)


def make_overlay_pdf(
    page_width: float,
    page_height: float,
    watermark_path: Path,
    placement: Placement,
) -> bytes:
    packet = BytesIO()
    pdf = canvas.Canvas(packet, pagesize=(page_width, page_height))
    pdf.drawImage(
        str(watermark_path),
        placement.x_pt,
        placement.y_pt,
        width=placement.width_pt,
        height=placement.height_pt,
        mask="auto",
    )
    pdf.save()
    return packet.getvalue()


def open_fitz_document(path: Path) -> fitz.Document:
    document = fitz.open(path)
    if document.needs_pass and not document.authenticate(""):
        raise ValueError(f"Unable to open encrypted PDF without a password: {path}")
    return document


def watermark_pdf(source_pdf: Path, output_pdf: Path, watermark_path: Path, watermark_size: tuple[int, int]) -> tuple[int, int]:
    reader = PdfReader(str(source_pdf))
    if reader.is_encrypted:
        reader.decrypt("")

    writer = PdfWriter()
    if reader.metadata:
        writer.add_metadata({key: str(value) for key, value in reader.metadata.items() if value is not None})

    adjusted_pages = 0
    overlay_cache: dict[tuple[float, float, float, float, float, float], bytes] = {}

    with open_fitz_document(source_pdf) as rendered_doc:
        for index, page in enumerate(reader.pages):
            rotation = int(page.get("/Rotate", 0) or 0)
            if rotation:
                page.transfer_rotation_to_content()

            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            placement = default_placement(width, height, watermark_size)

            try:
                analysis_image = render_analysis_image(rendered_doc[index])
                placement = choose_watermark_placement(width, height, watermark_size, analysis_image)
            except Exception:
                placement = default_placement(width, height, watermark_size)

            if placement.moved:
                adjusted_pages += 1

            cache_key = (
                round(width, 2),
                round(height, 2),
                round(placement.x_pt, 2),
                round(placement.y_pt, 2),
                round(placement.width_pt, 2),
                round(placement.height_pt, 2),
            )
            overlay_bytes = overlay_cache.get(cache_key)
            if overlay_bytes is None:
                overlay_bytes = make_overlay_pdf(width, height, watermark_path, placement)
                overlay_cache[cache_key] = overlay_bytes

            overlay_page = PdfReader(BytesIO(overlay_bytes)).pages[0]
            page.merge_page(overlay_page, over=True)
            writer.add_page(page)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as handle:
        writer.write(handle)

    return len(reader.pages), adjusted_pages


def build_inventory(records: list[PdfRecord]) -> None:
    json_path = CATALOG_DIR / "pdf_inventory.json"
    csv_path = CATALOG_DIR / "pdf_inventory.csv"
    md_path = CATALOG_DIR / "pdf_inventory.md"

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump([asdict(record) for record in records], handle, ensure_ascii=False, indent=2)

    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "relative_path",
                "filename",
                "pages",
                "file_size_bytes",
                "description_th",
                "output_relative_path",
            ]
        )
        for record in records:
            writer.writerow(
                [
                    record.relative_path,
                    record.filename,
                    record.pages,
                    record.file_size_bytes,
                    record.description_th,
                    record.output_relative_path,
                ]
            )

    lines = [
        "# PDF Catalog",
        "",
        "หมายเหตุ: ลายน้ำถูกสร้างใหม่จากภาพแนบในแชต เนื่องจากไฟล์ภาพต้นฉบับไม่ได้ปรากฏเป็นไฟล์ในระบบภายในเครื่องโดยตรง",
        "",
        f"จำนวนไฟล์ PDF ที่ประมวลผล: {len(records)}",
        "",
        "| ลำดับ | พาธสัมพัทธ์ | จำนวนหน้า | คำอธิบาย (ภาษาไทย) |",
        "| --- | --- | ---: | --- |",
    ]
    for index, record in enumerate(records, start=1):
        lines.append(
            f"| {index} | `{record.relative_path}` | {record.pages} | {record.description_th} |"
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watermark repository PDFs into a mirrored output tree.")
    parser.add_argument(
        "--watermark",
        type=Path,
        help="Optional explicit watermark image path. Defaults to preferred files in output/assets.",
    )
    parser.add_argument(
        "--rebuild-inventory",
        action="store_true",
        help="Rebuild the catalog files after watermarking.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ensure_dirs()
    watermark_path, watermark_size = resolve_watermark_asset(args.watermark)

    records: list[PdfRecord] = []
    total_pages = 0
    adjusted_pages = 0
    source_pdfs = iter_source_pdfs()

    for source_pdf in source_pdfs:
        relative_path = source_pdf.relative_to(ROOT).as_posix()
        output_pdf = WATERMARKED_ROOT / relative_path
        pages, adjusted = watermark_pdf(source_pdf, output_pdf, watermark_path, watermark_size)
        total_pages += pages
        adjusted_pages += adjusted

        if args.rebuild_inventory:
            records.append(
                PdfRecord(
                    relative_path=relative_path,
                    filename=source_pdf.name,
                    pages=pages,
                    file_size_bytes=source_pdf.stat().st_size,
                    description_th=DESCRIPTIONS_TH.get(relative_path, "ไม่พบคำอธิบายสำหรับไฟล์นี้"),
                    output_relative_path=output_pdf.relative_to(OUTPUT_DIR).as_posix(),
                )
            )

    if args.rebuild_inventory:
        build_inventory(records)

    print(f"Processed {len(source_pdfs)} PDF files and {total_pages} pages.")
    print(f"Adaptive placement adjusted {adjusted_pages} pages away from the default top-right anchor.")
    print(f"Watermarked PDFs: {WATERMARKED_ROOT}")
    print(f"Watermark asset used: {watermark_path}")
    if args.rebuild_inventory:
        print(f"Catalog files: {CATALOG_DIR}")
    else:
        print("Catalog files were left unchanged.")


if __name__ == "__main__":
    main()
