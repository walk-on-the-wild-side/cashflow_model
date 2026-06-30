"""

Waterfall engine.

Driven by waterfall_rules config. The rules below illustrate the structure
modeled by the bundled example deal (config/deal_config.yaml); a different
deal config produces a different waterfall.

Group 1 rules:
  Step 1: The BZ Accrual Amount to BV until retired, and thereafter to BZ.
  Step 2a: 50% of Group 1 CF -> BA -> BE -> BV -> BZ (sequential)
  Step 2b: 50% of Group 1 CF -> FB

Group 2 rules:
  Step 1: The CZ Accrual Amount to CA until retired, and thereafter to CZ.
  Step 2a: 50% of Group 2 CF -> CA -> CZ (sequential)
  Step 2b: 50% of Group 2 CF -> FC
"""

import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import Dict, List


def get_distribution_dates(settlement_date_str: str, n_periods: int,
                           distribution_day: int = 25) -> List[date]:
    """Generate monthly distribution dates from settlement."""
    from datetime import datetime
    settle = datetime.strptime(settlement_date_str, "%Y-%m-%d").date()
    dates = []
    d = settle.replace(day=distribution_day)
    if d <= settle:
        d = (settle.replace(day=1) + relativedelta(months=1)).replace(day=distribution_day)
    for _ in range(n_periods):
        dates.append(d)
        d = (d.replace(day=1) + relativedelta(months=1)).replace(day=distribution_day)
    return dates


def _sequential(available: float, targets: List[dict],
                balances: Dict[str, float]) -> Dict[str, float]:
    """Sequential allocation: fill each target class in priority order."""
    alloc = {t["class_id"]: 0.0 for t in targets}
    remaining = available
    for t in sorted(targets, key=lambda x: x["priority"]):
        cid = t["class_id"]
        cap = max(0.0, balances.get(cid, 0.0))
        take = min(remaining, cap)
        alloc[cid] = take
        remaining -= take
        if remaining < 1e-4:
            break
    return alloc


class Waterfall:
    def __init__(self, rules_config: dict, tranches: dict):
        self.rules = rules_config
        self.tranches = tranches

    def run_all_periods(self, coll_cfs: dict, dist_dates: list, sofr: float):
        """Run the full waterfall for all periods across all groups."""
        max_periods = max(len(df) for df in coll_cfs.values())
        balances = {cid: t.original_balance for cid, t in self.tranches.items()}

        for period_idx in range(max_periods):
            period = period_idx + 1
            dist_date = dist_dates[period_idx] if period_idx < len(dist_dates) else None

            for gid in sorted(coll_cfs.keys()):
                cf_df = coll_cfs[gid]
                if period_idx >= len(cf_df):
                    continue
                row = cf_df.iloc[period_idx]
                self._one_period(period, dist_date, gid,
                                 float(row["total_principal"]),
                                 float(row["ptr_interest"]),
                                 sofr, balances)

    def _one_period(self, period, dist_date, group_id, total_principal,
                    ptr_interest, sofr, balances):
        group_tranches = {cid: t for cid, t in self.tranches.items()
                          if t.group_id == group_id}

        # --- Interest calculation ---
        interest_cash = {}
        accrual_adds = {}
        coupon_rates = {}

        for cid, tranche in group_tranches.items():
            if tranche.is_notional and tranche.notional_ref_class:
                notional_bal = balances.get(tranche.notional_ref_class, 0.0)
            else:
                notional_bal = balances.get(cid, 0.0)

            rate = tranche.compute_rate(sofr)
            coupon_rates[cid] = rate
            monthly_int = notional_bal * rate / 12.0

            if tranche.is_accrual:
                accrual_adds[cid] = monthly_int
                interest_cash[cid] = 0.0
            else:
                accrual_adds[cid] = 0.0
                interest_cash[cid] = monthly_int

        # --- Add accrual to Z-class balances ---
        for cid, acc in accrual_adds.items():
            if acc > 0:
                balances[cid] = balances.get(cid, 0.0) + acc

        # --- Principal distribution ---
        principal_paid = {cid: 0.0 for cid in group_tranches}
        collateral_remaining = total_principal
        group_rules = self.rules.get(f"group{group_id}", [])

        for rule in group_rules:
            source = rule["source"]
            targets = rule["targets"]

            if source == "accrual":
                # The accrual amount already added to Z-class balance.
                # Now re-direct that same amount to BV/CA (per waterfall).
                # Net effect on Z-class: balance grows by accrual, then
                # reduces by what flows to BV/CA — net = only what stays on BZ/CZ.
                accrual_cls = rule["accrual_class"]
                avail = accrual_adds.get(accrual_cls, 0.0)
                if avail < 1e-4:
                    continue

                # Only redirect to classes OTHER than the accrual class itself
                redirect_targets = [t for t in targets if t["class_id"] != accrual_cls]
                if redirect_targets:
                    allocs = _sequential(avail, redirect_targets, balances)
                    for cid, amt in allocs.items():
                        if amt > 0:
                            balances[cid] = max(0.0, balances[cid] - amt)
                            principal_paid[cid] += amt
                    redirected = sum(allocs.values())
                    # The accrual class loses what was redirected (net of its accrual gain)
                    balances[accrual_cls] = max(0.0, balances[accrual_cls] - redirected)

            elif source == "collateral_cf":
                split = rule.get("split_pct", 1.0)
                avail = min(collateral_remaining * split, collateral_remaining)
                if avail < 1e-4:
                    continue

                allocs = _sequential(avail, targets, balances)
                actual = sum(allocs.values())
                for cid, amt in allocs.items():
                    if amt > 0:
                        balances[cid] = max(0.0, balances[cid] - amt)
                        principal_paid[cid] += amt
                collateral_remaining -= actual

        # --- Record results ---
        for cid, tranche in group_tranches.items():
            acc = accrual_adds.get(cid, 0.0)
            prin = principal_paid.get(cid, 0.0)
            eop = max(0.0, balances[cid])
            bop = eop + prin - acc
            if bop < 0:
                bop = 0.0

            tranche.history.append({
                "class_id": cid,
                "group_id": group_id,
                "period": period,
                "date": dist_date,
                "bop_balance": bop,
                "principal_payment": prin,
                "interest_payment": interest_cash.get(cid, 0.0),
                "accrual_addition": acc,
                "eop_balance": eop,
                "coupon_rate_annual": coupon_rates.get(cid, 0.0),
                "sofr": sofr,
            })
