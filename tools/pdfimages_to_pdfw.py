import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import img2pdf


def natural_key(value: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def load_pdfimages_path(script_dir: Path) -> Path:
    config_path = script_dir / "pdfimages-path.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")

    data = json.loads(config_path.read_text(encoding="utf-8-sig"))
    exe_path = data.get("pdfimages_exe")
    if not exe_path:
        raise ValueError(f"'pdfimages_exe' not found in {config_path}")

    pdfimages_exe = Path(exe_path)
    if not pdfimages_exe.exists():
        raise FileNotFoundError(f"pdfimages.exe not found: {pdfimages_exe}")
    return pdfimages_exe


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
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
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

        with output_pdf.open("wb") as output_file:
            output_file.write(img2pdf.convert([str(img) for img in images]))

    print(f"Created: {output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
