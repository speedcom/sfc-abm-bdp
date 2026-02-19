/*
 * ╔══════════════════════════════════════════════════════════════════╗
 * ║  SFC-ABM v5: MONTE CARLO + NETWORK + MULTI-SECTOR              ║
 * ║  Stock-Flow Consistent Agent-Based Model                       ║
 * ║  Complexity Economics × MMT × Non-Ergodicity                   ║
 * ╚══════════════════════════════════════════════════════════════════╝
 *
 * Rozszerzenia vs v4:
 *   - Monte Carlo: N seedów, deterministyczny RNG
 *   - Network effects: Watts-Strogatz small-world, demonstration effect
 *   - Multi-sector: 4 sektory z heterogenicznym σ
 *   - Per-firm income output for full Gini computation
 *
 * Uruchomienie:
 *   amm simulation_mc.sc <bdpAmount> <nSeeds> <outputPrefix>
 *   amm simulation_mc.sc 2000 100 baseline
 *   amm simulation_mc.sc 0    100 nobdp
 *   amm simulation_mc.sc 3000 100 bdp3000
 */

import java.io.{File, PrintWriter}
import java.util.Locale
import scala.util.Random

// ═══════════════════════════════════════════════════════════════════
// 0. CLI ARGUMENTS
// ═══════════════════════════════════════════════════════════════════

// Configuration via environment variables:
//   BDP=2000 SEEDS=100 PREFIX=baseline amm simulation_mc.sc
val BDP_AMOUNT    = sys.env.getOrElse("BDP", "2000").toDouble
val N_SEEDS       = sys.env.getOrElse("SEEDS", "3").toInt
val OUTPUT_PREFIX = sys.env.getOrElse("PREFIX", "test")
val IS_NO_BDP     = BDP_AMOUNT == 0.0

// ═══════════════════════════════════════════════════════════════════
// 1. KONFIGURACJA
// ═══════════════════════════════════════════════════════════════════

object Config {
  val FirmsCount       = 10000
  val WorkersPerFirm   = 10
  val TotalPopulation  = FirmsCount * WorkersPerFirm
  val Duration         = 120
  val ShockMonth       = 30

  // Firma (base — sektory modyfikują te wartości)
  val BaseRevenue      = 100000.0   // Skalowane do GUS 2024 wage level
  val OtherCosts       = 16667.0
  val AiCapex          = 1200000.0
  val HybridCapex      = 350000.0
  val AiOpex           = 30000.0
  val HybridOpex       = 12000.0
  val AutoSkeletonCrew = 2
  val HybridReadinessMin = 0.20
  val FullAiReadinessMin = 0.35

  // Gospodarstwa domowe (GUS 2024)
  val BaseWage              = 8266.0    // GUS średnia brutto 2024
  val BaseReservationWage   = 4666.0    // Płaca minimalna 2025
  val BdpAmount             = BDP_AMOUNT
  val ReservationBdpMult    = 0.5
  val Mpc                   = 0.82
  val LaborSupplySteepness  = 8.0
  val WageAdjSpeed          = 0.12

  // Rząd
  val CitRate          = 0.19
  val VatRate          = 0.23
  val GovBaseSpending  = 100000000.0

  // NBP (dane NBP 2024)
  val InitialRate      = 0.0575      // NBP stopa ref. 2024
  val TargetInflation  = 0.025       // Cel NBP 2.5% +/- 1pp
  val TaylorAlpha      = 1.5
  val TaylorBeta       = 0.8
  val TaylorInertia    = 0.70
  val RateFloor        = 0.005
  val RateCeiling      = 0.25

  // System bankowy
  val InitBankCapital  = 500000000.0
  val BaseSpread       = 0.015       // NBP MIR spread korporacyjny 2024
  val NplSpreadFactor  = 5.0
  val MinCar           = 0.08
  val LoanRecovery     = 0.30

  // Sektor zagraniczny (NBP/ECB 2024)
  val BaseExRate       = 4.33        // NBP średni kurs PLN/EUR 2024
  val ForeignRate      = 0.04        // ECB stopa 2024
  val ImportPropensity = 0.40
  val ExportBase       = 190000000.0
  val TechImportShare  = 0.40
  val IrpSensitivity   = 0.15
  val ExRateAdjSpeed   = 0.02
  val ExportAutoBoost  = 0.15

  // Popyt
  val DemandPassthrough = 0.40

  // Network
  val NetworkK          = 6      // Watts-Strogatz: neighbors
  val NetworkRewireP    = 0.10   // Watts-Strogatz: rewire probability
  val DemoEffectThresh  = 0.40   // If >40% neighbors automated → demonstration effect
  val DemoEffectBoost   = 0.15   // Modest boost to uncertainty discount from demonstration
}

// ═══════════════════════════════════════════════════════════════════
// 1b. SEKTORY (MULTI-SECTOR)
// ═══════════════════════════════════════════════════════════════════

/**
 * 4 sektory z heterogenicznym σ (elastyczność substytucji).
 * σ wpływa na: próg decyzyjny, efektywność automatyzacji, koszty CAPEX.
 */
case class SectorDef(
  name: String,
  share: Double,        // Udział w populacji firm (GUS BAEL 2024)
  sigma: Double,        // Elastyczność substytucji CES
  wageMultiplier: Double,        // Mnożnik płacy sektorowej vs średnia krajowa
  revenueMultiplier: Double,
  aiCapexMultiplier: Double,
  hybridCapexMultiplier: Double,
  baseDigitalReadiness: Double,  // Centralna tendencja digitalReadiness
  hybridRetainFrac: Double       // Fraction of workers RETAINED in hybrid mode (0.5 = halve)
)

