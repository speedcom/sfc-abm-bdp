"""
Formal bimodality analysis for BDP=2000 Monte Carlo data.
Hartigan's dip test + Gaussian Mixture Model BIC selection.
"""
import numpy as np
import pandas as pd
import diptest
from sklearn.mixture import GaussianMixture
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde, norm
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results"
FIGURES_DIR = Path(__file__).parent.parent / "figures"

plt.rcParams.update({
    'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10,
    'figure.dpi': 200, 'savefig.dpi': 200, 'savefig.bbox': 'tight',
})

# Load data
df = pd.read_csv(RESULTS_DIR / "baseline_terminal.csv", sep=";", decimal=",")
adopt = df['TotalAdoption'].values * 100

print("=" * 60)
print("FORMAL BIMODALITY ANALYSIS — BDP = 2000 PLN (N=100)")
print("=" * 60)

# 1. Hartigan's Dip Test
dip_stat, dip_pval = diptest.diptest(adopt)
print(f"\n1. HARTIGAN'S DIP TEST")
print(f"   Dip statistic: {dip_stat:.4f}")
print(f"   p-value:       {dip_pval:.2e}")
print(f"   Verdict:       {'REJECT unimodality' if dip_pval < 0.05 else 'Cannot reject'}")

# 2. Gaussian Mixture Model — BIC
print(f"\n2. GAUSSIAN MIXTURE MODEL (BIC)")
X = adopt.reshape(-1, 1)
bics = []
for k in range(1, 6):
    gmm = GaussianMixture(n_components=k, random_state=42, n_init=10)
    gmm.fit(X)
    bics.append(gmm.bic(X))
    tag = " <-- BEST" if k == np.argmin(bics) + 1 and k > 1 else ""
    print(f"   K={k}: BIC={bics[-1]:8.1f}{tag}")

best_k = np.argmin(bics) + 1
print(f"\n   Best model: K={best_k}")

# 3. Fit best GMM
gmm_best = GaussianMixture(n_components=best_k, random_state=42, n_init=10)
gmm_best.fit(X)
print(f"\n3. MIXTURE PARAMETERS (K={best_k}):")
for j in range(best_k):
    print(f"   Component {j+1}: mu={gmm_best.means_[j,0]:.1f}%, "
          f"sigma={np.sqrt(gmm_best.covariances_[j,0,0]):.1f}%, "
          f"weight={gmm_best.weights_[j]:.2f}")

# 4. Cross-scenario contrast
print(f"\n4. DIP TEST — ALL SCENARIOS:")
for fname, label in [("nobdp_terminal.csv", "BDP=0"),
                      ("baseline_terminal.csv", "BDP=2000"),
                      ("bdp3000_terminal.csv", "BDP=3000")]:
    d = pd.read_csv(RESULTS_DIR / fname, sep=";", decimal=",")
    vals = d['TotalAdoption'].values * 100
    ds, dp = diptest.diptest(vals)
    sig = '***' if dp < 0.001 else '**' if dp < 0.01 else '*' if dp < 0.05 else 'n.s.'
    print(f"   {label:12s}: dip={ds:.4f}, p={dp:.2e} [{sig}]")

# 5. Visualization
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

x_grid = np.linspace(20, 85, 200)
kde = gaussian_kde(adopt)
axes[0].hist(adopt, bins=20, density=True, alpha=0.4, color='#4CAF50', edgecolor='white')
axes[0].plot(x_grid, kde(x_grid), 'k-', linewidth=2, label='KDE')

gmm2 = GaussianMixture(n_components=2, random_state=42, n_init=10)
gmm2.fit(X)
for j in range(2):
    y = gmm2.weights_[j] * norm.pdf(x_grid, gmm2.means_[j, 0],
                                      np.sqrt(gmm2.covariances_[j, 0, 0]))
    axes[0].plot(x_grid, y, '--', linewidth=1.5,
                 label=f'GMM k={j+1}: \u03bc={gmm2.means_[j,0]:.0f}%')
axes[0].set_xlabel("Technology adoption M120 (%)")
axes[0].set_ylabel("Density")
axes[0].set_title(f"A. KDE + GMM (dip p={dip_pval:.2e})", fontweight='bold')
axes[0].legend(fontsize=7)

axes[1].bar(range(1, 6), bics,
            color=['#F44336' if i + 1 == best_k else '#90CAF9' for i in range(5)],
            edgecolor='white')
axes[1].set_xlabel("Components (K)")
axes[1].set_ylabel("BIC")
axes[1].set_title("B. Model selection (BIC)", fontweight='bold')
axes[1].set_xticks(range(1, 6))

for fname, label, color in [("nobdp_terminal.csv", "BDP=0", '#2196F3'),
                              ("baseline_terminal.csv", "BDP=2000", '#4CAF50'),
                              ("bdp3000_terminal.csv", "BDP=3000", '#F44336')]:
    d = pd.read_csv(RESULTS_DIR / fname, sep=";", decimal=",")
    vals = d['TotalAdoption'].values * 100
    kde_s = gaussian_kde(vals)
    x_s = np.linspace(max(0, vals.min() - 5), min(100, vals.max() + 5), 200)
    axes[2].plot(x_s, kde_s(x_s), color=color, linewidth=2, label=label)
    axes[2].fill_between(x_s, kde_s(x_s), alpha=0.15, color=color)

axes[2].set_xlabel("Technology adoption M120 (%)")
axes[2].set_ylabel("Density")
axes[2].set_title("C. KDE: 3 scenarios", fontweight='bold')
axes[2].legend()

plt.tight_layout()
plt.savefig(FIGURES_DIR / "v5_mc_diptest.png")
print(f"\nSaved: {FIGURES_DIR / 'v5_mc_diptest.png'}")
