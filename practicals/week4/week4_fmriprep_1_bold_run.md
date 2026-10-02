# Practical #3: Preprocessing with fMRIPrep & Inspecting the Outputs

**Assumes:** Docker Desktop installed and verified (from the FSL practical). You already have the local `ds000114` BIDS folder on your computer, and are comfortable with bind-mounting folders in and out of a container using `-v`.

**A note on file paths throughout this document:** anywhere you see a path like `/users/yourname/documents/fmri_class/...`, that's a placeholder, not a real path. You need to replace it with wherever these folders actually live on *your* computer. Copy-pasting the commands below verbatim, without editing the paths, will not work.

## Why we're doing this

In the FSL practical, you ran a few commands by hand on `sub-01`'s raw BOLD data: a mean image, a timeseries of whole-brain means, a tSNR map. That's a reasonable way to get a first look at data quality, but a "real" preprocessing pipeline needs to do a lot more before an image is ready for analysis: correct for head motion, correct for susceptibility-related image distortion, align the functional data to the anatomical scan, warp everything into a standard template space, and generate a battery of numbers ("confounds") describing how noisy each volume is.

You *could* chain together individual FSL, ANTs, and FreeSurfer commands by hand to do all of this yourself — people used to, and some still do for custom pipelines. **fMRIPrep** exists because that approach is slow to build, easy to get subtly wrong, and hard to compare across labs that each wire their own version of it together differently. fMRIPrep packages a specific, carefully validated sequence of steps — pulling in FSL, ANTs, FreeSurfer, and AFNI tools under the hood — into one command that runs the same way on anyone's data. It produces a standardized set of derivative files plus an HTML quality-control report for every subject. This matters beyond just convenience: the field has genuinely coalesced around fMRIPrep as something close to a shared standard for a large chunk of preprocessing, which means a growing number of papers, courses, and labs you'll interact with are already using it (or something that assumes its outputs) rather than each building preprocessing from scratch. Today you'll run it, in a container, on the same subject you've already gotten to know (`sub-01`), and then spend most of the practical learning to read its outputs.

**The full fMRIPrep documentation lives at <https://fmriprep.org/en/stable/>.** It's genuinely good, and worth getting comfortable navigating on your own — we'll link specific pages below where relevant, but you're encouraged to read around them rather than treating the links as the only parts that matter.

> **Budget real time for this.** The actual fMRIPrep run in Part 5 is not quick — expect it to take on the order of a few hours (roughly 3 hours was typical on an M1 MacBook Air during testing), even with the time-saving flag we'll use. This is normal, not a sign something's wrong. Start the run as early as you can in your working session, and plan to step away and come back rather than waiting at your terminal.

---

## Part 0: Set up your directory structure

Before touching Docker, get your folders organized. BIDS projects conventionally separate the original, unmodified dataset from anything a pipeline generates from it, using folders named `rawdata/` and `derivatives/`:

```
fmri_class/
└── datasets/
    └── ds000114/
        ├── rawdata/          <- the actual BIDS dataset: sub-01/, sub-02/, dataset_description.json, ...
        └── derivatives/      <- where fMRIPrep's outputs will go (you'll create this below)
```

If your `ds000114` folder from previous practicals isn't already organized this way (e.g., if `sub-01/` currently sits directly inside `ds000114/` rather than inside a `rawdata/` subfolder), move things around now so it matches the layout above.

> **`rawdata` vs. `sourcedata`:** you may also see a `sourcedata/` folder mentioned in BIDS documentation or other datasets. In the BIDS spec, `sourcedata/` has a specific, narrow meaning — pre-conversion data in its original format (e.g., DICOMs straight off the scanner), not valid BIDS NIfTIs. It is *not* meant to be pointed at as a BIDS app's input. `rawdata/` isn't part of the official spec either, but it's the standard convention labs use for "this folder is the actual valid BIDS dataset," kept clearly separate from `derivatives/`. Keeping this distinction clean from the start avoids a category of confusing errors later, where a tool ends up treating the wrong folder as if it were BIDS-valid data.

