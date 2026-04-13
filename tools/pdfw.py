import argparse
import io
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import img2pdf
from PIL import Image

WATERMARK_OPACITY = 0.3


def natural_key(value: str):
    """Build a natural-sort key so names with numbers sort in human order."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def load_pdfimages_path(script_dir: Path) -> Path:
    """Load and validate pdfimages.exe path from pdfimages-path.json near this script."""
    config_path = script_dir / "pdfimages-path.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON format in {config_path}: {exc}") from exc
    exe_path = data.get("pdfimages_exe")
    if not exe_path:
        raise ValueError(f"'pdfimages_exe' not found in {config_path}")

    pdfimages_exe = Path(exe_path)
    if not pdfimages_exe.exists():
        raise FileNotFoundError(f"pdfimages.exe not found: {pdfimages_exe}")
    return pdfimages_exe


def apply_watermark(pdf_path: Path, watermark_image: Path) -> None:
    """Overlay a centered watermark image at 70% opacity on every PDF page."""
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required when using -wmark.") from exc

    try:
        with Image.open(watermark_image) as source_image:
            rgba_image = source_image.convert("RGBA")
            alpha = rgba_image.getchannel("A")
            opacity_scale = max(0, min(255, int(round(WATERMARK_OPACITY * 255))))
            alpha = alpha.point(lambda value: (value * opacity_scale) // 255)
            rgba_image.putalpha(alpha)

            watermark_width, watermark_height = rgba_image.size
            buffer = io.BytesIO()
            rgba_image.save(buffer, format="PNG")
            watermark_png_bytes = buffer.getvalue()
    except Exception as exc:
        raise ValueError(
            f"Failed to process watermark image: {watermark_image}"
        ) from exc
    temp_output_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="pdfw-wm-",
            suffix=".pdf",
            dir=pdf_path.parent,
            delete=False,
        ) as tmp_file:
            temp_output_path = Path(tmp_file.name)

        with fitz.open(str(pdf_path)) as target_pdf:
            xref = 0
            for page in target_pdf:
                page_rect = page.rect
                scale = min(
                    page_rect.width / float(watermark_width),
                    page_rect.height / float(watermark_height),
                )
                draw_width = float(watermark_width) * scale
                draw_height = float(watermark_height) * scale
                offset_x = (page_rect.width - draw_width) / 2.0
                offset_y = (page_rect.height - draw_height) / 2.0
                watermark_rect = fitz.Rect(
                    offset_x,
                    offset_y,
                    offset_x + draw_width,
                    offset_y + draw_height,
                )
                xref = page.insert_image(
                    watermark_rect,
                    stream=watermark_png_bytes,
                    overlay=True,
                    keep_proportion=False,
                    xref=xref,
                )
            target_pdf.save(str(temp_output_path))

        temp_output_path.replace(pdf_path)
    except Exception as exc:
        raise OSError(f"Failed to apply watermark to {pdf_path}: {exc}") from exc
    finally:
        if temp_output_path and temp_output_path.exists():
            try:
                temp_output_path.unlink()
            except OSError:
                pass


def convert_pdf(
    source_pdf: Path,
    output_pdf: Path,
    script_dir: Path,
    pdfimages_exe: Path,
    watermark_image: Optional[Path] = None,
) -> int:
    with tempfile.TemporaryDirectory(prefix="pdfw-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        out_prefix = tmp_path / "w"

        try:
            subprocess.run(
                [str(pdfimages_exe), "-j", str(source_pdf), str(out_prefix)],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"pdfimages failed for {source_pdf} with exit code {exc.returncode}",
                file=sys.stderr,
            )
            return 1

        dedup_script = script_dir / "dedup.py"
        if not dedup_script.exists():
            print(f"Missing helper script: {dedup_script}", file=sys.stderr)
            return 1
        try:
            subprocess.run(
                [sys.executable, str(dedup_script), str(tmp_path)],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"dedup.py failed for {source_pdf} with exit code {exc.returncode}",
                file=sys.stderr,
            )
            return 1

        images = sorted(
            [p for p in tmp_path.iterdir() if p.is_file() and p.name.startswith("w-")],
            key=lambda p: natural_key(p.name),
        )

        if not images:
            print(f"No extracted images were found for {source_pdf}.", file=sys.stderr)
            return 1

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_pdf.open("wb") as output_file:
                output_file.write(img2pdf.convert([str(img) for img in images]))
        except (OSError, ValueError) as exc:
            print(f"Failed to create output PDF {output_pdf}: {exc}", file=sys.stderr)
            return 1

        if watermark_image is not None:
            try:
                apply_watermark(output_pdf, watermark_image)
            except (RuntimeError, ValueError, OSError) as exc:
                print(f"Failed to apply watermark to {output_pdf}: {exc}", file=sys.stderr)
                return 1

    print(f"Created: {output_pdf}")
    return 0


def iter_pdfs(source_dir: Path, output_root: Path):
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".pdf":
            continue
        try:
            # Skip generated outputs so reruns do not process files inside pdfw-pdfs.
            path.relative_to(output_root)
            continue
        except ValueError:
            pass
        yield path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a PDF (or all PDFs in a folder) into *_pdfw.pdf output(s)"
    )
    parser.add_argument("source_path", help="Path to source PDF file or folder")
    parser.add_argument(
        "-wmark",
        dest="watermark_image",
        help=(
            f"Optional watermark image path to overlay at "
            f"{int(WATERMARK_OPACITY * 100)}%% opacity on each output page"
        ),
    )
    args = parser.parse_args()

    source_path = Path(args.source_path).expanduser().resolve()
    if not source_path.exists():
        print(f"Input path not found: {source_path}", file=sys.stderr)
        return 1
    watermark_image = None
    if args.watermark_image:
        watermark_image = Path(args.watermark_image).expanduser().resolve()
        if not watermark_image.exists() or not watermark_image.is_file():
            print(f"Watermark image not found: {watermark_image}", file=sys.stderr)
            return 1

    script_dir = Path(__file__).resolve().parent
    try:
        pdfimages_exe = load_pdfimages_path(script_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if source_path.is_file():
        if source_path.suffix.lower() != ".pdf":
            print(f"Input file is not a PDF: {source_path}", file=sys.stderr)
            return 1
        output_pdf = source_path.with_name(f"{source_path.stem}_pdfw.pdf")
        return convert_pdf(source_path, output_pdf, script_dir, pdfimages_exe, watermark_image)

    if not source_path.is_dir():
        print(f"Input path is neither file nor directory: {source_path}", file=sys.stderr)
        return 1

    output_root = source_path / "pdfw-pdfs"
    pdfs = sorted(iter_pdfs(source_path, output_root), key=lambda p: str(p).lower())
    if not pdfs:
        print(f"No PDFs found in: {source_path}", file=sys.stderr)
        return 1

    failures = 0
    for source_pdf in pdfs:
        relative_dir = source_pdf.parent.relative_to(source_path)
        if relative_dir == Path("."):
            relative_dir = Path()
        output_pdf = output_root / relative_dir / f"{source_pdf.stem}_pdfw.pdf"
        if convert_pdf(source_pdf, output_pdf, script_dir, pdfimages_exe, watermark_image) != 0:
            failures += 1

    if failures:
        print(f"Completed with {failures} failed PDF(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