// Kalibracja GUS/NBP 2024: 6 sektorów polskiej gospodarki
val SECTORS = Vector(
  //                             share   σ    wage  rev   aiCpx hybCpx digiR  hybRet
  SectorDef("BPO/SSC",          0.03, 50.0, 1.35, 1.50, 0.70, 0.70,  0.50,  0.50),  // ~489k pracowników (ABSL), avg 11 154 PLN
  SectorDef("Manufacturing",    0.16, 10.0, 0.94, 1.05, 1.12, 1.05,  0.45,  0.60),  // ~2.8M pracowników, avg ~7 800 PLN
  SectorDef("Retail/Services",  0.45,  5.0, 0.79, 0.91, 0.85, 0.80,  0.40,  0.65),  // ~61% zatrudnienia (usługi), avg ~6 500 PLN
  SectorDef("Healthcare",       0.06,  2.0, 0.97, 1.10, 1.38, 1.25,  0.25,  0.75),  // ~5.5%, pielęgniarki 6 890, lekarze 16 300
  SectorDef("Public",           0.22,  1.0, 0.91, 1.08, 3.00, 2.50,  0.08,  0.90),  // ~22% zatrudnienia (budżetówka), avg ~7 500 PLN
  SectorDef("Agriculture",      0.08,  3.0, 0.67, 0.80, 2.50, 2.00,  0.12,  0.85)   // ~8% BAEL, avg ~5 500 PLN
)

// ═══════════════════════════════════════════════════════════════════
// 2. TYPY DOMENOWE
// ═══════════════════════════════════════════════════════════════════

sealed trait TechState
object TechState {
  case class Traditional(workers: Int) extends TechState
  case class Hybrid(workers: Int, aiEfficiency: Double) extends TechState
  case class Automated(efficiency: Double) extends TechState
  case class Bankrupt(reason: String) extends TechState
}

case class Firm(
  id: Int,
  cash: Double,
  debt: Double,
  tech: TechState,
  riskProfile: Double,
  innovationCostFactor: Double,
  digitalReadiness: Double,
  sector: Int,              // Index into SECTORS
  neighbors: Array[Int]     // Network adjacency (firm IDs)
)

object FirmOps {
  def isAlive(f: Firm): Boolean = f.tech match {
    case _: TechState.Bankrupt => false
    case _                     => true
  }

  def workers(f: Firm): Int = f.tech match {
    case TechState.Traditional(w) => w
    case TechState.Hybrid(w, _)   => w
    case _: TechState.Automated   => Config.AutoSkeletonCrew
    case _: TechState.Bankrupt    => 0
  }

  def capacity(f: Firm): Double = {
    val sec = SECTORS(f.sector)
    f.tech match {
      case TechState.Traditional(w) =>
        Config.BaseRevenue * sec.revenueMultiplier * Math.sqrt(w.toDouble / Config.WorkersPerFirm)
      case TechState.Hybrid(w, eff) =>
        Config.BaseRevenue * sec.revenueMultiplier *
          (0.4 * Math.sqrt(w.toDouble / Config.WorkersPerFirm) + 0.6 * eff)
      case TechState.Automated(eff) =>
        Config.BaseRevenue * sec.revenueMultiplier * eff
      case _: TechState.Bankrupt => 0.0
    }
  }

  /** Efektywny AI CAPEX dla sektora */
  def aiCapex(f: Firm): Double =
    Config.AiCapex * SECTORS(f.sector).aiCapexMultiplier * f.innovationCostFactor
  def hybridCapex(f: Firm): Double =
    Config.HybridCapex * SECTORS(f.sector).hybridCapexMultiplier * f.innovationCostFactor

  /** σ-based threshold modifier: high σ sectors find automation profitable at lower cost gap.
   *  Only used for profitability threshold, NOT for probability multiplier.
   *  Mapping: σ=2→0.91, σ=5→0.95, σ=10→0.98, σ=50→1.00
   *  At equilibrium P≈1.1: Manufacturing marginal, Healthcare blocked. */
  def sigmaThreshold(f: Firm): Double = {
    val s = SECTORS(f.sector).sigma
    Math.min(1.0, 0.88 + 0.075 * Math.log(s) / Math.log(10.0))
  }
}

case class GovState(bdpActive: Boolean, taxRevenue: Double, bdpSpending: Double,
  deficit: Double, cumulativeDebt: Double)
case class NbpState(referenceRate: Double)
case class BankState(totalLoans: Double, nplAmount: Double, capital: Double, deposits: Double) {
  def nplRatio: Double = if (totalLoans > 1.0) nplAmount / totalLoans else 0.0
  def car: Double = if (totalLoans > 1.0) capital / totalLoans else 10.0
  def lendingRate(refRate: Double): Double =
    refRate + Config.BaseSpread + Math.min(0.15, nplRatio * Config.NplSpreadFactor)
  def canLend(amount: Double): Boolean = {
    val projected = capital / (totalLoans + amount)
    projected >= Config.MinCar
  }
}
case class ForexState(exchangeRate: Double, imports: Double, exports: Double,
  tradeBalance: Double, techImports: Double)
case class HhState(employed: Int, marketWage: Double, reservationWage: Double,
  totalIncome: Double, consumption: Double, domesticConsumption: Double,
  importConsumption: Double)