Now create the `derivatives/` folder:
```
mkdir -p /users/yourname/documents/fmri_class/datasets/ds000114/derivatives
```

---

## Part 1: Get a FreeSurfer license file

fMRIPrep calls FreeSurfer internally (even in the reduced mode we'll use today), and FreeSurfer requires a free license file to run, even inside a container. Do this first — the registration email can take a few minutes, and nothing below will run without it.

1. Register for a license at <https://surfer.nmr.mgh.harvard.edu/registration.html> (free, instant, just an email + institution).
2. You'll get a `license.txt` emailed to you. Save it somewhere in your course folder, e.g.:
   ```
   /users/yourname/documents/fmri_class/freesurfer_license.txt
   ```

---

## Part 2: Pull the fMRIPrep image

We're pinning a specific released version rather than pulling `:latest`. `:latest` is a moving target — it gets overwritten on Docker Hub as new versions are pushed — so pulling it at different times can silently give different people different actual fMRIPrep versions, and each pull is exposed to whatever transient registry/build issue happens to exist at that exact moment. A version tag is fixed and reproducible: everyone running this practical ends up with the identical software.

Specifically, we're using **`25.2.5`**, the most recent patch release within fMRIPrep's current **Long-Term Support (LTS)** series (`25.2.x`, first released October 2025, supported through October 2029). LTS releases are the ones the fMRIPrep team commits to maintaining and backporting fixes to for years, which makes them a sensible choice here — you're not stuck on something that falls out of support partway through the semester.

```
docker pull nipreps/fmriprep:25.2.5
```

This image is large (10+ GB, compared to ~5 GB for the FSL image previously), because it bundles complete installs of FreeSurfer, FSL, ANTs, and AFNI. **This download will take a while** — start it and go do something else rather than waiting on it, especially on shared or slow wifi.

Confirm it downloaded:
```
docker images
```
You should see `nipreps/fmriprep` in the list alongside `brainlife/fsl` from before.

**Check the image before trusting it.** A bad pull (interrupted download, a corrupted layer, a registry hiccup) can leave you with an image that looks fine — `docker images` shows a normal size, everything appears to run — but is quietly missing real content inside a specific file. This is rare, but when it happens the failure shows up much later, in the middle of a long unattended run, in a way that's hard to trace back to "the image itself was the problem." It costs nothing to rule this out up front:
```
docker run --rm --entrypoint /bin/bash nipreps/fmriprep:25.2.5 -c "ls -la /usr/local/bin/3dvolreg"
```
This should report a real file size, on the order of tens or hundreds of KB — **not `0`**. If you ever see a `0` there (or fMRIPrep fails deep into a run with an AFNI-related step producing no output and no error text at all), the fix is to force a completely clean re-download:
```
docker rmi nipreps/fmriprep:25.2.5
docker pull nipreps/fmriprep:25.2.5
```

> **Apple Silicon / Windows users:** the same notes from the FSL practical apply here (platform emulation warning, WSL2 terminal, drive sharing, line-ending issues). One fMRIPrep-specific addition: open Docker Desktop's **Settings → Resources** and confirm at least **8GB of memory** is allocated to Docker (16GB if your laptop has it). fMRIPrep is memory-hungry, and the default allocation on some installs is too low — this shows up as the container silently dying partway through with no clear error, or a `MemoryError` in the log.

---

## Part 3: A quick tour of the fMRIPrep command

Unlike the individual FSL tools you called directly before, fMRIPrep is invoked as one long command with a specific structure:

```
fmriprep <bids_dir> <output_dir> participant  [options...]
```

The three **positional** arguments are always in this order: where your BIDS data lives, where derivatives should be written, and the analysis level (we always use `participant` in this class — it means "run on the subject(s) I specify," as opposed to `group`, which is for later group-level steps we aren't using fMRIPrep for).

**The full list of flags, with explanations, is documented at <https://fmriprep.org/en/stable/usage.html>.** It's worth reading through before your run — there are far more options than we're using today, and this is the authoritative reference rather than anything written here. A few of the options we'll use, and what they mean:

| Flag | What it does |
|---|---|
| `--participant-label 01` | Only process `sub-01` (otherwise it processes every subject it finds) |
| `--fs-license-file` | Path *inside the container* to the FreeSurfer license you mounted |
| `--fs-no-reconall` | Skip full FreeSurfer surface reconstruction (see below) |
| `--output-spaces` | Which space(s) to resample the final preprocessed BOLD into (e.g., standard template space, native anatomical space) — see <https://fmriprep.org/en/stable/spaces.html> |
| `--session-label` | Restrict processing to a specific session (e.g., `test`) when a subject has more than one — see Part 4 |
| `--bids-filter-file` | A JSON file telling fMRIPrep to only look at a subset of the BIDS data within whatever session(s) it's processing — see Part 4 |
| `--nthreads` / `--omp-nthreads` | How many CPU threads fMRIPrep is allowed to use |
| `--work-dir` | A scratch folder for intermediate files, kept separate from the final derivatives folder |
| `--stop-on-first-crash` | Fail loudly and immediately instead of trying to limp through remaining steps |

### What `--fs-no-reconall` actually skips, and why we're using it

"`recon-all`" is FreeSurfer's own pipeline for reconstructing the brain's cortical *surface* — a 3D mesh tracing the boundary between gray and white matter, and another tracing the outer edge of the brain, built separately for each hemisphere. This is a different kind of computation from most of the volumetric steps elsewhere in fMRIPrep (motion correction, normalization, etc.): instead of a handful of passes over a 3D grid of voxels, it's an iterative geometric optimization over the whole cortical surface, refined across many stages. That's genuinely slow — `recon-all` alone commonly takes several hours *per subject*, independent of and in addition to everything else fMRIPrep does.

Those surfaces are valuable — they're what you'd want for cortical thickness measurements, surface-based group analyses, or visualizing results on an inflated cortical mesh instead of a flat slice. But for the purposes of today's practical, which is about learning to run fMRIPrep and read its standard volumetric outputs and QC report, that multi-hour step would turn an already-long run into something impractical to complete as an assignment. `--fs-no-reconall` skips it, falling back to a faster volumetric-only skull-strip and segmentation instead of the full surface pipeline — which is exactly the trade-off we'll ask you to think about in the reflection at the end.

---

## Part 4: Scoping the run to one task

`ds000114` has two sessions per subject (`ses-test`, `ses-retest`) and five tasks each. Running fMRIPrep across all of that for even one subject would take many hours longer than what's reasonable for this assignment. We want to keep just the single task/session you already worked with before: `ses-test`, `task-overtwordrepetition`.

Older fMRIPrep versions made this genuinely annoying: a `--bids-filter-file` could restrict *which files within a session* got used, but it couldn't stop fMRIPrep from noticing that `ses-retest` folders existed on disk in the first place, since session detection happened by scanning the BIDS folder's structure before any filter was applied — supplying only a `ses-test` anatomical in your filter while fMRIPrep was simultaneously trying to build a `ses-retest` workflow produced a "conflicting session" error. **As of the `25.2.x` series, this is no longer a problem**: fMRIPrep now has genuine per-session processing support, with a dedicated flag for exactly this situation.

### Select the session directly

```
--session-label test
```

This tells fMRIPrep, at the top level, to only process `ses-test` for the requested subject — full stop. It never even considers `ses-retest`, so there's no conflict to run into. You can point this at your full `ds000114/rawdata` folder as-is; no need to build a separate subset copy of the dataset.

### Add a filter file for the task

`--session-label` narrows things to one session, but `ses-test` alone still has five tasks in it. Use `--bids-filter-file` the way it was originally intended — narrowing *within* the session you've already selected:

```json
{
  "bold": {
    "datatype": "func",
    "task": "overtwordrepetition"
  }
}
```

Save this as `bids_filter.json` in your `derivatives/` folder, e.g. `/users/yourname/documents/fmri_class/datasets/ds000114/derivatives/bids_filter.json`.

**This filter-file syntax is documented at <https://fmriprep.org/en/stable/faq.html#how-do-i-select-only-certain-files-to-be-input-to-fmriprep>.** It's worth reading if you want to filter on other entities (e.g., by `run`, `acquisition`, or `direction`) for your own data later — the format follows PyBIDS query syntax, which is more flexible than the single example above shows.

> **A note for the curious:** if you're ever working with an older fMRIPrep version (pre-`25.2.0`) or reading someone else's scripts from before this feature existed, you may see a workaround where people build a literal subset copy of the dataset (`rsync`-ing just the one session into a separate folder) specifically to sidestep this exact session-detection problem. That's not necessary here, but it's a reasonable thing to reach for if you're ever stuck on an older pinned version for reproducibility reasons.

---

## Part 5: Launch the run

Make the remaining folders you need: an output folder for derivatives, a scratch folder for intermediate files, and a folder to hold TemplateFlow's downloaded templates (kept separate so a bad or interrupted download never corrupts anything you can't just delete and re-fetch):
```
mkdir -p /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_outputs
mkdir -p /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/work
mkdir -p /users/yourname/documents/fmri_class/fmri_class/templateflow_cache
```

Now launch the container. This is a non-interactive run (same pattern as the final part of the FSL practical) — you're handing fMRIPrep one long job and walking away, not opening an interactive shell.

```
caffeinate -i docker run --rm --name fmriprep_sub-01 \
  -v /users/yourname/documents/fmri_class/datasets/ds000114/rawdata:/data:ro \
  -v /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_outputs:/out \
  -v /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/work:/work \
  -v /users/yourname/documents/fmri_class/freesurfer_license.txt:/opt/freesurfer/license.txt:ro \
  -v /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/bids_filter.json:/opt/bids_filter.json:ro \
  -v /users/yourname/documents/fmri_class/fmri_class/templateflow_cache:/opt/templateflow \
  -e TEMPLATEFLOW_HOME=/opt/templateflow \
  nipreps/fmriprep:25.2.5 \
  /data /out participant \
  --participant-label 01 \
  --session-label test \
  --fs-license-file /opt/freesurfer/license.txt \
  --bids-filter-file /opt/bids_filter.json \
  --fs-no-reconall \
  --output-spaces MNI152NLin2009cAsym:res-2 T1w \
  --nthreads 4 --omp-nthreads 4 \
  --work-dir /work \
  --stop-on-first-crash \
  2>&1 | tee /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_run.log
```

**Remember to replace every path above** with wherever these folders actually live on your computer — these are examples, not literal commands to copy unedited.

A few things worth noticing about this command:

- **`caffeinate -i`** at the very front — see the callout below; this is what keeps your laptop working while you're away from it during a run that will take hours.
- **`--session-label test`** is the flag doing the heavy lifting from Part 4 — it's what keeps fMRIPrep from ever considering `ses-retest` at all.
- **A `templateflow_cache` mount plus `-e TEMPLATEFLOW_HOME=...`.** fMRIPrep downloads its reference brain templates on first use and caches them; redirecting that cache to a mounted, empty folder means a failed or interrupted download never leaves you stuck with a corrupted file baked permanently into a run — you can just delete that folder and let it re-download.
- **`--name fmriprep_sub-01`** gives the container a fixed, memorable name instead of a random one, so you can find it again (`docker ps -a`, or `docker logs fmriprep_sub-01`) even after it's finished, as long as you haven't also used `--rm`.
- **`2>&1 | tee .../fmriprep_run.log`** at the very end sends both fMRIPrep's normal output and its errors (`2>&1`) through `tee`, which prints everything to your terminal *as it happens* while also saving an identical copy to a plain text file on your computer. This is the most reliable way to keep a permanent log of a long, unattended run.

> **A note on `--rm` and logs.** You might expect that dropping `--rm` is the way to keep a run's log around, using `docker logs <container>` afterward. That works, but has a real cost over time: `--rm` removes the *container* when it exits (not the image — `nipreps/fmriprep:25.2.5` itself stays on disk either way), and stopped containers you forget to clean up (`docker ps -a` lists every one; `docker system df` shows how much space they're using) are a slow, easy-to-forget way to fill your disk over repeated runs. The `tee` pattern above gets you a permanent, plain-text log without that trade-off — the container can vanish immediately via `--rm`, and you still have the whole transcript sitting in an ordinary file. If you do want to try the `docker logs` route sometime: run with `--name` and without `--rm`, then `docker logs -f fmriprep_sub-01` to live-tail it (`-f` follows, same idea as `tail -f`) — just remember to `docker rm fmriprep_sub-01` (or `docker container prune`) once you're done with it, or those containers will just sit there.

