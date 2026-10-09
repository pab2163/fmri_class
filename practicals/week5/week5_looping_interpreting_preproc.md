# Practical #5: Scripting fMRIPrep for Multiple Participants & Reading a Preprocessing Pipeline

**Assumptions from prior assignments:** You completed Practical #4: you have Docker working, the `nipreps/fmriprep:25.2.5` image pulled, your FreeSurfer license file, your `ds000114/rawdata` BIDS folder, your `bids_filter.json`, and a finished fMRIPrep run for `sub-01` from that dataset. Everything about *how a single fMRIPrep run is configured* is the same here. What's new is that you'll automate it.

**A note on file paths:** as before, any path like `/users/yourname/documents/fmri_class/...` is a placeholder. Replace it with where these folders actually live on *your* computer.

This assignment has two parts:

- **Part 1 (analysis):** Write a single script that loops over three more participants (`sub-02`, `sub-03`, `sub-04`) and runs each through fMRIPrep, then compare head motion for the BOLD run across all four participants.
- **Part 2 (reading):** Pick a published fMRI paper, turn its methods section into a preprocessing flow chart, and reflect on which preprocessing decisions matter most given that study's acquisition and analysis design.

---

# Part 1: Analysis: loop fMRIPrep over three more participants

## Why we're doing this

In Practical #4 you wrote a bash script for one participant, and then did some back-of-the-envelope math about what happens when you have 20, or 2,000, participants. The next skill is turning "one run that works" into "a script that can run over many." Looping over participants is one of the most common things you'll do in neuroimaging, and the same pattern shows up everywhere (fMRIPrep, first-level models, QC scripts, file conversion).

## This is a different kind of assignment: the instructions are intentionally a little bit more abstract

In Practical #4, I gave you the complete script and you mostly had to fill in paths. **This time I'm deliberately giving you much less.** The goal is for you to start figuring out for yourself how you'd design a script like this: what stays the same across participants, what has to change, and how to structure the loop. Getting comfortable with that kind of problem-solving is a really useful skill for developing your own pipelines (in fMRI or beyond!).

Some things that might help:

- **Use the same inputs as last time:** the same `rawdata/` BIDS folder, the same `bids_filter.json`, the same flags (`--session-label test`, `--fs-no-reconall`, `--output-spaces MNI152NLin2009cAsym:res-2 T1w`, etc.), and the same output folder. The only things that should differ are which participant gets processed and anything that has to be unique per participant to keep runs from colliding (see hints). You should be able to use a lot of the code for the fMRIPrep run you set up in the last practical. 
- **Participants to run:** `sub-02`, `sub-03`, `sub-04` (you already have `sub-01`). Again, you only should run on the `overtwordrepetition` task from `ses-test`
- **Language is your choice:** write it as either a **bash script** or a **Python script** (e.g., using `subprocess` or `os.system()` to run bash to call the Docker command). Use whichever you're more comfortable with, or whichever you'd like to practice.
- **It's one script, with a loop.** Not three copies of last week's code with the participant id changed.

**If you get stuck, reach out.** Please don't sit on a problem for hours; send me what you've tried and the error message you're seeing. Being stuck on a script and asking for help is a normal part of this, not a sign you're doing something wrong.

## Why launch a separate job for each participant?

When you read the fMRIPrep documentation, you'll notice `--participant-label` accepts *multiple* labels (e.g., `--participant-label 02 03 04`), so you could in principle hand fMRIPrep all three participants in one call. In practice this isn't always what people do in analysis, and that's true even if they're going to run everything in parallel on a computing cluster. Launching one separate job per participant is often the standard approach, for several reasons:

- **Memory errors are contained.** fMRIPrep is memory-hungry, and memory needs can vary from participant to participant (more volumes, higher-resolution data, a trickier registration). If one big job runs several participants and hits a memory limit, the whole job dies, and it may take participants who would have been fine down with it. With one job per participant, a memory failure on `sub-03` doesn't affect `sub-02` or `sub-04`.
- **Failures are easy to diagnose and re-run.** A separate log and a separate working directory per participant means that when something fails, you know exactly which participant, which log, and which scratch folder to look at. You re-run only the one that failed instead of re-launching everything.
- **It matches how clusters allocate resources.** Cluster schedulers (e.g., SLURM) have you request a specific amount of CPU, memory, and wall-clock time for each job. Requesting resources sized for *one* participant is more precise, and small jobs generally get scheduled sooner than one giant request. Cluster jobs also often have time limits; one participant fits within a limit that a multi-participant job might blow past.
- **It's what makes parallelization possible.** Because each participant's workflow is independent of the others, separate jobs can run at the same time on different cores or different machines. A cluster "job array" is essentially this exact loop, except each iteration is launched simultaneously rather than one after another.
- **Shared state can cause collisions.** Processing many participants in one process, or sharing a scratch directory across simultaneous jobs, creates more opportunities for steps to step on each other's intermediate files and cause errors.