case class World(month: Int, inflation: Double, priceLevel: Double, demandMultiplier: Double,
  gov: GovState, nbp: NbpState, bank: BankState, forex: ForexState, hh: HhState,
  automationRatio: Double, hybridRatio: Double, gdpProxy: Double)

// ═══════════════════════════════════════════════════════════════════
// 2b. WATTS-STROGATZ NETWORK
// ═══════════════════════════════════════════════════════════════════

object Network {
  /** Generate Watts-Strogatz small-world adjacency for N nodes */
  def wattsStrogatz(n: Int, k: Int, p: Double): Array[Array[Int]] = {
    val adj = Array.fill(n)(scala.collection.mutable.Set.empty[Int])

    // Ring lattice: connect each node to k/2 nearest neighbors on each side
    val halfK = k / 2
    for (i <- 0 until n; j <- 1 to halfK) {
      val right = (i + j) % n
      val left  = (i - j + n) % n
      adj(i) += right
      adj(right) += i
      adj(i) += left
      adj(left) += i
    }

    // Rewire with probability p
    for (i <- 0 until n; j <- 1 to halfK) {
      val target = (i + j) % n
      if (Random.nextDouble() < p && adj(i).size < n - 1) {
        // Find a random node not already connected
        var newTarget = Random.nextInt(n)
        var attempts = 0
        while ((newTarget == i || adj(i).contains(newTarget)) && attempts < 20) {
          newTarget = Random.nextInt(n)
          attempts += 1
        }
        if (newTarget != i && !adj(i).contains(newTarget)) {
          adj(i) -= target
          adj(target) -= i
          adj(i) += newTarget
          adj(newTarget) += i
        }
      }
    }

    adj.map(_.toArray)
  }

  /** Compute local automation ratio among neighbors */
  def localAutoRatio(firm: Firm, firms: Array[Firm]): Double = {
    val neighbors = firm.neighbors
    if (neighbors.isEmpty) return 0.0
    val autoCount = neighbors.count { nid =>
      val nf = firms(nid)
      nf.tech.isInstanceOf[TechState.Automated] || nf.tech.isInstanceOf[TechState.Hybrid]
    }
    autoCount.toDouble / neighbors.length
  }
}

// ═══════════════════════════════════════════════════════════════════
// 3. LOGIKA SEKTOROWA
// ═══════════════════════════════════════════════════════════════════

object Sectors {
  private def laborSupplyRatio(wage: Double, resWage: Double): Double = {
    val x = Config.LaborSupplySteepness * (wage / resWage - 1.0)
    1.0 / (1.0 + Math.exp(-x))
  }

  def updateLaborMarket(prevWage: Double, resWage: Double, laborDemand: Int): (Double, Int) = {
    val supplyAtPrev = (Config.TotalPopulation * laborSupplyRatio(prevWage, resWage)).toInt
    val excessDemand = (laborDemand - supplyAtPrev).toDouble / Config.TotalPopulation
    val wageGrowth   = excessDemand * Config.WageAdjSpeed
    val newWage      = Math.max(resWage, prevWage * (1.0 + wageGrowth))
    val newSupply    = (Config.TotalPopulation * laborSupplyRatio(newWage, resWage)).toInt
    val employed     = Math.min(laborDemand, newSupply)
    (newWage, employed)
  }

  def updateInflation(prevInflation: Double, prevPrice: Double, demandMult: Double,
    wageGrowth: Double, exRateDeviation: Double,
    autoRatio: Double, hybridRatio: Double): (Double, Double) = {
    val demandPull    = (demandMult - 1.0) * 0.15
    val costPush      = wageGrowth * 0.25
    val importPush    = Math.max(0.0, exRateDeviation) * Config.ImportPropensity * 0.25
    // In multi-sector economy, automated firms have stronger deflationary spillovers
    // (BPO/SSC services are inputs to all industries → supply-chain deflation)
    val techDeflation = autoRatio * 0.060 + hybridRatio * 0.018
    // Soft floor: beyond -1.5%/month, deflation passes through at 30% rate
    // (models downward price stickiness — Bewley 1999, Schmitt-Grohé & Uribe 2016)
    val rawMonthly    = demandPull + costPush + importPush - techDeflation
    val monthly       = if (rawMonthly >= -0.015) rawMonthly
                        else -0.015 + (rawMonthly + 0.015) * 0.3
    val annualized    = monthly * 12.0
    val smoothed      = prevInflation * 0.7 + annualized * 0.3
    val newPrice      = Math.max(0.30, prevPrice * (1.0 + monthly))
    (smoothed, newPrice)
  }

  def updateNbpRate(prevRate: Double, inflation: Double, exRateChange: Double): Double = {
    val neutral = 0.04
    val infGap  = inflation - Config.TargetInflation
    val taylor  = neutral +
      Config.TaylorAlpha * Math.max(0.0, infGap) +
      Config.TaylorBeta  * Math.max(0.0, exRateChange)
    val smoothed = prevRate * Config.TaylorInertia + taylor * (1.0 - Config.TaylorInertia)
    Math.max(Config.RateFloor, Math.min(Config.RateCeiling, smoothed))
  }

