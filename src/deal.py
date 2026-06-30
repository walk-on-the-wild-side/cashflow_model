"""

Loads config, runs scenarios, validates WALs, and writes outputs.

Usage:
    from src.deal import Deal
    deal = Deal("config/deal_config.yaml", "config/market_config.yaml")
    deal.run()
    deal.write_outputs("output/cashflows.xlsx")
"""

import os
import yaml
import pandas as pd
from typing import Optional


class Deal:
    """
    Main orchestrator for cash flow model.

    Parameterized entirely from YAML config files.
    """

    def __init__(self, deal_config_path: str, market_config_path: str):
        """
        Load deal and market configurations.

        Args:
            deal_config_path:   path to deal_config.yaml
            market_config_path: path to market_config.yaml
        """
        with open(deal_config_path) as f:
            self.deal_config = yaml.safe_load(f)
        with open(market_config_path) as f:
            self.market_config = yaml.safe_load(f)

        self.deal_name = self.deal_config["deal"]["name"]
        self.settlement_date = self.deal_config["deal"]["settlement_date"]
        self.benchmark_wals = self.deal_config.get("benchmark_wals", {})

        # Results populated after run()
        self.all_results = dict()  # scenario_id -> class_id -> cash flow DataFrame
        self.collateral_results = dict() # scenario_id -> group_id -> collateral cash flow DataFrame
        self.scenario_meta = dict() # scenario_id -> metadata dict (label, psa_speed, etc.)
        self.wal_df = pd.DataFrame()  # scenario_id, class_id, wal_years
        self.validation_df = pd.DataFrame() # scenario_id, class_id, model_wal, benchmark_wal, difference, within_tolerance

        print(f"Deal loaded: {self.deal_name}")
        print(f"Settlement: {self.settlement_date}")
        print(f"Groups: {len(self.deal_config['groups'])}")
        print(f"Classes: {len(self.deal_config['classes'])}")
        n_scenarios = len(self.market_config.get("scenarios", []))
        print(f"Scenarios: {n_scenarios}")

    def run(self, scenario_filter: list = []):
        """
        Run all (or filtered) scenarios.

        Args:
            scenario_filter: list of scenario_ids to run; None = all
        """
        from .scenarios import run_scenarios_with_fixes as run_scenarios
        from .outputs import validate_wals

        print(f"\nRunning scenarios for: {self.deal_name}")
        print("-" * 60)

        self.all_results, self.collateral_results, self.scenario_meta, self.wal_df = (
            run_scenarios(self.deal_config, self.market_config, scenario_filter)
        )

        # Validate WALs against prospectus benchmarks
        self.validation_df = validate_wals(
            self.wal_df,
            self.scenario_meta,
            self.benchmark_wals,
            tolerance=0.15,
        )

        print(f"\nCompleted {len(self.scenario_meta)} scenarios.")
        self._print_wal_summary()

    def write_outputs(self, output_path: str):
        """Write Excel output workbook."""
        from .outputs import write_excel_output
        summary_sids = [sid for sid, meta in self.scenario_meta.items()
                        if self.market_config.get("scenarios", []) and
                        any(s["scenario_id"] == sid and s.get("include_in_summary", False)
                            for s in self.market_config["scenarios"])]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        write_excel_output(
            all_results=self.all_results,
            collateral_results=self.collateral_results,
            wal_df=self.wal_df,
            validation_df=self.validation_df,
            scenario_meta=self.scenario_meta,
            output_path=output_path,
            deal_name=self.deal_name,
            deal_config=self.deal_config,
            summary_sids=summary_sids,
        )

    def get_class_cashflows(self, class_id: str, scenario_id: str) -> pd.DataFrame:
        """Return cash flow DataFrame for a specific class and scenario."""
        if self.all_results is None:
            raise RuntimeError("Run deal.run() first.")
        return self.all_results.get(scenario_id, {}).get(class_id, pd.DataFrame())

    def get_wal_table(self) -> pd.DataFrame:
        """Return WAL summary table with all classes and scenarios."""
        return self.wal_df

    def get_validation_table(self) -> pd.DataFrame:
        """Return WAL validation table (model vs. prospectus)."""
        return self.validation_df

    def _print_wal_summary(self):
        """Print WAL summary to console."""
        if self.wal_df is None or self.wal_df.empty:
            return

        # Show summary scenarios only
        summary_sids = [sid for sid, meta in self.scenario_meta.items()
                        if self.market_config.get("scenarios", []) and
                        any(s["scenario_id"] == sid and s.get("include_in_summary", False)
                            for s in self.market_config["scenarios"])]

        print("\n" + "=" * 70)
        print(f"  WAL SUMMARY — {self.deal_name}")
        print("=" * 70)

        # Pivot: classes x scenarios
        df = self.wal_df.copy()
        df["label"] = df["scenario_id"].map(
            lambda s: self.scenario_meta.get(s, {}).get("label", s)
        )
        pivot = df.pivot_table(
            index="class_id", columns="label", values="wal_years", aggfunc="first"
        )
        print(pivot.to_string())

        # Validation summary
        if self.validation_df is not None and not self.validation_df.empty:
            vdf = self.validation_df.dropna(subset=["benchmark_wal"])
            if not vdf.empty:
                passed = vdf["within_tolerance"].sum()
                total = len(vdf)
                print(f"\n  WAL Validation: {passed}/{total} within ±0.15yr tolerance")
                failed = vdf[vdf["within_tolerance"] == False]
                if not failed.empty:
                    print("  FAILED cases:")
                    for _, row in failed.iterrows():
                        print(f"    {row['class_id']} @ {row['psa_speed']}% PSA: "
                              f"model={row['model_wal']:.1f} bench={row['benchmark_wal']:.1f} "
                              f"diff={row['difference']:+.2f}")
