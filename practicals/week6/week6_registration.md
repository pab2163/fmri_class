# Practical #6: Registration

**Registering EPI → T1 and T1 → MNI**

**Assumptions from prior assignments:** You have the `ds000114/rawdata` BIDS folder from earlier practicals, and you are working with `sub-01`, `ses-test`, and the `overtwordrepetition` task.

**A note on file paths:** as before, any path like `/users/yourname/documents/fmri_class/...` is a placeholder. Replace it with where these folders actually live on *your* computer.

---

## What you will submit

Your submission is just two things:

1. **2 Final `slicer` overlay images** for your two registrations (EPI → T1 and T1 → MNI).
2. **A short written reflection** on the registration process 

Everything else in this document (BrainSwipes, the questions in each part, your scripts) is for your own learning. Keep your scripts, even though you don't submit them!

---

## Part A: Train Your Eye with BrainSwipes

First, it is important to develop skills to be able to visually check registrations, and differentiate good ones from bad ones. [BrainSwipes](https://brainswipes.us) is a crowdsourced quality-assessment web app for neuroimaging data: you look at an image and swipe left or right to mark it Pass or Fail. Large studies use it to screen registrations by eye, and you will use the same skills to check your own results later.

Complete two short tutorials (about 15 to 20 minutes total). You may need to set up an account (free) on BrainSwipes to do this.

Note: you don't actually have to do any "swiping" for this assignment but you're welcome to try!

| Tutorial | Link | What it teaches |
|----------|------|-----------------|
| **Functional registration** | <https://brainswipes.us/tutorial/func> | Judging whether a functional (EPI/BOLD) image is aligned to the structural (T1) image |
| **Atlas registration** | <https://brainswipes.us/tutorial/atlas> | Judging whether a structural (T1) image is aligned to a standard atlas/template such as MNI |

These map onto the two registrations you will build below: functional registration is **EPI → T1** (Part 1), and atlas registration is **T1 → MNI** (Part 2).


>### As you go through the tutorials, make sure you feel comfortable with the below:
>
>1. Which two images are overlaid, and what is drawn on top of what?
>2. What does a **passing** registration look like?
>3. What does a **failing** one look like? List every type of failure the tutorial shows.
>4. Which brain regions or landmarks help to evaluate registration quality?


---

## Registration Overview

Registration is how we get images from different modalities, sessions, and subjects into a shared coordinate space (e.g., 'aligning them'). In this assignment you will build the two most important links in the standard fMRI registration chain:

```
EPI (functional)  ──►  T1 (structural)  ──►  Template space (e.g., MNI Space)
        Part 1                  Part 2
```

Then you will combine them (Part 3) and **check that the registrations actually worked** (Part 3 and Part 4).

> **Why QA matters:** fMRIPrep and other software will happily produce an output file even when the registration is badly wrong. A successful exit code tells you nothing about registration quality. *We often need to rely on our own eyes for this!*

### Learning objectives

By the end of this assignment you should be able to:

1. Judge registration quality by eye, using Pass/Fail criteria you can justify (Part A).
2. Prepare inputs for registration (mean EPI volume, brain-extracted T1).
3. Register an EPI to a T1 using FSL's `epi_reg` (boundary-based registration).
4. Register a T1 to the MNI152 template using a FSL-based linear (`flirt`) then nonlinear (`fnirt`) pipeline.
5. Concatenate transforms and resample data into standard space in a single interpolation step.
6. Visually inspect your registrations using FSLeyes and `slicer`.

### Prerequisites

- FSL installed
- FSLeyes available (`fsleyes --version`)
- Familiarity with BIDS layout and the `bet` tool for brain extraction
- The `ds000114` BIDS dataset from prior assignments (`ds000114/rawdata`)

> Note: you *can* use your fMRIPrep Docker image to run the FSL commands in this practical (the image includes FSL). Start a shell in the container with your course folder mounted **at the same path inside the container**, so the paths in your scripts work unchanged:
>
> ```bash
> docker run --rm -it --entrypoint bash \
>   -v /users/yourname/documents/fmri_class:/users/yourname/documents/fmri_class \
>   -w /users/yourname/documents/fmri_class/registration_practical \
>   nipreps/fmriprep:25.2.5
> ```
>
> FSLeyes is *not* in that image, so you would still need a viewer on your own computer to look at the results (FSLeyes, or any NIfTI viewer you already use).

---

## Background: Types of Registration

> ### Note: registration terminology
>
> The same steps go by different names depending on the software and paper you are reading:
>
> | Step | Common terms | How fMRIPrep refers to it |
> |------|--------------|---------------------------|
> | **EPI → T1** (functional to structural, same person) | **Co-registration**, functional-to-structural registration | "**Co-registration**": the BOLD reference is co-registered to the T1w reference |
> | **T1 → template** (structural to standard space, across people) | **Normalization**, spatial normalization, standardization | "**Spatial normalization**" of the T1w to a template (e.g., `MNI152NLin2009cAsym`) |
>
> - **Co-registration** means aligning images *of the same subject* (usually from different modalities or scans, like an EPI and a T1). The brain isn't changing shape, which is why it is typically a 6-DOF (rigid-body) problem.
> - **Normalization** means warping a subject's brain into a *common template space* so different people can be compared. Brains differ in shape, which is why it needs more flexible (affine + nonlinear) transformations.
> - fMRIPrep also refers to the T1 as the **T1w reference** (`T1w`), and its outputs are labelled by the space they are in, e.g., "preprocessed BOLD in `T1w` space" or "in `MNI152NLin2009cAsym` space". When you read a methods section, translating these into "EPI → T1" and "T1 → template" will help you follow the pipeline.
> - **The template does not have to be MNI.** We use an MNI template in this practical because it is the most common choice, but *MNI is just one option*. A template could be a study-specific average of your own participants, an age-specific template (e.g., pediatric or older-adult), or a template for another species.

### Linear registration and degrees of freedom

A **linear (affine)** registration applies one transformation, a single matrix, to the whole image. The **degrees of freedom (DOF)** are the number of independent parameters it may adjust. You set this with `flirt -dof` ([FLIRT User Guide](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/flirt/user_guide.html)).

| DOF | Allows | Use when |
|-----|--------|----------|
| **6** (rigid-body) | 3 translations + 3 rotations | Same brain, so no change in shape (EPI → T1) |
| **12** (full affine) | Rigid body + 3 scalings (e.g. 'zooms') + 3 shears | Different brains that differ in overall size and proportions (T1 → MNI) |

To get more of a visual feel for what affine transformations are, check out the [affine transformations animation from Andy's Brain Book](https://andysbrainbook.readthedocs.io/en/stable/fMRI_Short_Course/Preprocessing/Registration_Normalization.html#affine-transformations). Make sure to watch until the end to see the zoom & shear.

### Nonlinear registration

A linear transform cannot match *local* differences, such as larger ventricles or differently shaped sulci. A **nonlinear** registration moves each part of the image by a different amount, producing a smooth **warp field** instead of one matrix ([FNIRT overview](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/fnirt/index.html)). FNIRT needs a FLIRT affine registration first, which is why Part 2 runs `flirt` first, then `fnirt`. The flexibility of non-linear transformations can sometimes go very wrong, so always check the result.

### Boundary-based registration (BBR)

[BBR](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/flirt/bbr.html) uses the **white-matter boundary** to align the EPI with the T1, where reliable intensity changes are expected in the functional image (outer gray-matter boundaries are less reliable). These intensity changes across tissue types can often allow for clearer markers of alignment than only the outline of the brain itself. The T1's white-matter boundary is mapped onto the EPI (usually with 6 DOF), and EPI intensities are sampled a short distance (2 mm by default) either side of it. The better the alignment, the more consistent the intensity change across the boundary between tissue types.

The `epi_reg` script runs BBR, and also builds the white-matter segmentation if needed.


Note: fMRIPrep uses somewhat different defaults than what you'll do in this practical - see the [fMRIPrep workflows documentation](https://fmriprep.org/en/stable/workflows.html).

---

## Part B: Running Registrations Step-by-Step with FSL

Use the **same ds000114 BIDS dataset as in previous assignments**. You'll be first co-registering a BOLD run (the same oververt word repetition task as before) to the T1, then registering the T1 to the MNI template. 

First, make a folder for this registration practical inside your course folder, with a `scripts` subfolder:

```bash
mkdir -p /users/yourname/documents/fmri_class/registration_practical/scripts
cd /users/yourname/documents/fmri_class/registration_practical/scripts
```

By the end, your folder will look like this:

```
fmri_class/
├── ds000114/
│   └── rawdata/                     # BIDS data (from prior practicals)
└── registration_practical/
    ├── scripts/                     # all of your .sh scripts
    └── sub-01/                      # outputs from this practical
```

### Put your commands in scripts

For this practical, rather than typing FSL commands one at a time, put them in bash scripts (in `scripts/`) so that you keep a record of exactly what you ran, and can fix a setting and re-run everything easily. 

### The config script

Create `scripts/config.sh`. Edit the first variable to match where your course folder lives:

```bash
#!/usr/bin/env bash
# scripts/config.sh : shared settings. Sourced by every other script.

# --- EDIT THIS ---
export COURSE_DIR=/users/yourname/documents/fmri_class   # your course folder
export PRAC_DIR=${COURSE_DIR}/registration_practical # path to your registration practical in the course folder 
export BIDS_DIR=${COURSE_DIR}/datasets/ds000114/rawdata # path to ds000114 BIDS data within the course folder

# --- Derived paths (don't edit) ---
export SUB=sub-01
export SES=ses-test
export T1=${BIDS_DIR}/${SUB}/${SES}/anat/${SUB}_${SES}_T1w.nii.gz
export BOLD=${BIDS_DIR}/${SUB}/${SES}/func/${SUB}_${SES}_task-overtwordrepetition_bold.nii.gz
export OUT=${PRAC_DIR}/${SUB}
export MNI=${FSLDIR}/data/standard/MNI152_T1_2mm
export MNI_BRAIN=${FSLDIR}/data/standard/MNI152_T1_2mm_brain
```

Load it in your terminal (for viewers and checks) and confirm your inputs exist:

```bash
cd /users/yourname/documents/fmri_class/registration_practical
source scripts/config.sh
ls -lh ${T1} ${BOLD}
fslinfo ${T1}
fslinfo ${BOLD}
```

You should see a T1 (`sub-01_ses-test_T1w.nii.gz`) and a BOLD file (`sub-01_ses-test_task-overtwordrepetition_bold.nii.gz`). If `ls` says a file is missing, check `COURSE_DIR` in `config.sh` first and make sure all the paths are correct. 

---

## Part 0: Prepare your inputs

Registration works best when the inputs are clean and appropriate. Put these steps in `scripts/01_prep.sh`.

### 0.1 Make a mean EPI volume

A mean (or single reference) volume has better SNR than any individual volume, so we use this `mean_func` image as the representation of the EPI image for registering it.

```bash
fslmaths ${BOLD} -Tmean ${OUT}/mean_func
```

### 0.2 Brain-extract the T1

You can use the brain extracted T1 you already created in a prior assignment (copy it to `${OUT}/T1_brain.nii.gz`), or run the below command to create it.

```bash
bet ${T1} ${OUT}/T1_brain -R -f 0.4
```

Run the script, then check that `bet` didn't remove brain or leave behind neck/skull:

```bash
fsleyes ${T1} ${OUT}/T1_brain -cm red -a 50 &
```

If the extraction is poor, edit `-f` in your script (smaller = larger brain estimate) and re-run. **A bad brain extraction may propagate into every registration step.**

---

## Part 1: Register EPI → T1

Functional images are low-resolution, geometrically distorted, and have little gray/white contrast. Structural images are high-resolution with excellent contrast. We want the transform that moves the EPI into the T1's space.

Put the following in `scripts/02_epi_to_t1.sh`.

### 1.1 Boundary-based registration with `epi_reg`

Docs: [FLIRT BBR](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/flirt/bbr.html) · [`epi_reg` in the FLIRT User Guide](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/epi_reg.html) · [FAST](https://fsl.fmrib.ox.ac.uk/fsl/docs/structural/fast.html)

`epi_reg` (1) does an initial 6-DOF alignment, (2) segments the T1 with FAST to find the white-matter boundary, and (3) refines the alignment with BBR (see Background).

```bash
epi_reg --epi=${OUT}/mean_func \
        --t1=${T1} \
        --t1brain=${OUT}/T1_brain \
        --out=${OUT}/epi2t1
```

Note that `--t1` takes the **whole-head** T1 and `--t1brain` takes the **brain-extracted** T1.

Outputs:

Note all `.mat` files are really just plain-text files that store matrices in them. They can be opened with most programming languages or text editors. 

| File | What it is |
|------|-----------|
| `epi2t1.nii.gz` | The mean EPI resampled into T1 space |
| `epi2t1.mat` | The final 6-DOF affine transform (EPI → T1) |
| `epi2t1_init.mat` | The initial transform before BBR refinement |
| `epi2t1_fast_wmseg.nii.gz` | White matter segmentation used by BBR |


### 1.2 Inspect

```bash
fsleyes ${T1} \
        ${OUT}/epi2t1 -cm red-yellow -a 50 \
        ${OUT}/epi2t1_fast_wmseg -ot mask -o -mc 0 1 0 &
```

The white-matter segmentation `epi2t1_fast_wmseg` should be shown as a green outline (see Tip 4 in Part 4) and the EPI is shown in the reg/yellow/green scale. Try toggling the mask and EPI on and off and scroll around the brain1. Apply what you learned for inspecting EPI co-registration from the BrainSwipes tutorial: does the EPI line up with cortical folds, the ventricles, and the brain edge? Is there any dropout (and if so, where)?

Bonus: compare this FSLeyes output against the fMRIPrep html summary for this same participant `sub-01`, looking at the "Alignment of functional and anatomical MRI data (coregistration)" section. The registrations and displays are slightly different, but do they give you a similar sense of what the registration quality is? 


---

## Part 2: Register T1 → MNI152

Now we move the subject's anatomy into a standard coordinate space so that results can be compared across subjects. Typicall we need a **nonlinear** transform for this to account for the fact that the size and shape of neuroanatomical features vary between people. Put the following in `scripts/03_t1_to_mni.sh`.

> **Remember:** we use an MNI template here, but the template doesn't have to be MNI. The same `flirt` + `fnirt` approach works for any template; you would just swap the reference images (see the terminology note in the Background).

Docs: [FNIRT](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/fnirt/index.html) 

### 2.1 Linear registration (12 DOF)

Use **brain-extracted** images for the linear step:

```bash
flirt -in ${OUT}/T1_brain \
      -ref ${MNI_BRAIN} \
      -dof 12 \
      -cost corratio \
      -omat ${OUT}/t1_to_mni_affine.mat \
      -out ${OUT}/t1_to_mni_affine
```

### 2.2 Nonlinear registration with `fnirt`

For `fnirt`, use the **whole-head** T1 as input and the affine matrix as the starting point. Note, unlike `flirt`, `fnirt` typically takes in the T1 image before brain extraction has taken place (skull and other tissue can help guide the algorithm). This isn't the case with fMRIprep so you don't have to worry about this outside the scope of this practical. 

```bash
fnirt --in=${T1} \
      --aff=${OUT}/t1_to_mni_affine.mat \
      --config=T1_2_MNI152_2mm \ 
      --cout=${OUT}/t1_to_mni_warp \
      --iout=${OUT}/t1_to_mni_nonlin \
      --jout=${OUT}/t1_to_mni_jacobian \
      -v
```

> This step can take **several minutes** (could be 5–20 minutes depending on your machine)

Outputs:

| File | What it is |
|------|-----------|
| `t1_to_mni_warp.nii.gz` | The nonlinear warp field (includes the affine) |
| `t1_to_mni_nonlin.nii.gz` | The T1 warped into MNI space |
| `t1_to_mni_jacobian.nii.gz` | Jacobian determinant map: local expansion/contraction |

### 2.3 Inspect

Check the registration by toggling the images on and off as in FSLeyes 

```bash
fsleyes ${OUT}/t1_to_mni_affine ${OUT}/t1_to_mni_nonlin ${MNI_BRAIN} 
```

This should display the template MNI brain on the "top" layer, with the nonlinear (flirt + fnirt) and affine-only (flirt) registrations below. **Remember**, the nonlinear image isn't skull-stripped here (that's why it looks a bit different from the other two with skull and neck). 

One great way to check the registration quality is to make sure the MNI image is selected, then slide the "Opacity" slider at the top back and forth. Does it look like the brain in the image directly underneath (the nonlinear fnirt + flirt one) is well aligned, or does tissue seem to change shape between the two images? Now toggle the nonlinear image in the overlay list off and try the same toggling of the opacity looking at the MNI image against the affine flirt-only one. WHich one is better?

More specifically, what does the affine step get right, and what mismatches remain (ventricles, cortical edge, cerebellum)? Where did `fnirt` improve things? 

---

## Part 3: Combine the transforms and make your overlays

For fMRI analysis, the overall goal of the registration process is often to get all the EPI images into the same template space (e.g., MNI space). Rather than resampling the EPI twice (EPI → T1, then T1 → MNI), which blurs the data twice, concatenate the transforms into one and interpolate **once** (fMRIPrep does the same). This minimizes the number of times we resample. Put the following in `scripts/04_combine.sh`.

Docs: `convertwarp`, `applywarp`, and `invwarp` are described in the [FNIRT User Guide](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/fnirt/user_guide.html); `convert_xfm` is in the [FLIRT User Guide](https://fsl.fmrib.ox.ac.uk/fsl/docs/registration/flirt/user_guide.html).

```bash
convertwarp --ref=${MNI} \
            --premat=${OUT}/epi2t1.mat \
            --warp1=${OUT}/t1_to_mni_warp \
            --out=${OUT}/epi_to_mni_warp

applywarp --in=${OUT}/mean_func \
          --ref=${MNI} \
          --warp=${OUT}/epi_to_mni_warp \
          --out=${OUT}/mean_func_in_mni
```

Check the end-to-end result:

```bash
fsleyes ${MNI} ${OUT}/mean_func_in_mni -cm red-yellow -a 50 &
```

**Questions to think about:** What would the drawback be if you applied the two transforms with two separate resampling steps?

### Make your final `slicer` overlays (you'll turn these in on Canvas)

Now create the two static images you will submit. `slicer` draws the second image as red edges over the first. Put these in `scripts/05_qa.sh`:

```bash
# T1 edges drawn over the registered EPI
slicer ${OUT}/epi2t1 ${OUT}/T1_brain -s 2 -a ${OUT}/qa_epi2t1.png

# MNI template edges drawn over the warped T1
slicer ${OUT}/t1_to_mni_nonlin ${MNI_BRAIN} -s 2 -a ${OUT}/qa_t1_to_mni.png
```

Optionally, if it's helpful for examining registration quality, you can also skullstrip the warped T1 then use that as input to `slicer` for QA visualization

```bash
bet ${OUT}/t1_to_mni_nonlin ${OUT}/t1_to_mni_nonlin_brain -R -f 0.4
slicer ${OUT}/t1_to_mni_nonlin_brain ${MNI_BRAIN} -s 2 -a ${OUT}/qa_t1_brain_to_mni.png

```

For a good EPI → T1 registration, the red T1 edges (especially at the gray/white boundary and ventricles) should follow the same boundaries in the EPI. Open the PNGs and judge them using what you learned in BrainSwipes; Part 4 has more tips on what to look for.

### Optional extension: going backwards

Create the inverse transforms so you could bring an MNI-space ROI into the subject's functional space (add these to `04_combine.sh`):

```bash
convert_xfm -omat ${OUT}/t1_to_epi.mat -inverse ${OUT}/epi2t1.mat 
invwarp --ref=${T1} --warp=${OUT}/t1_to_mni_warp --out=${OUT}/mni_to_t1_warp
```

---

## Part 4: Visual QA: How to check a registration

Thinking back to the BrainSwipes tutorials, visually QAing registration is probably the most important skill in this assignment. Use these techniques on **each** registration you create.

**Connect this to Part A:** Based on what you learned from BrainSwipes, would these registrations Pass or Fail, and what evidence supports that?

### Tip 1: Always check the raw outputs, not just the final result

Check each stage of a pipeline separately (the initial alignment, the linear result, the nonlinear result). If the final result is wrong, you need to know where it went wrong.

### Tip 2: Toggle (flicker) between images

In FSLeyes, load the reference image and the registered image, then repeatedly toggle the visibility of the top image (click the eye icon). When the registration is good, **anatomical features should not move** when you flicker. Your eye is very sensitive to motion, so this catches small errors.

### Tip 3: Use the opacity slider and a contrasting colormap

Set the registered image to a colormap such as `red-yellow`, set its opacity to ~50%, and place it over the reference. Adjust the opacity as needed so that you can visualize both sets of superimposed boundaries. Boundaries that match will look consistent; misalignments will show as doubled edges.

### Tip 4: Overlay edges or outlines (the gold-standard check)

Outlining the *reference* anatomy on top of the *warped* image is much easier to judge than blended images. This is the same approach you saw in the BrainSwipes tutorials.

**With FSLeyes:** load the white-matter segmentation (`epi2t1_fast_wmseg`) over your registered EPI. In the overlay list, set its **Overlay type** to *3D/4D volume → Mask* (or *Label*) and switch to **outline** display, so the WM boundary is drawn on top of the EPI.

**With `slicer`:** these are the overlays you already made in Part 3. The red edges come from the second image, so check whether they follow the same boundaries in the image underneath.

### Tip 5: Check multiple slices in all three planes

Don't just glance at one slice. Scroll through the **whole brain** in axial, coronal, and sagittal views. Registrations frequently look fine in the center and fail near the edges (frontal pole, temporal lobes, cerebellum).

### Tip 6: Look at the right landmarks

| Landmark | What to check |
|----------|---------------|
| **Ventricles** | Lateral ventricle edges and shape should line up |
| **Cortical edge / brain outline** | No overhang of one image past the other |
| **Corpus callosum** | Midline structure; good for spotting rotation/translation errors |
| **Cerebellum and brainstem** | Often misaligned in nonlinear registration |
| **Central sulcus / major gyri** | Large visible cortical folds should match |
| **Frontal and temporal poles** | Where EPI distortion/signal dropout may be most severe |

### Tip 7: Know what "good enough" looks like for EPI

* EPIs have **geometric distortion** (stretching/compression near air-tissue interfaces such as the frontal lobes and temporal poles) and **signal dropout**. 
* However, even images with significant signal dropout *can* be registered well (e.g., the rest of the brain is lined up well even if there are low-signal areas), although sometimes dropout can cause registratoin issues.
* Rigid registration cannot fix distortion. So a good EPI → T1 registration will still show *small* residual mismatches in frontal and inferior temporal regions. Large, brain-wide offsets are failures; small local mismatches are expected unless you also used a fieldmap.

---

## Submission

Submit (a) your two final `slicer` overlays and (b) a brief reflection
- `qa_epi2t1.png`: EPI → T1 (T1 edges over the registered EPI)
- `qa_t1_to_mni.png`: T1 → MNI (MNI template edges over the warped T1)

These are saved in `registration_practical/sub-01/` (the `${OUT}` folder).

Your reflection could cover:
1) How confident do you feel in QAing registration visually?
2) What will you look for going forward to assess registration quality?
3) What would the impacts of a bad registration be on fMRI analysis results?