  def updateForeign(prev: ForexState, importConsumption: Double, techImports: Double,
    autoRatio: Double, domesticRate: Double, gdp: Double): ForexState = {
    val exComp   = prev.exchangeRate / Config.BaseExRate
    val techComp = 1.0 + autoRatio * Config.ExportAutoBoost
    val exports  = Config.ExportBase * exComp * techComp
    val totalImp = importConsumption + techImports
    val tradeBal = exports - totalImp
    val rateDiff = domesticRate - Config.ForeignRate
    val capAcct  = rateDiff * Config.IrpSensitivity * gdp
    val bop      = tradeBal + capAcct
    val bopRatio = if (gdp > 0) bop / gdp else 0.0
    val exRateChg = -Config.ExRateAdjSpeed * bopRatio
    val newRate  = Math.max(3.0, Math.min(8.0, prev.exchangeRate * (1.0 + exRateChg)))
    ForexState(newRate, totalImp, exports, tradeBal, techImports)
  }

  def updateGov(prev: GovState, citPaid: Double, vat: Double,
    bdpActive: Boolean, priceLevel: Double): GovState = {
    val bdpSpend   = if (bdpActive) Config.TotalPopulation.toDouble * Config.BdpAmount else 0.0
    val totalSpend = bdpSpend + Config.GovBaseSpending * priceLevel
    val totalRev   = citPaid + vat
    val deficit    = totalSpend - totalRev
    GovState(bdpActive, totalRev, bdpSpend, deficit, prev.cumulativeDebt + deficit)
  }
}

// ═══════════════════════════════════════════════════════════════════
// 4. LOGIKA FIRM (z network + σ-boost)
// ═══════════════════════════════════════════════════════════════════

case class FirmResult(firm: Firm, taxPaid: Double, capexSpent: Double,
  techImports: Double, newLoan: Double)

object FirmLogic {
  private def calcPnL(firm: Firm, wage: Double, demandMult: Double,
    price: Double, lendRate: Double): (Double, Double, Double) = {
    val revenue = FirmOps.capacity(firm) * demandMult * price
    val labor   = FirmOps.workers(firm) * wage * SECTORS(firm.sector).wageMultiplier
    val other   = Config.OtherCosts * price
    // AI/hybrid opex is partially imported (40%) — not fully domestic price-sensitive
    val aiMaint = firm.tech match {
      case _: TechState.Automated => Config.AiOpex * (0.60 + 0.40 * price)
      case _: TechState.Hybrid    => Config.HybridOpex * (0.60 + 0.40 * price)
      case _                      => 0.0
    }
    val interest = firm.debt * (lendRate / 12.0)
    val costs    = labor + other + aiMaint + interest
    val profit   = revenue - costs
    val tax      = Math.max(0.0, profit) * Config.CitRate
    (revenue, costs, profit - tax)
  }

