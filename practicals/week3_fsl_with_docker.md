# Practical #2: Running FSL in a Container & Inspecting Real fMRI Data

**Assumes:** Docker Desktop installed and verified (from last week's in-class activity). You already have a local BIDS-formatted data folder from BIDS class (week 2), which you'll work with in this practical.

## Why we're doing this

You've gotten Docker running and got a first feel for how files inside a container are isolted from the computer you are running the container on. Now, you'll pull a containerized version of FSL via a docker image, and use it to actually look inside the real BIDS scan data you already have from our earlier BIDS session. The core skill this week is **"bind mounting"**: getting your laptop's files in and out of a container, so the container can do useful work on *your* data instead of just the files that ship inside the image.

---

## Part 1: Pull the FSL image

We'll use a pre-built FSL image maintained by the Brainlife project (https://brainlife.io/about/). In your terminal, run:
```
docker pull brainlife/fsl
```
This downloads the image (about 5GB, so it may take a few minutes). It contains FSL 6.0.7.22, fully installed and pre-configured, so you won't need to run any FSL installer yourself.

Confirm it's on your machine:
```
docker images
```
You should see `brainlife/fsl` listed.

**Note:** this is a lightweight, command-line-only build of FSL. It includes core tools like `bet`, `flirt`, `fnirt`, `fslmaths`, `fslhd`, `fslmeants`, `feat`, and `fslstats`, but not the FSLeyes graphical viewer. You'll still want to use the non-Docker FSL you have installed for viewing images in [FSLeyes](https://pages.fmrib.ox.ac.uk/fsl/docs/utilities/fsleyes/).

FSL is a big piece of software with a lot of tools beyond what we'll touch today. The [FSL documentation](https://fsl.fmrib.ox.ac.uk/fsl/docs/) is the best starting point if you want to see the full picture, and I encourage you to browse it at some point this semester, not just when you're stuck.

---

## Part 2: Quick refresher, running the container

This starts an interactive bash shell inside the container. The `--it` flag makes it interactive, so you can run code interactively, rather than just using the container to execute one script.

```
docker run --rm -it brainlife/fsl:latest /bin/bash
```
Try `echo $FSLDIR` (should show a directory) and `fslmaths --help` (should print out documentation for using fslmaths), then `exit` when you're done poking around. As before, `--rm` means the *container* disappears when you exit, but the *image* stays saved. Run `docker ps -a` after exiting to make sure the container is gone.

The rest of this practical is about doing something more useful than poking at the container's built-in files: getting **your own downloaded scan** in, and getting **results** back out.


> **Note for Apple Silicon (M1/M2/M3/M4) Mac users**
>
> When you pull or run the FSL image, you'll likely see this warning:
> ```
> WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8) and no specific platform was requested
> ```
> This is expected, not an error. The `brainlife/fsl` image was only built for Intel/AMD chips (`amd64`), and your Mac's Apple Silicon chip is a different architecture (`arm64`). Docker Desktop handles this automatically by emulating an amd64 environment, so the container will still run correctly. It will just run a bit slower than a native arm64 image would.
>
> You can safely ignore the warning. If you'd rather not see it, add `--platform linux/amd64` explicitly:
> ```
> docker pull --platform linux/amd64 brainlife/fsl
> docker run --rm -it --platform linux/amd64 brainlife/fsl:latest /bin/bash
> ```
> For a modest speed boost, you can also turn on **Use Rosetta for x86/amd64 emulation on Apple Silicon** under Docker Desktop's Settings → General.

> **Note for Windows users: troubleshooting tips**
>
> A few Windows-specific issues come up often enough that it's worth knowing about them ahead of time:
>
> - **`/bin/bash: no such file or directory`**: some images don't have bash at exactly that path. Try running just `bash` instead of `/bin/bash`, e.g. `docker run --rm -it brainlife/fsl:latest bash`. If that still fails, fall back to `sh`, which is present in almost every Linux image.
> - **Run commands from a WSL2 terminal, not PowerShell**: this course's instructions use Linux-style paths (`/workspace/bids`, `~/...`). Working inside your WSL2 (Ubuntu) terminal, rather than PowerShell or Command Prompt, means these paths behave the way we describe. Docker Desktop should already be configured to use the WSL2 backend (check under Settings → General → **Use the WSL 2 based engine**).
> - **"Drive has not been shared" errors when mounting a folder**: go to Docker Desktop's Settings → Resources → File Sharing, and make sure the drive containing your course folder is shared with Docker.
> - **Mounted paths look wrong or the `-v` flag doesn't work as expected**: if you're running Docker commands from PowerShell instead of WSL2, Windows paths need extra formatting (e.g., `//c/Users/yourname/...` instead of `C:\Users\yourname\...`). Switching to a WSL2 terminal avoids this entirely and is the recommended approach for this course.
> - **A mounted script fails with a "bad interpreter" error**: this usually means the file has Windows-style line endings (CRLF) instead of Unix-style (LF). Convert it with `dos2unix yourscript.sh`, or check your editor's line-ending setting (in VS Code, it's shown in the bottom-right corner).