> **On your laptop vs. on a cluster:** The loop you write here will run participants **one after another** (sequentially). That's the right choice on a laptop. **Don't try to launch all three at once on your laptop:** your Docker memory allocation is already probably tight for a single run. The *structure* of the script (one independent job per participant) is the same structure you'd later hand to a cluster scheduler to run in parallel.

## Your task

Write a single script (bash **or** Python) that:

1. Loops over participants `02`, `03`, and `04`.
2. For each one, launches the fMRIPrep Docker container using the same configuration as your `sub-01` run.
3. Saves a separate log file for each participant.

> **Requirement: the `Docker run` command must appear exactly once in your script.** There should NOT be three copies of the `docker run` command with different participant arguments. The whole point of this exercise is to write the command *once*, inside the loop, and let the loop variable change what's different on each pass. Copy-pasting the command per participant is can be a way for typos and silent inconsistencies to sneak in (a wrong path in one copy, a forgotten flag in another). It also doesn't scale (imagine doing that for 200 participants). If your script has the Docker command in more than one place, restructure it before you submit.

Then run it, and let it finish.

### Hints (not a full solution)

**Documentation that will help:**
- fMRIPrep command-line options (including `--participant-label`): <https://fmriprep.org/en/stable/usage.html>
- fMRIPrep output spaces: <https://fmriprep.org/en/stable/spaces.html>
- fMRIPrep filter-file FAQ: <https://fmriprep.org/en/stable/faq.html#how-do-i-select-only-certain-files-to-be-input-to-fmriprep>
- fMRIPrep outputs and report: <https://fmriprep.org/en/stable/outputs.html>
- Python `subprocess` (look at `subprocess.run`): <https://docs.python.org/3/library/subprocess.html>
- Python `os.system`: <https://docs.python.org/3/library/os.html#os.system>
- Bash loops (if you go the bash route): <https://www.gnu.org/software/bash/manual/html_node/Looping-Constructs.html>

Think about the problem before you write any code. A good first step is to take your working bash script from the last practical and ask: **"Which parts of this command are specific to `sub-01`, and which parts would be identical for every participant?"** The parts that are specific to the participant are your loop variable's job. Consider especially:
- the `--participant-label` value,
- the container `--name` (can two containers have the same name at once? What about one after another when `--rm` is used?),
- the log file name

