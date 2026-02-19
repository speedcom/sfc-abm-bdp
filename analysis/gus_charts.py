"""
GUS-calibrated model charts for essay section 4.8b.
Generates: v6_gus_sector_comparison.png, v6_gus_dual_paradox.png
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

plt.rcParams.update({
    'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10,
    'xtick.labelsize': 9, 'ytick.labelsize': 9, 'legend.fontsize': 8,
    'figure.dpi': 200, 'savefig.dpi': 200, 'savefig.bbox': 'tight',
})

MC_DIR = Path("mc")
OUT_DIR = Path(".")

# Load terminal data
term_nobdp = pd.read_csv(MC_DIR / "gus_nobdp_terminal.csv", sep=";", decimal=",")
term_base  = pd.read_csv(MC_DIR / "gus_baseline_terminal.csv", sep=";", decimal=",")
term_bdp3k = pd.read_csv(MC_DIR / "gus_bdp3k_terminal.csv", sep=";", decimal=",")

scenarios = ['BDP = 0', 'BDP = 2 000', 'BDP = 3 000']
colors = ['#2196F3', '#4CAF50', '#F44336']
dfs = [term_nobdp, term_base, term_bdp3k]

# ═══════════════════════════════════════════════════════════════
# FIGURE 1: 6-sector adoption comparison (grouped bar chart)
# ═══════════════════════════════════════════════════════════════

fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

# Panel A: Per-sector adoption bars
sectors = ['BPO/SSC\n(σ=50, 3%)', 'Przemysł\n(σ=10, 16%)', 'Handel/Usługi\n(σ=5, 45%)',
           'Ochrona zdrowia\n(σ=2, 6%)', 'Budżetówka\n(σ=1, 22%)', 'Rolnictwo\n(σ=3, 8%)']
sec_cols = ['BPO_Auto', 'Manuf_Auto', 'Retail_Auto', 'Health_Auto', 'Public_Auto', 'Agri_Auto']

x = np.arange(len(sectors))
w = 0.25

for i, (df, color, label) in enumerate(zip(dfs, colors, scenarios)):
    means = [df[c].mean() * 100 for c in sec_cols]
    stds = [df[c].std() * 100 for c in sec_cols]
    axes[0].bar(x + i * w, means, w, yerr=stds, label=label, color=color,
                alpha=0.85, capsize=3, edgecolor='white')

axes[0].set_xticks(x + w)
axes[0].set_xticklabels(sectors, rotation=20, ha='right', fontsize=8)
axes[0].set_ylabel("Adopcja technologiczna M120 (%)")
axes[0].set_title("A. Adopcja per sektor — kalibracja GUS 2024", fontweight='bold')
axes[0].legend(loc='upper right')
axes[0].set_ylim(0, 100)

# Panel B: Macro comparison (total adoption, inflation, unemployment)
metrics = ['Adopcja\nogółem (%)', 'Inflacja\n(%)', 'Bezrobocie\n(%)']
metric_cols = ['TotalAdoption', 'Inflation', 'Unemployment']

x2 = np.arange(len(metrics))
for i, (df, color, label) in enumerate(zip(dfs, colors, scenarios)):
    vals = [df[c].mean() * 100 for c in metric_cols]
    stds = [df[c].std() * 100 for c in metric_cols]
    axes[1].bar(x2 + i * w, vals, w, yerr=stds, label=label, color=color,
                alpha=0.85, capsize=3, edgecolor='white')

axes[1].set_xticks(x2 + w)
axes[1].set_xticklabels(metrics)
axes[1].axhline(y=0, color='gray', linewidth=0.5, linestyle=':')
axes[1].set_title("B. Agregaty makroekonomiczne", fontweight='bold')
axes[1].legend(loc='upper right')

fig.suptitle("Model skalibrowany GUS 2024: 6 sektorów × 3 scenariusze BDP (N=100 seedów)",
             fontsize=12, fontweight='bold', y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "v6_gus_sector_comparison.png")
print("Saved: v6_gus_sector_comparison.png")
plt.close()


# ═══════════════════════════════════════════════════════════════
# FIGURE 2: Dual Paradox — BPO acceleration vs Manufacturing deceleration
# ═══════════════════════════════════════════════════════════════

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

bdp_levels = [0, 2000, 3000]
colors_pts = ['#2196F3', '#4CAF50', '#F44336']

# Panel A: BPO — Paradoks Akceleracji (przyspieszenie)
bpo_means = [df['BPO_Auto'].mean()*100 for df in dfs]
bpo_stds = [df['BPO_Auto'].std()*100 for df in dfs]
axes[0].errorbar(bdp_levels, bpo_means, yerr=bpo_stds, fmt='o-', capsize=8,
                 color='#333', markersize=8, linewidth=2)
for x_pt, y_pt, c in zip(bdp_levels, bpo_means, colors_pts):
    axes[0].scatter(x_pt, y_pt, c=c, s=120, zorder=5, edgecolor='white', linewidth=1.5)
axes[0].set_xlabel("BDP (PLN/mies.)")
axes[0].set_ylabel("Adopcja BPO/SSC M120 (%)")
axes[0].set_title("A. BPO: Paradoks Akceleracji ↑", fontweight='bold', color='#4CAF50')
axes[0].set_xticks(bdp_levels)
axes[0].set_ylim(50, 95)
axes[0].annotate('+21pp', xy=(2000, bpo_means[1]), xytext=(2500, bpo_means[1]-8),
                arrowprops=dict(arrowstyle='->', color='green'), color='green', fontweight='bold')

# Panel B: Manufacturing — Odwrócony Paradoks (hamowanie)
mfg_means = [df['Manuf_Auto'].mean()*100 for df in dfs]
mfg_stds = [df['Manuf_Auto'].std()*100 for df in dfs]
axes[1].errorbar(bdp_levels, mfg_means, yerr=mfg_stds, fmt='o-', capsize=8,
                 color='#333', markersize=8, linewidth=2)
for x_pt, y_pt, c in zip(bdp_levels, mfg_means, colors_pts):
    axes[1].scatter(x_pt, y_pt, c=c, s=120, zorder=5, edgecolor='white', linewidth=1.5)
axes[1].set_xlabel("BDP (PLN/mies.)")
axes[1].set_ylabel("Adopcja Manufacturing M120 (%)")
axes[1].set_title("B. Przemysł: Odwrócony Paradoks ↓", fontweight='bold', color='#F44336')
axes[1].set_xticks(bdp_levels)
axes[1].set_ylim(15, 55)
axes[1].annotate('−14pp', xy=(2000, mfg_means[1]), xytext=(2500, mfg_means[1]+5),
                arrowprops=dict(arrowstyle='->', color='red'), color='red', fontweight='bold')

# Panel C: Inflacja — główny kanał makro
inf_means = [df['Inflation'].mean()*100 for df in dfs]
inf_stds = [df['Inflation'].std()*100 for df in dfs]
axes[2].errorbar(bdp_levels, inf_means, yerr=inf_stds, fmt='o-', capsize=8,
                 color='#333', markersize=8, linewidth=2)
for x_pt, y_pt, c in zip(bdp_levels, inf_means, colors_pts):
    axes[2].scatter(x_pt, y_pt, c=c, s=120, zorder=5, edgecolor='white', linewidth=1.5)
axes[2].axhline(y=0, color='gray', linewidth=0.5, linestyle=':')
axes[2].set_xlabel("BDP (PLN/mies.)")
axes[2].set_ylabel("Inflacja M120 (%)")
axes[2].set_title("C. Inflacja: główny efekt makro", fontweight='bold')
axes[2].set_xticks(bdp_levels)

fig.suptitle("Podwójny Paradoks: BDP przyspiesza BPO, hamuje Przemysł (kalibracja GUS 2024)",
             fontsize=12, fontweight='bold', y=1.03)
fig.tight_layout()
fig.savefig(OUT_DIR / "v6_gus_dual_paradox.png")
print("Saved: v6_gus_dual_paradox.png")
plt.close()


# ═══════════════════════════════════════════════════════════════
# Print summary for essay
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("GUS-CALIBRATED MODEL SUMMARY (N=100)")
print("="*70)

for label, df in [("BDP=0", term_nobdp), ("BDP=2000", term_base), ("BDP=3000", term_bdp3k)]:
    print(f"\n{label}:")
    for col, name, m in [("TotalAdoption", "Adoption", 100),
                          ("Inflation", "Inflation", 100),
                          ("Unemployment", "Unemployment", 100),
                          ("ExRate", "Exchange Rate", 1),
                          ("MarketWage", "Market Wage", 1)]:
        vals = df[col].values * m
        print(f"  {name:20s}: {vals.mean():8.2f} ± {vals.std():6.2f}")
    for scol, sname in [("BPO_Auto", "BPO/SSC"),
                          ("Manuf_Auto", "Manufacturing"),
                          ("Retail_Auto", "Retail/Services"),
                          ("Health_Auto", "Healthcare"),
                          ("Public_Auto", "Public"),
                          ("Agri_Auto", "Agriculture")]:
        vals = df[scol].values * 100
        print(f"  {sname:20s}: {vals.mean():8.2f} ± {vals.std():6.2f}%")

print("\nDone!")
