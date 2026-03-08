"""
Collateral cash flow engine.

Implements the PSA prepayment model and standard mortgage amortization to
generate month-by-month principal (scheduled + prepayment) and interest cash
flows for each collateral group.

CollateralGroup class is parameterized from config.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional


# PSA Model
def compute_cpr(psa_speed: float, loan_age_months: int, period: int) -> float:
    """
    Compute annual CPR for a given PSA speed, loan age, and projection period.

    PSA standard ramp: CPR ramps linearly from 0% to 6% over 30 months
    (seasoned from origination), then stays flat at 6%.

    N% PSA scales the entire curve by N/100.

    Args:
        psa_speed:       PSA speed (e.g., 100 = 100% PSA, 400 = 400% PSA)
        loan_age_months: Seasoning at deal settlement (months)
        period:          Month index in projection (1-based)

    Returns:
        Annual CPR as a decimal (e.g., 0.06 = 6%)
    """
    effective_age = loan_age_months + period          # total seasoning
    base_cpr = min(effective_age / 30.0, 1.0) * 0.06 # standard PSA ramp
    return base_cpr * (psa_speed / 100.0)

# cpr to smm conversion
def cpr_to_smm(annual_cpr: float) -> float:
    """
    Convert annual CPR to monthly Single Monthly Mortality (SMM).

    SMM = 1 - (1 - CPR)^(1/12)
    """
    return 1.0 - (1.0 - annual_cpr) ** (1.0 / 12.0)


# Single-Pool Amortization
def compute_monthly_payment(balance: float, annual_rate: float, remaining_months: int) -> float:
    """
    Standard level-payment mortgage monthly payment.

    P&I payment = balance * (r / (1 - (1+r)^-n))
    where r = monthly rate, n = remaining months.

    If monthly rate is 0, payment = balance / remaining_months.
    """
    if remaining_months <= 0:
        return 0.0
    r = annual_rate / 12.0
    if r == 0:
        return balance / remaining_months
    return balance * r / (1.0 - (1.0 + r) ** (-remaining_months))

# CollateralGroup class
@dataclass
class CollateralGroup:
    """
    Represents a single pool of mortgage collateral backing a group of REMIC classes.

    All parameters come from deal_config.yaml

    Attributes:
        group_id:              Identifier (1 or 2)
        principal_balance:     Starting UPB (Unpaid Principal Balance)
        pass_through_rate:     UMBS pass-through rate (net rate passed to REMIC)
        wac:                   Weighted average coupon of underlying loans
        original_term_months:  Original loan term
        remaining_term_months: Remaining term at settlement
        loan_age_months:       Loan seasoning at settlement
    """
    group_id: int
    principal_balance: float
    pass_through_rate: float          # PTR: interest rate used for REMIC distributions
    wac: float                        # WAC: used for amortization schedule
    original_term_months: int
    remaining_term_months: int
    loan_age_months: int
    pool_number: Optional[str] = None

    def generate_cashflows(self, psa_speed: float) -> pd.DataFrame:
        """
        Generate full monthly cash flow schedule for this collateral group.

        Returns a DataFrame with one row per month containing:
            period             : integer month (1-based)
            bop_balance        : beginning-of-period UPB
            scheduled_principal: amortization principal
            prepayment         : CPR-driven prepayment
            total_principal    : scheduled + prepayment
            gross_interest     : interest at WAC rate
            ptr_interest       : interest at pass-through rate (paid to REMIC)
            net_io             : difference 
            eop_balance        : ending UPB
            cpr                : annual CPR this period
            smm                : monthly SMM this period
        """
        records = []
        balance = self.principal_balance
        remaining = self.remaining_term_months

        for period in range(1, self.original_term_months + 1):
            if balance < 0.01:
                break

            # Prepayment rates
            annual_cpr = compute_cpr(psa_speed, self.loan_age_months, period)
            smm = cpr_to_smm(annual_cpr)

            # Scheduled amortization at WAC
            monthly_payment = compute_monthly_payment(balance, self.wac, remaining)
            monthly_wac = self.wac / 12.0
            gross_interest = balance * monthly_wac
            scheduled_principal = max(0.0, monthly_payment - gross_interest)
            scheduled_principal = min(scheduled_principal, balance)

            # Prepayment
            prepayment = smm * max(0.0, balance - scheduled_principal)
            prepayment = min(prepayment, balance - scheduled_principal)

            total_principal = scheduled_principal + prepayment
            total_principal = min(total_principal, balance)

            # PTR interest (what passes to REMIC) 
            ptr_interest = balance * (self.pass_through_rate / 12.0)
            net_io = gross_interest - ptr_interest

            eop_balance = max(0.0, balance - total_principal)

            records.append({
                "period": period,
                "group_id": self.group_id,
                "bop_balance": balance,
                "scheduled_principal": scheduled_principal,
                "prepayment": prepayment,
                "total_principal": total_principal,
                "gross_interest": gross_interest,
                "ptr_interest": ptr_interest,
                "net_io": net_io,
                "eop_balance": eop_balance,
                "cpr": annual_cpr,
                "smm": smm,
            })

            balance = eop_balance
            remaining = max(1, remaining - 1)

        df = pd.DataFrame(records)
        df["psa_speed"] = psa_speed
        return df


def load_collateral_groups(groups_config: list) -> dict:
    """
    Args:
        groups_config: list of group dicts from deal_config.yaml

    Returns:
        dict keyed by group_id
    """
    groups = {}
    for g in groups_config:
        grp = CollateralGroup(
            group_id=g["group_id"],
            pool_number=g.get("pool_number"),
            principal_balance=g["principal_balance"],
            pass_through_rate=g["pass_through_rate"],
            wac=g["wac"],
            original_term_months=g["original_term_months"],
            remaining_term_months=g["remaining_term_months"],
            loan_age_months=g["loan_age_months"],
        )
        groups[g["group_id"]] = grp
    return groups