---

## Part 3: Mounting your data into the container

Right now, the container can't see your laptop's files, and your laptop can't see the container's files. Anything you do inside disappears when the container closes. To fix this, we "mount" folders from your laptop into the container using the `-v` flag.

In general this follows the syntax `-v [path on your computer]:[path inside Docker container]`

This time we'll mount **two** folders: one for input (read-only) and one for output, because that's the pattern you'll use in almost every real analysis: keep raw data separate from what you generate. This kind of mount is officially called a [bind mount](https://docs.docker.com/storage/bind-mounts/) in Docker's documentation, which is worth reading if you want a deeper explanation of how it differs from other kinds of Docker storage.

On your laptop, make an empty output folder somewhere in your course folder. Use your own path here, this is just an example:
```
mkdir -p /users/yourname/documents/fmri_class/week3/fsl_docker_outputs
```

Now launch the container, mounting both folders. Notice the extra `:ro` on the input dataset. This makes it read-only so you can't accidentally change the input data. Adjust both paths below to match your own folders:
```
# the first -v mounts the input dataset (read-only)
# the second -v mounts the output directory (writable)
docker run --rm -it \
  -v /users/yourname/documents/fmri_class/datasets/ds000114:/workspace/bids:ro \
  -v /users/yourname/documents/fmri_class/week3/fsl_docker_outputs:/workspace/out \
  brainlife/fsl:latest /bin/bash
```

Everything else (`--rm -it`, image name, `/bin/bash`) is the same as before, this launches an interactive session so you can run commands one at a time from the bash command line.

Once inside the container, confirm you can see your data:
```
ls /workspace/bids
cd /workspace/bids/sub-01/ses-test/func
ls
```

You should see a bunch of bold data files files now (as well as an events tsv file). If not you might need to try to work through the prior steps again until you can see your data while working inside the docker container.

---

## Part 4: Look at some BOLD data using FSL via docker

Now, still inside the container and inside that `func` folder, run these on your `_bold.nii.gz` file.

First, `fslhd` prints the complete NIfTI header for an image, every field FSL knows about it. `fslhd`, along with the other command-line tools in this practical, is documented in FSL's [FSLUTILS reference](https://pages.fmrib.ox.ac.uk/fsl/docs/utilities/fslutils/), which we'd encourage you to read through rather than treating this practical as the whole story. Run it on your BOLD file:
```
fslhd sub-01_ses-test_task-overtwordrepetition_bold.nii.gz
```
Two sets of numbers matter most for this exercise:
- `pixdim1`, `pixdim2`, `pixdim3`, voxel dimensions in mm (the size of one 3D "pixel")
- `dim4`, the number of volumes (timepoints) in the scan
- `pixdim4`, the repetition time (TR), in seconds, i.e. how long each volume took to acquire

