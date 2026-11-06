#!/usr/bin/env python3
"""
fmriprep_confounds_to_fsl.py

Convert an fMRIPrep confounds file (*_desc-confounds_timeseries.tsv, or the older
*_desc-confounds_regressors.tsv) into a plain-text, whitespace-delimited, header-less
confound matrix that can be loaded as an "Additional confound EVs" file in the
FSL FEAT level-1 GLM (Stats tab).

Optionally creates one "spike" (scrubbing) regressor per volume whose framewise
displacement (FD) exceeds a chosen cutoff.

Examples
--------
# 24-parameter motion + 5 aCompCor comps + FD spikes at 0.5 mm
python fmriprep_confounds_to_fsl.py \
    sub-01_task-rest_desc-confounds_timeseries.tsv \
    -o sub-01_task-rest_fsl_confounds.txt \
    --motion 24 --compcor 5 --fd-threshold 0.5

# 6 motion params + WM/CSF (with derivatives) + cosine drift terms
python fmriprep_confounds_to_fsl.py confounds.tsv --motion 6 --wm --csf \
    --tissue-derivatives --cosine

Notes
-----
* The first row of fMRIPrep's FD (and of all *_derivative1 columns) is NaN.
  FSL cannot read NaNs, so these are replaced with 0.
* Output has no header and one row per volume, as FSL requires. The number of rows
  must equal the number of volumes in the 4D functional run you feed to FEAT.
* A sidecar "<output>_colnames.txt" listing the column order is also written so you
  can keep track of what each column is.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MOTION_BASE = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def say(msg="", quiet=False):
    if not quiet:
        print(msg, flush=True)


def warn(msg):
    print(f"  [WARNING] {msg}", file=sys.stderr, flush=True)


def fail(msg):
    print(f"[ERROR] {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def select_existing(df, wanted, label):
    """Return the subset of `wanted` present in df; warn about any that are missing."""
    present = [c for c in wanted if c in df.columns]
    missing = [c for c in wanted if c not in df.columns]
    if missing:
        warn(f"{label}: {len(missing)} requested column(s) not found in file: "
             f"{', '.join(missing[:6])}{' ...' if len(missing) > 6 else ''}")
    return present


def default_output_path(in_path: Path) -> Path:
    name = in_path.name
    for suffix in ("_desc-confounds_timeseries.tsv", "_desc-confounds_regressors.tsv"):
        if name.endswith(suffix):
            return in_path.with_name(name[: -len(suffix)] + "_fsl_confounds.txt")
    return in_path.with_name(in_path.stem + "_fsl_confounds.txt")


# --------------------------------------------------------------------------- #
# Column selection
# --------------------------------------------------------------------------- #
def motion_columns(df, mode):
    """6, 12 or 24 parameter motion model."""
    if mode == "none":
        return []
    cols = list(MOTION_BASE)
    if mode in ("12", "24"):
        cols += [f"{c}_derivative1" for c in MOTION_BASE]
    if mode == "24":
        cols += [f"{c}_power2" for c in MOTION_BASE]
        cols += [f"{c}_derivative1_power2" for c in MOTION_BASE]
    return select_existing(df, cols, f"{mode}-param motion")


def tissue_columns(df, args):
    base = []
    if args.wm:
        base.append("white_matter")
    if args.csf:
        base.append("csf")
    if args.global_signal:
        base.append("global_signal")
    cols = list(base)
    if args.tissue_derivatives:
        cols += [f"{c}_derivative1" for c in base]
    if args.tissue_power2:
        cols += [f"{c}_power2" for c in base]
    if args.tissue_derivatives and args.tissue_power2:
        cols += [f"{c}_derivative1_power2" for c in base]
    return select_existing(df, cols, "tissue signals") if cols else []


def compcor_columns(df, args):
    if args.compcor <= 0:
        return []
    prefix = args.compcor_type
    available = sorted(c for c in df.columns if c.startswith(prefix + "_"))
    if not available:
        warn(f"No '{prefix}_*' columns found in file; skipping CompCor.")
        return []
    if args.compcor > len(available):
        warn(f"Requested {args.compcor} {prefix} components but only "
             f"{len(available)} exist; using all {len(available)}.")
    return available[: args.compcor]


def onehot_columns(df, prefix):
    return sorted(c for c in df.columns if c.startswith(prefix))


# --------------------------------------------------------------------------- #
# Spike regressors
# --------------------------------------------------------------------------- #
def make_spike_regressors(df, fd_col, threshold, already_covered):
    """
    One column per volume with FD > threshold (a single 1 at that volume, 0 elsewhere).

    already_covered: set of volume indices that are already modelled by an existing
                     one-hot column (e.g. non-steady-state outliers) -> skipped to
                     avoid exact duplicate regressors.
    Returns (spike_df, info_dict)
    """
    fd = df[fd_col].to_numpy(dtype=float)
    n_nan = int(np.isnan(fd).sum())
    fd = np.nan_to_num(fd, nan=0.0)

    exceed = np.where(fd > threshold)[0]
    skipped = [int(i) for i in exceed if int(i) in already_covered]
    keep = [int(i) for i in exceed if int(i) not in already_covered]

    n = len(df)
    width = max(3, len(str(n - 1)))
    data = {}
    for i in keep:
        col = np.zeros(n)
        col[i] = 1.0
        data[f"spike_vol{i:0{width}d}"] = col

    spike_df = pd.DataFrame(data, index=df.index)
    info = {
        "fd": fd,
        "n_fd_nan": n_nan,
        "all_exceed": [int(i) for i in exceed],
        "kept": keep,
        "skipped_duplicate": skipped,
    }
    return spike_df, info


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def parse_args():
    p = argparse.ArgumentParser(
        description="Convert fMRIPrep confounds to an FSL FEAT-compatible confound "
                    "text file, with optional FD-based spike regressors.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("confounds", type=Path, help="fMRIPrep confounds .tsv file")
    p.add_argument("-o", "--output", type=Path, default=None,
                   help="Output .txt path (default: derived from input name)")

    g = p.add_argument_group("motion")
    g.add_argument("--motion", choices=["none", "6", "12", "24"], default="6",
                   help="Motion model: 6 = rigid-body params; 12 = +temporal derivatives; "
                        "24 = +squares of both (Friston 24)")

    g = p.add_argument_group("physiological / tissue / drift regressors")
    g.add_argument("--wm", action="store_true", help="Include white matter mean signal")
    g.add_argument("--csf", action="store_true", help="Include CSF mean signal")
    g.add_argument("--global-signal", action="store_true", help="Include global signal")
    g.add_argument("--tissue-derivatives", action="store_true",
                   help="Also include temporal derivatives of the selected tissue signals")
    g.add_argument("--tissue-power2", action="store_true",
                   help="Also include squares of the selected tissue signals")
    g.add_argument("--compcor", type=int, default=0, metavar="N",
                   help="Include the first N CompCor components (0 = none)")
    g.add_argument("--compcor-type", default="a_comp_cor",
                   choices=["a_comp_cor", "t_comp_cor", "c_comp_cor", "w_comp_cor"],
                   help="Which CompCor family to take components from")
    g.add_argument("--cosine", action="store_true",
                   help="Include fMRIPrep's cosine drift regressors (skip if you already "
                        "high-pass filter in FEAT)")
    g.add_argument("--non-steady-state", action="store_true",
                   help="Include non_steady_state_outlier## columns (one per dummy scan)")

    g = p.add_argument_group("spike regressors (scrubbing)")
    g.add_argument("--fd-threshold", type=float, default=None, metavar="MM",
                   help="If set, create one spike regressor per volume with FD > MM")
    g.add_argument("--fd-column", default="framewise_displacement",
                   help="Name of the FD column in the confounds file")

    g = p.add_argument_group("misc")
    g.add_argument("-q", "--quiet", action="store_true", help="Suppress verbose output")
    return p.parse_args()


def main():
    args = parse_args()
    q = args.quiet

    # ---- load -------------------------------------------------------------
    if not args.confounds.is_file():
        fail(f"Input file not found: {args.confounds}")
    out_path = args.output or default_output_path(args.confounds)

    try:
        df = pd.read_csv(args.confounds, sep="\t", na_values=["n/a", "NA", "nan", "NaN"])
    except Exception as e:  # noqa: BLE001
        fail(f"Could not read {args.confounds}: {e}")

    n_vols, n_cols_in = df.shape
    say("=" * 72, q)
    say("fMRIPrep -> FSL confound conversion", q)
    say("=" * 72, q)
    say(f"Input file       : {args.confounds}", q)
    say(f"Volumes (rows)   : {n_vols}", q)
    say(f"Columns in file  : {n_cols_in}", q)
    say("", q)

    # ---- select regressors ------------------------------------------------
    groups = {}  # ordered: group name -> list of column names
    groups[f"Motion ({args.motion}-param)"] = motion_columns(df, args.motion)

    tissue = tissue_columns(df, args)
    if tissue:
        groups["Tissue signals"] = tissue

    compcor = compcor_columns(df, args)
    if compcor:
        groups[f"CompCor ({args.compcor_type})"] = compcor

    if args.cosine:
        cos = onehot_columns(df, "cosine")
        if not cos:
            warn("--cosine requested but no cosine## columns found.")
        else:
            groups["Cosine drift"] = cos

    nss = []
    if args.non_steady_state:
        nss = onehot_columns(df, "non_steady_state_outlier")
        if not nss:
            say("  (No non_steady_state_outlier columns in file -> no dummy scans flagged.)", q)
        else:
            groups["Non-steady-state outliers"] = nss

    # drop empty groups
    groups = {k: v for k, v in groups.items() if v}
    selected = [c for cols in groups.values() for c in cols]
    base_df = df[selected].copy() if selected else pd.DataFrame(index=df.index)

    # ---- spike regressors -------------------------------------------------
    spike_df = pd.DataFrame(index=df.index)
    spike_info = None
    if args.fd_threshold is not None:
        if args.fd_threshold < 0:
            fail("--fd-threshold must be non-negative.")
        if args.fd_column not in df.columns:
            fail(f"FD column '{args.fd_column}' not found. "
                 f"Available FD-like columns: "
                 f"{[c for c in df.columns if 'displacement' in c.lower() or c.lower() == 'fd']}")

        # volumes already modelled by an existing single-volume one-hot column
        covered = set()
        for c in nss:
            v = base_df[c].fillna(0).to_numpy()
            if v.sum() == 1:
                covered.add(int(np.argmax(v)))

        spike_df, spike_info = make_spike_regressors(
            df, args.fd_column, args.fd_threshold, covered)

    # ---- assemble ---------------------------------------------------------
    full = pd.concat([base_df, spike_df], axis=1)
    if full.shape[1] == 0:
        fail("No regressors were selected - nothing to write. "
             "Choose at least one of --motion, --wm, --csf, --compcor, --fd-threshold, ...")

    # NaN handling (first-row NaNs in derivatives / FD)
    n_nan = int(full.isna().sum().sum())
    nan_cols = full.columns[full.isna().any()].tolist()
    full = full.fillna(0.0)

    if not np.isfinite(full.to_numpy(dtype=float)).all():
        fail("Non-finite values (inf) found in selected regressors.")

    # ---- write ------------------------------------------------------------
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(out_path, full.to_numpy(dtype=float), fmt="%.6f", delimiter="  ")
    names_path = out_path.with_name(out_path.stem + "_colnames.txt")
    names_path.write_text("\n".join(full.columns) + "\n")

    # ---- report -----------------------------------------------------------
    say("Regressors selected", q)
    say("-" * 72, q)
    for name, cols in groups.items():
        preview = ", ".join(cols[:4]) + (" ..." if len(cols) > 4 else "")
        say(f"  {name:<28}: {len(cols):>3}   [{preview}]", q)

    if spike_info is not None:
        fd = spike_info["fd"]
        n_exceed = len(spike_info["all_exceed"])
        n_kept = len(spike_info["kept"])
        n_skip = len(spike_info["skipped_duplicate"])
        say("", q)
        say(f"Spike regressors (FD > {args.fd_threshold} mm, column '{args.fd_column}')", q)
        say("-" * 72, q)
        say(f"  FD mean / median / max     : {fd.mean():.3f} / {np.median(fd):.3f} / {fd.max():.3f} mm", q)
        say(f"  Volumes exceeding cutoff   : {n_exceed} of {n_vols} "
            f"({100 * n_exceed / n_vols:.1f}%)", q)
        say(f"  Spike regressors created   : {n_kept}", q)
        if n_skip:
            say(f"  Skipped (already modelled) : {n_skip}  "
                f"(volumes {spike_info['skipped_duplicate']})", q)
        if spike_info["n_fd_nan"]:
            say(f"  FD NaNs set to 0           : {spike_info['n_fd_nan']} "
                f"(normally just the first volume)", q)
        if n_kept:
            shown = spike_info["kept"][:40]
            say(f"  Spike volume indices (0-based): {shown}"
                f"{' ...' if n_kept > 40 else ''}", q)
        else:
            say("  No volumes exceeded the cutoff; no spike regressors added.", q)

    n_spikes = spike_df.shape[1]
    n_nonspike = full.shape[1] - n_spikes
    say("", q)
    say("Summary", q)
    say("-" * 72, q)
    say(f"  Non-spike regressors       : {n_nonspike}", q)
    say(f"  Spike regressors           : {n_spikes}", q)
    say(f"  TOTAL regressors           : {full.shape[1]}", q)
    say(f"  Output matrix shape        : {full.shape[0]} rows (volumes) x {full.shape[1]} cols", q)
    say(f"  NaNs replaced with 0       : {n_nan}"
        f"{'  in ' + str(nan_cols[:5]) + (' ...' if len(nan_cols) > 5 else '') if n_nan else ''}", q)
    say(f"  Regressor file             : {out_path}", q)
    say(f"  Column-name sidecar        : {names_path}", q)

    # ---- sanity checks / warnings ----------------------------------------
    say("", q)
    say("Checks", q)
    say("-" * 72, q)
    problems = 0

    const = [c for c in full.columns
             if not c.startswith("spike_") and np.ptp(full[c].to_numpy()) == 0]
    if const:
        problems += 1
        warn(f"{len(const)} constant (zero-variance) column(s): {const[:5]}")

    rank = np.linalg.matrix_rank(full.to_numpy(dtype=float))
    if rank < full.shape[1]:
        problems += 1
        warn(f"Confound matrix is rank-deficient (rank {rank} < {full.shape[1]} columns). "
             f"Check for redundant regressors (e.g. cosine + FEAT high-pass, or "
             f"global signal + WM + CSF).")

    frac = full.shape[1] / n_vols
    if frac > 0.25:
        problems += 1
        warn(f"Confounds use {100 * frac:.0f}% of your degrees of freedom "
             f"({full.shape[1]} regressors / {n_vols} volumes).")
    elif n_spikes and n_spikes / n_vols > 0.20:
        problems += 1
        warn(f"{100 * n_spikes / n_vols:.0f}% of volumes are being scrubbed; consider "
             f"whether this run should be excluded or the cutoff relaxed.")

    if problems == 0:
        say("  All checks passed.", q)

    say("", q)
    say("Done. In FEAT: Stats -> 'Add additional confound EVs' -> select the file above.", q)
    say("(Row count must match the number of volumes in the 4D input to FEAT.)", q)


if __name__ == "__main__":
    main()
