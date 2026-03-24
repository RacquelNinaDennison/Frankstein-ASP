"""
Frankenstein ASP Driver
=======================
Loads historical application data, pre-computes fixed route outcomes
(Ceiling and Base), scales financial values to integers, and generates
the data.lp facts file for the ASP solver.

Also runs clingo and parses the optimal weight configuration.

Usage:
    python driver.py --input frankenstein_engineered.csv --output data.lp
    python driver.py --input frankenstein_engineered.csv --solve

Requirements:
    pip install pandas clingo
"""

import argparse
import json
import math
from pathlib import Path

import pandas as pd

# -------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------

# Scale factor for converting float ratios to integers.
# E.g., current_ratio of 1.15 → 115 with RATIO_SCALE=100.
RATIO_SCALE = 100

# Scale factor for monetary values to reduce magnitude
# while preserving relative differences.
# E.g., R1,500,000 → 150 with MONEY_SCALE=10000.
MONEY_SCALE = 10000

# Target approval ratio and loss ratio (from the doc)
TARGET_APPROVAL_RATIO = 0.70
TARGET_LOSS_RATIO = 0.40


def load_and_prepare(csv_path: str) -> pd.DataFrame:
    """
    Load the engineered dataset and compute derived features
    needed for the ASP encoding.
    
    The column names below are PLACEHOLDERS based on the doc's
    feature descriptions. Replace with actual column names from
    the frankenstein_engineered table.
    """
    df = pd.read_csv(csv_path)
    
    # ---- Placeholder column mapping ----
    # Uncomment and adjust once you have the actual schema.
    # 
    # COLUMN_MAP = {
    #     'RequestedAmount': 'limit_requested',
    #     'ApprovedAmount': 'approved_amount',
    #     'CurrentRatio': 'current_ratio',
    #     'FinancialLeverage': 'leverage',
    #     'NetProfitAfterTax': 'npat',
    #     'TotalEquity': 'equity',
    #     'CostOfSales': 'cost_of_sales',
    #     'Cash': 'cash',
    #     'WorkingCapitalCycle': 'nwc_days',
    #     'InventoryPeriod': 'inv_period',
    #     'DebtorCollectionPeriod': 'dcp',
    #     'CreditorPaymentPeriod': 'cpp',
    #     'TotalCurrentLiabilities': 'total_current_liabilities',
    #     'Premium': 'premium',
    #     'ClaimAmount': 'claims',
    #     'CeilingPasses': 'ceiling_passes',   # pre-computed boolean
    #     'BasePasses': 'base_passes',          # pre-computed boolean
    # }
    # df = df.rename(columns=COLUMN_MAP)
    
    return df


def compute_fixed_outcomes(df: pd.DataFrame) -> dict:
    """
    Compute the fixed approval counts, premium, and claims
    from applications that pass Ceiling or Base (regardless
    of Finance weights).
    
    Returns a dict with:
        fixed_approval_count: int
        fixed_premium: int (scaled)
        fixed_claims: int (scaled)
        target_swing_approvals: int
    """
    # Applications that are approved regardless of Finance
    fixed_mask = df['ceiling_passes'] | df['base_passes']
    
    fixed_approval_count = fixed_mask.sum()
    fixed_premium = int(df.loc[fixed_mask, 'premium'].sum() / MONEY_SCALE)
    fixed_claims = int(df.loc[fixed_mask, 'claims'].fillna(0).sum() / MONEY_SCALE)
    
    total_applications = len(df)
    target_total_approvals = round(TARGET_APPROVAL_RATIO * total_applications)
    target_swing_approvals = max(0, target_total_approvals - fixed_approval_count)
    
    return {
        'fixed_approval_count': fixed_approval_count,
        'fixed_premium': fixed_premium,
        'fixed_claims': fixed_claims,
        'total_applications': total_applications,
        'target_swing_approvals': target_swing_approvals,
    }


