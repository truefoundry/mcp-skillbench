"""Verify and unpack the sanitized trajectory archive stored in this repository."""

from __future__ import annotations

import hashlib
import shutil
import tarfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ARCHIVE_NAME = "mcp-skillbench-trajectories-2026-09-29.tar.gz"
ARCHIVE = PROJECT / "eval" / "data" / ARCHIVE_NAME
CHECKSUMS = PROJECT / "eval" / "data" / "SHA256SUMS"
DOWNLOAD_DIR = PROJECT / "data" / "trajectories"


def expected_sha256() -> str:
    for line in CHECKSUMS.read_text().splitlines():
        digest, name = line.split()
        if name == ARCHIVE_NAME:
            return digest
    raise SystemExit(f"{CHECKSUMS} has no entry for {ARCHIVE_NAME}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not ARCHIVE.is_file():
        raise SystemExit(f"Missing trajectory archive: {ARCHIVE}")
    actual = sha256(ARCHIVE)
    expected = expected_sha256()
    if actual != expected:
        raise SystemExit(f"Checksum mismatch: {actual} != {expected}")
    print(f"Verified {ARCHIVE.relative_to(PROJECT)}")
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(ARCHIVE) as bundle:
        bundle.extractall(DOWNLOAD_DIR)
    source = DOWNLOAD_DIR / "mcp-skillbench-trajectories"
    for name in ("linear", "slack"):
        destination = PROJECT / "eval" / "experiments" / name / "model-runs"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source / name, destination)
        print(f"Installed {destination.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
