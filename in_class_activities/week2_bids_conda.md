# Assignment: Neuroimaging Data Standards & Python Environments

## Learning Objectives
By the end of this assignment, you will be able to:
- Explain what BIDS (Brain Imaging Data Structure) is and why it matters for reproducible fMRI research
- Identify the key naming conventions and metadata fields required for anatomical (T1W, MPRAGE) and BOLD (functional) MRI data
- Use the browser-based BIDS Validator to check a dataset's compliance
- Diagnose BIDS errors by reading validator output
- Install Anaconda/Miniconda and create an isolated conda environment
- Install a neuroimaging Python package (`nilearn`) into a conda environment and verify the installation

---

## Before You Start: Organize Your Files & Get a Text Editor

**1. Set up a course folder.** Create a folder on your computer for this course, and inside it, a subfolder called `datasets`, e.g.:

```
fmri_course_fall_2026
└── datasets/
```

Every dataset you download for this course (this week and in future weeks) should live in its own subfolder inside `datasets/`, e.g. `fmri_course_fall_2026/datasets/ds000114/`. Keeping things organized now will save you a lot of confusion later when you're juggling multiple datasets.

**2. Install a text editor if you don't have one.** You'll want something other than Notepad/TextEdit to comfortably view and edit JSON and code files. Install one of the following (either is fine — pick whichever you prefer):

- **VS Code** (recommended if you're not sure): https://code.visualstudio.com/download — free, works on Windows/Mac/Linux, has built-in JSON syntax highlighting and a file explorer sidebar that's handy for browsing dataset folders. **NOTE:** some versions of VS Code may install AI code editing tools by default. If this is the case, please turn it off! This can make it harder to learn and also be a big problem for data privacy depending on files AI tools have access to.
- **Sublime Text**: https://www.sublimetext.com/download — free to try indefinitely (occasional save prompt), lightweight, fast to open.

You can use either for the JSON editing in Part 1 and the script writing in Part 2.

---

## Part 1: BIDS Data Structure & the BIDS Validator

### Step 1: Get the dataset from OpenNeuro

For this assignment, everyone will use the same dataset so we can compare notes: **ds000114**, *"A test-retest fMRI dataset for motor, language and spatial attention functions"* (10 healthy participants, each scanned twice with T1w anatomical scans and several BOLD task runs).

**Dataset page:** https://openneuro.org/datasets/ds000114

The full dataset is about 4.3 GB (10 subjects × 2 sessions). Download the whole thing from OpenNeuro and put it in your datasets folder.

The file tree should look something like this:

```
ds000114/
├── CHANGES
├── dataset_description.json
├── dwi.bval
├── dwi.bvec
├── participants.tsv
├── sub-01
│   ├── ses-retest
│   │   ├── anat
│   │   │   └── sub-01_ses-retest_T1w.nii.gz
│   │   ├── dwi
│   │   │   └── sub-01_ses-retest_dwi.nii.gz
│   │   └── func
│   │       ├── sub-01_ses-retest_task-covertverbgeneration_bold.nii.gz
│   │       ├── sub-01_ses-retest_task-fingerfootlips_bold.nii.gz
│   │       ├── sub-01_ses-retest_task-linebisection_bold.nii.gz
│   │       ├── sub-01_ses-retest_task-linebisection_events.tsv
│   │       ├── sub-01_ses-retest_task-overtverbgeneration_bold.nii.gz
│   │       └── sub-01_ses-retest_task-overtwordrepetition_bold.nii.gz
│   └── ses-test
...
```

If you're unsure whether you've grabbed the right files, that's fine — the BIDS Validator in Step 3 will tell you if anything required is missing.

### Step 2: Explore the structure

Open the dataset folder and look around. Based on what you downloaded in Step 1, you should see something like:

```
ds000114/
├── dataset_description.json
├── task-fingerfootlips_bold.json
├── task-fingerfootlips_events.tsv
└── sub-01/
    └── ses-test/
        ├── anat/
        │   └── sub-01_ses-test_T1w.nii.gz
        └── func/
            ├── sub-01_ses-test_task-fingerfootlips_bold.nii.gz
            └── sub-01_ses-test_task-fingerfootlips_events.tsv
```

Open a couple of the `.json` "sidecar" files in your text editor (VS Code or Sublime Text — right next to the imaging files) and skim them. Note down:
- What does `RepetitionTime` mean, and why would it matter only for functional data?
- Look at the `SliceTiming` information in `task-overtverbgeneration_bold.json`. In what order were the slices acquired?
- What information is encoded in the *filename itself* (e.g., `sub-`, `ses-`, `task-`, `run-`) versus what's stored in the JSON?

#### Understanding sidecar conventions: the "inheritance principle"

You'll notice that `ds000114` has a `task-fingerfootlips_bold.json` sitting at the **top level** of the dataset (not inside any `sub-XX` folder), rather than a separate JSON next to every single subject's BOLD file. This is intentional, and it's one of the most important conventions in BIDS: the **inheritance principle**.

BIDS lets you place a sidecar JSON at *any level* of the folder hierarchy: the dataset root (as is the case with this dataset), a subject folder, a session folder, or right next to an individual file. A metadata field defined at a higher (more general) level applies to every matching file below it, unless a file has its own **more specific** sidecar that overrides that field. Two common patterns you'll see in real datasets:

- **One inherited sidecar for many files** (what `ds000114` does): a single `task-fingerfootlips_bold.json` at the root applies to *every* subject's `task-fingerfootlips_bold.nii.gz` file, for every subject and session, because they all used the same acquisition parameters (same `RepetitionTime`, same `TaskName`, etc.). This avoids duplicating identical metadata dozens of times.
- **Individual sidecars per file**: if, say, `sub-05` had a different `RepetitionTime` than everyone else (maybe the scanner protocol changed for that session), you'd add a `sub-05_ses-test_task-fingerfootlips_bold.json` *right next to that subject's BOLD file*. That file only needs to contain the field(s) that differ (e.g., just `RepetitionTime`) — every other field is still inherited from the top-level JSON. The more specific, per-file sidecar takes precedence over the general one, field by field.

Overall: BIDS doesn't require one JSON per imaging file. Instead, it requires that every file have *access to* the correct metadata, however many levels up the hierarchy it lives. This is why deleting or editing a top-level sidecar (as you're about to do in Step 4) can affect metadata for many files at once, not just one.

