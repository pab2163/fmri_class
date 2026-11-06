import os
import pandas as pd

# ---------------------------------------------------------------------------
# PATHS: update these for your own project
# ---------------------------------------------------------------------------
flanker_dir = '/Users/mexico/Documents/Teaching/fundamentals_human_brain_imaging/datasets/flanker'
bids_dir = f'{flanker_dir}/rawdata'  # <- BIDS directory containing the *_events.tsv files

# Which participants and runs to process
subs = ['sub-01', 'sub-02', 'sub-03']
runs = ['run-1', 'run-2']


for sub in subs:
    for run in runs:

        # -------------------------------------------------------------------
        # Part 1: Confound regressors (from fMRIPrep) -> FSL confounds file
        # -------------------------------------------------------------------
        # Input: fMRIPrep confounds timeseries for this subject/run
        confounds_input_path = f'{flanker_dir}/derivatives/fmriprep_outputs/{sub}/func/{sub}_task-flanker_{run}_desc-confounds_timeseries.tsv'

        # Output: one folder per subject inside derivatives/fsl_inputs
        confounds_output_dir = f'{flanker_dir}/derivatives/fsl_inputs/{sub}'

        # Create the output folder if it doesn't already exist
        os.system(f'mkdir -p {confounds_output_dir}')

        confounds_output_path = f'{confounds_output_dir}/{sub}_task-flanker_{run}_fsl_confounds.txt'

        # Call the helper script to select 6 motion params, 5 CompCor components,
        # and flag high-motion volumes (FD > 0.5 mm), saved in FSL's format
        cmd = f'python fmriprep_confounds_to_fsl.py {confounds_input_path} -o {confounds_output_path} \
            --motion 6 --compcor 5 --fd-threshold 0.5'

        os.system(cmd)

        # -------------------------------------------------------------------
        # Part 2: BIDS events.tsv -> FSL 3-column regressor files
        # -------------------------------------------------------------------
        # Input: the BIDS events file for this subject/run
        events_path = f'{bids_dir}/{sub}/func/{sub}_task-flanker_{run}_events.tsv'
        events = pd.read_csv(events_path, sep='\t')

        # Make one file per condition. To use different conditions, change this
        # list and the column name ('Stimulus') below to match your events file.
        for cond in ['congruent', 'incongruent']:

            # Keep only the trials of this condition, and only the onset
            # and duration columns (both in seconds)
            ev = events.loc[events['Stimulus'] == cond, ['onset', 'duration']].copy()

            # FSL's 3rd column is the weight/amplitude; 1 = equal weight for all trials
            # If we had a parametric design, the weight would differ for different trials here
            ev['weight'] = 1

            # Save as tab-separated with no header or index (FSL's required format),
            # in the same folder as the confounds file
            ev.to_csv(f'{confounds_output_dir}/{sub}_task-flanker_{run}_{cond}_fsl_ev.txt',
                      sep='\t', header=False, index=False)