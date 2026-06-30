# CMO/REMIC Cash Flow Model

**A configurable Python cash flow engine for Collateralized Mortgage Obligations (CMOs) and REMIC (Real Estate Mortgage Investment Conduit) structured finance deals.**

**Author:** Amartya Mani Triapthi
**Email:** mt.amartya@gmail.com

---

## Overview

This project implements a **cash flow modeling engine** for CMO/REMIC structured finance deals. It supports:

- **Multi-class tranches** with fixed, floating, inverse, and accrual rate structures
- **Principal & interest waterfalls** with complex distribution rules
- **PSA prepayment scenarios**
- **SOFR rate scenarios**
- **WAL (Weighted Average Life) calculations**
- **Excel output**

All deal-specific inputs are **parameterized in YAML configuration files** — no code changes are needed to model a different deal structure. The repo ships with a worked example based on the Fannie Mae REMIC Trust 2025-21 prospectus supplement (see `docs/`), which doubles as a validation case against published WAL benchmarks.

---

## Key Features

✓ **Scenario-based modeling** — Multi-dimensional PSA × SOFR scenario matrix
✓ **Complex rate mechanics** — Support for fixed, floating, inverse, I/O and Z-class (accrual) bonds
✓ **Cash flow distribution** — Principal and interest waterfalls with priority of payment rules
✓ **Mortgage dynamics** — PSA prepayment model
✓ **Validation & verification** — WAL comparisons against prospectus benchmarks
✓ **Excel generation** — Summary tables and multiple analysis tabs
✓ **Configuration-driven** — Zero-code deal modifications via YAML configs

---

## Project Structure

```
cashflow_model/
├── config/
│   ├── deal_config.yaml              # Deal structure, classes, groups, waterfall rules
│   └── market_config.yaml            # SOFR rates, PSA scenarios
├── src/
│   ├── __init__.py
│   ├── collateral.py                 # PSA prepayment model & mortgage amortization
│   ├── rate_model.py                 # Interest rate calculators (all class types)
│   ├── waterfall.py                  # Principal & interest distribution engine
│   ├── scenarios.py                  # Scenario runner (PSA × SOFR matrix iteration)
│   ├── outputs.py                    # WAL calculation, Excel writer, validation
│   └── deal.py                       # Top-level Deal orchestrator
├── tests/
│   └── test_wal.py                   # Unit tests for WAL calculations
├── output/
│   └── cashflows.xlsx                # Generated Excel output file
├── docs/                             # Reference prospectus for the bundled example deal
├── run_model.py                      # Main entry point
├── requirements.txt                  # Python dependencies
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Clone the repo:
```bash
git clone https://github.com/walk-on-the-wild-side/cashflow_model.git
cd cashflow_model
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

The following key packages are included:
- **pandas** — Data manipulation and analysis
- **numpy** — Numerical computations
- **PyYAML** — Configuration file parsing
- **openpyxl** — Excel file generation

---

## Usage

### Quick Start

```bash
# Run all scenarios with default (example) config
python run_model.py
```

This generates the default output file: `output/cashflows.xlsx`

### Command-Line Options

```bash
# Display help
python run_model.py -h

# Run specific scenarios only
python run_model.py --scenarios 0PSA_Base 400PSA_Base

# Use custom configuration files
python run_model.py --deal config/my_deal.yaml \
                    --market config/my_market.yaml \
                    --output output/my_output.xlsx
```

### Python API

```python
from src.deal import Deal

# Load and initialize deal
deal = Deal("config/deal_config.yaml", "config/market_config.yaml")

# Run all scenarios
deal.run()

# Or run specific scenarios
deal.run(scenario_filter=["0PSA_Base", "400PSA_Base"])

# Write results to Excel
deal.write_outputs("output/results.xlsx")

# Access results programmatically
print(deal.wal_df)            # WAL results table
print(deal.all_results)       # Scenario cash flows
print(deal.validation_df)     # WAL vs. benchmark validation
```

---

## Configuration

### Deal Configuration (`config/deal_config.yaml`)

Defines the deal structure, collateral pools, tranches, and distribution rules:

```yaml
deal:
  name: "Fannie Mae REMIC Trust 2025-21"
  total_balance: 332607408
  settlement_date: "2025-02-28"
  distribution_day: 25

groups:                              # Collateral pools
  - group_id: 1
    pool_number: "MA5073"
    principal_balance: 146244678
    pass_through_rate: 0.0600
    wac: 0.06905                    # Weighted average coupon
    remaining_term_months: 334
    # ... additional group parameters

classes:                             # Tranches/securities
  - class_id: "A1"
    group_id: 1
    original_balance: 75000000
    principal_type: "sequential"
    interest_type: "fixed"
    fixed_rate: 0.0450
    waterfall_priority: 1
    # ... additional class parameters

benchmark_wals:                      # Prospectus WAL targets
  "A1": {0: 2.5, 400: 1.2}
  # ...
```

### Market Configuration (`config/market_config.yaml`)

Specifies SOFR levels and scenario definitions:

```yaml
market:
  default_sofr: 0.043293            # Base SOFR rate

scenarios:
  - scenario_id: "0PSA_Base"
    label: "0% PSA (No Prepayment)"
    psa_speed: 0
    sofr: 0.043293
    include_in_summary: true

  - scenario_id: "400PSA_Base"
    label: "400% PSA (Fast Prepayment)"
    psa_speed: 400
    sofr: 0.043293
    include_in_summary: true
```

---

## Key Components

### `collateral.py` — Prepayment & Amortization
Implements the **PSA (Public Securities Association) model**:
- Compounds monthly CPR (conditional prepayment rate) from PSA speed parameter
- Amortizes mortgage principal monthly
- Calculates mortgage pool cash flows (principal + interest)

