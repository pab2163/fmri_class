# Practical #3: Preprocessing with fMRIPrep & Inspecting the Outputs

**Assumes:** Docker Desktop installed and verified (from the FSL practical). You already have the local `ds000114` BIDS folder on your computer, and are comfortable with bind-mounting folders in and out of a container using `-v`.

**A note on file paths throughout this document:** anywhere you see a path like `/users/yourname/documents/fmri_class/...`, that's a placeholder, not a real path. You need to replace it with wherever these folders actually live on *your* computer. Copy-pasting the commands below verbatim, without editing the paths, will not work.

## Why we're doing this

In the FSL practical, you ran a few commands by hand on `sub-01`'s raw BOLD data: a mean image, a timeseries of whole-brain means, a tSNR map. That's a reasonable way to get a first look at data quality, but a "real" preprocessing pipeline needs to do a lot more before an image is ready for analysis: correct for head motion, correct for susceptibility-related image distortion, align the functional data to the anatomical scan, warp everything into a standard template space, and generate a battery of numbers ("confounds") describing how noisy each volume is.

You *could* chain together individual FSL, ANTs, and FreeSurfer commands by hand to do all of this yourself. People used to, and some still do for custom pipelines. **fMRIPrep** exists because that approach is slow to build, easy to get subtly wrong, and hard to compare across labs that each wire their own version of it together differently. fMRIPrep packages a specific, carefully validated sequence of steps (pulling in FSL, ANTs, FreeSurfer, and AFNI tools under the hood) into one command that runs the same way on anyone's data. It produces a standardized set of derivative files plus an HTML quality-control report for every subject. The field has  coalesced around fMRIPrep as something close to a shared standard for a large chunk of preprocessing, which means a growing number of papers, courses, and labs you'll interact with are already using it (or something that assumes its outputs) rather than each building preprocessing from scratch. Today you'll run it, in a container, on the same subject you've already gotten to know (`sub-01`), and then spend most of the practical learning to read its outputs.

**The full fMRIPrep documentation lives at <https://fmriprep.org/en/stable/>.** It's good documentation, and worth getting comfortable navigating on your own (espeecially because you'll probably need to use different flags to customize a little bit depending on the project). Specific pages are linked below where relevant, but you're encouraged to read around them rather than treating the links as the only parts that matter.

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

> **Context: `rawdata` vs. `sourcedata`.** You may also see a `sourcedata/` folder mentioned in BIDS documentation or other datasets. In the BIDS spec, `sourcedata/` has a specific, narrow meaning — pre-conversion data in its original format (e.g., DICOMs straight off the scanner), not valid BIDS NIfTIs. It is *not* meant to be pointed at as a BIDS app's input. `rawdata/` isn't part of the official spec either, but it's a somewhat standard convention labs use for "this folder is the actual valid BIDS dataset," kept clearly separate from `derivatives/`. Keeping this distinction clean from the start avoids a category of confusing errors later, where a tool ends up treating the wrong folder as if it were BIDS-valid data.

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

**Check the image before trusting it.** A bad pull (interrupted download, a corrupted layer) can leave you with an image that looks fine such that `docker images` shows a normal size and everything appears to run, but it could be missing real content inside a specific file. This is rare, but when it happens the failure shows up much later, in the middle of a long unattended run, in a way that's hard to trace back to "the image itself was the problem." Here's one straightforward way to test whether some of the needed software (`3dvolreg` as part of AFNI) is working up front before running the whole thing. 
```
docker run --rm --entrypoint /bin/bash nipreps/fmriprep:25.2.5 -c "ls -lah /usr/local/bin/3dvolreg"
```
This should report a real file size, on the order of tens or hundreds of KB — **not `0`**, something like the below is a good sign (101K).

```
-rwxr-xr-x 1 root users 101K Aug 24  2025 /usr/local/bin/3dvolreg
```

If you ever see a `0` there (or fMRIPrep fails deep into a run with an AFNI-related step producing no output and no error text at all), the fix is to delete the docker *image* and pull it again as a clean reset:
```
docker rmi nipreps/fmriprep:25.2.5
docker pull nipreps/fmriprep:25.2.5
```

> **Context: Apple Silicon / Windows users.** The same notes from the FSL practical apply here (platform emulation warning, WSL2 terminal, drive sharing, line-ending issues). One fMRIPrep-specific addition: open Docker Desktop's **Settings → Resources** and confirm at least **8GB of memory** is allocated to Docker (16GB if your laptop has it). fMRIPrep is memory-hungry, and the default allocation on some installs is too low — this shows up as the container silently dying partway through with no clear error, or a `MemoryError` in the log.

