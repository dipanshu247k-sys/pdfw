import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import img2pdf


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


def delete_duplicate_files(files: list[Path]) -> tuple[list[Path], int]:
    """Delete duplicate files by content hash and return unique files + deleted count."""
    seen_hashes: set[str] = set()
    unique_files: list[Path] = []
    deleted_count = 0

    for file_path in files:
        file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if file_hash in seen_hashes:
            file_path.unlink()
            deleted_count += 1
            continue
        seen_hashes.add(file_hash)
        unique_files.append(file_path)

    return unique_files, deleted_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract images from a PDF and rebuild them into <basename>_pdfw.pdf"
    )
    parser.add_argument("pdf_file", help="Path to source PDF file")
    args = parser.parse_args()

    source_pdf = Path(args.pdf_file).expanduser().resolve()
    if not source_pdf.exists():
        print(f"Input PDF not found: {source_pdf}", file=sys.stderr)
        return 1

    script_dir = Path(__file__).resolve().parent
    try:
        pdfimages_exe = load_pdfimages_path(script_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    output_pdf = source_pdf.with_name(f"{source_pdf.stem}_pdfw.pdf")

    with tempfile.TemporaryDirectory(prefix="pdfw-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        out_prefix = tmp_path / "w"

        try:
            subprocess.run(
                [str(pdfimages_exe), "-j", str(source_pdf), str(out_prefix)],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            print(f"pdfimages failed with exit code {exc.returncode}", file=sys.stderr)
            return 1

        images = sorted(
            [p for p in tmp_path.iterdir() if p.is_file() and p.name.startswith("w-")],
            key=lambda p: natural_key(p.name),
        )

        if not images:
            print("No extracted images were found.", file=sys.stderr)
            return 1

        try:
            images, deleted_duplicates = delete_duplicate_files(images)
        except OSError as exc:
            print(f"Failed while deleting duplicate files: {exc}", file=sys.stderr)
            return 1

        try:
            with output_pdf.open("wb") as output_file:
                output_file.write(img2pdf.convert([str(img) for img in images]))
        except (OSError, ValueError) as exc:
            print(f"Failed to create output PDF: {exc}", file=sys.stderr)
            return 1

    if deleted_duplicates:
        print(f"Deleted duplicate files: {deleted_duplicates}")
    print(f"Created: {output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
