#!/bin/bash
# BDP parameter sweep: 0 to 5000 PLN, step 250, 30 seeds each
# Total: 21 points × 30 seeds = 630 simulations (~10 minutes)
set -e

echo "Starting BDP sweep (21 × 30 = 630 simulations)..."
for bdp in 0 250 500 750 1000 1250 1500 1750 2000 2250 2500 2750 3000 3250 3500 3750 4000 4250 4500 4750 5000; do
    echo "BDP=$bdp (30 seeds)..."
    BDP=$bdp SEEDS=30 PREFIX="sweep_${bdp}" amm simulation_mc.sc 2>&1 | grep "Total Adoption"
done
echo "Sweep complete! Results in mc/sweep_*_terminal.csv"