---

## Part 3: A quick tour of the fMRIPrep command

Unlike the individual FSL tools you called directly before, fMRIPrep is invoked as one long command with a specific structure:

```
fmriprep <bids_dir> <output_dir> participant  [options...]
```

The three **positional** arguments are always in this order: where your BIDS data lives, where derivatives should be written, and the analysis level (we pretty much always use `participant` in this class — it means "run on the subject(s) I specify," as opposed to `group`, which is for later group-level steps we aren't using fMRIPrep for).

**The full list of flags, with explanations, is documented at <https://fmriprep.org/en/stable/usage.html>.** It's worth reading through before your run: there are far more options than we're using today. A few of the options we'll use, and what they mean:

| Flag | What it does |
|---|---|
| `--participant-label 01` | Only process `sub-01` (otherwise it processes every subject it finds) |
| `--fs-license-file` | Path *inside the container* to the FreeSurfer license you mounted |
| `--fs-no-reconall` | Skip full FreeSurfer surface reconstruction (see below) |
| `--output-spaces` | Which space(s) to resample the final preprocessed BOLD into (e.g., standard template space, native anatomical space) — see <https://fmriprep.org/en/stable/spaces.html> |
| `--session-label` | Restrict processing to a specific session (e.g., `test`) when a subject has more than one — see Part 4 |
| `--bids-filter-file` | A JSON file telling fMRIPrep to only look at a subset of the BIDS data within whatever session(s) it's processing — see Part 4 |
| `--nthreads` / `--omp-nthreads` | How many CPU threads fMRIPrep is allowed to use. 4 is probably a good place to start, and reduce if you are having multithreading issues. `--omp-nthreads` should always be equal to or lower than `--nthreads` |
| `--work-dir` | A scratch folder for intermediate files, kept separate from the final derivatives folder |
| `--stop-on-first-crash` | Overrides fMRIPrep's default behavior: stop immediately at the first failure, rather than continuing on (see below) |

### `--stop-on-first-crash` is not the default, and that's worth knowing

By default, fMRIPrep tries to keep going even after one part of the pipeline fails, since many steps (different runs, different stages) are independent of each other; it then reports everything that went wrong together, all at once, at the end. `--stop-on-first-crash` overrides that: the whole run halts the instant anything fails, rather than continuing on and possibly burying a real problem somewhere inside a long end-of-run summary you might skim past.

The tradeoff with this: one failure stops the entire run, even unrelated steps that would otherwise have finished fine. For a real multi-subject study, that might be more disruptive than it's worth. But for a single-subject learning exercise like this one, where the goal is to notice and understand problems as they happen rather than discover them later, catching a failure immediately and unambiguously is worth more than letting the run limp to a possibly-incomplete finish. If you're ever being extra careful about not missing a hidden error, this flag is a reasonable one to reach for even outside a class setting.

### What `--fs-no-reconall` actually skips, and why we're using it

"`recon-all`" is [FreeSurfer's](https://surfer.nmr.mgh.harvard.edu/fswiki) own pipeline for reconstructing the brain's cortical *surface* — a 3D mesh tracing the boundary between gray and white matter, and another tracing the outer edge of the brain, built separately for each hemisphere. This is a different kind of computation from most of the volumetric steps elsewhere in fMRIPrep (motion correction, normalization, etc.): instead of a handful of passes over a 3D grid of voxels, it's an iterative geometric optimization over the whole cortical surface, refined across many stages. `recon-all` alone commonly takes several hours *per subject*, independent of and in addition to everything else fMRIPrep does.

Those surfaces are valuable — they're what you'd want for cortical thickness measurements, surface-based group analyses, or visualizing results on an inflated cortical mesh instead of a flat slice. But for the purposes of today's practical, which is about learning to run fMRIPrep and read its standard volumetric outputs and QC report, we don't need this. `--fs-no-reconall` skips it, falling back to a faster volumetric-only skull-strip and segmentation instead of the full surface pipeline.

---

## Part 4: Scoping the run to one task

`ds000114` has two sessions per subject (`ses-test`, `ses-retest`) and five tasks each. Running fMRIPrep across all of that for even one subject would take many hours longer than what's reasonable for this assignment. We want to keep just the single task/session you already worked with before: `ses-test`, `task-overtwordrepetition`.

### Select the session directly

Add this flag to your fMRIPrep launch script

```
--session-label test
```

This tells fMRIPrep, at the top level, to only process `ses-test` for the requested subject. It never even considers `ses-retest`, so there's no conflict to run into. You can point this at your full `ds000114/rawdata` folder as-is; no need to build a separate subset copy of the dataset.

### Add a filter file for the task

**Note:** in many applied cases we might just want to fMRIPrep all of our data at once (e.g., multiple fMRI tasks, resting state data) and we wouldn't need a filter file or set session labels. We're doing that in this assignment to scale down the length of processing and learn how to use these tools.  

`--session-label` narrows things to one session, but `ses-test` alone still has five tasks in it. Use `--bids-filter-file` to narrow what files to process *within* the session you've already selected:

```json
{
  "bold": {
    "datatype": "func",
    "task": "overtwordrepetition"
  }
}
```

Save this as `bids_filter.json` in your `derivatives/` folder, e.g. `/users/yourname/documents/fmri_class/datasets/ds000114/derivatives/bids_filter.json`.

**This filter-file syntax is documented at <https://fmriprep.org/en/stable/faq.html#how-do-i-select-only-certain-files-to-be-input-to-fmriprep>.** It's worth reading if you want to filter on other entities (e.g., by `run`, `acquisition`, or `direction`) for your own data later. The format follows [PyBIDS query syntax](https://bids-standard.github.io/pybids/examples/pybids_tutorial.html), which is more flexible than the single example above shows.

---

> **Troubleshooting (optional): working with an older fMRIPrep version**
>
> Everything above (`--session-label`) assumes `25.2.x` or later. If you're ever working with an older fMRIPrep version (pre-`25.2.0`), or reading someone else's scripts written before this feature existed, you may run into the problem described earlier: a `--bids-filter-file` could restrict *which files within a session* got used, but it couldn't stop fMRIPrep from noticing that `ses-retest` folders existed on disk in the first place, since session detection happened before any filter was applied. Supplying only a `ses-test` anatomical in your filter while fMRIPrep simultaneously tried to build a `ses-retest` workflow produced a "conflicting session" error.
>
> If you're ever stuck on an older pinned version (for reproducibility reasons, or because a specific analysis depends on it) and hit this, the workaround is to build a literal subset copy of the dataset containing only the one session you want, rather than relying on the filter file alone:
> ```
> mkdir -p /users/yourname/documents/fmri_class/datasets/ds000114_practical/sub-01/ses-test
>
> rsync -av \
>   /users/yourname/documents/fmri_class/datasets/ds000114/rawdata/sub-01/ses-test/ \
>   /users/yourname/documents/fmri_class/datasets/ds000114_practical/sub-01/ses-test/
>
> cp /users/yourname/documents/fmri_class/datasets/ds000114/rawdata/dataset_description.json \
>    /users/yourname/documents/fmri_class/datasets/ds000114_practical/
> ```
> Then point `/data` at this subset folder instead of the full `rawdata/`. This isn't necessary on `25.2.5`, the version we're using, but it's worth knowing this exists if you ever encounter it elsewhere.

---

## Part 5: Launch the run

Make the remaining folders you need: an output folder for derivatives, and a scratch folder for intermediate files:
```
mkdir -p /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_outputs
mkdir -p /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/work
```

This command is long, which makes it difficult to run directly at the command line. **Instead of running it directly, save it as a bash script.** This is a good habbit worth building: any time a command gets long enough that getting it wrong would be annoying, writing it into a script first is standard practice, not overkill. A script is also, itself, documentation: it's a permanent, exact record of what you actually did, which matters the moment you (or anyone else) needs to reproduce this run or adapt it for another subject.

Create a new file called `run_fmriprep_sub-01.sh` in your course folder, with this content:

```bash
#!/bin/bash

LOGFILE=/users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_run.log

echo "fMRIPrep run started: $(date)" | tee "$LOGFILE"

docker run --rm --name fmriprep_sub-01 \
  -v /users/yourname/documents/fmri_class/datasets/ds000114/rawdata:/data:ro \
  -v /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/fmriprep_outputs:/out \
  -v /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/work:/work \
  -v /users/yourname/documents/fmri_class/freesurfer_license.txt:/opt/freesurfer/license.txt:ro \
  -v /users/yourname/documents/fmri_class/datasets/ds000114/derivatives/bids_filter.json:/opt/bids_filter.json:ro \
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
  2>&1 | tee -a "$LOGFILE"

echo "fMRIPrep run finished: $(date)" | tee -a "$LOGFILE"
```

**Remember to replace every path above** with wherever these folders actually live on your computer — these are examples, not literal commands to copy unedited.

Run it:
```
bash /users/yourname/documents/fmri_class/run_fmriprep_sub-01.sh
```

**You'll submit this script at the end of this assignment**, alongside your other materials (see the "What to turn in" section at the very end).

A few things worth noticing about this command:

- **The `echo "... $(date)"` lines bracketing the command** record exactly when the run started and finished, written straight into your terminal and into the same log file via `tee` below. You'll use these in Part 9 to figure out how long your run actually took.
- **`--session-label test`** is the flag doing the heavy lifting from Part 4 — it's what keeps fMRIPrep from ever considering `ses-retest` at all.
- **`--name fmriprep_sub-01`** gives the container a fixed, memorable name instead of a random one, so you can find it again (`docker ps -a`, or `docker logs fmriprep_sub-01`) even after it's finished, as long as you haven't also used `--rm`.
- **`2>&1 | tee .../fmriprep_run.log`** at the very end sends both fMRIPrep's normal output and its errors (`2>&1`) through `tee`, which prints everything to your terminal *as it happens* while also saving an identical copy to a plain text file on your computer. This is the most reliable way to keep a permanent log of a long, unattended run.

> **Context: `--rm` and logs.** You might expect that dropping `--rm` is the way to keep a run's log around, using `docker logs <container>` afterward. That works, but has a real cost over time: `--rm` removes the *container* when it exits (not the image — `nipreps/fmriprep:25.2.5` itself stays on disk either way), and stopped containers you forget to clean up (`docker ps -a` lists every one; `docker system df` shows how much space they're using) are a slow, easy-to-forget way to fill your disk over repeated runs. The `tee` pattern above gets you a permanent, plain-text log without that trade-off — the container can vanish immediately via `--rm`, and you still have the whole transcript sitting in an ordinary file. If you do want to try the `docker logs` route sometime: run with `--name` and without `--rm`, then `docker logs -f fmriprep_sub-01` to live-tail it (`-f` follows, same idea as `tail -f`) — just remember to `docker rm fmriprep_sub-01` (or `docker container prune`) once you're done with it, or those containers will just sit there.

**Expected runtime:** as noted at the top of this document, plan on a few hours — roughly 3 hours was typical on an M1 MacBook Air with `--fs-no-reconall` set. This varies a fair amount with your specific CPU, how much memory Docker has, and whether Docker is emulating a different CPU architecture than your machine's. Start this well ahead of when you actually need the outputs.

> **Troubleshooting (optional): preventing your computer from sleeping during a long run**
>
> A screensaver activating, or your screen locking, does **not** pause anything — the container keeps running fine behind a locked screen. What *does* pause it is your computer going into actual system sleep (lid closed, or an idle-sleep timer under battery/energy settings) — this doesn't crash the run, it just freezes the entire machine, including Docker, until you wake it back up. Given this run takes **hours**, not minutes, an unnoticed sleep is a very easy way to come back expecting a finished run and instead find it's barely progressed.
>
> If you want to guard against this, add `caffeinate -i` to the front of the `docker run` line in your script:
> ```
> caffeinate -i docker run --rm --name fmriprep_sub-01 \
>   ...
> ```
> `caffeinate -i` tells macOS not to let the system idle-sleep for as long as that command is running, and automatically stops holding that prevention the moment it exits — nothing to remember to undo afterward. Two other things still matter alongside it, whether or not you add `caffeinate`:
> - **Stay plugged in.** A laptop trying to run this on battery alone, for hours, is also just going to drain fast or shut down when the battery runs out, regardless of any sleep setting.
> - **Don't close the lid.** Closing the lid is a *hardware* sleep trigger that `caffeinate` cannot override — if you need to physically pack up and move somewhere else mid-run, this will still stop everything.

> **Troubleshooting (optional): common errors**
> - `"fMRIPrep: cannot open license file"` — the path on the right-hand side of the license mount must exactly match what you passed to `--fs-license-file`. Double check both.
> - `Permission denied` writing to `/out` — sometimes an earlier crashed run leaves files owned in a way your user can't overwrite. Delete the output folder and re-create it.
> - `ValueError: Conflicting entities for "session"` — this specific error is from older fMRIPrep versions and shouldn't happen on `25.2.5` with `--session-label test` set. If you see it anyway, double check `--session-label test` is actually present in your command (a dropped flag is an easy thing to miss in a long multi-line command).
> - Any error that looks unrelated to your actual data or config, especially right after you've fixed something else — **clear your `--work-dir` before re-running.** fMRIPrep/Nipype caches intermediate state there to support resuming; if an early step got cached during a broken attempt, a later fixed attempt can still pick up the stale cached result. `rm -rf .../derivatives/work/*` and re-run.
> - The container exits with no obvious error — check Docker Desktop's memory allocation (Part 2) before anything else.
> - `--skip-bids-validation` is **not** included above on purpose — if fMRIPrep complains about your BIDS structure, don't just add that flag to silence it; read the specific complaint first, since it usually points at something worth understanding (or worth checking with your dataset).

> **Troubleshooting (optional): corrupted TemplateFlow cache**
>
> A crash early on involving `templateflow`, or a `JSONDecodeError`/`OSError` while fMRIPrep is trying to read a template file (e.g. something under a `tpl-...` folder), means TemplateFlow's cache of reference brain templates got corrupted, usually from an interrupted download. By default, that cache lives *inside the container's own filesystem* and disappears each time thanks to `--rm`, so simply re-running the exact same command should give you a clean cache and fix it. If the identical error keeps happening across repeated re-runs, redirect the cache to a mounted folder on your computer so you can delete just the broken piece instead of hoping a fresh container fixes it:
> ```
> mkdir -p /users/yourname/documents/fmri_class/fmri_class/templateflow_cache
> ```
> then add these two lines to your `docker run` command (anywhere among the other `-v` flags, before the image name):
> ```
>   -v /users/yourname/documents/fmri_class/fmri_class/templateflow_cache:/opt/templateflow \
>   -e TEMPLATEFLOW_HOME=/opt/templateflow \
> ```
> Re-run once to let it download a fresh cache into that folder. If it fails again, delete just the specific broken template subfolder named in the error (e.g. `rm -rf .../templateflow_cache/tpl-MNI152NLin2009cAsym`) rather than the whole cache, and re-run again.

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

Look at what files actually got written out, not just the report. Find the `anat` and `func` outputs within your `fmriprep_outputs` folder:
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
Compare what you see here to the framewise displacement plot shown in the HTML report for the same run (e.g., the 'FD' timeseries). They should tell the same story.

---

## Part 9: How long did this actually take, and what does that mean for more than one subject?

Open `fmriprep_run.log` (the file your script's `tee` command wrote to) and find the two `echo` lines your script printed, right at the top and bottom:
```
fMRIPrep run started: ...
fMRIPrep run finished: ...
```
Subtract the two to get your actual wall-clock runtime for this one subject, one task, no surface reconstruction. (If you forgot to use the script, or started the run some other way, you can approximate the same thing from file timestamps instead: `ls -la --full-time` on an early file inside your `work/` folder versus on the final `sub-01.html` report will bracket roughly the same window, though less precisely than the script's own timestamps.)

**Now do a back-of-the-envelope estimate**, the kind of rough planning math you'll want to get comfortable with before running anything at real study scale:

- If this one run took your measured time, and `ds000114` had, say, 20 participants instead of 1, how long would processing all of them take **run one at a time, in sequence**, on this same laptop?
- Real studies might have anywhere between tens to tens of thousands (e.g., UK Biobank dataset) of participants. At those scales, does "just run it on my laptop overnight" still hold up? What would you actually do instead?
- fMRIPrep processes each subject's `participant`-level workflow independently of every other subject's — nothing about `sub-01`'s run depends on `sub-02`'s. What does that independence buy you, if you have access to more than one CPU core, more than one machine, or a shared compute cluster at your institution?

You don't a super specific time estimate here, just work through math to approximate the timing. The goal is building the instinct to estimate compute time *before* committing a cluster, a lab server, or your own laptop to a job.

---

## Reflection

Write a short reflection (no more than one paragraph). Things you could mention:
- What did you think about running fMRIPrep in general?
- Anything that looked off in the brain mask, segmentation, or coregistration panels of your report, and what that might mean for someone analyzing this data downstream.
- How framewise displacement in your Python plot compares to what the HTML report showed.
- Based on your back-of-the-envelope estimate in Part 9: if you were planning your own study tomorrow, how would knowing this per-subject runtime change how you think about scheduling, hardware, or needing access to a cluster, versus just assuming "preprocessing" is a quick step?

## What to turn in

Submit on Canvas: your reflection, `run_fmriprep_sub-01.sh` (your bash script from Part 5), `fd_plot.png`, and your Part 9 runtime estimate and reasoning.