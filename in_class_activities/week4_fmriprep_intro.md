# In-Class Activity: Understanding fMRIPrep's Inputs and Outputs


## How to submit this

**Create a new `.txt` or Word (`.docx`) file**, not this document, and write your answers to every numbered question below in it, numbered to match so you can submit it via Canvas. You can create 1 single file working as a group to answer this - if you do so, please put everyone's names at the top of the file and everyone turn this in on Canvas individually.  

## Why we're doing this

Before you run fMRIPrep yourself for the next practical assignment, it's worth getting comfortable with what it actually takes in and produces, using a fully worked example someone else has already run. fMRIPrep usually takes hours to fully run, so we wouldn't get much done by running it in class. 

Today has one goal: given a raw BIDS dataset and a derivatives folder fMRIPrep produced from it, can you say what each output file represents and where it came from? Note: for today we aren't yet focused on QAing the outputs (whether they look "good"), but rather just understanding what they are. We'll get to judging quality in a later assignment.

---

## Part 1: The raw input (the Flanker dataset)

The Andy's Brain Book's fMRIPrep demonstration uses a real, publicly available dataset: a Flanker task dataset on OpenNeuro (the same one used earlier in that course's AFNI/FSL/SPM tutorials), focusing throughout on one subject, **`sub-08`**.

Open this link to view the BIDS data structure on OpenNeuro: <https://openneuro.org/datasets/ds000102/versions/00001>

You don't have to download the data for this, but open up the folder on OpenNeuro for `sub-08` and inspect the files for the participant.

**Answer:**

1. What are the two main subfolders that make up this dataset's BIDS structure for a given subject, and what does each one contain?
2. Andy's Brain Book's [Tutorial #3](https://andysbrainbook.readthedocs.io/en/latest/OpenScience/OS/fMRIPrep_Demo_3_ExaminingPreprocData.html) (which you'll read next) refers to "each of the runs" for this task, implying there's more than one functional run per subject. What is a run? What task is there more than one run for, and how many runs are there per participant?

---

## Part 2: Read Andy's Brain Book's walkthrough of the outputs

Read **[Andy's Brain Book's Tutorial #3: Examining the Preprocessed Data](https://andysbrainbook.readthedocs.io/en/latest/OpenScience/OS/fMRIPrep_Demo_3_ExaminingPreprocData.html)** in full. Make sure you also watch the video at the end (https://www.youtube.com/watch?v=fQHEKSzFKDc).

This page shows the actual `anat/` and `func/` output listings fMRIPrep produced for `sub-08`, and walks through the HTML summary report section by section. Read it closely enough to answer Parts 3 and 4 below; you'll need to refer back to specific filenames and descriptions on this page. No answers needed for this part on its own.

> **One thing to note before you read on:** the fMRIPrep run documented in Tutorial #3 was configured to do full FreeSurfer surface reconstruction and produce CIFTI output (a combined surface+volume format), a heavier, slower configuration than the one we'll use for our own `ds000114` run in the next practical, which skips surface reconstruction entirely (`--fs-no-reconall`) to keep runtime manageable. Keep that difference in mind, since you'll see fewer output files and report sections in your own run than Tutorial #3 describes here.

---

## Part 3: Input → output mapping

Using the combination of the Flanker dataset on OpenNeuro and what [Andy's Brain Book Tutorial #3](https://andysbrainbook.readthedocs.io/en/latest/OpenScience/OS/fMRIPrep_Demo_3_ExaminingPreprocData.html) showed you, answer the following:

3. Tutorial #3 gives the example file `sub-08_space-MNI152NLin2009cAsym_desc-preproc_T1w.nii.gz`. Which raw input file was this ultimately derived from, and what does the `space-MNI152NLin2009cAsym` part of the name tell you about it?
4. Tutorial #3 also mentions `sub-08_space-MNI152NLin2009cAsym_label-CSF_probseg.nii.gz`. What does this file represent, and how is a "probabilistic segmentation" conceptually different from a binary brain mask?
5. What is native space? Based on the naming pattern in question 3, what would change about the filename if you were looking at the native space version of that same preprocessed T1w image?
6. What is a `boldref` file, and why does fMRIPrep generate one separately rather than just providing the full preprocessed BOLD time series?
7. Tutorial #3 describes a `desc-brain_mask` file in the `func/` directory, estimated for a specific run. How is this mask conceptually different from the brain mask generated in the `anat/` directory, given that they're computed from different source images?
8. Tutorial #3 describes a confounds file containing "a list of confound regressors." What are confound regressors? Provide some specific examples.

---

## Part 4: Finding your way around the HTML report

Still using [Andy's Brain Book Tutorial #3](https://andysbrainbook.readthedocs.io/en/latest/OpenScience/OS/fMRIPrep_Demo_3_ExaminingPreprocData.html), answer the following. These questions aren't about whether anything looks *good*; they're about **where** in the report you'd go to find each piece of information:

9. Where would you check whether this subject had any processing errors, and why does Tutorial #3 suggest checking there *first*, before looking at anything else?
10. Where would you confirm how many T1w images and how many functional runs were actually processed for this subject?
11. Which panel shows the brain mask and tissue-type contours overlaid on the anatomical image, and which three tissue/region boundaries does it outline?
12. Which panel is specifically about assessing whether the BOLD data and the anatomical image are aligned to each other (as opposed to whether the anatomical image is aligned to the template)?
13. Which panel would you check to see framewise displacement visualized as a plot, rather than reading the raw values out of the confounds `.tsv` file yourself?

---

## Reflection

14. Now, if someone handed you a folder of fMRIPrep derivatives, would you be able to identify what is what for subsequent statistical analyses? What's the one part of the naming convention (an entity like `space-`, `desc-`, `res-`, or something else) that you now feel is the most important one to get right when reading or searching through output files?
15. What would you do if you ran fMRIPrep and *did not see* some of the expected outputs discussed today? 

## What to turn in

Submit your answer file (`.txt` or `.docx`, numbered 1 to 15) on Canvas.