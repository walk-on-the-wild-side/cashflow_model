# CMO REMIC Deal Model

**A Python cash flow model for Fannie Mae REMIC Trust 2025-21 structured finance deals.**

**Author:** Amartya Mani Triapthi  
**Email:** mt.amartya@gmail.com  
**Phone:** +91-9792810946

---

## Overview

This project implements a **comprehensive cash flow modeling engine** for Collateralized Mortgage Obligations (CMOs) and REMIC (Real Estate Mortgage Investment Conduit) structured finance deals. The model is built from the **Fannie Mae REMIC Trust 2025-21 prospectus supplement** and supports:

- **Multi-class tranches** with fixed, floating, inverse, and accrual rate structures
- **Principal & interest waterfalls** with complex distribution rules
- **PSA prepayment scenarios** 
- **SOFR rate scenarios** 
- **WAL (Weighted Average Life) calculations** 
- **Excel output** 

All deal-specific inputs are **parameterized in YAML configuration files** — no code changes are needed to model a different deal structure.

---

## Key Features

✓ **Scenario-based modeling** — Multi-dimensional PSA × SOFR scenario matrix  
✓ **Complex rate mechanics** — Support for fixed, floating, inverse, I/O and Z-class (accrual) bonds  
✓ **Cash flow distribution** — Principal and interest waterfalls with priority of payment rules  
✓ **Mortgage dynamics** — PSA prepayment model  
✓ **Validation & verification** — WAL comparisons against prospectus benchmarks  
✓ **Excel generation** — Summary Tables and multiple analysis tabs  
✓ **Configuration-driven** — Zero-code deal modifications via YAML configs  

---

## Project Structure

```
cashfow_model/
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
│   └── FNM_2025_21_cashflows.xlsx    # Generated Excel output file
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

1. Clone or download the project:
```bash
cd riskspan_assesment
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
# Run all scenarios with default config
python run_model.py
```

This generates the default output file: `output/FNM_2025_21_cashflows.xlsx`

### Command-Line Options

```bash
# Display help
python run_model.py -h

# Run specific scenarios only
python run_model.py --scenarios 0PSA_Base 400PSA_Base

# Use custom configuration files
python run_model.py --deal config/deal_config.yaml \
                    --market config/market_config.yaml \
                    --output output/custom_output.xlsx

# Run subset of scenarios
python run_model.py --scenarios 100PSA_Base 200PSA_Base 300PSA_Base
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
print(deal.wal_df)           # WAL results table
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
Implements **PSA (Public Securities Association) model**:
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
Distributes mortgage cash flows to tranches following priority rules:
- Sequential principal paydown (by waterfall priority)
- Interest payments to all classes
- Residual/equity to final tier

### `scenarios.py` — Scenario Engine
Iterates through all scenario combinations:
- Runs cash flow model for each (PSA speed, SOFR rate) pair
- Aggregates results by scenario
- Computes statistics and metrics

### `outputs.py` — Analysis & Reporting
Generates analysis outputs:
- **WAL calculations** — Weighted average life for each class
- **Validation** — Compares calculated WALs vs. prospectus benchmarks
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

The generated Excel file (`output/FNM_2025_21_cashflows.xlsx`) contains:

| Sheet | Content |
|-------|---------|
| **WAL Summary** | Weighted average life by class and scenario |
| **Scenario Results** | Detailed monthly cash flows for each scenario |
| **Validation** | WAL calculations vs. prospectus benchmarks |
| **Collateral CF** | Mortgage pool cash flows (principal + interest) |
| **Decrement Tables** | Principal balance by class and month |

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

# Run specific scenarios only
python run_model.py --scenarios 0PSA_Base 400PSA_Base

---
# Custom deal config
python run_model.py --deal config/my_deal.yaml --market config/my_market.yaml

### Using as a Library

```python
from src.deal import Deal

deal = Deal("config/deal_config.yaml", "config/market_config.yaml")
deal.run()

# Access results
wal_table = deal.get_wal_table()
ba_cf = deal.get_class_cashflows("BA", "0PSA_Base")
validation = deal.get_validation_table()

# Write Excel
deal.write_outputs("output/my_output.xlsx")
```


---
# Core Logic Summary

#### 1. Collateral Engine (`collateral.py`)
Standard PSA amortization model:
- CPR(m) = min(loan_age + m, 30) / 30 × 6% × PSA/100
- SMM = 1 − (1 − CPR)^(1/12)
- Monthly principal = scheduled amortization + SMM × remaining balance
- Interest at pass-through rate passed to REMIC

#### 2. Interest Rate Models (`rate_model.py`)
| Type    | Formula                              | Classes        |
|---------|--------------------------------------|----------------|
| FIX     | fixed_rate (constant)                | BA, BE, BV, CA |
| FIX/Z   | fixed_rate; interest → principal     | BZ, CZ         |
| FLT     | max(floor, min(cap, SOFR + spread))  | FB, FC         |
| INV/IO  | max(0, min(cap, cap_rate − SOFR))    | SB, SC         |

#### 3. Waterfall (`waterfall.py`)
**Group 1 (Page 10 of supplement):**
1. BZ Accrual Amount → BV (until retired), then BZ
2. 50% of Group 1 CF → BA → BE → BV → BZ (sequential)
3. 50% of Group 1 CF → FB

**Group 2 (Page 10 of supplement):**
1. CZ Accrual Amount → CA (until retired), then CZ
2. 50% of Group 2 CF → CA → CZ (sequential)
3. 50% of Group 2 CF → FC

#### 4. WAL Calculation (`outputs.py`)
WAL = Σ(t × Principal_payment) / Σ(Principal_payment)
where t = period / 12 (years from settlement)

---

### Output Excel Workbook

| Sheet | Contents |
|-------|----------|
| Summary Dashboard | Deal overview, WAL table color-coded vs. prospectus benchmarks |
| WAL Validation | Model WAL vs. prospectus benchmark (PASS/FAIL) |
| WAL Pivot | Classes × scenarios pivot table |
| Coll G1/G2 [scenario] | Monthly collateral cash flows per group |
| ClassCF [scenario] | Monthly class-level principal, interest, balance |
| Decr [class] | Decrement tables: % original balance outstanding |

---

### Generalizing to a New Deal

To model a different REMIC deal:

1. **Copy** `config/deal_config.yaml` → `config/my_new_deal.yaml`
2. **Edit** the following sections:
   - `deal:` — name, settlement date, total balance
   - `groups:` — collateral characteristics per group
   - `classes:` — all tranche definitions, rates, types
   - `waterfall_rules:` — principal distribution rules
   - `benchmark_wals:` — prospectus WAL benchmarks for validation
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

### Key Assumptions (from Supplement)

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
| Assignment scenarios | 0% PSA and 400% PSA | Assignment doc |

---

### WAL Notes

BA, BE, CA, and CZ WALs tie out closely to prospectus.  
BV/BZ/FB show modest differences due to:
- The prospectus uses pool-level heterogeneity (not a single WAC/WAM repline)
- The AD (Accrual-Directed) component for BV has timing nuances
- Exact SOFR level affects floating class WALs

These are standard modeling approximations for a single-repline engine.