**Expected runtime:** as noted at the top of this document, plan on a few hours — roughly 3 hours was typical on an M1 MacBook Air with `--fs-no-reconall` set. This varies a fair amount with your specific CPU, how much memory Docker has, and whether Docker is emulating a different CPU architecture than your machine's. Start this well ahead of when you actually need the outputs.

> **Keep your computer working while you're away from it.** A screensaver activating, or your screen locking, does **not** pause anything — the container keeps running fine behind a locked screen. What *does* pause it is your computer going into actual system sleep (lid closed, or an idle-sleep timer under battery/energy settings) — this doesn't crash the run, it just freezes the entire machine, including Docker, until you wake it back up. Given this run takes **hours**, not minutes, an unnoticed sleep is a very easy way to come back expecting a finished run and instead find it's barely progressed.
>
> The command above already includes the fix: `caffeinate -i` at the very front tells macOS not to let the system idle-sleep for as long as that command is running, and it automatically stops holding that prevention the moment `docker run` exits — you don't need to remember to undo anything afterward. Two other things still matter alongside it:
> - **Stay plugged in.** `caffeinate` prevents sleep either way, but a laptop trying to run this on battery alone, for hours, is also just going to drain fast or shut down when the battery runs out regardless of the sleep setting.
> - **Don't close the lid.** Closing the lid is a *hardware* sleep trigger that `caffeinate` cannot override — if you need to physically pack up and move somewhere else mid-run, this will still stop everything.