**If you go with bash:**
- Look up how a `for` loop works in bash (`for VAR in a b c; do ... done`), and how to use a variable inside a longer command (and why you'd put it in double quotes).
- Remember that a backslash `\` at the end of a line is what lets a long command span multiple lines. A stray space after it will break it.

**If you go with Python:**
- [`subprocess.run()`](https://docs.python.org/3/library/subprocess.html) takes the command as a *list* of separate arguments (e.g., `["docker", "run", "--rm", ...]`), which can be less error-prone than building one big string. [`os.system()`](https://www.geeksforgeeks.org/python/python-os-system-method/) takes one string and hands it to the shell, which is simpler but easier to get quoting wrong.
- f-strings (`f"sub-{sub}"`) are a convenient way to build paths and names that change on every iteration of a loop.
- `pathlib.Path` can make building paths less messy than gluing strings together.
- Think about how you'd get the same "output to terminal *and* to a log file" behavior that `tee` gave you in bash. What does `subprocess.run(..., stdout=..., stderr=...)` let you do?
- Remember that Docker's `-v` bind mounts need **absolute** paths on your computer, and you still need the filter file and license mounted into the container the same way as last time.

**For either language:**
- **Do a dry run first.** Before launching a multi-hour job, make your script *print* each full Docker command instead of running it (an `echo` in bash, a `print` in Python). Read the printed commands carefully: do the participant labels, log names, and paths look right for each iteration? Catching a typo here costs you seconds instead of hours.
- Decide what should happen if one participant fails. Should the loop stop, or move on to the next? Different choices make sense for different situations, so pick one, and be able to explain why. (In Python, look at what `check=True` does. In bash, look at what happens by default when a command in a loop fails.)
- Keep the `echo`/`print` timestamps before and after each participant's run, like you had in `sub-01`'s script, so you can see how long each one took.

### Practical considerations

- **Time:** Think back to how long fMRIPrep took for `sub-01` last week and **multiply that by 3** to get a rough estimate of how long this script will run (probably on the order of hours). **I do not expect you to spend this whole time working on the assignment.** The time the script spends running is not time you spend working: the work is writing and checking the script, which should take a fraction of that. Plan to launch the script right before you're going to be away from your computer. Plug in your computer, and use the same sleep-prevention tips from last time (`caffeinate -i` on macOS or make sure to turn of settings that allow your computer to sleep automatically when plugged in). Do the dry run (see hints) *before* you walk away, so you're not coming back to find a typo wasted the whole night. If you're worried about fitting this into your schedule, **tell me early**.
- **Disk space:** each participant generates output *and* a scratch `work/` folder. Check you have enough free space before starting (should require about 1.5GB per participant).
- **If a participant fails:** use the troubleshooting tips from Practical #4 (check Docker's memory allocation first; clear that participant's `work/` folder before re-running). You shouldn't need to re-run participants that already finished.

## Compare head motion across participants

Once all runs finish, open each participant's HTML report (`sub-01.html` through `sub-04.html`) in your browser. In the **functional** section of each report, find the **BOLD Summary** panel. The mean framewise displacement (FD) is shown there, usually to the right of the FD timeseries. **Get the mean FD estimate directly from the report.**


Identify **which participant's BOLD scan has the highest mean FD and which has the lowest.**

(If you can't find the mean FD value in a report, send me a screenshot and what you've tried.)

---

# Part 2: Reading — Flow chart of a preprocessing pipeline from a published paper

## Why we're doing this

Reading papers a great way to learn what preprocessing decisions are, what alternatives exist, and which choices were *deliberate* versus defaults. Methods sections are also where it becomes clear that "preprocessing" isn't one fixed recipe: it's a series of choices that should depend on what data was collected and what scientific question is being asked.

## Your task

1. **Choose any fMRI paper** with a methods section that describes its preprocessing with at least some detail. It can be a topic you're interested in, or a paper from your own lab or field. (A paper that only says "data were preprocessed using standard procedures" won't give you enough to work with. If the paper used fMRIPrep, that's fine, but your flow chart should still show the individual steps the paper describes, not just a single box labeled "fMRIPrep.").

2. **Make a flow chart of the preprocessing pipeline, as best you can, from the methods section.** Show the steps in the order they were applied (e.g., slice-timing correction, motion correction, coregistration, normalization, smoothing, etc.), and note key parameters where reported (e.g., smoothing kernel size, high-pass filter cutoff, template space). It doesn't matter what program you use or how you format it (you can even draw it by hand and upload) as long as it clearly shows the steps in that paper. If the paper doesn't clearly say whether or in what order something was done, say so on your chart (e.g., "order not specified") rather than guessing silently. Also note down any jargon you're not sure about and bring this up in class!

3. **Identify the key acquisition parameters and the scientific analysis design** from the paper. You'll need these for the next step:
   - Acquisition: **TR**, **voxel size**, **number of volumes collected**, and **field of view (FOV)** (plus anything else you think is relevant, like multiband acceleration or field strength).
   - Design: what's the statistical question? (e.g., event-related vs. block design, task activation vs. resting-state connectivity, ROI vs. whole-brain, individual-level vs. group-level inference, decoding/multivariate vs. univariate)

4. **Write 2–3 sentences** on which preprocessing decisions seem **most important given the acquisition parameters and the scientific analysis, and why.** Tie your argument to specifics. Some things you might think about (you don't need to cover all of them):
   - **Spatial resolution:** How big are the voxels, and what does that imply? Does the question need precise anatomical localization (e.g., small subcortical structures, individual-level or pattern analyses) or is the analysis at the group level where some smoothing can help with alignment and power?
   - **Temporal resolution:** Is the TR short or long? Does the design depend on precise timing (e.g., fast event-related designs)?
   - **Statistical power:** Which steps would help or hurt your power to detect the effect of interest (e.g., denoising choices, how motion is handled, filtering that might remove signal along with noise)?
   - **Fit between acquisition and analysis:** Is anything about the pipeline a mismatch for the data or the question? Or did the authors make a choice that seems especially well-suited?

There's no single right answer here. I'm looking for evidence that you're connecting the pipeline to the data and the scientific question, instead of treating preprocessing as a checklist.

---

## What to turn in

Submit on Canvas:

**Part 1**
- Your single script (bash `.sh` or Python `.py`) that loops over participants `02`, `03`, and `04`, with the Docker command written only once.
- Your log file(s) from the run (or, if easier, a screenshot/excerpt showing each participant started and finished).
- A note on **which participant's scan has the highest mean FD and which has the lowest**.

**Part 2**

This can all be one document: 
- The **citation** for the paper you chose.
- Your **preprocessing flow chart** (image or PDF).
- Your **list of the key acquisition parameters (TR, voxel size, number of volumes, FOV) and a brief description of the scientific analysis design.**
- Your **2–3 sentence response** about which preprocessing decisions seem most important and why.