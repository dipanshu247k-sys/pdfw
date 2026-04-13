import argparse
import hashlib
import sys
from pathlib import Path


def file_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(root: Path, recursive: bool):
    if recursive:
        return (p for p in root.rglob("*") if p.is_file())
    return (p for p in root.iterdir() if p.is_file())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Delete duplicate files while always keeping one copy."
    )
    parser.add_argument("target_dir", help="Directory to scan for duplicate files")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subdirectories recursively",
    )
    args = parser.parse_args()

    target_dir = Path(args.target_dir).expanduser().resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Directory not found: {target_dir}", file=sys.stderr)
        return 1

    files = sorted(iter_files(target_dir, args.recursive), key=lambda p: str(p).lower())
    if not files:
        print("No files found.")
        return 0

    kept_by_hash = {}
    deleted_count = 0

    for file_path in files:
        try:
            fingerprint = file_sha256(file_path)
        except OSError as exc:
            print(f"Failed to read {file_path}: {exc}", file=sys.stderr)
            return 1

        if fingerprint in kept_by_hash:
            try:
                file_path.unlink()
                deleted_count += 1
                print(f"Deleted duplicate: {file_path}")
            except OSError as exc:
                print(f"Failed to delete {file_path}: {exc}", file=sys.stderr)
                return 1
        else:
            kept_by_hash[fingerprint] = file_path

    kept_count = len(kept_by_hash)
    print(f"Completed. Kept {kept_count} unique file(s), deleted {deleted_count} duplicate file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
