import os
import re

# ---------------------------------------------------------------------------
# EDIT THIS PART ONLY
# ---------------------------------------------------------------------------
flanker_dir = '/Users/mexico/Documents/Teaching/fundamentals_human_brain_imaging/datasets/flanker'
template_fsf = f'{flanker_dir}/derivatives/fsl_level1/sub-01_run-01.feat/design.fsf'     # your working fsf for one subject/run
subs = ['sub-01', 'sub-02', 'sub-03']
runs = ['run-1', 'run-2']
# ---------------------------------------------------------------------------
# EVERYTHING BELOW RUNS AUTOMATICALLY
# ---------------------------------------------------------------------------

fsf_dir = f'{flanker_dir}/derivatives/fsl_fsfs'          # folder where the new fsfs are saved
os.makedirs(fsf_dir, exist_ok=True)

template = open(template_fsf).read()

def set_field(text, field, new_value):
    """Replace the quoted value of one line in the fsf, e.g. set fmri(outputdir) "..." """
    pattern = rf'(set {re.escape(field)} )".*"'
    return re.sub(pattern, rf'\1"{new_value}"', text)

for sub in subs:
    for run in runs:
        inputs = f'{flanker_dir}/derivatives/fsl_inputs/{sub}/{sub}_task-flanker_{run}'

        fsf = template
        fsf = set_field(fsf, 'fmri(outputdir)',
                        f'{flanker_dir}/derivatives/fsl_level1/{sub}_{run}')
        fsf = set_field(fsf, 'feat_files(1)',
                        f'{flanker_dir}/derivatives/fmriprep_outputs/{sub}/func/{sub}_task-flanker_{run}_space-MNI152NLin2009cAsym_res-2_desc-preproc_bold')
        fsf = set_field(fsf, 'confoundev_files(1)', f'{inputs}_fsl_confounds.txt')
        fsf = set_field(fsf, 'fmri(custom1)', f'{inputs}_congruent_fsl_ev.txt')
        fsf = set_field(fsf, 'fmri(custom2)', f'{inputs}_incongruent_fsl_ev.txt')

        out_path = f'{fsf_dir}/{sub}_task-flanker_{run}_level1.fsf'
        with open(out_path, 'w') as f:
            f.write(fsf)

print(f'Wrote {len(subs) * len(runs)} fsf files to {fsf_dir}')
print('Run them with:  for f in ' + fsf_dir + '/*.fsf; do feat $f; done')