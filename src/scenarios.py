"""
Scenario runner — waterfall simulation for each scenario.

run_scenarios_with_fixes function runs scenarios and applies notional WAL correction.
"""

import copy
import pandas as pd
from typing import Dict, Any

from .collateral import load_collateral_groups
from .rate_model import load_tranches
from .waterfall import Waterfall, get_distribution_dates


def run_scenarios(deal_config, market_config, scenario_filter=None):
    from .outputs import compute_wal, validate_wals

    scenarios = market_config.get("scenarios", [])
    if scenario_filter:
        scenarios = [s for s in scenarios if s["scenario_id"] in scenario_filter]

    all_results = {}
    collateral_results = {}
    scenario_meta = {}
    settlement_date = deal_config["deal"]["settlement_date"]
    dist_day = deal_config["deal"].get("distribution_day", 25)

    for scenario in scenarios:
        sid = scenario["scenario_id"]
        psa = scenario["psa_speed"]
        sofr = scenario.get("sofr", market_config["market"]["default_sofr"])
        label = scenario.get("label", sid)

        print(f"  Running: {label} (PSA={psa}, SOFR={sofr:.4f})")
        scenario_meta[sid] = {"label": label, "psa_speed": psa, "sofr": sofr}

        # Fresh collateral groups
        groups = load_collateral_groups(deal_config["groups"])
        coll_cfs = {gid: grp.generate_cashflows(psa) for gid, grp in groups.items()}
        collateral_results[sid] = {gid: df.copy() for gid, df in coll_cfs.items()}

        # Fresh tranches
        tranches = load_tranches(deal_config["classes"])

        # Distribution dates
        max_periods = max(len(df) for df in coll_cfs.values())
        dist_dates = get_distribution_dates(settlement_date, max_periods, dist_day)

        # Run waterfall
        wf = Waterfall(deal_config.get("waterfall_rules", {}), tranches)
        wf.run_all_periods(coll_cfs, dist_dates, sofr)

        # Collect results
        scenario_class_results = {}
        for cid, tranche in tranches.items():
            df = tranche.history_df()
            df["psa_speed"] = psa
            df["scenario_id"] = sid
            df["scenario_label"] = label
            scenario_class_results[cid] = df
        all_results[sid] = scenario_class_results

    # WALs
    from datetime import datetime
    settle = datetime.strptime(settlement_date, "%Y-%m-%d").date()
    wal_rows = []
    for sid, class_results in all_results.items():
        for cid, df in class_results.items():
            wal = compute_wal(df, settle)
            wal_rows.append({
                "scenario_id": sid,
                "scenario_label": scenario_meta[sid]["label"],
                "psa_speed": scenario_meta[sid]["psa_speed"],
                "sofr": scenario_meta[sid]["sofr"],
                "class_id": cid,
                "wal_years": wal,
            })

    wal_df = pd.DataFrame(wal_rows)
    return all_results, collateral_results, scenario_meta, wal_df


def fix_notional_wals(wal_df, all_results, notional_map):
    """
    For notional IO classes (SB->FB, SC->FC), copy the reference class WAL.
    """
    rows = []
    for _, row in wal_df.iterrows():
        cid = row["class_id"]
        sid = row["scenario_id"]
        if cid in notional_map:
            ref_cid = notional_map[cid]
            ref_row = wal_df[(wal_df["class_id"] == ref_cid) &
                             (wal_df["scenario_id"] == sid)]
            if not ref_row.empty:
                row = row.copy()
                row["wal_years"] = ref_row.iloc[0]["wal_years"]
        rows.append(row)
    return pd.DataFrame(rows)


def run_scenarios_with_fixes(deal_config, market_config, scenario_filter=None):
    """Wrapper that runs scenarios and applies notional WAL correction."""
    all_results, collateral_results, scenario_meta, wal_df = run_scenarios(
        deal_config, market_config, scenario_filter
    )
    # Fix SB -> FB, SC -> FC notional WALs (Page 7: "FB and SB" share WAL)
    notional_map = {}
    for c in deal_config.get("classes", []):
        if c.get("is_notional") and c.get("notional_ref_class"):
            notional_map[c["class_id"]] = c["notional_ref_class"]
    if notional_map:
        wal_df = fix_notional_wals(wal_df, all_results, notional_map)
    return all_results, collateral_results, scenario_meta, wal_df