`fslinfo` is a lighter-weight cousin of `fslhd`. It reports just the handful of fields people check most often (dimensions, voxel size, data type) without printing the entire header. For a quicker, more compact view of the same information:
```
fslinfo sub-01_ses-test_task-overtwordrepetition_bold.nii.gz
```

`fslnvols` is a small, single-purpose utility that returns just the number of volumes in a 4D image, so you don't have to hunt for it inside a full header. To get the number of volumes directly:
```
fslnvols sub-01_ses-test_task-overtwordrepetition_bold.nii.gz
```
Confirm this number matches `dim4` from `fslhd`.

---

## Part 5: Create outputs from your data

Let's create two new files from your BOLD scan and confirm they land back on your laptop, not just inside the (soon-to-vanish) container.

### A mean image across time

`fslmaths` is FSL's general-purpose, voxelwise image calculator. It can add, subtract, threshold, smooth, and compute all kinds of statistics on an image, one voxel at a time. One thing it can do is collapse a 4D image (with a time dimension) down into a single 3D image by averaging across time, using the `-Tmean` flag. `fslmaths` has dozens of other flags documented in the [FSLUTILS reference](https://pages.fmrib.ox.ac.uk/fsl/docs/utilities/fslutils/); this practical only scratches the surface.

Compute the mean BOLD signal at every voxel, averaged across all timepoints, and save it to your mounted output folder:
```
fslmaths sub-01_ses-test_task-overtwordrepetition_bold.nii.gz -Tmean /workspace/out/sub-01_mean_bold.nii.gz
```
This gives you a single 3D "mean image", useful for a quick visual check of where signal is present, and a common first step before more complex analyses.

Confirm that the file output now exists, especially that `dim4` (time) should now just be 1 (since it is a single mean image, rather than a timeseries)

```
fslinfo /workspace/out/sub-01_mean_bold.nii.gz
```

### A timeseries of whole-volume means

`fslmeants` does the opposite kind of averaging: instead of collapsing across time, it collapses across space. For each timepoint in a 4D image, it averages together every voxel in that volume and writes out one number per timepoint, as a text file. If you don't give it a mask, it uses the whole volume by default, which is exactly what we want here.

Export a timeseries of the mean of each whole volume to a text file in your output folder:
```
fslmeants -i sub-01_ses-test_task-overtwordrepetition_bold.nii.gz -o /workspace/out/sub-01_mean_timeseries.txt
```

Use `cat` to print out the contents of that file you created to the command line

```
cat /workspace/out/sub-01_mean_timeseries.txt
```

This produces one row per volume (timepoint), each containing the average signal across the whole brain volume at that timepoint.

Now exit the container:
```
exit
```
You can run `docker ps -a` again to confirm that the container has been removed. Back on your own laptop (not inside a container), check that both files are there:

```
ls -lh /users/yourname/documents/fmri_class/week3/fsl_docker_outputs
```
You should see `sub-01_mean_bold.nii.gz` and `sub-01_mean_timeseries.txt` sitting there, both created by a container that no longer exists.

