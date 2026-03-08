"""

Main entry point for the Deal Model.

Usage:
    python run_model.py                    # Run all scenarios, write Excel
    python run_model.py --scenarios 0PSA_Base 400PSA_Base   # Run specific scenarios
    python run_model.py --deal config/deal_config.yaml      # Custom deal config

"""

import sys
import os
import argparse

# sys.path.insert(0, os.path.dirname(__file__))

from src.deal import Deal


def main():
    parser = argparse.ArgumentParser(description="CMO REMIC Cash Flow Model")
    parser.add_argument("--deal", default="config/deal_config.yaml",
                        help="Path to deal config YAML")
    parser.add_argument("--market", default="config/market_config.yaml",
                        help="Path to market config YAML")
    parser.add_argument("--output", default="output/FNM_2025_21_cashflows.xlsx",
                        help="Output Excel file path")
    parser.add_argument("--scenarios", nargs="*", default=None,
                        help="Scenario IDs to run (default: all)")
    args = parser.parse_args()

    print("=" * 70)
    print("  CMO REMIC DEAL MODEL — Fannie Mae REMIC Trust 2025-21")
    print("=" * 70)

    # Load deal
    deal = Deal(args.deal, args.market)

    # Run scenarios
    deal.run(scenario_filter=args.scenarios)

    # Write outputs
    os.makedirs("output", exist_ok=True)
    deal.write_outputs(args.output)

    print(f"\nDone. Output: {args.output}")


if __name__ == "__main__":
    main()
