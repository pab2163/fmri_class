#!/usr/bin/env python3
"""
tsnr_compare.py

Compute temporal SNR (tSNR) for an original and a motion-corrected 4D image,
then compute the voxelwise ratio moco / original.

    tSNR = mean over time / standard deviation over time

Usage:
    python tsnr_compare.py ORIG.nii.gz MOCO.nii.gz OUTPUT_PREFIX

Outputs:
    OUTPUT_PREFIX_tsnr_orig.nii.gz
    OUTPUT_PREFIX_tsnr_moco.nii.gz
    OUTPUT_PREFIX_tsnr_ratio.nii.gz   (moco / orig; >1 means moco improved tSNR)
"""
import sys
import numpy as np
import nibabel as nib


def tsnr(img):
    data = img.get_fdata(dtype=np.float32)
    mean = data.mean(axis=-1)
    sd = data.std(axis=-1, ddof=1)
    out = np.zeros_like(mean)
    # Only compute where there is signal and variance (avoids divide-by-zero
    # in the background, where both mean and sd are ~0)
    ok = (sd > 0) & (mean > 0)
    out[ok] = mean[ok] / sd[ok]
    return out, mean


def main(orig_path, moco_path, prefix):
    orig = nib.load(orig_path)
    moco = nib.load(moco_path)

    if orig.shape != moco.shape:
        sys.exit(f"Shape mismatch: {orig.shape} vs {moco.shape}")

    tsnr_orig, mean_orig = tsnr(orig)
    tsnr_moco, _ = tsnr(moco)

    # Crude brain mask: voxels brighter than 20% of the 98th percentile
    # of the mean image. Good enough for a summary; not a real brain mask.
    thr = 0.2 * np.percentile(mean_orig[mean_orig > 0], 98)
    mask = mean_orig > thr

    ratio = np.zeros_like(tsnr_orig)
    ok = mask & (tsnr_orig > 0)
    ratio[ok] = tsnr_moco[ok] / tsnr_orig[ok]

    for name, arr in [("tsnr_orig", tsnr_orig),
                      ("tsnr_moco", tsnr_moco),
                      ("tsnr_ratio", ratio)]:
        nib.save(nib.Nifti1Image(arr, orig.affine, orig.header),
                 f"{prefix}_{name}.nii.gz")

    print(f"Voxels in crude mask:      {mask.sum()}")
    print(f"Median tSNR  original:     {np.median(tsnr_orig[mask]):.2f}")
    print(f"Median tSNR  motion-corr.: {np.median(tsnr_moco[mask]):.2f}")
    r = ratio[ok]
    print(f"Median ratio (moco/orig):  {np.median(r):.3f}")
    print(f"Voxels with ratio > 1.05:  {(r > 1.05).mean() * 100:.1f}%")
    print(f"Voxels with ratio < 0.95:  {(r < 0.95).mean() * 100:.1f}%")
    print(f"Saved maps with prefix:    {prefix}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])