> **If something goes wrong:**
> - `"fMRIPrep: cannot open license file"` — the path on the right-hand side of the license mount must exactly match what you passed to `--fs-license-file`. Double check both.
> - `Permission denied` writing to `/out` — sometimes an earlier crashed run leaves files owned in a way your user can't overwrite. Delete the output folder and re-create it.
> - `ValueError: Conflicting entities for "session"` — this specific error is from older fMRIPrep versions and shouldn't happen on `25.2.5` with `--session-label test` set. If you see it anyway, double check `--session-label test` is actually present in your command (a dropped flag is an easy thing to miss in a long multi-line command).
> - Any error that looks unrelated to your actual data or config, especially right after you've fixed something else — **clear your `--work-dir` before re-running.** fMRIPrep/Nipype caches intermediate state there to support resuming; if an early step got cached during a broken attempt, a later fixed attempt can still pick up the stale cached result. `rm -rf .../derivatives/work/*` and re-run.
> - The container exits with no obvious error — check Docker Desktop's memory allocation (Part 2) before anything else.
> - `--skip-bids-validation` is **not** included above on purpose — if fMRIPrep complains about your BIDS structure, don't just add that flag to silence it; read the specific complaint first, since it usually points at something worth understanding (or worth checking with your dataset).

---

## Part 6: While it's running — what's actually happening

