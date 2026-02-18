"""
Analyze BDP sweep results and generate bifurcation diagram.
Reads sweep_XXX_terminal.csv files from mc/ directory.
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

ROOT = Path(__file__).parent.parent
MC_DIR = ROOT / "results" / "sweep"
OUT_DIR = ROOT / "figures"

bdp_levels = list(range(0, 5001, 250))
results = []

print("Loading sweep data...")
for bdp in bdp_levels:
    fpath = MC_DIR / f"sweep_{bdp}_terminal.csv"
    if not fpath.exists():
        print(f"  MISSING: sweep_{bdp}_terminal.csv")
        continue
    df = pd.read_csv(fpath, sep=";", decimal=",")
    for _, row in df.iterrows():
        results.append({
            'BDP': bdp,
            'Adoption': row['TotalAdoption'] * 100,
            'Inflation': row['Inflation'] * 100,
            'Unemployment': row['Unemployment'] * 100,
            'ExRate': row['ExRate'],
        })
    print(f"  BDP={bdp:5d}: {len(df)} seeds, "
          f"Adopt={df.TotalAdoption.mean()*100:.1f}±{df.TotalAdoption.std()*100:.1f}%")

data = pd.DataFrame(results)
print(f"\nTotal datapoints: {len(data)}")

# ═══════════════════════════════════════════════════════════════
# FIGURE: 4-panel bifurcation diagram
# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(12, 9))

# Color by BDP level for scatter
cmap = plt.cm.RdYlGn_r

# Panel A: Bifurcation diagram — Adoption vs BDP
ax = axes[0, 0]
ax.scatter(data['BDP'], data['Adoption'], c=data['BDP'], cmap=cmap,
           alpha=0.3, s=15, edgecolor='none')
# Add mean line
means = data.groupby('BDP')['Adoption'].agg(['mean', 'std'])
ax.plot(means.index, means['mean'], 'k-', linewidth=2, zorder=5)
ax.fill_between(means.index, means['mean']-means['std'], means['mean']+means['std'],
                alpha=0.2, color='gray')
ax.set_xlabel("BDP (PLN/mies.)")
ax.set_ylabel("Adopcja technologiczna M120 (%)")
ax.set_title("A. Diagram bifurkacyjny: adopcja", fontweight='bold')
ax.axvline(x=2000, color='green', linestyle='--', alpha=0.5, linewidth=1)
ax.set_xlim(-100, 5100)

# Panel B: Inflation vs BDP
ax = axes[0, 1]
ax.scatter(data['BDP'], data['Inflation'], c=data['BDP'], cmap=cmap,
           alpha=0.3, s=15, edgecolor='none')
means_inf = data.groupby('BDP')['Inflation'].agg(['mean', 'std'])
ax.plot(means_inf.index, means_inf['mean'], 'k-', linewidth=2, zorder=5)
ax.fill_between(means_inf.index, means_inf['mean']-means_inf['std'],
                means_inf['mean']+means_inf['std'], alpha=0.2, color='gray')
ax.axhline(y=0, color='gray', linewidth=0.5, linestyle=':')
ax.set_xlabel("BDP (PLN/mies.)")
ax.set_ylabel("Inflacja M120 (%)")
ax.set_title("B. Diagram bifurkacyjny: inflacja", fontweight='bold')
ax.axvline(x=2000, color='green', linestyle='--', alpha=0.5, linewidth=1)

# Panel C: Variance (σ) of adoption vs BDP — shows critical point
ax = axes[1, 0]
stds = data.groupby('BDP')['Adoption'].std()
ax.bar(stds.index, stds.values, width=200, color='#FF5722', alpha=0.7, edgecolor='white')
ax.set_xlabel("BDP (PLN/mies.)")
ax.set_ylabel("σ adopcji (%)")
ax.set_title("C. Wariancja adopcji — sygnatura punktu krytycznego", fontweight='bold')
ax.axvline(x=2000, color='green', linestyle='--', alpha=0.5, linewidth=1)

# Panel D: Unemployment vs BDP
ax = axes[1, 1]
ax.scatter(data['BDP'], data['Unemployment'], c=data['BDP'], cmap=cmap,
           alpha=0.3, s=15, edgecolor='none')
means_u = data.groupby('BDP')['Unemployment'].agg(['mean', 'std'])
ax.plot(means_u.index, means_u['mean'], 'k-', linewidth=2, zorder=5)
ax.fill_between(means_u.index, means_u['mean']-means_u['std'],
                means_u['mean']+means_u['std'], alpha=0.2, color='gray')
ax.set_xlabel("BDP (PLN/mies.)")
ax.set_ylabel("Bezrobocie M120 (%)")
ax.set_title("D. Bezrobocie vs. BDP", fontweight='bold')
ax.axvline(x=2000, color='green', linestyle='--', alpha=0.5, linewidth=1)

fig.suptitle("Diagram bifurkacyjny: BDP sweep 0–5 000 PLN (30 seedów × 21 punktów)",
             fontsize=12, fontweight='bold', y=1.01)
fig.tight_layout()
fig.savefig(OUT_DIR / "v5_mc_bifurcation.png")
print("\nSaved: v5_mc_bifurcation.png")

# ═══════════════════════════════════════════════════════════════
# Summary table
# ═══════════════════════════════════════════════════════════════
print("\n" + "="*80)
print("BDP SWEEP SUMMARY")
print("="*80)
print(f"{'BDP':>6s} | {'Adopt μ':>8s} {'±σ':>6s} | {'Infl μ':>8s} {'±σ':>6s} | "
      f"{'Unemp μ':>8s} {'±σ':>6s} | {'σ_adopt':>8s}")
print("-"*80)
for bdp in bdp_levels:
    sub = data[data['BDP'] == bdp]
    if len(sub) == 0:
        continue
    print(f"{bdp:6d} | {sub.Adoption.mean():8.1f} {sub.Adoption.std():6.1f} | "
          f"{sub.Inflation.mean():8.1f} {sub.Inflation.std():6.1f} | "
          f"{sub.Unemployment.mean():8.1f} {sub.Unemployment.std():6.1f} | "
          f"{sub.Adoption.std():8.1f}")

# Identify critical region (max variance)
max_var_bdp = stds.idxmax()
print(f"\nCritical point (max σ): BDP = {max_var_bdp} PLN")
print(f"  σ_adoption at critical point: {stds[max_var_bdp]:.1f}%")

print("\nDone!")
