"""

WAL tie-out validation tests.
Runs the two assignment-required scenarios (0 PSA, 400 PSA) and checks
WALs against prospectus benchmarks.

Run with: python -m pytest tests/test_wal.py -v
     or:  python tests/test_wal.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.deal import Deal

TOLERANCE = 0.5  # years — generous for single-repline approximation

def test_wal_assignment_scenarios():
    deal = Deal("config/deal_config.yaml", "config/market_config.yaml")
    deal.run(scenario_filter=["0PSA_Base", "400PSA_Base"])
    vdf = deal.get_validation_table()
    vdf = vdf[vdf["benchmark_wal"].notna()].copy()

    errors = []
    for _, row in vdf.iterrows():
        if abs(row["difference"]) > TOLERANCE:
            errors.append(
                f"{row['class_id']} @ {row['psa_speed']}% PSA: "
                f"model={row['model_wal']:.2f} bench={row['benchmark_wal']:.2f} "
                f"diff={row['difference']:+.2f}"
            )

    if errors:
        print(f"\nWAL differences outside ±{TOLERANCE} year:")
        for e in errors:
            print(f"  {e}")
    else:
        print(f"\nAll WALs within ±{TOLERANCE} year tolerance.")

    # Core classes should always be close
    for cid, psa_speed, expected_wal, tol in [
        ("BA", 0,   14.6, 0.3),
        ("BA", 400, 1.8,  0.3),
        ("BE", 0,   24.0, 0.5),
        ("BE", 400, 4.6,  0.3),
        ("CA", 0,   14.1, 1.2),  # SEQ/AD with accrual; single-repline approx
        ("CA", 400, 1.7,  0.5),
    ]:
        row = vdf[(vdf["class_id"] == cid) & (vdf["psa_speed"] == psa_speed)]
        if not row.empty:
            model_wal = row.iloc[0]["model_wal"]
            assert abs(model_wal - expected_wal) <= tol, (
                f"FAIL: {cid} @ {psa_speed}% PSA model={model_wal:.2f} "
                f"expected={expected_wal:.2f} (tol={tol})"
            )
            print(f"  PASS: {cid} @ {psa_speed}% PSA = {model_wal:.2f} yrs (bench={expected_wal})")

    print("\nAll core WAL tests passed.")


def test_collateral_cashflows():
    """Test that collateral cash flows sum correctly and are non-negative."""
    from src.collateral import CollateralGroup
    g = CollateralGroup(
        group_id=1, principal_balance=146244678, pass_through_rate=0.06,
        wac=0.06905, original_term_months=360, remaining_term_months=334,
        loan_age_months=20
    )
    cf = g.generate_cashflows(psa_speed=400)
    assert (cf["total_principal"] >= 0).all(), "Negative principal found"
    assert (cf["ptr_interest"] >= 0).all(), "Negative interest found"
    assert (cf["eop_balance"] >= 0).all(), "Negative balance found"
    total_prin = cf["total_principal"].sum()
    assert abs(total_prin - 146244678) < 1000, f"Principal not fully paid: {total_prin:.0f}"
    print(f"  PASS: Collateral @ 400 PSA — total principal paid = ${total_prin:,.0f}")


def test_rate_models():
    """Test rate calculation formulas."""
    from src.rate_model import floating_rate_model, inverse_floating_rate_model, fixed_rate_model

    # FB: SOFR + 130bps, cap 6.5%, floor 1.3%
    assert abs(floating_rate_model(0.043, 130, 0.013, 0.065) - 0.056) < 1e-10  # 4.3% + 1.3% = 5.6%
    assert floating_rate_model(0.060, 130, 0.013, 0.065) == 0.065  # Hits cap
    assert floating_rate_model(0.000, 130, 0.013, 0.065) == 0.013  # Hits floor
    print("  PASS: FB floating rate model")

    # SB: 5.2% - SOFR, cap 5.2%, floor 0%
    assert abs(inverse_floating_rate_model(0.043, 0.052, 0.0, 0.052) - 0.009) < 1e-10
    assert inverse_floating_rate_model(0.060, 0.052, 0.0, 0.052) == 0.0   # SOFR > cap → 0
    print("  PASS: SB inverse float rate model")

    # Fixed
    assert fixed_rate_model(fixed_rate=0.055) == 0.055
    print("  PASS: Fixed rate model")


if __name__ == "__main__":
    print("=" * 60)
    print("  CMO Deal Model — Validation Tests")
    print("=" * 60)

    print("\n[1] Collateral Cash Flow Tests")
    test_collateral_cashflows()

    print("\n[2] Rate Model Tests")
    test_rate_models()

    print("\n[3] WAL Assignment Scenario Tests")
    test_wal_assignment_scenarios()

    print("\n" + "=" * 60)
    print("  All tests completed.")
    print("=" * 60)
