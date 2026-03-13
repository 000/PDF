from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
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


def ensure_dirs() -> None:
    for path in (OUTPUT_DIR, WATERMARKED_ROOT, CATALOG_DIR, ASSET_DIR):
        path.mkdir(parents=True, exist_ok=True)


def iter_source_pdfs() -> list[Path]:
    pdfs: list[Path] = []
    for path in ROOT.rglob("*.pdf"):
        rel = path.relative_to(ROOT)
        if rel.parts and rel.parts[0] in EXCLUDED_TOP_LEVEL_DIRS:
            continue
        pdfs.append(path)
    for path in ROOT.rglob("*.PDF"):
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


def make_overlay_pdf(page_width: float, page_height: float, watermark_path: Path, watermark_size: tuple[int, int]) -> bytes:
    wm_width, wm_height = watermark_size
    aspect_ratio = wm_width / wm_height

    target_width = max(150.0, min(page_width * 0.28, 220.0))
    if page_width > page_height:
        target_width = max(170.0, min(page_width * 0.24, 235.0))
    target_height = target_width / aspect_ratio
    margin = max(12.0, min(page_width, page_height) * 0.02)
    x = page_width - target_width - margin
    y = page_height - target_height - margin

    packet = BytesIO()
    pdf = canvas.Canvas(packet, pagesize=(page_width, page_height))
    pdf.drawImage(str(watermark_path), x, y, width=target_width, height=target_height, mask="auto")
    pdf.save()
    return packet.getvalue()


def watermark_pdf(source_pdf: Path, output_pdf: Path, watermark_path: Path, watermark_size: tuple[int, int]) -> int:
    reader = PdfReader(str(source_pdf))
    if reader.is_encrypted:
        reader.decrypt("")

    writer = PdfWriter()
    if reader.metadata:
        writer.add_metadata({k: str(v) for k, v in reader.metadata.items() if v is not None})

    overlay_cache: dict[tuple[float, float], bytes] = {}
    for page in reader.pages:
        rotation = int(page.get("/Rotate", 0) or 0)
        if rotation:
            page.transfer_rotation_to_content()

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        key = (round(width, 2), round(height, 2))
        overlay_bytes = overlay_cache.get(key)
        if overlay_bytes is None:
            overlay_bytes = make_overlay_pdf(width, height, watermark_path, watermark_size)
            overlay_cache[key] = overlay_bytes

        overlay_page = PdfReader(BytesIO(overlay_bytes)).pages[0]
        page.merge_page(overlay_page, over=True)
        writer.add_page(page)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    with output_pdf.open("wb") as handle:
        writer.write(handle)

    return len(reader.pages)


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


def main() -> None:
    ensure_dirs()
    watermark_path = ASSET_DIR / WATERMARK_IMAGE_NAME
    watermark_size = create_watermark_image(watermark_path)

    records: list[PdfRecord] = []
    for source_pdf in iter_source_pdfs():
        relative_path = source_pdf.relative_to(ROOT).as_posix()
        output_pdf = WATERMARKED_ROOT / relative_path
        pages = watermark_pdf(source_pdf, output_pdf, watermark_path, watermark_size)
        record = PdfRecord(
            relative_path=relative_path,
            filename=source_pdf.name,
            pages=pages,
            file_size_bytes=source_pdf.stat().st_size,
            description_th=DESCRIPTIONS_TH.get(relative_path, "ไม่พบคำอธิบายสำหรับไฟล์นี้"),
            output_relative_path=output_pdf.relative_to(OUTPUT_DIR).as_posix(),
        )
        records.append(record)

    build_inventory(records)
    print(f"Processed {len(records)} PDF files.")
    print(f"Watermarked PDFs: {WATERMARKED_ROOT}")
    print(f"Catalog files: {CATALOG_DIR}")
    print(f"Watermark asset: {watermark_path}")


if __name__ == "__main__":
    main()
