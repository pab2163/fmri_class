# Week 6 Practical: Head Motion Correction

**Data:** dataset ds000114 `sub-01`, `ses-test`, task `overtwordrepetition` (the same run we used previously)

**Tools:** Docker (fMRIPrep image, for FSL's `mcflirt`), Python (numpy, pandas, matplotlib, nibabel), FSLeyes

## Learning objectives

By the end of this practical you should be able to:

1. Run FSL's [`mcflirt`](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/mcflirt.html) to realign every volume of a 4D fMRI run to a reference volume. This is the tool used by fMRIPrep by default under the hood.
2. Explain how the choice of reference volume (`-refvol` vs `-meanvol`) affects the output.
3. Plot and interpret the rotation and translation timeseries that `mcflirt` produces.
4. Calculate [Power framewise displacement (FD)](https://pmc.ncbi.nlm.nih.gov/articles/PMC3254728/) from the `.par` file, and discuss what FD means.
5. Visually compare raw and motion-corrected volumes in FSLeyes.
6. Quantify the effect of motion correction on temporal SNR (tSNR).

---

## 1. Run `mcflirt` inside the fMRIPrep Docker image

`mcflirt` is FSL's motion correction tool. The name stands for **M**otion **C**orrection using **F**MRIB's **L**inear **I**mage **R**egistration **T**ool. It is FLIRT (FMRIB's Linear Image Registration Tool) applied to every volume of a 4D run in turn, registering each volume to a reference volume with a rigid-body transformation (3 rotations + 3 translations).

The fMRIPrep image ships with FSL, so we can use `mcflirt` without installing FSL locally. By default the image's *entrypoint* is `fmriprep`, so we override it to get a normal shell.

First, on your own machine, set up some variables (**edit the paths to match your machine**) and start an interactive container, mounting your data (read-only) and your output folder:

```bash
# Folder that contains your BIDS dataset (the one containing sub-01/)
export BIDS=/path/to/your/bids_dataset

# Folder where you want practical outputs to go
export OUT=[somewhere in your class folder to put these outputs]
mkdir -p $OUT

# Start the container
docker run --rm -it \
    --entrypoint bash \
    -v $BIDS:/data:ro \
    -v $OUT:/out \
    nipreps/fmriprep:<VERSION>      # use the version you used in the previous practical
```


You are now *inside* the container. Check that FSL is available:

```bash
which mcflirt
mcflirt            # prints the usage message which tells you the mcflirt tool is available
```

Now run motion correction:

```bash
mcflirt \
    -in   /data/sub-01/ses-test/func/sub-01_ses-test_task-overtwordrepetition_bold.nii.gz \
    -out  /out/sub-01_ses-test_task-overtwordrepetition_moco \
    -refvol 0 \
    -plots \
    -report
```

What do the flags do?

| Flag | Meaning |
|------|---------|
| `-in` | The 4D image to correct |
| `-out` | Output basename (`.nii.gz` is added). The corrected 4D image is written here |
| `-plots` | Save the six motion parameters to a `.par` file |
| `-report` | Print progress messages |

When it finishes, leave the container:

```bash
ls /out
exit
```

Back on your own machine, look in `$OUT`. You should see:

```
sub-01_ses-test_task-overtwordrepetition_moco.nii.gz   <- motion-corrected 4D image
sub-01_ses-test_task-overtwordrepetition_moco.par      <- the 6 motion parameters per volume
```

> **Why no plots?** `mcflirt` can normally draw its own PNG plots of the motion parameters, but it relies on a separate FSL tool (`fsl_tsplot`) that isn't included in the fMRIPrep image. That's fine. The `.par` file is the important output, and you'll plot it yourself in Python in section 2.

### Choosing the reference volume

`mcflirt` registers every volume to a **reference**, so it needs to know which one. You've just used the default, which is the **middle volume** of the run. There are other options:

| Option | What it does |
|---|---|
| *(default)* | Use the middle volume of the run |
| `-refvol N` | Use volume number `N` as the reference (**0-indexed**, so `-refvol 0` is the first volume) |
| `-meanvol` | Register everything to the **mean image** of the whole timeseries |
| `-reffile image.nii.gz` | Use a separate 3D image as the reference (overrides the two options above) |

Which should you pick? They each have trade-offs:

- **Middle volume (default).** It is a real volume that was actually acquired, and it is, on average, as close in time as possible to every other volume. This matters if the head slowly drifts: with a middle reference the drift is split either side, so the maximum displacement is roughly halved compared with using the first or last volume. The weakness is that it is a single noisy volume, and if the participant happened to move during that volume it is a poor reference.
- **First volume (`-refvol 0`).** Easy to explain and often used for historical reasons, but the first volumes of a run can be affected by the scanner not having reached steady state (they can have a different brightness and contrast to the rest of the run), which makes them a poor target. Drift is also maximal at the far end of the run.
- **Mean volume (`-meanvol`).** The mean averages out the noise in individual volumes, so it is a more stable, higher-SNR target. The downsides are that the mean of a run with a lot of motion is slightly blurred, and that *no* volume sits exactly at the reference position, so no volume will have motion parameters of exactly zero.
- **External reference (`-reffile`).** Useful if you want to align to something specific, for example a single-band reference image or a reference shared between runs. fMRIPrep generates its own BOLD reference image (usually a median image) and registers to that rather than the middle volume.

The important thing to take away is that **the reference you choose changes the *absolute* motion parameters** (the whole trace is shifted, so that "zero" means "same position as the reference"), **but changes framewise displacement very little**, because FD only looks at volume-to-volume differences. You'll see this yourself in section 3.5.

### Checkpoint questions

- How many volumes are in the run? (Hint: `fslnvols`, or `nib.load(...).shape`.) How many rows are in the `.par` file? Should those numbers match?
- Which volume was used as the reference? What would you expect the motion parameters to be for that volume?

---

## 2. Plot the motion parameters and think about what the timeseries mean

### What's in the `.par` file?

The `.par` file is a plain text table with **one row per volume** and **six columns**:

| Column | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Parameter | rot x (pitch) | rot y (roll) | rot z (yaw) | trans x | trans y | trans z |
| Units | **radians** | **radians** | **radians** | **mm** | **mm** | **mm** |

(For a standard axial acquisition: x is left-right, y is anterior-posterior, z is inferior-superior. So rot x is "nodding yes", rot y is "tilting ear to shoulder", rot z is "shaking head no".)

```bash
head $OUT/sub-01_ses-test_task-overtwordrepetition_moco.par
```

### Plot it in Python

Start up a jupyter notebook and load the `.par` file. Remember to use the `fmri_class` conda environment you set up a few weeks ago as the kernel! 

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

par_file = "moco_practical/sub-01_ses-test_task-overtwordrepetition_moco.par"   # edit path

# Load the .par file (whitespace-delimited, no header)
cols = ["rot_x", "rot_y", "rot_z", "trans_x", "trans_y", "trans_z"]
par = pd.read_csv(par_file, sep=r"\s+", header=None, names=cols)
print(par.shape)
par.head()
```

Now plot the six parameters. Rotations are converted from radians to degrees so they are easier to read:

```python
fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

ax[0].plot(np.degrees(par[["rot_x", "rot_y", "rot_z"]]))
ax[0].set_ylabel("Rotation (degrees)")
ax[0].legend(["x (pitch)", "y (roll)", "z (yaw)"])

ax[1].plot(par[["trans_x", "trans_y", "trans_z"]])
ax[1].set_ylabel("Translation (mm)")
ax[1].set_xlabel("Volume")
ax[1].legend(["x (L-R)", "y (A-P)", "z (I-S)"])

plt.tight_layout()
```

### Things to think about while looking at the plots

Write short answers (a sentence or two each) in your notes:

1. **Scale.** What are the maximum values of rotation (in degrees) and translation (mm)? Compare to your voxel size. Is the biggest translation less than one voxel? More than one?
2. **Shape.** Do you see a *slow drift* (the head gradually sinking or rotating over minutes), *sudden jumps* (a single movement that is then held in the new position), or *brief spikes* (a movement that returns quickly)? These have different causes, and different consequences for your data.
3. **Which axis moves most?** Head motion is usually dominated by z translation and x rotation (nodding), because the head tends to sink into the cushion and pitch around the neck. Is that true here?
4. **Coupling.** Do the translation and rotation lines tend to move at the same time? Why might they? (Think about where the head pivots relative to the centre of the scanner.)

---

## 3. Calculate Power framewise displacement (FD)

The six parameters tell you *where the head is* at each volume. For quality control we usually want a single number per volume that says *how much the head moved*. [Power et al. (2012)](https://doi.org/10.1016/j.neuroimage.2011.10.018) defined framewise displacement for this purpose.

### 3.1 The idea: a relative measure

The `.par` file values are **absolute** with respect to the reference volume: "at volume 80, the head is 1.2 mm further along z and rotated by 0.01 rad compared to the reference volume."

**FD is relative.** It asks: *how far did the head move between volume *t-1* and volume *t*?* It is built from **differences** between consecutive rows of the `.par` file.

Why does this matter? Imagine two runs:

- **Run A:** the head is 3 mm away from the reference for the whole run, perfectly still.
- **Run B:** the head sits at the reference position but jerks 3 mm and back every other volume.

Run A has big *absolute* displacement but FD ≈ 0 everywhere (the head isn't moving). Run B has small absolute displacement but massive FD. Run B is the one that will wreck your data: signal in a voxel is being mixed with signal from its neighbour and the spin history of the tissue is being disturbed from volume to volume. FD is a better index of this than absolute position.

Consequences of being relative:

- **Slow drift is nearly invisible to FD.** A 5 mm drift over 10 minutes gives an FD of only a few hundredths of a mm per volume. (The absolute position plots from section 2 would show it clearly, so look at both.)
- **A single step movement produces one FD spike** (at the volume where the step occurred), not a long elevated period.
- **The reference volume you picked doesn't matter** for FD (shifting every row by a constant cancels out in the differences). It *does* matter for absolute position. You'll check this in section 3.5.
- **The first volume has no previous volume**, so FD is undefined; by convention we set it to 0.

### 3.2 The formula

For volume *t*, with six parameters (*x, y, z, α, β, γ*) where *x, y, z* are translations in mm and *α, β, γ* are rotations in radians:

$$
\mathrm{FD}_t = |\Delta x_t| + |\Delta y_t| + |\Delta z_t| + r\,|\Delta \alpha_t| + r\,|\Delta \beta_t| + r\,|\Delta \gamma_t|
$$

where

$$
\Delta x_t = x_{t-1} - x_t \quad (\text{and similarly for } y,z,\alpha,\beta,\gamma)
$$

and *r* = 50 mm.

In words: **add up how much each of the six parameters changed since the last volume, in millimetres.** Absolute values are used so that movements in opposite directions don't cancel.

### 3.3 Why do we multiply rotations by 50 mm?

Translations are already in mm, but rotations are in radians, and you can't add radians to millimetres. We need to convert each rotation into "how far did a point on the brain surface move because of this rotation?"

For a small rotation of *θ* radians about the origin, a point at distance *r* from the axis moves along an arc of length

$$
s = r\,\theta
$$

(this is just the definition of a radian: arc length = radius × angle).

So we need to pick a value of *r*. Power et al. chose **50 mm**, which is roughly the distance from the centre of the head to the surface of the cortex. This means FD is approximately "the distance moved by a point on the cortical surface" summed over axes.

Things to keep in mind about this assumption:

- It is a **convention**, not a measurement. A different head size, or the choice of a different centre of rotation, would give different FD values.
- It is a **small-angle approximation** (fine for the few-degree rotations we see in practice).
- It treats the three rotation axes identically, even though for real heads the distance of the cortex from each axis is different, and in children the radius is smaller (people sometimes use ~40 mm for paediatric data).
- Because it adds absolute values across axes (a "city block" or L1 distance) rather than combining them as a Euclidean distance, FD is *not* the same as the actual displacement of a point. It is a convenient upper-ish bound.
- FSL has its own RMS-based displacement measure (`rel.rms`, from the `-rmsrel` flag, which we are not using here). It is a different metric (RMS displacement within a brain-sized sphere), so don't expect it to match FD numerically, though the two should be highly correlated.

### 3.4 Now do it in Python

Continue in the same Python session, where `par` is already loaded. Fill in the blanks marked `TODO`.

```python
radius = 50  # mm. The assumed head radius used to convert radians to mm of arc length

# TODO (a): convert the three rotation columns from radians to mm of arc length
#           (arc length = radius * angle)
par_mm = par.copy()
rot_cols = ["rot_x", "rot_y", "rot_z"]
par_mm[rot_cols] = ______________________

# TODO (b): take the difference between each volume and the previous one.
#           Hint: pandas has a .diff() method
delta = ______________________

# TODO (c): take absolute values and sum across the six columns (axis=1)
fd = ______________________

# The first volume has no predecessor, so .diff() gives NaN. By convention FD = 0.
fd = fd.fillna(0)
```

<details>
<summary>Solution</summary>

```python
radius = 50
par_mm = par.copy()
rot_cols = ["rot_x", "rot_y", "rot_z"]
par_mm[rot_cols] = par[rot_cols] * radius

delta = par_mm.diff()
fd = delta.abs().sum(axis=1)
fd = fd.fillna(0)
```

</details>

Plot your FD and add threshold lines:

```python
plt.figure(figsize=(10, 3))
plt.plot(fd)
plt.axhline(0.5, color="r", ls="--", label="0.5 mm (liberal)")
plt.axhline(0.2, color="orange", ls="--", label="0.2 mm (stringent)")
plt.xlabel("Volume")
plt.ylabel("FD (mm)")
plt.legend()
plt.tight_layout()

print(f"Mean FD:   {fd.mean():.3f} mm")
print(f"Max FD:    {fd.max():.3f} mm")
print(f"Volumes with FD > 0.5 mm: {(fd > 0.5).sum()} ({(fd > 0.5).mean()*100:.1f}%)")
print(f"Volumes with FD > 0.2 mm: {(fd > 0.2).sum()} ({(fd > 0.2).mean()*100:.1f}%)")
```

### Questions

1. What is the mean FD for this run? Is that typical for a cooperative adult participant (roughly 0.1-0.2 mm) or high?
2. Where are the largest FD spikes? Find the corresponding volume numbers in your translation/rotation plot from section 2. Do they correspond to a step, a spike, or both?
3. Look at FD for **volumes 55-62** (`fd.iloc[55:63]`). Is there a high-motion event in or near this window? Keep this in mind for the next section.
4. Compare your FD plot to the motion parameter plots from section 2. Describe one thing that is easy to see in one and not in the other.
5. **Thought experiment:** you re-run `mcflirt` with `-refvol 0` instead of the middle volume. Which would change, the absolute motion parameters or FD? Write down your prediction, then test it in 3.5.
6. **Thought experiment:** you set `radius = 80` instead of 50. Would FD go up or down? Which component (translation or rotation) would be affected?



## 4. Look at the raw vs. motion-corrected data in FSLeyes

Now let's see what motion correction actually does to the images. Use the motion-corrected image from your first (default reference) run.

Open FSLeyes with the raw and corrected images (run this on your own machine, not in Docker):

```bash
fsleyes \
    $BIDS/$BOLD \
    $OUT/sub-01_ses-test_task-overtwordrepetition_moco.nii.gz &
```

1. In the **Overlay list**, the **top** image is displayed on top. Make sure the images have the **same display range** (same min and max brightness) so you're comparing like with like. You can set these in the display settings panel (the sliders button at the top).
2. Change the colour map of the moco image to something that stands out (e.g. *Red-Yellow*), or just toggle the eye icon on and off to flick between them.
3. Use the **Volume** control in the bottom toolbar to go to frames **55 to 62**.
   - ⚠️ FSLeyes volume numbers are **0-indexed**, the same as in Python and in the `.par` file. So "frame 55" means volume number 55 in the box, which is **row 55** (the 56th row) of your `.par` file.
4. For each frame in that range, look at one or two distinctive landmarks, for example the edge of the brain at the top of the cortex, the ventricles, the eyes, or the edge of the cerebellum. Place the crosshairs on the landmark and then step through frames.

### Questions

1. Do the raw and moco images look different in frames 55-62? In which frames is the difference most obvious? Does that match what you found in the FD trace?
2. Looking at the **raw** image only: step through frames 55-62. Does the position of the landmark visibly move? How many voxels?
3. Looking at the **moco** image only: does the landmark stay put?
4. Can you see any side effects of motion correction (e.g., slightly blurrier images or black "borders" where the volume was shifted in)? Why does this happen? (Hint: `mcflirt` resamples the data using interpolation.)
5. If a participant moves their head by 2 mm *during* a single volume acquisition, can volume realignment fix that volume? Why or why not?

---

## 5. Did motion correction change tSNR?

### 5.1 What is tSNR?

Temporal SNR, for each voxel, is

$$
\mathrm{tSNR} = \frac{\text{mean of the signal over time}}{\text{standard deviation of the signal over time}}
$$

A voxel in the brain should have a fairly constant baseline signal (the BOLD fluctuations are only a few percent). If the head moves, the voxel is sampling different tissue at different times, which adds variance and **lowers tSNR**. A good motion correction should therefore **increase** tSNR, especially at tissue boundaries where signal changes sharply with position.

### 5.2 Run the script

The script `tsnr_compare.py` is provided with this practical. It:

1. loads the original and motion-corrected 4D images,
2. computes tSNR maps for both,
3. computes the ratio **moco tSNR / original tSNR** (so values above 1 mean motion correction improved tSNR, values below 1 mean it got worse), and
4. saves all three maps as NIfTI files, plus prints a short summary.


Then run:

```bash
python tsnr_compare.py \
    [your raw BOLD file before motion correction] \
    [your output motion-corrected BOLD file ] \
    $OUT/sub-01
```

What do you notice about the printouts about the raw vs. motion-corrected tSNR?

This script also creates `sub-01_tsnr_orig.nii.gz`, `sub-01_tsnr_moco.nii.gz` and `sub-01_tsnr_ratio.nii.gz` in your `$OUT` folder.

### 5.3 Look at the tSNR maps

Open the tSNR maps in fsleyes to see if you notice any patterns for where tSNR was impacted by motion correction. 

```bash
fsleyes \
    $OUT/sub-01_tsnr_orig.nii.gz \
    $OUT/sub-01_tsnr_moco.nii.gz \
    $OUT/sub-01_tsnr_ratio.nii.gz &
```

Tips:

- Give the original and moco tSNR maps the **same display range** (e.g. 0 to 100).
- For the **ratio** map, use a diverging or heat colour map and set the display range to roughly **0.8 to 1.2**. That puts "no change" (1.0) in the middle, so improvements and degradations are visually distinct. 

### Questions

1. Is overall tSNR higher after motion correction? By roughly how much (see the printed medians)?
2. **Where in the brain has tSNR changed the most?** Look at the ratio map. Consider:
   - the **edges of the brain** (brain/CSF/skull boundary),
   - the **ventricles**,
   - **deep grey matter and white matter**,
   - areas near the **sinuses** and **ear canals** (where there is susceptibility distortion).
3. Why would you expect tSNR improvement to be largest at tissue boundaries and smallest in the middle of homogeneous tissue?
4. Are there any places where tSNR got **worse** (ratio < 1)? Propose one reason why motion correction could lower tSNR in some voxels. (Hints: interpolation smooths the data; the images were corrected for rigid-body motion but the head's *distortion* changes with position; some voxels at the edge of the field of view get shifted out or in.)

---

## 6. Wrap-up

Write a short (5-10 sentence) summary of the motion & motion correction in this run that you could put in the "methods/QC" section of a paper. It should include:

- the software used and reference volume,
- the mean and max FD, and the number/percentage of volumes above your chosen FD threshold,
- whether this run would pass a typical exclusion criterion (e.g. mean FD < 0.5 mm, or fewer than 20% of volumes with FD > 0.5 mm), and
- the effect of motion correction on tSNR.

### Things to take away

- `mcflirt` outputs **absolute** position relative to a reference volume; **FD is relative** (volume-to-volume change) and is built from differences between consecutive rows.
- The **reference volume** (middle by default, or `-refvol N`, `-meanvol`, `-reffile`) changes the absolute motion parameters but usually has very little effect on FD.
- Rotations are converted to mm by arc length using an assumed **50 mm head radius**, a convention rather than a measurement.
- Rigid-body realignment can put brain voxels back in alignment, which typically **raises tSNR at tissue boundaries**, but it cannot remove all motion-related artefacts (within-volume motion, spin-history effects, and distortion changes remain), which is why FD is still used for scrubbing and as a nuisance regressor.

### Submit on Canvas

Your short written responses to the questions above as a single file