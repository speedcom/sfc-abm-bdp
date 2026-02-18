"""
Welfare analysis from Monte Carlo terminal data:
- Two-class Gini coefficient
- Real consumption per capita
- Welfare panel chart
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).parent.parent
MC_DIR = ROOT / "results"
OUT_DIR = ROOT / "figures"

plt.rcParams.update({
    'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10,
    'xtick.labelsize': 9, 'ytick.labelsize': 9, 'legend.fontsize': 8,
    'figure.dpi': 200, 'savefig.dpi': 200, 'savefig.bbox': 'tight',
})

POP = 100_000
MPC = 0.82

def compute_welfare(df, bdp_amount):
    """Compute welfare metrics for each seed."""
    results = []
    for _, row in df.iterrows():
        unemp_rate = row['Unemployment']
        wage = row['MarketWage']
        price = row['PriceLevel']

        n_employed = int((1 - unemp_rate) * POP)
        n_unemployed = POP - n_employed

        y_emp = wage + bdp_amount
        y_unemp = bdp_amount

        # Nominal consumption per capita
        total_income = n_employed * y_emp + n_unemployed * y_unemp
        nominal_consumption = total_income * MPC / POP

        # Real consumption (deflated by price level)
        real_consumption = nominal_consumption / price

        # Two-class Gini
        if total_income > 0 and y_emp != y_unemp:
            gini = (n_employed * n_unemployed * abs(y_emp - y_unemp)) / \
                   (POP * total_income)
        else:
            gini = 0.0

        # Income floor
        income_floor = bdp_amount

        results.append({
            'real_consumption': real_consumption,
            'gini': gini,
            'income_floor': income_floor,
            'nominal_consumption': nominal_consumption,
        })

    return pd.DataFrame(results)


# Load terminal data
term_nobdp = pd.read_csv(MC_DIR / "nobdp_terminal.csv", sep=";", decimal=",")
term_base = pd.read_csv(MC_DIR / "baseline_terminal.csv", sep=";", decimal=",")
term_bdp3k = pd.read_csv(MC_DIR / "bdp3000_terminal.csv", sep=";", decimal=",")

# Compute welfare for each scenario
w_nobdp = compute_welfare(term_nobdp, 0)
w_base = compute_welfare(term_base, 2000)
w_bdp3k = compute_welfare(term_bdp3k, 3000)

# Print summary
print("="*70)
print("WELFARE ANALYSIS (Monte Carlo, N=100)")
print("="*70)

for label, w, adopt_df in [("BDP=0", w_nobdp, term_nobdp),
                              ("BDP=2000", w_base, term_base),
                              ("BDP=3000", w_bdp3k, term_bdp3k)]:
    print(f"\n{label}:")
    for col, name in [("real_consumption", "Real Consumption/cap"),
                       ("gini", "Gini Coefficient"),
                       ("nominal_consumption", "Nominal Consumption/cap"),
                       ("income_floor", "Income Floor")]:
        vals = w[col].values
        print(f"  {name:25s}: {vals.mean():8.1f} ± {vals.std():6.1f}  "
              f"[{np.percentile(vals, 5):8.1f}, {np.percentile(vals, 95):8.1f}]")
    print(f"  {'Adoption (%)':25s}: {adopt_df['TotalAdoption'].mean()*100:8.1f} ± "
          f"{adopt_df['TotalAdoption'].std()*100:6.1f}")

# ═══════════════════════════════════════════════════════════════
# WELFARE CHART: 4-panel
# ═══════════════════════════════════════════════════════════════

fig, axes = plt.subplots(2, 2, figsize=(10, 8))

scenarios = ['BDP = 0', 'BDP = 2 000', 'BDP = 3 000']
colors = ['#2196F3', '#4CAF50', '#F44336']
welfare_dfs = [w_nobdp, w_base, w_bdp3k]

# Panel A: Real consumption per capita
for w, c, lab in zip(welfare_dfs, colors, scenarios):
    axes[0, 0].hist(w['real_consumption'], bins=20, alpha=0.5, color=c,
                     label=lab, edgecolor='white')
axes[0, 0].set_xlabel("Realna konsumpcja per capita (PLN/mies.)")
axes[0, 0].set_ylabel("Liczba seedów")
axes[0, 0].set_title("A. Realna konsumpcja per capita", fontweight='bold')
axes[0, 0].legend()

# Panel B: Gini coefficient
for w, c, lab in zip(welfare_dfs, colors, scenarios):
    axes[0, 1].hist(w['gini'], bins=20, alpha=0.5, color=c,
                     label=lab, edgecolor='white')
axes[0, 1].set_xlabel("Współczynnik Giniego")
axes[0, 1].set_ylabel("Liczba seedów")
axes[0, 1].set_title("B. Nierówność dochodowa (Gini)", fontweight='bold')
axes[0, 1].legend()

# Panel C: Scatter — Gini vs Real Consumption (tradeoff)
adopt_dfs = [term_nobdp, term_base, term_bdp3k]
markers = ['o', 's', '^']
for w, adf, c, m, lab in zip(welfare_dfs, adopt_dfs, colors, markers, scenarios):
    axes[1, 0].scatter(w['gini'], w['real_consumption'],
                       c=c, marker=m, alpha=0.4, s=30, label=lab)
axes[1, 0].set_xlabel("Gini")
axes[1, 0].set_ylabel("Realna konsumpcja per capita (PLN)")
axes[1, 0].set_title("C. Tradeoff: równość vs konsumpcja", fontweight='bold')
axes[1, 0].legend()

# Panel D: Bar chart summary
bar_data = {
    'Realna kons.\n(×1000 PLN)': [w.real_consumption.mean()/1000 for w in welfare_dfs],
    'Gini\n(×10)': [w.gini.mean()*10 for w in welfare_dfs],
    'Adopcja\n(×10%)': [df.TotalAdoption.mean()*10 for df in adopt_dfs],
    'Bezrobocie\n(×10%)': [df.Unemployment.mean()*10 for df in adopt_dfs],
}

x = np.arange(len(scenarios))
w_bar = 0.18
for i, (metric, vals) in enumerate(bar_data.items()):
    axes[1, 1].bar(x + i * w_bar, vals, w_bar, label=metric, alpha=0.8,
                    edgecolor='white')

axes[1, 1].set_xticks(x + 1.5 * w_bar)
axes[1, 1].set_xticklabels(scenarios)
axes[1, 1].set_title("D. Porównanie wielowymiarowe", fontweight='bold')
axes[1, 1].legend(loc='upper right', fontsize=7)

fig.suptitle("Analiza dobrostanu — Monte Carlo (N=100 seedów per scenariusz)",
             fontsize=12, fontweight='bold', y=1.01)
fig.tight_layout()
fig.savefig(OUT_DIR / "v5_mc_welfare.png")
print("\nSaved: v5_mc_welfare.png")
plt.close()

print("\nDone!")