Now, try opening up `sub-01_mean_bold.nii.gz` with FSLeyes (not using Docker). Can you confirm here that the file is represented by only a single volume (not multiple volumes over time?

---

## Part 6: Running Docker non-interactively to compute a tSNR image

Many of the things we will want to run via docker will most likely not be interactive at all, especially if they are tasks (like preprocessing with fMRIPrep, some analyses) that take a long time to run. In these cases, we might just want to run the whole docker container in one go, and then inspect the outputs on our computers once it is done. You can run a single FSL command directly from your laptop's terminal by putting the command at the end of `docker run` instead of `/bin/bash`. This pattern, along with every other `docker run` option, is documented in the [docker run reference](https://docs.docker.com/reference/run/).

We'll use this non-interactive pattern to compute something called **tSNR: temporal signal-to-noise ratio**.

### What is tSNR, and why does it matter?

tSNR is a simple but widely used measure of fMRI data quality. At every voxel, it's defined as:

```
tSNR = (mean signal over time) / (standard deviation of signal over time)
```

In other words: for a given voxel, how strong is the average BOLD signal, relative to how much that signal bounces around from one timepoint to the next? A voxel with a **high** tSNR has a signal that is strong and stable over time, so it's easier to reliably detect real changes in activity there. A voxel with a **low** tSNR has a signal that may be weak and/or noisy, which makes it harder to trust any stats you might see from that voxel.

tSNR maps are a standard quality-control step in fMRI analysis. Researchers use them to spot regions of a scan that are likely to be unreliable, so that low-tSNR regions can be interpreted cautiously (or excluded) rather than mistaken for genuine effects.

### Step 1: compute the standard deviation over time

You already computed the mean image (`sub-01_mean_bold.nii.gz`) in Part 5. Now use `fslstats` again to compute the matching standard deviation image, using the `-Tstd` flag, which is the temporal analog of `-Tmean`. Notice we are NOT including the `--it` flag, so this will not be interactive and you will not be put into a terminal "inside" the container.

```
docker run --rm \
  -v /users/yourname/documents/fmri_class/datasets/ds000114:/workspace/bids:ro \
  -v /users/yourname/documents/fmri_class/week3/fsl_docker_outputs:/workspace/out \
  brainlife/fsl:latest \
  fslmaths /workspace/bids/sub-01/ses-test/func/sub-01_ses-test_task-overtwordrepetition_bold.nii.gz -Tstd /workspace/out/sub-01_std.nii.gz
```
This produces a 3D image, `sub-01_std.nii.gz`, where each voxel's value is how much that voxel's signal varied across the scan. Make sure this showed up on your output folder on your computer!

### Step 2: divide the mean by the standard deviation to get tSNR

Now divide the mean image by the standard deviation image, voxel by voxel, using `-div`. Since both inputs (`sub-01_mean_bold.nii.gz` and `sub-01_std.nii.gz`) already live in your output folder, this command only needs to mount that one folder:
```
docker run --rm \
  -v /users/yourname/documents/fmri_class/week3/fsl_docker_outputs:/workspace/out \
  brainlife/fsl:latest \
  fslmaths /workspace/out/sub-01_mean_bold.nii.gz -div /workspace/out/sub-01_std.nii.gz /workspace/out/sub-01_tSNR.nii.gz
```
Notice both of these commands skip `-it` and `/bin/bash` entirely: each container just runs its one command and exits, which is exactly the pattern you'd use for a long, unattended job.

Confirm the file exists on your laptop:
```
ls -lh /users/yourname/documents/fmri_class/week3/fsl_docker_outputs
```
You should now see `sub-01_std.nii.gz` and `sub-01_tSNR.nii.gz` alongside the two files from Part 5.

### Look at your tSNR map in FSLeyes

Open `sub-01_tSNR.nii.gz` in FSLeyes (not through Docker, the same non-Docker FSLeyes install you used at the end of Part 5). Scroll through the brain and look for patterns in where tSNR is high versus low.

A few things to look for, and note down for your reflection:
- Where does tSNR look **highest**? This is usually in the middle of the brain, away from air/tissue boundaries.
- Where does tSNR look **lowest**? 

---

## Reflection

Write a short reflection (no more than one paragraph). Things you could mention:
- Any errors or points of confusion you ran into, and how you resolved them (or didn't)
- What types of tasks do you think Docker would be useful for? What types of tasks do you think Docker would *not* be useful for?
- What did you notice about where SNR was higher versus lower in your subject's data, and does that match what the reflection prompt above described?

Submit your reflection on Canvas, as well as the 3 file outputs generated via running the FSL docker container (`sub-01_mean_bold.nii.gz`, `sub-01_mean_timeseries.txt`, `sub-01_tSNR.nii.gz`).