def generate_facts(df: pd.DataFrame, output_path: str):
    """
    Generate the data.lp file with:
      - application/1 facts for all applications
      - ceiling_passes/1 and base_passes/1 for fixed-outcome apps
      - Feature facts for swing applications (scaled to integers)
      - Premium and claims facts for swing applications
      - Fixed totals as constants
    """
    lines = []
    lines.append("% Auto-generated data facts for Frankenstein ASP encoding")
    lines.append(f"% Generated from dataset with {len(df)} applications")
    lines.append("")
    
    # Identify swing applications
    swing_mask = ~df['ceiling_passes'] & ~df['base_passes']
    swing_count = swing_mask.sum()
    
    lines.append(f"% Total applications: {len(df)}")
    lines.append(f"% Swing applications (Finance-dependent): {swing_count}")
    lines.append(f"% Fixed approvals (Ceiling or Base pass): {(~swing_mask).sum()}")
    lines.append("")
    
    # --- All application IDs ---
    lines.append("% Application IDs")
    for idx in df.index:
        lines.append(f"application({idx}).")
    lines.append("")
    
    # --- Fixed route outcomes ---
    lines.append("% Pre-computed Ceiling route outcomes")
    for idx in df[df['ceiling_passes']].index:
        lines.append(f"ceiling_passes({idx}).")
    lines.append("")
    
    lines.append("% Pre-computed Base route outcomes")
    for idx in df[df['base_passes']].index:
        lines.append(f"base_passes({idx}).")
    lines.append("")
    
    # --- Feature facts for swing applications only ---
    # (No need to load features for non-swing apps since their
    #  outcome is fixed regardless of Finance weights)
    lines.append("% Financial features for swing applications (scaled to integers)")
    
    swing_df = df[swing_mask].copy()
    
    for idx, row in swing_df.iterrows():
        app_id = idx
        
        # Scale ratios by RATIO_SCALE, monetary values by MONEY_SCALE
        cr = _safe_int(row.get('current_ratio', 0) * RATIO_SCALE)
        lev = _safe_int(row.get('leverage', 0))
        npat = _safe_int(row.get('npat', 0) / MONEY_SCALE)
        eq = _safe_int(row.get('equity', 0) / MONEY_SCALE)
        limit_req = _safe_int(row.get('limit_requested', 0) / MONEY_SCALE)
        cos = _safe_int(row.get('cost_of_sales', 0) / MONEY_SCALE)
        cash = _safe_int(row.get('cash', 0) / MONEY_SCALE)
        nwc = _safe_int(row.get('nwc_days', 0))
        inv_p = _safe_int(row.get('inv_period', 0))
        dcp_val = _safe_int(row.get('dcp', 0))
        cpp_val = _safe_int(row.get('cpp', 0))
        tcl = _safe_int(row.get('total_current_liabilities', 0) / MONEY_SCALE)
        
        # Premium and claims (scaled for objective function)
        prem = _safe_int(row.get('premium', 0) / MONEY_SCALE)
        claims = _safe_int(row.get('claims', 0) / MONEY_SCALE)
        
        lines.append(f"current_ratio({app_id}, {cr}).")
        lines.append(f"leverage({app_id}, {lev}).")
        lines.append(f"npat({app_id}, {npat}).")
        lines.append(f"equity({app_id}, {eq}).")
        lines.append(f"limit_requested({app_id}, {limit_req}).")
        lines.append(f"cost_of_sales({app_id}, {cos}).")
        lines.append(f"cash({app_id}, {cash}).")
        lines.append(f"nwc_days({app_id}, {nwc}).")
        lines.append(f"inv_period({app_id}, {inv_p}).")
        lines.append(f"dcp({app_id}, {dcp_val}).")
        lines.append(f"cpp({app_id}, {cpp_val}).")
        lines.append(f"total_current_liabilities({app_id}, {tcl}).")
        lines.append(f"premium_scaled({app_id}, {prem}).")
        lines.append(f"claims_scaled({app_id}, {claims}).")
        lines.append("")
    
    # --- Fixed totals (constants for the objective) ---
    fixed = compute_fixed_outcomes(df)
    lines.append("% Fixed outcome constants")
    lines.append(f"fixed_approval_count({fixed['fixed_approval_count']}).")
    lines.append(f"fixed_premium({fixed['fixed_premium']}).")
    lines.append(f"fixed_claims({fixed['fixed_claims']}).")
    lines.append(f"total_applications({fixed['total_applications']}).")
    lines.append(f"target_swing_approvals({fixed['target_swing_approvals']}).")
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"Generated {output_path}")
    print(f"  Total applications: {len(df)}")
    print(f"  Swing applications: {swing_count}")
    print(f"  Target swing approvals: {fixed['target_swing_approvals']}")


def _safe_int(value) -> int:
    """Convert a value to int, handling NaN and inf."""
    if pd.isna(value) or math.isinf(value):
        return 0
    return int(round(value))


