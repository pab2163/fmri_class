#!/usr/bin/env python3
"""
fake_feat_reg.py

Implements the "Mumford trick" for running a FEAT higher-level (2nd level)
analysis when the level-1 analysis was run on data that is ALREADY in
standard space (e.g., fMRIPrep MNI outputs).

For each level-1 .feat directory listed in a CSV/text file, the script:

  1. Skips the directory if it already contains a reg/ folder.
  2. Creates <feat>/reg/
  3. Writes identity matrices (same content as $FSLDIR/etc/flirtsch/ident.mat)
     as example_func2standard.mat and standard2example_func.mat.
     (No highres mats are written: if reg/highres2standard.mat exists,
     FEAT's featregapply tries to resample reg/highres, which we don't have.)
  4. Copies <feat>/mean_func.nii.gz to <feat>/reg/standard.nii.gz
     (same voxel grid as the level-1 stats, so no resampling occurs later)

If you already ran an earlier version of this script, re-run with --force to
delete and rebuild reg/ (and any partial reg_standard/ left by the failed
level-2 attempt).

No FSL installation is required (the identity matrix is written directly),
but if $FSLDIR is set and ident.mat exists, that file is used instead.

Usage:
    python fake_feat_reg.py feat_dirs.csv
    python fake_feat_reg.py feat_dirs.csv --dry-run
    python fake_feat_reg.py feat_dirs.csv --column feat_path

Input file format:
    - A CSV with a header row containing the column given by --column, OR
    - A plain list with one .feat path per line (first column is used).
    - Blank lines and lines starting with '#' are ignored.
    - Relative paths are resolved relative to the current working directory
      (use --base-dir to change this).
"""

import argparse
import csv
import os
import shutil
import sys
from pathlib import Path

IDENTITY = "1 0 0 0\n0 1 0 0\n0 0 1 0\n0 0 0 1\n"

# Only the functional <-> standard transforms are written. Identity is its own
# inverse, so both are the same matrix.
#
# IMPORTANT: do NOT add highres2standard.mat (or other highres mats) here.
# FEAT's featregapply script checks whether reg/highres2standard.mat exists and,
# if so, tries to resample reg/highres, which we don't have. That was the cause
# of the "No image files match: reg/highres" error.
MAT_FILES = [
    "example_func2standard.mat",
    "standard2example_func.mat",
]


def get_identity_text() -> str:
    """Prefer FSL's own ident.mat if available; otherwise use a literal identity."""
    fsldir = os.environ.get("FSLDIR")
    if fsldir:
        ident = Path(fsldir) / "etc" / "flirtsch" / "ident.mat"
        if ident.is_file():
            return ident.read_text()
    return IDENTITY


def read_feat_paths(list_file: Path, column: str | None, base_dir: Path) -> list[Path]:
    """Read .feat paths from a CSV or plain-text list."""
    with open(list_file, newline="") as fh:
        lines = [ln for ln in fh.read().splitlines()
                 if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return []

    rows = list(csv.reader(lines))
    first = rows[0]

    col_idx = 0
    data_rows = rows
    if column is not None:
        if column in first:
            col_idx = first.index(column)
            data_rows = rows[1:]
        else:
            sys.exit(f"ERROR: column '{column}' not found in header: {first}")
    elif first and not first[0].strip().rstrip("/").endswith(".feat"):
        # Looks like a header row (first cell isn't a .feat path)
        data_rows = rows[1:]

    paths = []
    for row in data_rows:
        if len(row) <= col_idx or not row[col_idx].strip():
            continue
        p = Path(row[col_idx].strip()).expanduser()
        if not p.is_absolute():
            p = base_dir / p
        paths.append(p)
    return paths


def process_feat_dir(feat: Path, identity_text: str, dry_run: bool,
                     force: bool = False) -> str:
    """Returns a status string: 'done', 'skipped', or 'error: ...'."""
    if not feat.is_dir():
        return "error: not a directory"

    reg = feat / "reg"
    reg_standard = feat / "reg_standard"
    if reg.exists() and not force:
        return "skipped (reg/ already exists; use --force to rebuild)"

    mean_func = feat / "mean_func.nii.gz"
    if not mean_func.is_file():
        return "error: mean_func.nii.gz not found"

    if not (feat / "stats").is_dir():
        return "error: stats/ not found (did level 1 finish?)"

    if dry_run:
        return "would create reg/ (dry run)"

    if force:
        # Remove a previous reg/ and any partial reg_standard/ left behind by a
        # failed featregapply run, so FEAT regenerates it cleanly.
        shutil.rmtree(reg, ignore_errors=True)
        shutil.rmtree(reg_standard, ignore_errors=True)

    reg.mkdir()
    try:
        for name in MAT_FILES:
            (reg / name).write_text(identity_text)
        shutil.copyfile(mean_func, reg / "standard.nii.gz")
    except Exception as exc:  # clean up a half-built reg/ so a rerun isn't skipped
        shutil.rmtree(reg, ignore_errors=True)
        return f"error: {exc}"
    return "done"


def main():
    ap = argparse.ArgumentParser(
        description="Fake FEAT registration for level-1 .feat dirs already in standard space."
    )
    ap.add_argument("list_file", type=Path,
                    help="CSV or text file listing .feat directories")
    ap.add_argument("--column", default=None,
                    help="Header name of the column containing .feat paths "
                         "(default: first column)")
    ap.add_argument("--base-dir", type=Path, default=Path.cwd(),
                    help="Base directory for relative paths (default: cwd)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would happen without writing anything")
    ap.add_argument("--force", action="store_true",
                    help="Delete and rebuild an existing reg/ (and reg_standard/). "
                         "Use to repair directories from an earlier run of this script. "
                         "WARNING: this also deletes any real registration in reg/.")
    args = ap.parse_args()

    if not args.list_file.is_file():
        sys.exit(f"ERROR: list file not found: {args.list_file}")

    feat_dirs = read_feat_paths(args.list_file, args.column, args.base_dir)
    if not feat_dirs:
        sys.exit("ERROR: no .feat paths found in list file")

    identity_text = get_identity_text()
    counts = {"done": 0, "skipped": 0, "error": 0, "dry": 0}

    for feat in feat_dirs:
        status = process_feat_dir(feat, identity_text, args.dry_run, args.force)
        print(f"[{status}] {feat}")
        if status == "done":
            counts["done"] += 1
        elif status.startswith("skipped"):
            counts["skipped"] += 1
        elif status.startswith("would"):
            counts["dry"] += 1
        else:
            counts["error"] += 1

    print(f"\nSummary: {counts['done']} processed, {counts['skipped']} skipped, "
          f"{counts['error']} errors" +
          (f", {counts['dry']} would be processed (dry run)" if args.dry_run else ""))
    sys.exit(1 if counts["error"] else 0)


if __name__ == "__main__":
    main()