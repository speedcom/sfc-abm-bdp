"""
Monte Carlo Chart Generation for SFC-ABM v5 Paper
Generates publication-quality figures for the essay.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

plt.rcParams.update({
    'font.size': 10,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 8,
    'figure.dpi': 200,
    'savefig.dpi': 200,
    'savefig.bbox': 'tight',
})

ROOT = Path(__file__).parent.parent
MC_DIR = ROOT / "results"
OUT_DIR = ROOT / "figures"

def load_timeseries(prefix):
    """Load aggregated timeseries CSV (semicolon-separated, comma decimal)."""
    df = pd.read_csv(MC_DIR / f"{prefix}_timeseries.csv", sep=";", decimal=",")
    return df

def load_terminal(prefix):
    """Load per-seed terminal values CSV."""
    df = pd.read_csv(MC_DIR / f"{prefix}_terminal.csv", sep=";", decimal=",")
    return df

# Load all data
ts_base = load_timeseries("baseline")
ts_nobdp = load_timeseries("nobdp")
ts_bdp3k = load_timeseries("bdp3000")

term_base = load_terminal("baseline")
term_nobdp = load_terminal("nobdp")
term_bdp3k = load_terminal("bdp3000")


# ═══════════════════════════════════════════════════════════════
# FIGURE 1: 6-panel time series with confidence bands
# ═══════════════════════════════════════════════════════════════

def plot_ts_panel(ax, months, datasets, col_base, title, ylabel, mult=1.0,
                  hline=None, shade_shock=True):
    """Plot time series with mean + 90% CI bands for 3 scenarios."""
    colors = ['#2196F3', '#4CAF50', '#F44336']
    labels = ['BDP = 0 PLN', 'BDP = 2 000 PLN', 'BDP = 3 000 PLN']

    for i, (ts, color, label) in enumerate(zip(datasets, colors, labels)):
        mean = ts[f"{col_base}_mean"].values * mult
        p05 = ts[f"{col_base}_p05"].values * mult
        p95 = ts[f"{col_base}_p95"].values * mult
        ax.plot(months, mean, color=color, linewidth=1.5, label=label)
        ax.fill_between(months, p05, p95, color=color, alpha=0.15)

    if shade_shock:
        ax.axvline(x=30, color='gray', linestyle='--', linewidth=0.8, alpha=0.5)
    if hline is not None:
        ax.axhline(y=hline, color='gray', linestyle=':', linewidth=0.6, alpha=0.5)

    ax.set_title(title, fontweight='bold')
    ax.set_ylabel(ylabel)
    ax.set_xlim(1, 120)

fig, axes = plt.subplots(2, 3, figsize=(14, 8))
months = ts_base["Month"].values

plot_ts_panel(axes[0, 0], months, [ts_nobdp, ts_base, ts_bdp3k],
              "Inflation", "Inflacja (roczna)", "%", mult=100, hline=0)

plot_ts_panel(axes[0, 1], months, [ts_nobdp, ts_base, ts_bdp3k],
              "Unemployment", "Bezrobocie", "%", mult=100)

plot_ts_panel(axes[0, 2], months, [ts_nobdp, ts_base, ts_bdp3k],
              "TotalAdoption", "Adopcja technologiczna", "%", mult=100)

plot_ts_panel(axes[1, 0], months, [ts_nobdp, ts_base, ts_bdp3k],
              "ExRate", "Kurs PLN/EUR", "PLN/EUR")

plot_ts_panel(axes[1, 1], months, [ts_nobdp, ts_base, ts_bdp3k],
              "MarketWage", "Płaca rynkowa", "PLN/mies.")

plot_ts_panel(axes[1, 2], months, [ts_nobdp, ts_base, ts_bdp3k],
              "GovDebt", "Dług publiczny", "mld PLN", mult=1e-9)

axes[0, 0].legend(loc='lower left', framealpha=0.9)
for ax in axes[1, :]:
    ax.set_xlabel("Miesiąc")

fig.suptitle("Monte Carlo SFC-ABM: 100 seedów × 3 scenariusze (pasma = 90% CI)",
             fontsize=13, fontweight='bold', y=1.01)
fig.tight_layout()
fig.savefig(OUT_DIR / "v5_mc_panel6.png")
print("Saved: v5_mc_panel6.png")
plt.close()


# ═══════════════════════════════════════════════════════════════
# FIGURE 2: Bimodal histogram + sector bars
# ═══════════════════════════════════════════════════════════════

fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))

# Panel A: Adoption histogram (all 3 scenarios)
for df, color, label in [(term_nobdp, '#2196F3', 'BDP=0'),
                          (term_base, '#4CAF50', 'BDP=2000'),
                          (term_bdp3k, '#F44336', 'BDP=3000')]:
    vals = df['TotalAdoption'].values * 100
    axes[0].hist(vals, bins=20, alpha=0.5, color=color, label=label, edgecolor='white')

axes[0].set_xlabel("Adopcja technologiczna M120 (%)")
axes[0].set_ylabel("Liczba seedów (N=100)")
axes[0].set_title("A. Rozkład adopcji — bimodalność BDP=2000", fontweight='bold')
axes[0].legend()
axes[0].axvline(x=term_base['TotalAdoption'].mean()*100, color='#4CAF50',
                linestyle='--', linewidth=1.5, alpha=0.7)

# Panel B: Per-sector adoption bars
sectors = ['BPO/SSC', 'Manufacturing', 'Retail/Services', 'Healthcare']
sec_cols = ['BPO_Auto', 'Manuf_Auto', 'Retail_Auto', 'Health_Auto']

x = np.arange(len(sectors))
w = 0.25

for i, (df, color, label) in enumerate([(term_nobdp, '#2196F3', 'BDP=0'),
                                          (term_base, '#4CAF50', 'BDP=2000'),
                                          (term_bdp3k, '#F44336', 'BDP=3000')]):
    means = [df[c].mean() * 100 for c in sec_cols]
    stds = [df[c].std() * 100 for c in sec_cols]
    axes[1].bar(x + i * w, means, w, yerr=stds, label=label, color=color,
                alpha=0.8, capsize=3, edgecolor='white')

axes[1].set_xticks(x + w)
axes[1].set_xticklabels(sectors, rotation=15, ha='right')
axes[1].set_ylabel("Adopcja (%)")
axes[1].set_title("B. Adopcja per sektor", fontweight='bold')
axes[1].legend()

# Panel C: Inflation vs Adoption scatter
for df, color, marker, label in [(term_nobdp, '#2196F3', 'o', 'BDP=0'),
                                   (term_base, '#4CAF50', 's', 'BDP=2000'),
                                   (term_bdp3k, '#F44336', '^', 'BDP=3000')]:
    axes[2].scatter(df['TotalAdoption'].values * 100,
                    df['Inflation'].values * 100,
                    c=color, marker=marker, alpha=0.4, s=30, label=label)

axes[2].set_xlabel("Adopcja technologiczna (%)")
axes[2].set_ylabel("Inflacja (%)")
axes[2].set_title("C. Przestrzeń fazowa: adopcja × inflacja", fontweight='bold')
axes[2].axhline(y=0, color='gray', linewidth=0.5, linestyle=':')
axes[2].legend()

fig.tight_layout()
fig.savefig(OUT_DIR / "v5_mc_bimodal.png")
print("Saved: v5_mc_bimodal.png")
plt.close()


# ═══════════════════════════════════════════════════════════════
# FIGURE 3: Sector adoption time series (BDP=2000 only)
# ═══════════════════════════════════════════════════════════════

fig, ax = plt.subplots(figsize=(8, 5))
sec_map = {
    'BPO_Auto': ('BPO/SSC (σ=50)', '#E91E63'),
    'Manuf_Auto': ('Manufacturing (σ=10)', '#FF9800'),
    'Retail_Auto': ('Retail/Services (σ=5)', '#00BCD4'),
    'Health_Auto': ('Healthcare (σ=2)', '#795548'),
}

for col, (label, color) in sec_map.items():
    mean = ts_base[f"{col}_mean"].values * 100
    p05 = ts_base[f"{col}_p05"].values * 100
    p95 = ts_base[f"{col}_p95"].values * 100
    ax.plot(months, mean, color=color, linewidth=2, label=label)
    ax.fill_between(months, p05, p95, color=color, alpha=0.15)

ax.axvline(x=30, color='gray', linestyle='--', linewidth=0.8, alpha=0.5, label='BDP shock (M30)')
ax.set_xlabel("Miesiąc")
ax.set_ylabel("Adopcja technologiczna (%)")
ax.set_title("Adopcja per sektor — BDP=2000 PLN (pasma = 90% CI, N=100)",
             fontweight='bold')
ax.legend(loc='upper left')
ax.set_xlim(1, 120)
ax.set_ylim(0, 100)
fig.tight_layout()
fig.savefig(OUT_DIR / "v5_mc_sectors.png")
print("Saved: v5_mc_sectors.png")
plt.close()


# ═══════════════════════════════════════════════════════════════
# FIGURE 4: Non-monotonic BDP response curve
# ═══════════════════════════════════════════════════════════════

fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

bdp_levels = [0, 2000, 3000]
colors_pts = ['#2196F3', '#4CAF50', '#F44336']

# Panel A: Adoption vs BDP
means = [term_nobdp['TotalAdoption'].mean()*100,
         term_base['TotalAdoption'].mean()*100,
         term_bdp3k['TotalAdoption'].mean()*100]
stds = [term_nobdp['TotalAdoption'].std()*100,
        term_base['TotalAdoption'].std()*100,
        term_bdp3k['TotalAdoption'].std()*100]

axes[0].errorbar(bdp_levels, means, yerr=stds, fmt='o-', capsize=8,
                 color='#333', markersize=8, linewidth=2)
for i, (x, y, c) in enumerate(zip(bdp_levels, means, colors_pts)):
    axes[0].scatter(x, y, c=c, s=120, zorder=5, edgecolor='white', linewidth=1.5)

axes[0].set_xlabel("BDP (PLN/mies.)")
axes[0].set_ylabel("Adopcja technologiczna M120 (%)")
axes[0].set_title("A. Paradoks Akceleracji", fontweight='bold')
axes[0].set_xticks(bdp_levels)

# Panel B: Inflation vs BDP
means_inf = [term_nobdp['Inflation'].mean()*100,
             term_base['Inflation'].mean()*100,
             term_bdp3k['Inflation'].mean()*100]
stds_inf = [term_nobdp['Inflation'].std()*100,
            term_base['Inflation'].std()*100,
            term_bdp3k['Inflation'].std()*100]

axes[1].errorbar(bdp_levels, means_inf, yerr=stds_inf, fmt='o-', capsize=8,
                 color='#333', markersize=8, linewidth=2)
for i, (x, y, c) in enumerate(zip(bdp_levels, means_inf, colors_pts)):
    axes[1].scatter(x, y, c=c, s=120, zorder=5, edgecolor='white', linewidth=1.5)

axes[1].axhline(y=0, color='gray', linewidth=0.5, linestyle=':')
axes[1].set_xlabel("BDP (PLN/mies.)")
axes[1].set_ylabel("Inflacja M120 (%)")
axes[1].set_title("B. Inflacja vs. BDP", fontweight='bold')
axes[1].set_xticks(bdp_levels)

fig.suptitle("Odpowiedź nieliniowa: BDP ↔ transformacja technologiczna",
             fontsize=12, fontweight='bold', y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "v5_mc_nonlinear.png")
print("Saved: v5_mc_nonlinear.png")
plt.close()


# ═══════════════════════════════════════════════════════════════
# Print summary statistics for essay
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("SUMMARY STATISTICS FOR ESSAY")
print("="*70)

for prefix, df, label in [("nobdp", term_nobdp, "BDP=0"),
                            ("baseline", term_base, "BDP=2000"),
                            ("bdp3000", term_bdp3k, "BDP=3000")]:
    print(f"\n{label} (N=100 seeds):")
    for col, name, m in [("TotalAdoption", "Adoption", 100),
                          ("Inflation", "Inflation", 100),
                          ("Unemployment", "Unemployment", 100),
                          ("ExRate", "Exchange Rate", 1),
                          ("MarketWage", "Market Wage", 1),
                          ("GovDebt", "Gov Debt (mld)", 1e-9),
                          ("NPL", "NPL Ratio", 100)]:
        vals = df[col].values * m
        print(f"  {name:20s}: {vals.mean():8.2f} ± {vals.std():6.2f}  "
              f"[{np.percentile(vals, 5):8.2f}, {np.percentile(vals, 95):8.2f}]")

    for scol, sname in [("BPO_Auto", "BPO/SSC"),
                          ("Manuf_Auto", "Manufacturing"),
                          ("Retail_Auto", "Retail/Services"),
                          ("Health_Auto", "Healthcare")]:
        vals = df[scol].values * 100
        print(f"  {sname:20s}: {vals.mean():8.2f} ± {vals.std():6.2f}")

# Bimodality analysis for BDP=2000
print("\n\nBIMODALITY ANALYSIS (BDP=2000):")
adopt = term_base['TotalAdoption'].values * 100
threshold = 55  # midpoint between attractors
high = adopt[adopt > threshold]
low = adopt[adopt <= threshold]
print(f"  Seeds in HIGH attractor (>{threshold}%): {len(high)} ({len(high)/len(adopt)*100:.0f}%)")
print(f"    Mean: {high.mean():.1f}% ± {high.std():.1f}%")
print(f"  Seeds in LOW attractor (≤{threshold}%): {len(low)} ({len(low)/len(adopt)*100:.0f}%)")
print(f"    Mean: {low.mean():.1f}% ± {low.std():.1f}%")

print("\nDone!")
