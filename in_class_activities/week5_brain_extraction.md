# In-Class Practical: Skull Stripping with FSL BET (and How fMRIPrep Does It)

**Estimated time:** 40 to 60 minutes
**Tools:** FSL Docker image (the one you pulled for the earlier assignment), FSLeyes, a terminal
**Data:** One T1-weighted anatomical image (`sub-01_T1w.nii.gz`) from the BIDS dataset we used previously

**Useful documentation:**
[BET user guide](https://fsl.fmrib.ox.ac.uk/fsl/docs/structural/bet.html) ·
[FSL course BET practical](https://pages.fmrib.ox.ac.uk/fslcourse/practicals/intro2/index.html) ·
[FSLeyes user guide](https://open.win.ox.ac.uk/pages/fsl/fsleyes/fsleyes/userdoc/) ·
[fMRIPrep usage](https://fmriprep.org/en/stable/usage.html) ·
[fMRIPrep workflows](https://fmriprep.org/en/stable/workflows.html) ·
[ANTs](https://github.com/ANTsX/ANTs)

---

## Background: What Is Skull Stripping?

A T1-weighted image of the head contains much more than brain: skull, scalp, fat, muscle, eyes, sinuses, and often part of the neck and shoulders. **Skull stripping**, also called **brain extraction**, separates the brain from everything else. The result is usually saved two ways: a **brain mask** (a binary image where brain voxels are 1 and everything else is 0) and a **brain-extracted image** (the original image with non-brain voxels set to 0).

Almost every pipeline depends on this step. Non-brain tissue can throw off **registration** to a template, confuse **tissue segmentation**, and distort **cortical thickness and volume** measurements. In functional analyses, the mask often decides which voxels get analyzed at all.

Errors go in two directions. A mask that is **too aggressive** cuts off real brain. A mask that is **too lenient** leaves skull, dura, eyes, or neck attached. Both are common, and both cause problems downstream.

Common approaches include:

- **Intensity and surface based** methods like FSL's [BET](https://fsl.fmrib.ox.ac.uk/fsl/docs/structural/bet.html) (Brain Extraction Tool), which inflates a surface from the center of the head until it reaches the brain's edge. Fast, with a few tunable parameters.
- **Atlas based** methods like [ANTs](https://github.com/ANTsX/ANTs) [`antsBrainExtraction.sh`](https://github.com/ANTsX/ANTs/blob/master/Scripts/antsBrainExtraction.sh) (the approach fMRIPrep uses), which register a template with a known brain mask to your image. Slower, but more consistent across scans.
- **Deep learning** methods like FreeSurfer's [SynthStrip](https://surfer.nmr.mgh.harvard.edu/docs/synthstrip/) or [HD-BET](https://github.com/MIC-DKFZ/HD-BET).

Today you will make BET fail in both directions on purpose, then tune it toward a good result. Then we will look at how fMRIPrep handles the same step.

---

## Learning Objectives

By the end of this session you should be able to:

1. Run FSL's `bet` from a Docker container and check the results visually and numerically.
2. Recognize over-stripping and under-stripping and explain how the `-f` threshold causes each.
3. Identify the fMRIPrep options that control skull stripping and argue for when you would take control of this step yourself.

---

## Part 1: Setup

### 1.1 Make a working folder

```bash
mkdir -p ~/bet_practical/qc
cd ~/bet_practical
cp /path/to/your/bids/sub-01/anat/sub-01_T1w.nii.gz ./T1.nii.gz
```

Replace `/path/to/your/bids` with wherever your dataset lives from the earlier assignment.

### 1.2 Make a script that runs FSL in Docker

Create a file called `fsl.sh` in your `bet_practical` folder with these contents, changing the image name to the one you pulled before (run `docker images` if you have forgotten it):

```bash
#!/bin/bash
# Run any FSL command inside the FSL Docker image.
# Usage: bash fsl.sh <fsl command> <arguments>

FSL_IMAGE="your-fsl-image:tag"   # <-- change this

docker run --rm -v "$PWD":/data -w /data "$FSL_IMAGE" "$@"
```

What this does (see the [`docker run` reference](https://docs.docker.com/reference/cli/docker/container/run/) for details):

- `-v "$PWD":/data` makes your current folder visible inside the container at `/data`.
- `-w /data` runs the command from there.
- `--rm` removes the container when it finishes. Your output files stay.
- `"$@"` passes along whatever FSL command you type after `bash fsl.sh`.

Test it:

```bash
bash fsl.sh fslinfo T1.nii.gz
```

You should see the image dimensions and voxel sizes.

This small wrapper is a convenient pattern for any tool you run from a Docker image. Instead of typing the full `docker run` command with all its options every time, you write it once and reuse it. You can make the same kind of script for other containerized tools later in the course.

> **If you see "command not found":** your image may need the FSL environment loaded first. Replace the `docker run` line with:
> `docker run --rm -v "$PWD":/data -w /data "$FSL_IMAGE" bash -c "source \$FSLDIR/etc/fslconf/fsl.sh && $*"`
>
> **Windows users:** run these commands in WSL rather than Git Bash, which rewrites paths like `/data` and breaks the Docker command.

### 1.3 Look at the raw image

Make a snapshot with `slicer` and count the non-zero voxels in the raw image:

```bash
bash fsl.sh slicer T1.nii.gz -a qc/00_raw.png
bash fsl.sh fslstats T1.nii.gz -V
```

`fslstats -V` prints two numbers. The **first is the number of non-zero voxels** in the image; that is the number we will compare all session. (The second is the same thing in mm³, which you can ignore today.)

The `slicer` picture only shows three slices. For a fuller look, open the image in FSLeyes, which is already installed on your computer, so it does not need Docker:

```bash
fsleyes T1.nii.gz &
```

Scroll through the sagittal, coronal, and axial views. Then answer:

- **Is this image defaced?** Defacing tools remove or blur the face (and sometimes the ears) to protect participant privacy before data are shared. Look at the front of the head in a sagittal slice near the midline. Is the nose, mouth, and chin intact, or has that region been cut away or zeroed out?
- How much neck and shoulder is in the field of view?

### 1.4 The BET options we will use

BET has many options (see the [BET user guide](https://fsl.fmrib.ox.ac.uk/fsl/docs/structural/bet.html)). Today we only need three:

| Option | What it does |
|---|---|
| `-f <0..1>` | Fractional intensity threshold (default 0.5). **Smaller values give a larger brain estimate; larger values give a smaller one.** |
| `-R` | Robust brain center estimation. Runs BET several times to find a better starting point. Helpful when there is a lot of neck in the image. |
| `-m` | Also save a binary brain mask. |

For each run below, you will use three tools:

1. `bet` to strip the brain.
2. `slicer` to save a snapshot with the mask edge drawn in red.
3. `fslstats -V` to count the non-zero voxels in the mask.

Then you will open the result in FSLeyes for a closer look.

---

## Part 2: Deliberately Too Aggressive

```bash
bash fsl.sh bet T1.nii.gz T1_brain_aggressive -f 0.8 -m
bash fsl.sh slicer T1.nii.gz T1_brain_aggressive_mask.nii.gz -a qc/01_aggressive.png
bash fsl.sh fslstats T1_brain_aggressive_mask.nii.gz -V
```

Write down the number of non-zero voxels. Then look at the mask on top of the original image in FSLeyes:

```bash
fsleyes T1.nii.gz T1_brain_aggressive_mask.nii.gz -cm red -a 40 &
```

This shows the mask in red at 40% opacity. Use the eye icon in the overlay list to toggle the mask on and off. Check the top of the brain, the occipital pole, the temporal lobes, and the cerebellum.

**Question:** Which regions were lost? If you measured gray matter volume on data stripped like this, which direction would the bias go?

---

## Part 3: Deliberately Too Lenient

Now write the three commands yourself, modeled on Part 2, with these changes:

- Use `-f 0.11 -m` (a very low threshold).
- Name the output `T1_brain_lenient`, so the mask is `T1_brain_lenient_mask.nii.gz`.
- Save the snapshot as `qc/02_lenient.png`.

Open the result in FSLeyes the same way. Look for skull, scalp, eyes, sinuses, and neck inside the mask.

**Question:** How does the non-zero voxel count compare with the aggressive mask, and with the raw image from Part 1? Name one downstream step that leftover skull and neck would hurt.

---

## Part 4: Zooming In on Reasonable Settings

### 4.1 Sweep a few thresholds

Run BET with robust center estimation at three thresholds using a bash `for` loop:

```bash
for f in 0.3 0.4 0.5; do
  echo "Threshold: $f"
  bash fsl.sh bet T1.nii.gz T1_brain_R_f${f} -R -f ${f} -m
  bash fsl.sh slicer T1.nii.gz T1_brain_R_f${f}_mask.nii.gz -a qc/03_R_f${f}.png
  bash fsl.sh fslstats T1_brain_R_f${f}_mask.nii.gz -V
done
```

Each time through the loop, `$f` takes the next value in the list, so the same three commands run with a different threshold and save to different file names. Feel free to add values of your own.

> **If the neck is causing trouble: `robustfov`**
>
> If your masks keep leaking into the neck no matter the threshold, the field of view may include too much below the brain. FSL's `robustfov` crops the image to remove the lower head and neck before stripping:
>
> ```bash
> bash fsl.sh robustfov -i T1.nii.gz -r T1_crop.nii.gz
> ```
>
> You would then run BET on `T1_crop.nii.gz` instead. Keep in mind that the cropped image has a different voxel grid than the original, so a mask made from it will not line up with `T1.nii.gz` without resampling. That matters if you later want to use the mask in another pipeline (see Part 5).

### 4.2 Check in FSLeyes and choose

Open the original image with all three sweep masks loaded:

```bash
fsleyes T1.nii.gz \
  T1_brain_R_f0.3_mask.nii.gz -cm red -a 40 \
  T1_brain_R_f0.4_mask.nii.gz -cm green -a 40 \
  T1_brain_R_f0.5_mask.nii.gz -cm blue -a 40 &
```

Toggle the masks on and off to compare them. Scroll through all three planes, paying attention to:

- the top of the brain
- the orbitofrontal cortex above the eyes
- the inferior temporal lobes
- the cerebellum

Fill in this table:

| Run | Settings | Non-zero voxels | Brain lost? (where) | Non-brain kept? (where) |
|---|---|---|---|---|
| Raw image | none | | n/a | n/a |
| Aggressive | `-f 0.8` | | | |
| Lenient | `-f 0.11` | | | |
| Sweep | `-R -f 0.3` | | | |
| Sweep | `-R -f 0.4` | | | |
| Sweep | `-R -f 0.5` | | | |

**Pick your best mask** and justify it in one or two sentences based on what you saw. The voxel count alone is not enough: two masks with the same count can be wrong in completely different places.

---

## Part 5: How fMRIPrep Handles Skull Stripping (reading)

You do **not** need to run fMRIPrep today.

fMRIPrep does not use BET for the anatomical image. It uses an implementation of [ANTs](https://github.com/ANTsX/ANTs) [`antsBrainExtraction`](https://github.com/ANTsX/ANTs/blob/master/Scripts/antsBrainExtraction.sh), an **atlas-based** method that registers a template brain mask to your T1w image and refines the result with tissue segmentation. When FreeSurfer is enabled, fMRIPrep skips FreeSurfer's own skull stripping and hands it this mask instead, so one mask drives both the volumetric and surface pipelines. The [fMRIPrep workflows page](https://fmriprep.org/en/stable/workflows.html) describes this in more detail.

The options that control this are listed on the [fMRIPrep usage page](https://fmriprep.org/en/stable/usage.html). Check `fmriprep --help` for your version, since options change between releases.

| Option | What it controls |
|---|---|
| `--skull-strip-t1w {auto,skip,force}` | Whether to strip at all. `force` (default) always strips, `skip` assumes the T1w is already stripped, `auto` guesses. |
| `--skull-strip-template <TEMPLATE>` | Which [TemplateFlow](https://www.templateflow.org/) template to use as the prior. Default is `OASIS30ANTs`. |
| `--skull-strip-fixed-seed` | Removes randomness in the ANTs registration so repeated runs match (with `--omp-nthreads 1` and a fixed `--random-seed`). |
| `--derivatives <PATH>` | Points to precomputed derivatives in BIDS Derivatives format. A brain mask found here can be used instead of computing a new one. |
| `--fs-subjects-dir <PATH>` | Reuses an existing (possibly hand-edited) FreeSurfer subjects directory. |

To plug in your own mask, you would save it as `sub-01/anat/sub-01_desc-brain_mask.nii.gz` inside a folder with a `dataset_description.json` that includes `"DatasetType": "derivative"`, then pass that folder to `--derivatives`. The mask must be on the same voxel grid as the original T1w.

---

## Part 6: Small-Group Discussion

In groups of three or four, discuss the questions below. Be ready to share one answer with the class.

1. **When does the default struggle?** Describe a dataset where fMRIPrep's default skull stripping might fail. Consider children, older adults with atrophy, lesions or tumors, unusual contrasts, or heavy motion.
2. **Change the template or replace the mask?** For a study of 6-year-olds, would you change `--skull-strip-template` to a better-matched template, or tune masks outside fMRIPrep and supply them through `--derivatives`? Weigh time, reproducibility, and how clearly you could describe each in a methods section.
3. **Tuning outside the pipeline.** What do you gain by tuning a skull strip yourself and plugging it in? What new risks does it bring? (Think about grid alignment, using consistent settings for every participant, and whether someone else could reproduce your work.)
4. **Scaling up.** Tuning one subject took a good part of this session. Your study has 300. How would you keep quality high without tuning every scan by hand?

---

## Deliverables

Submit two files:

1. **`fsl.sh`** from Part 1.
2. **`lastname_bet_practical.md`**, a single markdown document containing:
   - **Part 4:** your completed table and your one- or two-sentence justification for the mask you chose as best.
   - **Part 6:** a response to each of the four discussion questions. One sentence each is enough.

Parts 2, 3, and 5 are for in-class work and do not need to be turned in.