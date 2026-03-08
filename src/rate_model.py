"""
Rate Model and Trance Class

Each rate model is a callable that takes current market inputs and returns
the applicable annualized interest rate for a given distribution period.

Rate types (from supplement):
  - FIX:    Fixed rate
  - FIX/Z:  Fixed rate, accrual class — same rate calc, different payment handling
  - FLT:    SOFR + spread, capped and floored
  - INV/IO: cap - SOFR, capped and floored
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

# Rate model functions

def fixed_rate_model(fixed_rate: float, **kwargs) -> float:
    """
    Fixed rate class: constant coupon regardless of market conditions.
    """
    return fixed_rate


def floating_rate_model(
    sofr: float,
    float_spread_bps: float,
    rate_floor: float,
    rate_ceiling: float,
    **kwargs
) -> float:
    """
    Floating rate class: SOFR + spread, subject to cap and floor.

    Formula: rate = max(floor, min(ceiling, SOFR + spread))

    FB: SOFR + 130bps, cap 6.50%, floor 1.30%
    FC: SOFR + 90bps,  cap 8.00%, floor 0.90%
    """
    spread = float_spread_bps / 10000.0
    raw_rate = sofr + spread
    return max(rate_floor, min(rate_ceiling, raw_rate))


def inverse_floating_rate_model(
    sofr: float,
    inv_cap: float,
    rate_floor: float,
    rate_ceiling: float,
    **kwargs
) -> float:
    """
    Inverse floating rate IO class: cap - SOFR, subject to cap and floor.

    Formula: rate = max(floor, min(ceiling, cap - SOFR))

    When SOFR >= cap, rate = 0 (investor loses all coupon income).

    SB: 5.20% - SOFR, cap 5.20%, floor 0.00%
    SC: 7.10% - SOFR, cap 7.10%, floor 0.00%
    """
    raw_rate = inv_cap - sofr
    return max(rate_floor, min(rate_ceiling, raw_rate))


# Get Rate Model 

def get_rate_model(interest_type: str):
    """
    Return the appropriate rate function for a given interest_type string.

    Args:
        interest_type: one of "FIX", "FIX/Z", "FLT", "INV/IO"

    Returns:
        Callable rate model function

    Raises:
        ValueError if type is not recognized
    """
    dispatch = {
        "FIX":    fixed_rate_model,
        "FIX/Z":  fixed_rate_model,    # Same rate calc; accrual handling is in waterfall
        "FLT":    floating_rate_model,
        "INV/IO": inverse_floating_rate_model,
    }
    if interest_type not in dispatch:
        raise ValueError(
            f"Unknown interest_type '{interest_type}'. "
            f"Supported: {list(dispatch.keys())}"
        )
    return dispatch[interest_type]

# Tranche object — holds state and rate config per class

@dataclass
class Tranche:
    """
    Represents a single REMIC tranche/class.

    Tracks balance, computes interest each period, and records monthly history.

    """
    class_id: str
    group_id: int
    original_balance: float
    principal_type: str
    interest_type: str
    is_accrual: bool
    is_notional: bool
    notional_ref_class: Optional[str]
    is_delay: bool

    # Rate inputs
    fixed_rate: Optional[float] = None
    float_spread_bps: Optional[float] = None
    inv_cap: Optional[float] = None
    rate_floor: Optional[float] = 0.0
    rate_ceiling: Optional[float] = None
    initial_rate: Optional[float] = None

    # Metadata
    cusip: Optional[str] = None
    final_dist_date: Optional[str] = None

    def __post_init__(self):
        self.balance = self.original_balance
        self._rate_fn = get_rate_model(self.interest_type)
        self.history = []               # list of MonthlyRecord dicts

    def compute_rate(self, sofr: float = 0.0) -> float:
        """
        Compute the applicable annual interest rate for this period.

        Args:
            sofr: Current 30-day average SOFR (decimal, e.g., 0.043)

        Returns:
            Annual rate as decimal
        """
        return self._rate_fn(
            fixed_rate=self.fixed_rate or 0.0,
            sofr=sofr,
            float_spread_bps=self.float_spread_bps or 0.0,
            inv_cap=self.inv_cap or 0.0,
            rate_floor=self.rate_floor or 0.0,
            rate_ceiling=self.rate_ceiling or 99.0,
        )

    def compute_interest(self, notional_balance: float, sofr: float = 0.0) -> float:
        """
        Compute gross interest accrual for this period.

        For normal classes: interest = balance * rate / 12
        For notional IO classes: uses notional_balance

        Args:
            notional_balance: balance to apply rate to (equals self.balance for
                              non-notional classes; ref class balance for IO)
            sofr:             current SOFR

        Returns:
            Monthly interest dollar amount
        """
        rate = self.compute_rate(sofr)
        return notional_balance * rate / 12.0

    def record(self, period: int, date, bop_bal: float,
               principal_paid: float, interest_paid: float,
               accrual_add: float, coupon_rate: float, sofr: float):
        """Append a monthly record to history."""
        self.history.append({
            "class_id": self.class_id,
            "group_id": self.group_id,
            "period": period,
            "date": date,
            "bop_balance": bop_bal,
            "principal_payment": principal_paid,
            "interest_payment": interest_paid,
            "accrual_addition": accrual_add,
            "eop_balance": bop_bal - principal_paid + accrual_add,
            "coupon_rate_annual": coupon_rate,
            "sofr": sofr,
        })

    def history_df(self) -> pd.DataFrame:
        import pandas as pd
        return pd.DataFrame(self.history)


def load_tranches(classes_config: list) -> dict:
    """
    Create Tranche objects from config list.

    Returns:
        dict: key -> class_id
    """
    tranches = {}
    for c in classes_config:
        t = Tranche(
            class_id=c["class_id"],
            group_id=c["group_id"],
            original_balance=c["original_balance"],
            principal_type=c["principal_type"],
            interest_type=c["interest_type"],
            is_accrual=c.get("is_accrual", False),
            is_notional=c.get("is_notional", False),
            notional_ref_class=c.get("notional_ref_class"),
            is_delay=c.get("is_delay", True),
            fixed_rate=c.get("fixed_rate"),
            float_spread_bps=c.get("float_spread_bps"),
            inv_cap=c.get("inv_cap"),
            rate_floor=c.get("rate_floor", 0.0),
            rate_ceiling=c.get("rate_ceiling"),
            initial_rate=c.get("initial_rate"),
            cusip=c.get("cusip"),
            final_dist_date=c.get("final_dist_date"),
        )
        tranches[c["class_id"]] = t
    return tranches
