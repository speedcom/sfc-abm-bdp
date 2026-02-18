# SFC-ABM Model of Universal Basic Income and Technological Transformation

A Stock-Flow Consistent Agent-Based Model (SFC-ABM) investigating how Universal Basic Income (UBI) acts as a catalyst for technological transformation in a small open economy. The model discovers a **phase transition** at the optimal UBI level, where the economy bifurcates between high-adoption and low-adoption attractors.

## Key Findings

| Scenario | Adoption | Inflation | Unemployment | Gini | Real Consumption |
|---|---|---|---|---|---|
| UBI = 0 | 12.9% ± 4.3% | -22.6% | 78.7% | 0.80 | 2,311 PLN |
| **UBI = 2,000** | **61.9% ± 16.4%** | -13.4% | 39.6% | **0.20** | **5,950 PLN** |
| UBI = 3,000 | 32.8% ± 2.1% | +19.4% | 19.4% | 0.10 | 1,570 PLN |

**Bimodality at UBI = 2,000 PLN**: Hartigan's dip test rejects unimodality with p = 1.7 × 10⁻⁵. 70% of Monte Carlo realizations converge to high adoption (μ = 73.2%), while 30% settle at moderate adoption (μ = 34.2%). This is a signature of a **critical point** (phase transition) — the mean outcome (62%) does not correspond to any typical realization.

![Bifurcation Diagram](figures/v5_mc_bifurcation.png)

## Model Architecture

- **10,000 heterogeneous firm-agents** across 4 sectors with different CES elasticities of substitution (σ):
  - BPO/SSC (σ=50), Manufacturing (σ=10), Retail/Services (σ=5), Healthcare (σ=2)
- **Watts-Strogatz small-world network** (k=6, rewiring p=0.10) with demonstration effects
- **6 macro sectors**: firms, households, government (MMT fiscal), banking (Basel III), central bank (Taylor rule), foreign sector (IRP exchange rate)
- **Stock-flow consistency**: all flows have counterpart stocks, government spending creates private assets
- **Soft deflation floor**: 30% pass-through beyond -1.5%/month, modeling downward price stickiness (Bewley 1999)

## Reproduction

### Requirements

- [Ammonite](https://ammonite.io/) 3.0.2+ (Scala 3)
- Python 3.10+ with: `numpy`, `pandas`, `matplotlib`, `scikit-learn`, `diptest`, `scipy`

### Run Monte Carlo (3 scenarios × 100 seeds)

```bash
BDP=0    SEEDS=100 PREFIX=nobdp    amm simulation_mc.sc
BDP=2000 SEEDS=100 PREFIX=baseline amm simulation_mc.sc
BDP=3000 SEEDS=100 PREFIX=bdp3000  amm simulation_mc.sc
```

Output: `mc/{prefix}_terminal.csv` (per-seed terminal values) and `mc/{prefix}_timeseries.csv` (monthly aggregates with mean/p05/p95).

### Run BDP parameter sweep (bifurcation diagram)

```bash
bash run_sweep.sh  # 21 points × 30 seeds = 630 simulations, ~10 min
```

### Generate figures

```bash
python analysis/mc_charts.py          # 6-panel time series, bimodal histogram, sectors, nonlinear
python analysis/mc_welfare.py         # Welfare analysis (Gini, real consumption)
python analysis/diptest_analysis.py   # Hartigan's dip test + GMM BIC
python analysis/sweep_analysis.py     # Bifurcation diagram
```

## Figures

| Figure | Description |
|---|---|
| `v5_mc_panel6.png` | 6-panel time series with 90% CI bands (inflation, unemployment, adoption, FX, wages, debt) |
| `v5_mc_bimodal.png` | Bimodal adoption distribution, per-sector bars, phase space scatter |
| `v5_mc_bifurcation.png` | Bifurcation diagram: continuous BDP sweep 0–5,000 PLN (630 simulations) |
| `v5_mc_diptest.png` | Formal bimodality test: KDE + GMM fit, BIC model selection, cross-scenario comparison |
| `v5_mc_welfare.png` | Welfare analysis: real consumption, Gini, equality-consumption tradeoff |
| `v5_mc_nonlinear.png` | Non-monotonic (inverted-U) response of adoption and inflation to UBI level |
| `v5_mc_sectors.png` | Per-sector adoption time series (BPO fastest, Healthcare slowest) |

## Theoretical Framework

The model integrates three heterodox economics traditions:

1. **Modern Monetary Theory (MMT)**: Government as currency issuer faces no nominal budget constraint; UBI is financed via sovereign money creation (Kelton 2020, Mosler 1997)
2. **Non-ergodic economics**: Firms maximize survival probability, not expected profit; ruin barriers force irreversible automation decisions (Peters 2019)
3. **CES production functions**: Heterogeneous elasticity of substitution across sectors determines automation speed and labor displacement patterns (Acemoglu & Restrepo 2018)

The central thesis — the **Acceleration Paradox** — states that UBI, conventionally viewed as a response to technological unemployment, actually *causes* accelerated automation through cost-pressure and interest-rate channels.

## Citation

If you use this model or its results, please cite:

```
Maciaszek, M. (2026). Paradoks Akceleracji: Bezwarunkowy Dochód Podstawowy jako
katalizator transformacji technologicznej w ujęciu MMT, ekonomii nieergodycznej
i funkcji produkcji CES. MBA thesis, Mateusz Maciaszek.
```

## License

MIT License. See [LICENSE](LICENSE).
