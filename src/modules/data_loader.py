import json
from pathlib import Path


def load_applications(json_path):
    with open(json_path) as f:
        return json.load(f)


def to_ceiling_facts(app):
    req = int(app["RequestedAmount"])
    indiv = int(app["DebtorIndividualCeilingLimit"])
    group = int(app["DebtorGroupCeilingLimit"])
    return f"app_data({req}, {indiv}, {group})."


def to_credit_facts(app):
    facts = []
    facts.append(f"credit_scores({int(app['DelphiScore'])}).")
    facts.append(f"enquiries({int(app['EnquiriesLast3Months'])}, {int(app['EnquiriesLast12Months'])}).")

    has_claims = 1 if app.get("ClaimStatus") else 0
    facts.append(f"claims({has_claims}).")

    return "\n".join(facts)


def to_finance_facts(app_id, app):
    req = int(app["RequestedAmount"])
    npat = int(app.get("PricingFinancialsNetProfitAfterTax") or 0)
    trade_recv = int(app.get("PricingFinancialsCA_TradeAndOtherReceivables") or 0)
    revenue = int(app.get("PricingFinancialsRevenue") or 0)
    inventories = int(app.get("PricingFinancialsCA_Inventories") or 0)
    current_assets = int(app.get("PricingFinancialsCA_TotalCurrentAssets") or 0)
    current_liab = int(app.get("PricingFinancialsCL_TotalCurrentLiabilities") or 0)
    total_assets = int(app.get("PricingFinancialsTotalAssets") or 0)
    total_liab = int(app.get("PricingFinancialsTotalLiabilities") or 0)

    debtor_days = int((trade_recv / revenue) * 365) if revenue > 0 else 999


    cash = current_assets - inventories - trade_recv


    equity = total_assets - total_liab

    facts = [
        f"app({app_id}).",
        f"app_data({app_id}, {equity}, {req}).",
        f"raw_financials({app_id}, limit_requested, {req}).",
        f"raw_financials({app_id}, npat, {npat}).",
        f"raw_financials({app_id}, debtor_days, {debtor_days}).",
        f"raw_financials({app_id}, cash, {cash}).",
        f"raw_financials({app_id}, current_assets, {current_assets}).",
        f"raw_financials({app_id}, current_liab, {current_liab}).",
    ]
    return "\n".join(facts)


def to_optimization_facts(apps):
    """Build the full set of facts needed by the optimization encoding.

    This pre-evaluates the financial rules in Python (mirroring financial.lp)
    so the optimizer can work with app_passed_rule/2 atoms.
    """
    lines = []

    for idx, app in enumerate(apps, start=1):
        app_id = idx
        req = int(app["RequestedAmount"])
        npat = int(app.get("PricingFinancialsNetProfitAfterTax") or 0)
        trade_recv = int(app.get("PricingFinancialsCA_TradeAndOtherReceivables") or 0)
        revenue = int(app.get("PricingFinancialsRevenue") or 0)
        inventories = int(app.get("PricingFinancialsCA_Inventories") or 0)
        current_assets = int(app.get("PricingFinancialsCA_TotalCurrentAssets") or 0)
        current_liab = int(app.get("PricingFinancialsCL_TotalCurrentLiabilities") or 0)
        total_assets = int(app.get("PricingFinancialsTotalAssets") or 0)
        total_liab = int(app.get("PricingFinancialsTotalLiabilities") or 0)
        claim_amount = int(app.get("amnt") or 0)

        debtor_days = int((trade_recv / revenue) * 365) if revenue > 0 else 999
        cash = current_assets - inventories - trade_recv
        equity = total_assets - total_liab

        lines.append(f"app({app_id}).")
        lines.append(f"app_data({app_id}, {equity}, {req}).")
        lines.append(f"app_financials({app_id}, {claim_amount}, {req}).")

    
        if npat > 0:
            lines.append(f"app_passed_rule({app_id}, npat_positive).")
        if debtor_days < 60:
            lines.append(f"app_passed_rule({app_id}, debtor_collection_under_60).")
        if (cash * 100) > (req * 15):
            lines.append(f"app_passed_rule({app_id}, cash_15_percent_limit).")
        if (current_assets * 10) > (current_liab * 11):
            lines.append(f"app_passed_rule({app_id}, current_ratio_over_1_1).")

    return "\n".join(lines)