### Step 3: Validate the dataset (baseline check)

Go to the browser-based BIDS Validator: **https://bids-standard.github.io/bids-validator/**

Upload or point it at your dataset folder (the validator runs locally in your browser). Confirm it passes (OpenNeuro datasets should already be BIDS-valid). 

**A note on warnings vs. errors:** even on this clean, unmodified dataset, you'll likely see a long list of yellow **warnings** in addition to (or even in the absence of) any red **errors**. This is completely normal and does *not* mean the dataset is invalid. Warnings are the validator's way of flagging things that are *worth a second look* e.g., a scan parameter that's slightly inconsistent across subjects, or a recommended-but-not-required field that's missing. But it is not asserting that something is actually wrong. A dataset with warnings but zero errors still passes validation and is considered BIDS-compliant. **Errors**, on the other hand, mean the dataset violates the BIDS specification and must be fixed. As you work through Step 4, pay attention to whether each change you make produces a warning or an error.

### Step 4: Break it, then fix it

Rather than working from a copy, you'll edit your **actual working `ds000114` folder** directly: introduce one error, observe how the validator responds, then **undo that specific change before moving on to the next one**. By the end of this step, your dataset should be back in its original state and pass validation again, just as it did in Step 3.

1. **Rename a file to break the naming convention** — rename `sub-01_ses-test_task-fingerfootlips_bold.nii.gz` to `sub-01_ses-test_fingerfootlips_bold.nii.gz` (dropping the `task-` entity) or `sub-01_ses-test_bold.nii.gz` (dropping `task-` entirely). Run the validator — what does it say is wrong, and is it an error or a warning? Then **rename the file back** to its original name.
2. **Remove the inherited (top-level) sidecar** — delete the root-level `task-fingerfootlips_bold.json`. Since `sub-01` doesn't have its own per-file override, this file was the *only* source of metadata (like `RepetitionTime` and `TaskName`) for that BOLD scan. Run the validator. What does it flag, and how does this illustrate that a single top-level sidecar can apply to many files at once? Then **put the file back**.
3. **Edit a field in that same top-level sidecar** — open `task-fingerfootlips_bold.json` and delete the `RepetitionTime` field (or change it to an invalid value like a string instead of a number). Run the validator — what does it flag this time? Then **restore the field to its original value**.