### `rate_model.py` — Interest Rate Calculation
Computes monthly coupon rates for all class types:
- **Fixed-rate classes** — Constant coupon
- **Floating-rate classes** — SOFR + spread, with optional caps/floors
- **Inverse/IO classes** — Inverse relationship to index
- **Accrual/Z-classes** — Accrue interest, paid at maturity

### `waterfall.py` — Cash Flow Distribution
Distributes mortgage cash flows to tranches following priority rules defined in config:
- Sequential principal paydown (by waterfall priority)
- Interest payments to all classes
- Residual/equity to final tier

### `scenarios.py` — Scenario Engine
Iterates through all scenario combinations:
- Runs the cash flow model for each (PSA speed, SOFR rate) pair
- Aggregates results by scenario
- Computes statistics and metrics

### `outputs.py` — Analysis & Reporting
Generates analysis outputs:
- **WAL calculations** — Weighted average life for each class
- **Validation** — Compares calculated WALs vs. configured benchmarks
- **Excel export** — Multi-tab workbook with detailed cash flows
- **Decrement tables** — Principal activity by month/scenario

### `deal.py` — Orchestrator
Main controller class that:
- Loads YAML configurations
- Coordinates all model components
- Manages results and output writing

---

## Output

### Excel Workbook Structure

The generated Excel file contains:

| Sheet | Content |
|-------|---------|
| Summary Dashboard | Deal overview, WAL table color-coded vs. benchmarks |
| WAL Validation | Model WAL vs. benchmark (PASS/FAIL) |
| WAL Pivot | Classes × scenarios pivot table |
| Coll G1/G2 [scenario] | Monthly collateral cash flows per group |
| ClassCF [scenario] | Monthly class-level principal, interest, balance |
| Decr [class] | Decrement tables: % original balance outstanding |

---

## Testing

Run unit tests for WAL calculations:

```bash
pytest tests/test_wal.py -v
```

Tests validate:
- Correct WAL computation for sequential classes
- Floating rate mechanics with SOFR updates
- Scenario isolation and proper result aggregation

---

## Generalizing to a New Deal

To model a different REMIC deal:

1. **Copy** `config/deal_config.yaml` → `config/my_new_deal.yaml`
2. **Edit** the following sections:
   - `deal:` — name, settlement date, total balance
   - `groups:` — collateral characteristics per group
   - `classes:` — all tranche definitions, rates, types
   - `waterfall_rules:` — principal distribution rules
   - `benchmark_wals:` — benchmark WALs for validation
3. **Run:** `python run_model.py --deal config/my_new_deal.yaml`

Supported deal types via config:
- Sequential (SEQ) classes
- Accrual / Z-classes (FIX/Z)
- Floating rate (SOFR + spread)
- Inverse floating IO (cap − SOFR)
- Notional IO classes
- Pass-through (PT) classes
- Multiple collateral groups

---

## Core Logic Summary

#### 1. Collateral Engine (`collateral.py`)
Standard PSA amortization model:
- CPR(m) = min(loan_age + m, 30) / 30 × 6% × PSA/100
- SMM = 1 − (1 − CPR)^(1/12)
- Monthly principal = scheduled amortization + SMM × remaining balance
- Interest at pass-through rate passed to REMIC

#### 2. Interest Rate Models (`rate_model.py`)
| Type    | Formula                              |
|---------|---------------------------------------|
| FIX     | fixed_rate (constant)                |
| FIX/Z   | fixed_rate; interest → principal     |
| FLT     | max(floor, min(cap, SOFR + spread))  |
| INV/IO  | max(0, min(cap, cap_rate − SOFR))    |

#### 3. Waterfall (`waterfall.py`)
Priority of payments is fully defined by `waterfall_rules` in the deal config. The bundled example deal (Fannie Mae REMIC Trust 2025-21) uses:

**Group 1:**
1. BZ Accrual Amount → BV (until retired), then BZ
2. 50% of Group 1 CF → BA → BE → BV → BZ (sequential)
3. 50% of Group 1 CF → FB

**Group 2:**
1. CZ Accrual Amount → CA (until retired), then CZ
2. 50% of Group 2 CF → CA → CZ (sequential)
3. 50% of Group 2 CF → FC

#### 4. WAL Calculation (`outputs.py`)
WAL = Σ(t × Principal_payment) / Σ(Principal_payment)
where t = period / 12 (years from settlement)

---

## Example Deal: Fannie Mae REMIC Trust 2025-21

The repo's default config models this real-world deal as a worked example and validation case against its prospectus supplement (`docs/`).

### Key Assumptions

| Assumption | Value | Source |
|------------|-------|--------|
| Prepayment model | PSA ramp (0→6% CPR over 30 months) | Page 11 |
| Group 1 loan age | 20 months | Page 5 |
| Group 2 loan age | 15 months | Page 5 |
| Group 1 WAC | 6.905% | Page 5 |
| Group 2 WAC | 7.454% | Page 5 |
| Group 1 PTR | 6.00% | Page 5 |
| Group 2 PTR | 6.50% | Page 5 |
| SOFR basis | 30-day Average SOFR (FRBNY) | Pages 9-10 |
| OID PSA — Group 1 | 198% PSA | Page 17 |
| OID PSA — Group 2 | 324% PSA | Page 17 |
| Distribution day | 25th of each month | Page 10 |

### WAL Notes

BA, BE, CA, and CZ WALs tie out closely to the prospectus.
BV/BZ/FB show modest differences due to:
- The prospectus uses pool-level heterogeneity (not a single WAC/WAM repline)
- The AD (Accrual-Directed) component for BV has timing nuances
- The exact SOFR level affects floating class WALs

These are standard modeling approximations for a single-repline engine.
