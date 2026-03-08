"""
Fannie Mae REMIC Trust 2025-21 Implementation

Cash flow model for multi-class REMIC structures.

Modules:
    collateral  : PSA prepayment model and amortization engine
    rate_model  : Pluggable interest rate calculators (FIX, FLT, INV/IO, accrual)
    waterfall   : Principal and interest distribution engine
    scenarios   : Scenario runner
    outputs     : WAL calculation, Excel output, validation
    deal        : Top-level orchestrator

Usage:
    from src.deal import Deal
    deal = Deal("config/deal_config.yaml", "config/market_config.yaml")
    deal.run()
    deal.write_outputs("output/cashflows.xlsx")
"""