Given how long this takes, don't just watch the terminal. While your job runs, skim the ["Outputs" page of the fMRIPrep documentation](https://fmriprep.org/en/stable/outputs.html) and match it to the stages below, which is roughly the order fMRIPrep works through for each subject:

1. **Anatomical workflow:** bias field correction, skull-stripping, tissue segmentation (gray matter / white matter / CSF), and spatial normalization of the T1w image to standard (MNI) template space.
2. **Functional workflow (per run):** head motion estimation and correction, susceptibility distortion correction (if fieldmaps are present), boundary-based coregistration of the functional data to the anatomical, and resampling into each of your requested `--output-spaces`.
3. **Confound computation:** framewise displacement, DVARS, and other per-volume noise metrics, saved out as a single confounds table per run.
4. **Report generation:** a series of image panels ("SVGs") documenting how each of the above steps went, assembled into one HTML file per subject.

You don't need to memorize this — just have a rough map in your head of "which part of the pipeline am I looking at" before you open the report in Part 7.

---

## Part 7: Inspecting the HTML report

Once the run finishes, open the report directly in a browser (not through Docker — it's just an HTML file now sitting in your output folder):
```
/users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_outputs/sub-01.html
```
(If you don't see it there, check inside a `fmriprep/` subfolder of your outputs directory — the exact layout has shifted slightly across fMRIPrep versions.)

Scroll through it section by section:

- **Summary:** confirms which subject, session, and task(s) actually got processed — check this matches what you expect from your `--session-label` and `bids_filter.json`.
- **Anatomical:** look at the brain-mask and tissue-segmentation overlay on the T1w image. Does the mask look like it includes the whole brain and excludes skull/scalp? Are gray/white matter boundaries roughly where you'd expect?
- **T1 → MNI Normalization:** a side-by-side or blink comparison of your subject's brain warped into template space versus the template itself. Look for gross misalignment (a badly warped image will look "smeared" or clearly offset).
- **Functional:** for your one task/run, look at the **carpet plot** — a grayscale image with every brain voxel stacked as a row and time running left-to-right. Horizontal banding or bright vertical stripes usually mean motion or breathing artifacts affecting many voxels at once during specific volumes. Also check the BOLD-to-T1w coregistration panel the same way you checked normalization above.
- **Confounds:** a plot of framewise displacement (and other metrics) across the run, with any high-motion volumes flagged.

---

## Part 8: Inspecting the derivative files directly

Look at what actually got written to disk, not just the report:
```
ls /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_outputs/sub-01/anat
ls /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_outputs/sub-01/func
```
In `anat/`, you should find things like the preprocessed T1w, a brain mask, a tissue segmentation, and the transform files fMRIPrep computed to warp between spaces. In `func/`, you should find a preprocessed BOLD file for **each** `--output-spaces` you requested (so, one in `T1w` space and one in `MNI152NLin2009cAsym` space), a matching brain mask for each, and a `desc-confounds_timeseries.tsv` file.

Open the MNI-space preprocessed BOLD file in FSLeyes (non-Docker, as usual) and compare it to the raw file you looked at previously: same brain, but now motion-corrected and sitting in standard template space instead of native scanner space.

**Bring back Python from the earlier practical.** Activate your `fmri_class` conda environment and load the confounds file to plot framewise displacement across the run:
```python
import pandas as pd
import matplotlib.pyplot as plt

confounds = pd.read_csv("sub-01_ses-test_task-overtwordrepetition_desc-confounds_timeseries.tsv", sep="\t")

plt.plot(confounds["framewise_displacement"])
plt.xlabel("Volume (timepoint)")
plt.ylabel("Framewise displacement (mm)")
plt.title("sub-01, ses-test, task-overtwordrepetition")
plt.savefig("fd_plot.png")
```
Compare what you see here to the framewise displacement plot shown in the HTML report for the same run — they should tell the same story.

---

## Reflection

Write a short reflection (no more than one paragraph). Things you could mention:
- Anything that looked off in the brain mask, segmentation, or coregistration panels of your report, and what that might mean for someone analyzing this data downstream.
- How framewise displacement in your Python plot compares to what the HTML report showed.
- Now that you've both run FSL commands by hand (previously) and used fMRIPrep to automate a full pipeline (today): what do you gain by doing it by hand? What do you gain from a standardized, automated tool like fMRIPrep? When might you want one approach over the other?
- We turned off full FreeSurfer surface reconstruction (`--fs-no-reconall`) today purely for time, given how long `recon-all` takes on its own. What kinds of downstream analyses do you think would actually need those surface outputs, and would you leave that flag on or off for your own data?

Submit your reflection on Canvas, along with `fd_plot.png` and one screenshot each of the **Anatomical** and **Functional** sections of your subject's HTML report.