# Python Practical: Running Scripts from the Terminal, and Nilearn

## Andy's Brain Book Python Tutorial
**First:** Go through all 5 sections of the ["Python for Neuroimagers" tutorial from Andy's Brain Book"](https://andysbrainbook.readthedocs.io/en/latest/PythonForNeuroimagers/PythonForNeuroimagers_Overview.html#what-is-python).

Note, it's a good idea to read parts 1 and 5, but this practical will mostly focus on the content from parts 2-4 using python scripts. We'll be using Jupyter Notebooks (covered in part 1) too soon!

### Goals for this activity 
Write a series of short Python scripts in a text editor and run
each one from the command line, building up to using `nilearn`. 

**Why separate scripts?** Each part below is its own `.py` file. Write one,
run it, and get it working *before* moving on to the next. This makes it
much easier to tell exactly where a problem is if something goes wrong, as 
you're only ever troubleshooting one small piece at a time, instead of
hunting through one long script for a bug. 

---

## Setup

No new Python installation is needed for this assignment — you'll use the
`fmri_class` conda environment we set up in class, which already has `nilearn`
and its dependencies installed.

1. Open a terminal and activate that environment:
   ```bash
   conda activate fmri_class
   ```
   Your terminal prompt should now show `(fmri_class)` at the start of the
   line. If `conda activate` isn't recognized, run `conda init` for your
   shell as instructed, restart your terminal, and try again.
2. Pick an editor:
   - **VS Code:** open your folder, then open the built-in terminal
     (`` Ctrl+` `` / `` Cmd+` ``) and activate the environment there — VS
     Code opens a plain terminal by default, so this step still applies.
     You can also select the `nilearn` environment as your Python
     interpreter (bottom-right corner), but still run your script from the
     terminal, not with a "Run" button.
   - **Sublime Text:** write your code there, but run it in a *separate*
     terminal window with the `nilearn` environment activated — Sublime
     doesn't execute Python for you.
3. Initial check: save a one-line file (`print("ready")`) as `hello.py`, `cd`
   into its folder in your terminal (with `nilearn` still activated), and
   run:
   ```bash
   python hello.py
   ```
   Confirm you see the output before moving on. Every time you open a new
   terminal window for this assignment, re-run `conda activate nilearn`
   first.

---

## Part 1: Variables, Types, and a Scan-Parameters Dictionary

Create a new file called `part1.py`.

Start by declaring a few variables that describe a made-up fMRI scan: a
repetition time (`tr`, a float), a number of volumes (`n_volumes`, an
integer), a scan ID (`scan_id`, a string), and whether it's resting-state
(`is_resting_state`, a boolean). Print each variable's `type()` to confirm
Python is treating it the way you expect.

Next, build a dictionary called `scan_params` with keys `"TR"`,
`"voxel_dimensions"`, and `"volumes"` — the same pattern used for
`fMRI_Image` in Tutorial #2. Add a new key (`"orientation"`), overwrite the
`"TR"` value using your `tr` variable, and print the result.

Then create a tuple, `scanner_info`, with three pieces of scanner
information (e.g. manufacturer, field strength, coil type), and print it
along with its length.

Finally, use a string method or an f-string to print a sentence containing
`scan_id` written entirely in uppercase.

**Run it:** in your terminal, with `nilearn` activated, run
`python part1.py` and confirm all of the printed output looks correct
before moving on.

---

## Part 2: Lists, For-Loops, and Conditionals

Create a new file called `part2.py`.

Create a list called `subjects` with at least six subject IDs, and a second
list, `outliers`, containing one or two IDs you want to exclude.

Write a `for`-loop over `subjects`. For each subject, check whether it's in
`outliers` (the `in` keyword works on lists) and print a different message
depending on the result — something like "skipping outlier" versus
"processing subject." Add a counter variable, incremented only for subjects
that get processed, and print the total once the loop finishes.

**Run it:** run `python part2.py` and confirm the loop prints the expected
messages and the final count is correct before moving on.

---

## Part 3: Functions — A Scan Duration Calculator

Create a new file called `part3.py`.

Define a function, `calculate_scan_duration(tr, volumes)`, with a
[docstring](https://www.geeksforgeeks.org/python/python-docstrings/#google_vignette),
that returns the total scan time in seconds (TR × number of volumes).

Define a second function, `classify_scan_length(duration_seconds)`, that
uses `if` / `elif` / `else` to return `"short scan"` (under 120 seconds),
`"typical scan"` (120–600 seconds), or `"long scan"` (over 600 seconds).

Create a list of at least three dictionaries, each with `"id"`, `"tr"`, and
`"volumes"` keys, representing different scans. Loop through the list,
calling both functions on each entry, and print a summary line for each one
(id, computed duration, and classification as short/typical/long).

**Run it:** run `python part3.py` and confirm each scan gets a duration and
classification that matches what you'd expect by hand before moving on.

---

## Part 4: Modules and Nilearn

Create a new file called `part4.py`.

`nilearn` can automatically download small, public reference datasets, so
you don't need any scans of your own for this practical.

Import `datasets` and `plotting` from `nilearn`, and `pyplot` from
`matplotlib`. Fetch a small cortical atlas:

```python
atlas = datasets.fetch_atlas_harvard_oxford("cort-maxprob-thr25-2mm")
```

The first run will download a few MB and cache it; later runs will be fast.

Explore what came back: print `type(atlas.labels)` and `len(atlas.labels)`,
then use a `for`-loop with `range()` to print the first five labels along
with their index numbers. Next, write a loop that counts how many labels
contain the substring `"Frontal"` (check with `if "Frontal" in label:`) and
print the total.

Finally, plot the atlas and save it to a file — don't use `plt.show()`,
since you're running from the terminal:

```python
display = plotting.plot_roi(atlas.maps, title="Harvard-Oxford Cortical Atlas")
display.savefig("atlas_plot.png")
```

**Run it:** run `python part4.py`. Confirm the labels and count print
correctly, and that `atlas_plot.png` appears in the same folder and opens to
show a labeled brain atlas image. If something fails, read the last line of
the error message first — it usually names the line number and the type of
problem (`NameError`, `IndentationError`, `TypeError`, etc.).

## What to turn in

Submit each of your 4 python scripts (`part1.py`, `part2.py`, `part3.py`, and `part4.py`) and your plot of the Harvard-Oxford Cortical atlas (`atlas_plot.png`) on Canvas. 