def solve(encoding_path: str, data_path: str, num_solutions: int = 1):
    """
    Run clingo with the encoding and data, parse optimal weights.
    
    Returns a list of solution dicts, each containing:
        weights: dict mapping rule_id → passing_weight
        var_approved: set of approved swing application IDs
        optimization: list of optimization values per priority level
    """
    try:
        import clingo
    except ImportError:
        print("ERROR: clingo Python API not installed.")
        print("Install with: pip install clingo")
        return []
    
    solutions = []
    
    def on_model(model):
        """Callback for each optimal model found."""
        sol = {
            'weights': {},
            'var_approved': set(),
            'optimization': list(model.cost),
        }
        
        for atom in model.symbols(shown=True):
            if atom.name == 'pass_weight':
                rule_id = str(atom.arguments[0])
                weight = atom.arguments[1].number
                sol['weights'][rule_id] = weight
                
            elif atom.name == 'var_approved':
                app_id = atom.arguments[0].number
                sol['var_approved'].add(app_id)
        
        solutions.append(sol)
    
    # Configure clingo
    ctl = clingo.Control([
        f'-n {num_solutions}',   # number of optimal models to find
        '--opt-mode=optN',        # find optimal, then enumerate
    ])
    
    # Load encoding and data
    ctl.load(encoding_path)
    ctl.load(data_path)
    
    # Ground and solve
    ctl.ground([("base", [])])
    
    print("Solving... (this may take a while for large datasets)")
    result = ctl.solve(on_model=on_model)
    
    print(f"\nSolve result: {result}")
    print(f"Found {len(solutions)} optimal solution(s)")
    
    for i, sol in enumerate(solutions):
        print(f"\n--- Solution {i+1} ---")
        print("Optimal weights:")
        for rule, weight in sorted(sol['weights'].items()):
            print(f"  {rule}: {weight}")
        print(f"Swing approvals: {len(sol['var_approved'])}")
        print(f"Optimization costs: {sol['optimization']}")
    
    return solutions


def compare_with_baseline(solutions: list, baseline_weights: dict):
    """
    Compare ASP-optimized weights with the GA baseline.
    Prints a side-by-side comparison table.
    """
    if not solutions:
        print("No solutions to compare.")
        return
    
    asp_weights = solutions[0]['weights']
    
    print("\n" + "=" * 65)
    print(f"{'Rule':<35} {'GA Baseline':>12} {'ASP Optimal':>12}")
    print("=" * 65)
    
    all_rules = sorted(set(list(baseline_weights.keys()) + list(asp_weights.keys())))
    
    for rule in all_rules:
        ga_w = baseline_weights.get(rule, '—')
        asp_w = asp_weights.get(rule, '—')
        marker = " *" if ga_w != asp_w else ""
        print(f"{rule:<35} {str(ga_w):>12} {str(asp_w):>12}{marker}")
    
    print("=" * 65)
    print("* = weight differs from GA baseline")


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Frankenstein ASP Driver: generate data facts and/or solve'
    )
    parser.add_argument(
        '--input', required=True,
        help='Path to frankenstein_engineered CSV file'
    )
    parser.add_argument(
        '--output', default='data.lp',
        help='Output path for generated ASP facts (default: data.lp)'
    )
    parser.add_argument(
        '--solve', action='store_true',
        help='Run clingo solver after generating facts'
    )
    parser.add_argument(
        '--encoding', default='encoding.lp',
        help='Path to ASP encoding file (default: encoding.lp)'
    )
    parser.add_argument(
        '--num-solutions', type=int, default=1,
        help='Number of optimal solutions to enumerate (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.input}...")
    df = load_and_prepare(args.input)
    
    # Generate facts
    generate_facts(df, args.output)
    
    # Optionally solve
    if args.solve:
        solutions = solve(args.encoding, args.output, args.num_solutions)
        
        # Compare with GA baseline (from Table 1 in the doc)
        ga_baseline = {
            'current_ratio_gt_1_1': 5,
            'leverage_lt_50': 0,
            'npat_positive': 10,
            'equity_gt_75pct_limit': 0,
            'limit_lt_8pct_cos': 0,
            'cash_gt_15pct_limit': 0,
            'current_ratio_gt_2_1': 0,
            'equity_gt_2_3x_limit': 0,
            'nwc_lt_30': 10,
            'inv_period_lt_60': 5,
            'dcp_lt_60': 30,
            'cpp_lt_60': 10,
            'limit_lte_tcl': 20,
            'limit_lte_cos': 10,
            'nwc_lte_60': 0,
        }
        compare_with_baseline(solutions, ga_baseline)