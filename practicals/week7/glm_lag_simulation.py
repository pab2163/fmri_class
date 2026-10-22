"""
Simulation: how does the temporal separation between events A and B affect
regressor correlation, contrast variability, standard errors, and t-values?

For each lag (B onset = A onset + lag), we:
  1. build the HRF-convolved design matrix (same approach as the Ch. 18 lab)
  2. compute the correlation between the A and B regressors
  3. simulate N_SIMS noisy voxels with known betas, fit OLS, and record the
     A-B contrast estimate, its SE, and its t-value
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")           # remove this line if running interactively
import matplotlib.pyplot as plt
from scipy import stats

# ----------------------------------------------------------------- settings
N_SIMS = 100                     # simulated voxels per lag
LAGS = [0.5, 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12]   # seconds between A and B onset
BETA_TRUE = np.array([0.8, 0.4, 100.0])           # [A, B, intercept]
SIGMA = 2.0                      # noise SD
SEED = 2024

T_R, N_SCANS, DT, DURATION = 2.0, 180, 0.1, 1.0
RUN_LEN = N_SCANS * T_R
frame_times = np.arange(N_SCANS) * T_R
t_hi = np.arange(0, RUN_LEN, DT)
idx = np.round(frame_times / DT).astype(int)

# A onsets are fixed (same as the lab); B onsets = A onsets + lag
ONSETS_A = np.array([12, 40, 74, 96, 135, 162, 190, 224, 255, 288, 310, 331])

# --------------------------------------------------------------------- HRF
def canonical_hrf(t):
    h = stats.gamma.pdf(t, 6, scale=1) - stats.gamma.pdf(t, 16, scale=1) / 6
    return h / h.max()

hrf = canonical_hrf(np.arange(0, 32, DT))

def make_regressor(onsets):
    stim = np.zeros_like(t_hi)
    for onset in onsets:
        stim[(t_hi >= onset) & (t_hi < onset + DURATION)] = 1.0
    return np.convolve(stim, hrf)[: len(t_hi)][idx]

def design_matrix(lag):
    return np.column_stack([make_regressor(ONSETS_A),
                            make_regressor(ONSETS_A + lag),
                            np.ones(N_SCANS)])

# ------------------------------------------------------------- simulation
c = np.array([1.0, -1.0, 0.0])           # A - B contrast
true_contrast = c @ BETA_TRUE
rng = np.random.default_rng(SEED)

rows, per_sim = [], []
for lag in LAGS:
    X = design_matrix(lag)
    n, p = X.shape
    dfe = n - p
    XtX_inv = np.linalg.inv(X.T @ X)
    r_AB = np.corrcoef(X[:, 0], X[:, 1])[0, 1]

    est, ses, ts = [], [], []
    for _ in range(N_SIMS):
        y = X @ BETA_TRUE + SIGMA * rng.standard_normal(n)
        beta_hat = np.linalg.solve(X.T @ X, X.T @ y)
        resid = y - X @ beta_hat
        sigma2_hat = resid @ resid / dfe
        se_c = np.sqrt(sigma2_hat * c @ XtX_inv @ c)
        est.append(c @ beta_hat); ses.append(se_c); ts.append((c @ beta_hat) / se_c)
        per_sim.append({"lag": lag, "contrast": est[-1], "t": ts[-1]})

    rows.append({
        "lag (s)": lag,
        "corr(A,B)": r_AB,
        "mean contrast": np.mean(est),
        "mean SE": np.mean(ses),
        "mean t": np.mean(ts),
    })

summary = pd.DataFrame(rows).set_index("lag (s)")
sims = pd.DataFrame(per_sim)
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)
print(f"True contrast (A - B) = {true_contrast:.2f}; {N_SIMS} simulations per lag\n")
print(summary.round(3))

# ------------------------------------------------------------------- plots
fig, axes = plt.subplots(2, 2, figsize=(11, 8))

ax = axes[0, 0]
ax.plot(summary.index, summary["corr(A,B)"], "o-")
ax.set(xlabel="Lag between A and B onsets (s)", ylabel="Correlation",
       title="Correlation between A and B regressors")

ax = axes[0, 1]
ax.scatter(sims["lag"], sims["contrast"], alpha=0.5, s=18, label="individual sims")
ax.plot(summary.index, summary["mean contrast"], "k-o", lw=1.5, label="mean")
ax.axhline(true_contrast, color="r", ls="--", label=f"true = {true_contrast:.1f}")
ax.set(xlabel="Lag (s)", ylabel="A - B contrast estimate",
       title=f"Contrast estimates ({N_SIMS} sims per lag)")
ax.legend(fontsize=8)

ax = axes[1, 0]
ax.plot(summary.index, summary["mean SE"], "o-", label="mean estimated SE")
ax.set(xlabel="Lag (s)", ylabel="Standard error / SD",
       title="Standard error of the contrast")
ax.legend(fontsize=8)

ax = axes[1, 1]
ax.scatter(sims["lag"], sims["t"], alpha=0.5, s=18, label="individual sims")
ax.plot(summary.index, summary["mean t"], "k-o", lw=1.5, label="mean")
ax.set(xlabel="Lag (s)", ylabel="t-value (A - B)", title="t-values for the contrast")
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig("glm_lag_simulation.png", dpi=150)
print("\nSaved figure: glm_lag_simulation.png")