  def process(firm: Firm, w: World, lendRate: Double,
    bankCanLend: Double => Boolean,
    allFirms: Array[Firm]): FirmResult = {

    firm.tech match {
      case _: TechState.Bankrupt =>
        FirmResult(firm, 0, 0, 0, 0)

      case _: TechState.Automated =>
        val (rev, costs, net) = calcPnL(firm, w.hh.marketWage, w.demandMultiplier, w.priceLevel, lendRate)
        val tax = Math.max(0.0, rev - costs) * Config.CitRate
        val nc  = firm.cash + net
        if (nc < 0)
          FirmResult(firm.copy(cash = nc, tech = TechState.Bankrupt("Pułapka płynności (dług AI)")), tax, 0, 0, 0)
        else
          FirmResult(firm.copy(cash = nc), tax, 0, 0, 0)

      case TechState.Hybrid(wkrs, aiEff) =>
        val (rev, costs, net) = calcPnL(firm, w.hh.marketWage, w.demandMultiplier, w.priceLevel, lendRate)
        val tax = Math.max(0.0, rev - costs) * Config.CitRate
        val ready2 = Math.min(1.0, firm.digitalReadiness + 0.005)

        val upCapex = Config.AiCapex * SECTORS(firm.sector).aiCapexMultiplier *
          firm.innovationCostFactor * 0.6
        val upLoan  = upCapex * 0.85
        val upDown  = upCapex * 0.15
        val wMult   = SECTORS(firm.sector).wageMultiplier
        val upCost  = Config.AiOpex * (0.60 + 0.40 * w.priceLevel) +
          (firm.debt + upLoan) * (lendRate / 12.0) +
          Config.AutoSkeletonCrew * w.hh.marketWage * wMult + Config.OtherCosts * w.priceLevel
        val profitable = costs > upCost * 1.1
        val canPay     = firm.cash > upDown
        val ready      = firm.digitalReadiness >= Config.FullAiReadinessMin
        val bankOk     = bankCanLend(upLoan)

        val prob = if (profitable && canPay && ready && bankOk)
          ((firm.riskProfile * 0.15) + (w.automationRatio * 0.3)) * firm.digitalReadiness
        else 0.0

        if (Random.nextDouble() < prob) {
          val eff  = 1.0 + Random.between(0.2, 0.6) * firm.digitalReadiness
          val tImp = upCapex * Config.TechImportShare
          FirmResult(
            firm.copy(tech = TechState.Automated(eff), debt = firm.debt + upLoan,
              cash = firm.cash + net - upDown, digitalReadiness = ready2),
            tax, upCapex, tImp, upLoan)
        } else {
          val nc = firm.cash + net
          if (nc < 0)
            FirmResult(firm.copy(cash = nc, tech = TechState.Bankrupt("Niewypłacalność (hybryda)")),
              tax, 0, 0, 0)
          else
            FirmResult(firm.copy(cash = nc, digitalReadiness = ready2), tax, 0, 0, 0)
        }

      case TechState.Traditional(wkrs) =>
        val (rev, costs, net) = calcPnL(firm, w.hh.marketWage, w.demandMultiplier, w.priceLevel, lendRate)
        val tax = Math.max(0.0, rev - costs) * Config.CitRate

        // Full AI
        val sWm    = SECTORS(firm.sector).wageMultiplier
        val fCapex = FirmOps.aiCapex(firm)
        val fLoan  = fCapex * 0.85
        val fDown  = fCapex * 0.15
        val fCost  = Config.AiOpex * (0.60 + 0.40 * w.priceLevel) +
          (firm.debt + fLoan) * (lendRate / 12.0) +
          Config.AutoSkeletonCrew * w.hh.marketWage * sWm + Config.OtherCosts * w.priceLevel
        val fProf  = costs > fCost * (1.1 / FirmOps.sigmaThreshold(firm))
        val fPay   = firm.cash > fDown
        val fReady = firm.digitalReadiness >= Config.FullAiReadinessMin
        val fBank  = bankCanLend(fLoan)

        // Hybrid — sector-specific worker retention
        val hCapex = FirmOps.hybridCapex(firm)
        val hLoan  = hCapex * 0.80
        val hDown  = hCapex * 0.20
        val hWkrs  = Math.max(3, (wkrs * SECTORS(firm.sector).hybridRetainFrac).toInt)
        val hCost  = hWkrs * w.hh.marketWage * sWm + Config.HybridOpex * (0.60 + 0.40 * w.priceLevel) +
          (firm.debt + hLoan) * (lendRate / 12.0) + Config.OtherCosts * w.priceLevel
        val hProf  = costs > hCost * (1.05 / FirmOps.sigmaThreshold(firm))
        val hPay   = firm.cash > hDown
        val hReady = firm.digitalReadiness >= Config.HybridReadinessMin
        val hBank  = bankCanLend(hLoan)

        // Network-aware mimetic pressure: blend local + global with moderate weights
        val localAuto = Network.localAutoRatio(firm, allFirms)
        val globalPanic = (w.automationRatio + w.hybridRatio * 0.5) * 0.5
        val panic  = localAuto * 0.4 + globalPanic * 0.4  // Balanced local/global
        val desper = if (net < 0) 0.2 else 0.0
        val strat  = if (!fProf && fPay && fReady && fBank)
          firm.riskProfile * 0.005 * firm.digitalReadiness else 0.0

        // Uncertainty discount with network demonstration effect
        val baseDiscount = if (IS_NO_BDP) {
          // No BDP: gradual natural competitive pressure
          0.15 + 0.15 * (w.month.toDouble / Config.Duration.toDouble)
        } else {
          if (w.month < Config.ShockMonth) 0.15 else 1.0
        }
        // Network demonstration: if many neighbors automated, reduce hesitation
        val demoBoost = if (localAuto > Config.DemoEffectThresh)
          Config.DemoEffectBoost * (localAuto - Config.DemoEffectThresh)
        else 0.0
        val uncertaintyDiscount = Math.min(1.0, baseDiscount + demoBoost)

        val pFull = uncertaintyDiscount *
          (if (fProf && fPay && fReady && fBank)
            ((firm.riskProfile * 0.1) + panic + desper) * firm.digitalReadiness
          else strat)

        val pHyb = uncertaintyDiscount *
          (if (hProf && hPay && hReady && hBank)
            ((firm.riskProfile * 0.04) + (panic * 0.5) + (desper * 0.5)) * firm.digitalReadiness
          else 0.0)

        val canReduce = wkrs > 3 && net < 0
        val roll = Random.nextDouble()

        if (roll < pFull) {
          val failRate = 0.05 + (1.0 - firm.digitalReadiness) * 0.10
          val tImp = fCapex * Config.TechImportShare
          if (Random.nextDouble() < failRate) {
            FirmResult(firm.copy(cash = firm.cash + net - fDown * 0.5,
              debt = firm.debt + fLoan * 0.3,
              tech = TechState.Bankrupt("Porażka implementacji AI")),
              tax, fCapex * 0.5, tImp * 0.5, fLoan * 0.3)
          } else {
            val eff = 1.0 + Random.between(0.05, 0.6) * firm.digitalReadiness
            FirmResult(firm.copy(tech = TechState.Automated(eff),
              debt = firm.debt + fLoan, cash = firm.cash + net - fDown),
              tax, fCapex, tImp, fLoan)
          }

        } else if (roll < pFull + pHyb) {
          val failRate = 0.03 + (1.0 - firm.digitalReadiness) * 0.07
          val tImp = hCapex * Config.TechImportShare
          val ir = Random.nextDouble()
          if (ir < failRate * 0.4) {
            FirmResult(firm.copy(cash = firm.cash + net - hDown * 0.5,
              debt = firm.debt + hLoan * 0.3,
              tech = TechState.Bankrupt("Porażka implementacji hybrydy")),
              tax, hCapex * 0.5, tImp * 0.5, hLoan * 0.3)
          } else if (ir < failRate) {
            val badEff = 0.85 + Random.between(0.0, 0.20)
            FirmResult(firm.copy(tech = TechState.Hybrid(hWkrs, badEff),
              debt = firm.debt + hLoan, cash = firm.cash + net - hDown),
              tax, hCapex, tImp, hLoan)
          } else {
            val goodEff = 1.0 + (0.05 + Random.between(0.0, 0.15)) *
              (0.5 + firm.digitalReadiness * 0.5)
            FirmResult(firm.copy(tech = TechState.Hybrid(hWkrs, goodEff),
              debt = firm.debt + hLoan, cash = firm.cash + net - hDown),
              tax, hCapex, tImp, hLoan)
          }

        } else if (canReduce && Random.nextDouble() < 0.10) {
          FirmResult(firm.copy(tech = TechState.Traditional(Math.max(3, wkrs - 2)),
            cash = firm.cash + net), tax, 0, 0, 0)

        } else {
          val nc = firm.cash + net
          if (nc < 0)
            FirmResult(firm.copy(cash = nc,
              tech = TechState.Bankrupt("Niewypłacalność (koszty pracy)")), tax, 0, 0, 0)
          else
            FirmResult(firm.copy(cash = nc), tax, 0, 0, 0)
        }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════
// 5. KROK MIESIĘCZNY
// ═══════════════════════════════════════════════════════════════════

object Simulation {
  def step(w: World, firms: Array[Firm]): (World, Array[Firm]) = {
    val m = w.month + 1
    val bdpActive = m >= Config.ShockMonth

    val bdp = if (bdpActive) Config.BdpAmount else 0.0
    val resWage = Config.BaseReservationWage + bdp * Config.ReservationBdpMult

    val living = firms.filter(FirmOps.isAlive)
    val laborDemand = living.map(FirmOps.workers).sum
    val (newWage, employed) = Sectors.updateLaborMarket(w.hh.marketWage, resWage, laborDemand)
    val wageGrowth = if (w.hh.marketWage > 0) newWage / w.hh.marketWage - 1.0 else 0.0

    val wageIncome = employed.toDouble * newWage
    val bdpIncome  = if (bdpActive) Config.TotalPopulation.toDouble * bdp else 0.0
    val totalIncome = wageIncome + bdpIncome
    val consumption = totalIncome * Config.Mpc

    val importAdj = Config.ImportPropensity *
      Math.pow(Config.BaseExRate / w.forex.exchangeRate, 0.5)
    val importCons = consumption * Math.min(0.65, importAdj)
    val domesticCons = consumption - importCons

    val baseIncome = Config.TotalPopulation.toDouble * Config.BaseWage
    val demandMult = 1.0 + (totalIncome / baseIncome - 1.0) *
      Config.Mpc * (1.0 - Math.min(0.65, importAdj)) * Config.DemandPassthrough

    val lendRate = w.bank.lendingRate(w.nbp.referenceRate)
    val bankCanLend: Double => Boolean = { amt =>
      val approvalP = Math.max(0.1, 1.0 - w.bank.nplRatio * 3.0)
      w.bank.canLend(amt) && Random.nextDouble() < approvalP
    }

    var sumTax      = 0.0
    var sumCapex    = 0.0
    var sumTechImp  = 0.0
    var sumNewLoans = 0.0

    val macro4firms = w.copy(
      month = m, demandMultiplier = demandMult,
      hh = w.hh.copy(marketWage = newWage, reservationWage = resWage))

    // Process firms — pass allFirms for network lookups
    val newFirms = firms.map { f =>
      val r = FirmLogic.process(f, macro4firms, lendRate, bankCanLend, firms)
      sumTax      += r.taxPaid
      sumCapex    += r.capexSpent
      sumTechImp  += r.techImports
      sumNewLoans += r.newLoan
      r.firm
    }

    val prevAlive = firms.filter(FirmOps.isAlive).map(_.id).toSet
    val newlyDead = newFirms.filter(f => !FirmOps.isAlive(f) && prevAlive.contains(f.id))
    val nplNew    = newlyDead.map(_.debt).sum
    val nplLoss   = nplNew * (1.0 - Config.LoanRecovery)
    val intIncome = firms.filter(FirmOps.isAlive).map(_.debt * lendRate / 12.0).sum

    val newBank = w.bank.copy(
      totalLoans = Math.max(0, w.bank.totalLoans + sumNewLoans - nplNew * Config.LoanRecovery),
      nplAmount  = Math.max(0, w.bank.nplAmount + nplNew - w.bank.nplAmount * 0.05),
      capital    = w.bank.capital - nplLoss + intIncome * 0.3,
      deposits   = w.bank.deposits + (totalIncome - consumption))

    val living2 = newFirms.filter(FirmOps.isAlive)
    val nLiving = living2.length.toDouble
    val autoR   = if (nLiving > 0) living2.count(_.tech.isInstanceOf[TechState.Automated]) / nLiving else 0.0
    val hybR    = if (nLiving > 0) living2.count(_.tech.isInstanceOf[TechState.Hybrid]) / nLiving else 0.0
    val gdp     = domesticCons + Config.GovBaseSpending + w.forex.exports

    val exDev = (w.forex.exchangeRate / Config.BaseExRate) - 1.0
    val (newInfl, newPrice) = Sectors.updateInflation(
      w.inflation, w.priceLevel, demandMult, wageGrowth, exDev, autoR, hybR)

    val newForex = Sectors.updateForeign(
      w.forex, importCons, sumTechImp, autoR, w.nbp.referenceRate, gdp)

    val exRateChg = (newForex.exchangeRate / w.forex.exchangeRate) - 1.0
    val newRefRate = Sectors.updateNbpRate(w.nbp.referenceRate, newInfl, exRateChg)

    val vat = consumption * Config.VatRate
    val newGov = Sectors.updateGov(w.gov, sumTax, vat, bdpActive, newPrice)

    val newW = World(m, newInfl, newPrice, demandMult, newGov, NbpState(newRefRate),
      newBank, newForex,
      HhState(employed, newWage, resWage, totalIncome, consumption, domesticCons, importCons),
      autoR, hybR, gdp)
    (newW, newFirms)
  }
}

// ═══════════════════════════════════════════════════════════════════
// 6. SINGLE SIMULATION RUN
// ═══════════════════════════════════════════════════════════════════

/** Run one simulation with given seed. Returns time-series array. */
def runSingle(seed: Int): Array[Array[Double]] = {
  Random.setSeed(seed.toLong)

  // Generate Watts-Strogatz network
  val adjList = Network.wattsStrogatz(Config.FirmsCount, Config.NetworkK, Config.NetworkRewireP)

  // Assign sectors
  val sectorCounts = SECTORS.map(s => (s.share * Config.FirmsCount).toInt)
  // Adjust last sector to fill remaining
  val totalAssigned = sectorCounts.sum
  val sectorAssignments = {
    val arr = new Array[Int](Config.FirmsCount)
    var idx = 0
    for (s <- SECTORS.indices; _ <- 0 until sectorCounts(s)) {
      if (idx < Config.FirmsCount) { arr(idx) = s; idx += 1 }
    }
    while (idx < Config.FirmsCount) { arr(idx) = SECTORS.length - 1; idx += 1 }
    // Shuffle to avoid spatial sector clustering
    val shuffled = Random.shuffle(arr.toList).toArray
    shuffled
  }

  // Initialize firms
  var firms = (0 until Config.FirmsCount).map { i =>
    val sec = SECTORS(sectorAssignments(i))
    Firm(
      id = i,
      cash = Random.between(10000.0, 80000.0) + (if (Random.nextDouble() < 0.1) 200000.0 else 0.0),
      debt = 0.0,
      tech = TechState.Traditional(Config.WorkersPerFirm),
      riskProfile = Random.between(0.1, 0.9),
      innovationCostFactor = Random.between(0.8, 1.5),
      digitalReadiness = Math.max(0.02, Math.min(0.98,
        sec.baseDigitalReadiness + (Random.nextGaussian() * 0.20))),
      sector = sectorAssignments(i),
      neighbors = adjList(i)
    )
  }.toArray

  val initCash = firms.map(_.cash).sum
  var world = World(0, 0.02, 1.0, 1.0,
    GovState(false, 0, 0, 0, 0), NbpState(Config.InitialRate),
    BankState(0, 0, Config.InitBankCapital, initCash),
    ForexState(Config.BaseExRate, 0, Config.ExportBase, 0, 0),
    HhState(Config.TotalPopulation, Config.BaseWage, Config.BaseReservationWage, 0, 0, 0, 0),
    0, 0, Config.BaseRevenue * Config.FirmsCount)

  // Collect time-series: 120 rows × N columns
  // Columns: Month, Inflation, Unemployment, AutoRatio+HybridRatio, ExRate, MarketWage,
  //          GovDebt, NPL, RefRate, PriceLevel, AutoRatio, HybridRatio,
  //          SectorAutoRatio(0..5): BPO, Manuf, Retail, Health, Public, Agri
  val nCols = 18
  val results = Array.ofDim[Double](Config.Duration, nCols)

  for (t <- 0 until Config.Duration) {
    val (newW, newF) = Simulation.step(world, firms)
    world = newW
    firms = newF

    val unemployPct = 1.0 - world.hh.employed.toDouble / Config.TotalPopulation
    val living = firms.filter(FirmOps.isAlive)
    val nLiving = living.length.toDouble

    // Per-sector automation ratios
    val sectorAuto = SECTORS.indices.map { s =>
      val secFirms = living.filter(_.sector == s)
      if (secFirms.isEmpty) 0.0
      else secFirms.count(f =>
        f.tech.isInstanceOf[TechState.Automated] || f.tech.isInstanceOf[TechState.Hybrid]
      ).toDouble / secFirms.length
    }

    results(t) = Array(
      (t + 1).toDouble,          // 0: Month
      world.inflation,            // 1: Inflation
      unemployPct,                // 2: Unemployment
      world.automationRatio + world.hybridRatio, // 3: TotalAdoption
      world.forex.exchangeRate,   // 4: ExRate
      world.hh.marketWage,        // 5: MarketWage
      world.gov.cumulativeDebt,   // 6: GovDebt
      world.bank.nplRatio,        // 7: NPL
      world.nbp.referenceRate,    // 8: RefRate
      world.priceLevel,           // 9: PriceLevel
      world.automationRatio,      // 10: AutoRatio
      world.hybridRatio,          // 11: HybridRatio
      sectorAuto(0),              // 12: BPO auto
      sectorAuto(1),              // 13: Manuf auto
      sectorAuto(2),              // 14: Retail auto
      sectorAuto(3),              // 15: Health auto
      sectorAuto(4),              // 16: Public auto
      sectorAuto(5)               // 17: Agri auto
    )
  }

  results
}

// ═══════════════════════════════════════════════════════════════════
// 7. MAIN: MONTE CARLO LOOP
// ═══════════════════════════════════════════════════════════════════

{
  println(s"╔══════════════════════════════════════════════════════════════╗")
  println(s"║  SFC-ABM v6 GUS-CALIBRATED MC: BDP=${BDP_AMOUNT.toInt} PLN, N=${N_SEEDS} seeds  ║")
  println(s"║  10 000 firm × 6 sectors (GUS 2024) × WS network × 120m   ║")
  println(s"╚══════════════════════════════════════════════════════════════╝")

  val outDir = new File(s"mc")
  if (!outDir.exists()) outDir.mkdirs()

  // Aggregation arrays
  val nMonths = Config.Duration
  val nCols   = 18
  val allRuns = Array.ofDim[Double](N_SEEDS, nMonths, nCols)

  val startTime = System.currentTimeMillis()

  for (seed <- 1 to N_SEEDS) {
    val t0 = System.currentTimeMillis()
    val results = runSingle(seed)
    allRuns(seed - 1) = results
    val dt = System.currentTimeMillis() - t0

    if (seed <= 3 || seed % 10 == 0 || seed == N_SEEDS) {
      val adoption = results(nMonths - 1)(3)
      val inflation = results(nMonths - 1)(1)
      val unemp = results(nMonths - 1)(2)
      println(f"  Seed $seed%3d/${N_SEEDS} (${dt}ms) | " +
        f"Adopt=${adoption * 100}%5.1f%% | π=${inflation * 100}%5.1f%% | " +
        f"Unemp=${unemp * 100}%5.1f%%")
    }
  }

  val totalTime = (System.currentTimeMillis() - startTime) / 1000.0
  println(f"\nTotal time: ${totalTime}%.1f seconds")

  // ── Write per-seed terminal values ─────────────────────────
  val termPw = new PrintWriter(new File(s"mc/${OUTPUT_PREFIX}_terminal.csv"))
  termPw.write("Seed;Inflation;Unemployment;TotalAdoption;ExRate;MarketWage;" +
    "GovDebt;NPL;RefRate;PriceLevel;AutoRatio;HybridRatio;" +
    "BPO_Auto;Manuf_Auto;Retail_Auto;Health_Auto;Public_Auto;Agri_Auto\n")
  for (seed <- 0 until N_SEEDS) {
    val last = allRuns(seed)(nMonths - 1)
    termPw.write(s"${seed + 1}")
    for (c <- 1 until nCols)
      termPw.write(f";${last(c)}%.6f")
    termPw.write("\n")
  }
  termPw.close()

  // ── Write aggregated time-series (mean, std, p5, p95) ─────
  val aggPw = new PrintWriter(new File(s"mc/${OUTPUT_PREFIX}_timeseries.csv"))
  val colNames = Array("Month", "Inflation", "Unemployment", "TotalAdoption", "ExRate",
    "MarketWage", "GovDebt", "NPL", "RefRate", "PriceLevel",
    "AutoRatio", "HybridRatio", "BPO_Auto", "Manuf_Auto", "Retail_Auto", "Health_Auto",
    "Public_Auto", "Agri_Auto")
  // Header: Month, then for each metric: mean, std, p05, p95
  aggPw.write("Month")
  for (c <- 1 until nCols) {
    aggPw.write(s";${colNames(c)}_mean;${colNames(c)}_std;${colNames(c)}_p05;${colNames(c)}_p95")
  }
  aggPw.write("\n")

  for (t <- 0 until nMonths) {
    aggPw.write(s"${t + 1}")
    for (c <- 1 until nCols) {
      val vals = (0 until N_SEEDS).map(s => allRuns(s)(t)(c)).sorted.toArray
      val mean = vals.sum / vals.length
      val variance = vals.map(v => (v - mean) * (v - mean)).sum / vals.length
      val std  = Math.sqrt(variance)
      val p05  = vals((vals.length * 0.05).toInt)
      val p95  = vals(Math.min(vals.length - 1, (vals.length * 0.95).toInt))
      aggPw.write(f";$mean%.6f;$std%.6f;$p05%.6f;$p95%.6f")
    }
    aggPw.write("\n")
  }
  aggPw.close()

  // ── Summary statistics ─────────────────────────────────────
  println("\n══════════════════════════════════════════════════════")
  println(s"MONTE CARLO SUMMARY: ${OUTPUT_PREFIX} (BDP=${BDP_AMOUNT.toInt}, N=${N_SEEDS})")
  println("══════════════════════════════════════════════════════")

  def statsSummary(name: String, colIdx: Int, mult: Double = 1.0): Unit = {
    val vals = (0 until N_SEEDS).map(s => allRuns(s)(nMonths - 1)(colIdx) * mult).sorted.toArray
    val mean = vals.sum / vals.length
    val std  = Math.sqrt(vals.map(v => (v - mean) * (v - mean)).sum / vals.length)
    val p05  = vals((vals.length * 0.05).toInt)
    val p95  = vals(Math.min(vals.length - 1, (vals.length * 0.95).toInt))
    println(f"  $name%-25s mean=${mean}%8.2f ± ${std}%6.2f  [${p05}%8.2f, ${p95}%8.2f]")
  }

  statsSummary("Inflation (%)", 1, 100.0)
  statsSummary("Unemployment (%)", 2, 100.0)
  statsSummary("Total Adoption (%)", 3, 100.0)
  statsSummary("Exchange Rate", 4)
  statsSummary("Market Wage (PLN)", 5)
  statsSummary("Gov Debt (mld PLN)", 6, 1.0 / 1e9)
  statsSummary("NPL Ratio (%)", 7, 100.0)

  println("\nPer-sector adoption at M120:")
  val secNames = SECTORS.map(_.name)
  for (s <- SECTORS.indices) {
    statsSummary(f"  ${secNames(s)}%-22s", 12 + s, 100.0)
  }

  println(s"\nSaved: mc/${OUTPUT_PREFIX}_terminal.csv")
  println(s"Saved: mc/${OUTPUT_PREFIX}_timeseries.csv")
}