After reversing all three changes, run the validator one final time and confirm you're back to the same clean result (warnings-only, no errors) you saw in Step 3.

For each of the three errors, try to determine:
- What error or warning message did the validator give, and which was it (error vs. warning)?
- Why does BIDS require this piece of information (naming entity or JSON field)? What would break downstream (e.g., in analysis software) if it were missing?

---

## Part 2: Setting Up Anaconda & Conda Environments

Anaconda is a distribution of Python (and R) built specifically for scientific and data-heavy work, and it's a tool a lot of neuroimaging researchers use to manage their software. Two things make it especially useful here: **first**, different neuroimaging tools often need different, sometimes conflicting, versions of Python and its libraries. Anaconda lets you create separate environments, each with its own isolated set of packages, so installing something for one project never breaks another. **Second**, it comes with conda, a package manager that handles not just Python packages but many of the underlying scientific libraries that neuroimaging tools depend on, which is often more reliable than using pip (another installation tool for Python) alone for this kind of work. 

It's a good habit to get into to set up conda environments for the different projects you are working on, so that installations for one project don't accidentaly break working software for another one. Today, you'll go through installing Anaconda and setting up/using an environment.

### Step 1: Install Anaconda (or Miniconda)

If you don't already have it, download and install **Anaconda**  from:
- Anaconda: https://www.anaconda.com/download

Follow the installer for your OS (Windows/Mac/Linux). Once installed, open a terminal (Anaconda Prompt on Windows, or Terminal on Mac/Linux) and confirm it worked:

```bash
conda --version
```

### Step 2: Create a new conda environment

Create an environment specifically for this class, using Python 3.11:

```bash
conda create -n fmri_class python=3.11
```

This step may take a while to set up the enviornment. 

Activate it:

```bash
conda activate fmri_class
```

Your terminal prompt should now show `(fmri_class)` at the start of the line, confirming you're inside the environment.

### Step 3: Install nilearn

Inside your activated environment, install [**nilearn**](https://nilearn.github.io/stable/index.html), a Python library for working with fMRI/neuroimaging data (we'll use it in future assignments):

```bash
pip install nilearn matplotlib
```

This will pull in several dependencies (numpy, scipy, scikit-learn, nibabel, etc.). This command also installs the graphic library matplotlib

### Step 4: Verify the installation

There are a few different ways to confirm nilearn is actually installed and working inside your `fmri_class` environment. Try all three:

**a) Ask conda what's in the environment:**

```bash
conda list fmri_class
```

This lists any package matching "nilearn" in your active environment, along with its version number.

**b) Ask pip directly:**

```bash
pip show fmri_class
```

This shows metadata about the installed package — version, install location, and its dependencies.

**c) Import it in Python and print the version:**

```bash
python -c "import nilearn; print(nilearn.__version__)"
```

If nilearn is properly installed, this prints a version number (e.g., `0.10.4`) with no errors. Take a screenshot and submit on Canvas to show you completed the assignment!


