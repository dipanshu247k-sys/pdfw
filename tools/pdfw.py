import argparse
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


def convert_pdf(source_pdf: Path, output_pdf: Path, script_dir: Path, pdfimages_exe: Path) -> int:
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

    print(f"Created: {output_pdf}")
    return 0


def iter_pdfs(source_dir: Path, output_root: Path):
    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".pdf":
            continue
        try:
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
    args = parser.parse_args()

    source_path = Path(args.source_path).expanduser().resolve()
    if not source_path.exists():
        print(f"Input path not found: {source_path}", file=sys.stderr)
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
        return convert_pdf(source_path, output_pdf, script_dir, pdfimages_exe)

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
        if convert_pdf(source_pdf, output_pdf, script_dir, pdfimages_exe) != 0:
            failures += 1

    if failures:
        print(f"Completed with {failures} failed PDF(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
