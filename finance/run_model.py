#!/usr/bin/env python3
"""Modelo financiero reproducible GameMetrics.

Uso:
  python finance/run_model.py
  python finance/run_model.py --assumptions finance/model_assumptions.json --out finance/model_output.json

Todos los números salen de supuestos explícitos en JSON — no son datos reales de la empresa.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def money(x: float) -> float:
    return round(float(x), 2)


def run_scenario(users: int, a: dict) -> dict:
    conv = a["conversion"]
    plat = a["platform"]
    cat = a["catalog"]
    opex_map = a["opex_monthly_by_scale"]
    key = str(users)
    opex = opex_map[key]

    mau = int(round(users * conv["mau_share_of_registered"]))
    buyers = int(round(mau * conv["buyer_share_of_mau"]))
    orders = buyers * conv["orders_per_buyer_per_month"]
    gmv = money(orders * conv["aov_usd"])
    games = int(round((users / 10000) * cat["games_per_10k_users"]))

    refunds = money(gmv * plat["refund_rate"])
    chargebacks = money(gmv * plat["chargeback_rate"])
    agr = money(gmv - refunds - chargebacks)

    platform_revenue = money(agr * plat["take_rate"])
    publisher_payout = money(agr * (1 - plat["take_rate"]))

    # PSP cost on successful + refunded volume (simplified assumption)
    psp_variable = money(gmv * plat["payment_processing_rate"])
    psp_fixed = money(orders * plat["payment_processing_fixed_usd"])
    cb_fees = money((gmv * plat["chargeback_rate"] / max(conv["aov_usd"], 0.01)) * plat["chargeback_fee_usd_assumption"])
    processing_cost = money(psp_variable + psp_fixed + cb_fees)

    contribution = money(platform_revenue - processing_cost)
    opex_total = money(sum(opex.values()))
    operating = money(contribution - opex_total)
    contrib_margin = round(contribution / platform_revenue, 4) if platform_revenue else 0.0
    op_margin = round(operating / platform_revenue, 4) if platform_revenue else 0.0

    return {
        "registered_users": users,
        "active_users_mau": mau,
        "buyers": buyers,
        "conversion_buyer_of_mau": conv["buyer_share_of_mau"],
        "orders_per_month": round(orders, 2),
        "games_estimate": games,
        "aov_usd": conv["aov_usd"],
        "gmv_usd": gmv,
        "refunds_usd": refunds,
        "chargebacks_usd": chargebacks,
        "adjusted_gross_revenue_usd": agr,
        "take_rate": plat["take_rate"],
        "platform_revenue_usd": platform_revenue,
        "publisher_payout_usd": publisher_payout,
        "payment_processing_usd": processing_cost,
        "contribution_usd": contribution,
        "contribution_margin": contrib_margin,
        "opex": opex,
        "opex_total_usd": opex_total,
        "operating_result_usd": operating,
        "operating_margin_on_platform_rev": op_margin,
        "assumption": True,
    }


def break_even(a: dict, scale_key: str = "100000") -> dict:
    """GMV needed so contribution covers opex at a given scale's cost base."""
    plat = a["platform"]
    conv = a["conversion"]
    opex = a["opex_monthly_by_scale"][scale_key]
    opex_total = sum(opex.values())

    # contribution ≈ GMV * (1 - refund - cb) * take - GMV*psp_rate - orders*fixed
    # Approximate orders ≈ GMV / AOV
    net_factor = (1 - plat["refund_rate"] - plat["chargeback_rate"]) * plat["take_rate"]
    psp = plat["payment_processing_rate"]
    fixed_per_gmv = plat["payment_processing_fixed_usd"] / max(conv["aov_usd"], 0.01)
    cb_fee_per_gmv = (plat["chargeback_rate"] / max(conv["aov_usd"], 0.01)) * plat["chargeback_fee_usd_assumption"]
    unit_contrib = net_factor - psp - fixed_per_gmv - cb_fee_per_gmv
    if unit_contrib <= 0:
        return {"error": "contribution per GMV <= 0 under assumptions", "assumption": True}

    gmv_be = money(opex_total / unit_contrib)
    buyers_be = int(round(gmv_be / (conv["aov_usd"] * conv["orders_per_buyer_per_month"])))
    mau_be = int(round(buyers_be / conv["buyer_share_of_mau"]))
    users_be = int(round(mau_be / conv["mau_share_of_registered"]))
    sales_be = int(round(gmv_be / conv["aov_usd"]))

    return {
        "scale_cost_base": scale_key,
        "opex_monthly_usd": money(opex_total),
        "contribution_per_gmv_dollar": round(unit_contrib, 4),
        "gmv_break_even_usd": gmv_be,
        "sales_break_even": sales_be,
        "buyers_break_even": buyers_be,
        "mau_break_even": mau_be,
        "registered_users_break_even": users_be,
        "assumption": True,
        "formula": "GMV_be = opex / ((1-r-cb)*take - psp - fixed/AOV - cb_fees/AOV)",
    }


def unit_economics(a: dict) -> dict:
    ue = a["unit_economics_inputs"]
    plat = a["platform"]
    conv = a["conversion"]
    take = plat["take_rate"]
    # ARPU on registered: monthly platform rev / users (use 100k scenario as reference)
    ref = run_scenario(100_000, a)
    arpu = money(ref["platform_revenue_usd"] / max(ref["registered_users"], 1))
    arppu = money(ref["platform_revenue_usd"] / max(ref["buyers"], 1))
    ltv = money(arppu * ue["avg_buyer_lifetime_months"] * ue["gross_margin_on_take_after_psp"])
    cac = ue["cac_usd_assumption"]
    return {
        "definitions": {
            "CAC": "Cost to acquire one paying user (assumption until marketing attribution exists)",
            "LTV": "ARPPU * lifetime_months * gross_margin_on_take_after_psp",
            "ARPU": "Platform revenue / registered users (monthly)",
            "ARPPU": "Platform revenue / buyers (monthly)",
            "TakeRate": "platform_fee / AGR",
            "GrossMargin": "gross_margin_on_take_after_psp assumption",
            "ContributionMargin": "contribution / platform_revenue",
            "Churn": "monthly_churn_assumption",
            "Conversion": "buyer_share_of_mau",
            "AOV": "average order value",
            "RefundRate": "refunds / GMV",
            "ChargebackRate": "chargebacks / GMV",
        },
        "formulas": {
            "CAC": "marketing_spend / new_buyers",
            "LTV": "ARPPU * avg_buyer_lifetime_months * gross_margin_on_take_after_psp",
            "ARPU": "platform_revenue / registered_users",
            "ARPPU": "platform_revenue / buyers",
            "TakeRate": "platform_fee / adjusted_gross_revenue",
            "ContributionMargin": "(platform_revenue - processing) / platform_revenue",
        },
        "computed_from_assumptions_ref_100k": {
            "CAC_usd": cac,
            "LTV_usd": ltv,
            "LTV_CAC_ratio": round(ltv / cac, 2) if cac else None,
            "ARPU_usd": arpu,
            "ARPPU_usd": arppu,
            "take_rate": take,
            "gross_margin_assumption": ue["gross_margin_on_take_after_psp"],
            "contribution_margin": ref["contribution_margin"],
            "churn_monthly_assumption": ue["monthly_churn_assumption"],
            "conversion_buyer_of_mau": conv["buyer_share_of_mau"],
            "AOV_usd": conv["aov_usd"],
            "refund_rate": plat["refund_rate"],
            "chargeback_rate": plat["chargeback_rate"],
        },
        "required_fields_for_live_metrics": [
            "marketing_spend",
            "new_buyers",
            "platform_revenue",
            "registered_users",
            "buyers",
            "gmv",
            "refunds",
            "chargebacks",
            "processing_fees",
        ],
        "assumption": True,
    }


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--assumptions", default=str(root / "model_assumptions.json"))
    parser.add_argument("--out", default=str(root / "model_output.json"))
    args = parser.parse_args()

    a = json.loads(Path(args.assumptions).read_text(encoding="utf-8"))
    scenarios = [run_scenario(u, a) for u in a["scenarios_users"]]
    out = {
        "disclaimer": "ASSUMPTIONS ONLY — not audited financials",
        "scenarios": scenarios,
        "break_even": {
            "at_10k_cost_base": break_even(a, "10000"),
            "at_100k_cost_base": break_even(a, "100000"),
            "at_1m_cost_base": break_even(a, "1000000"),
        },
        "unit_economics": unit_economics(a),
    }
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    # CSV summary
    csv_path = Path(args.out).with_suffix(".csv")
    lines = [
        "users,mau,buyers,gmv,platform_revenue,opex,operating_result,assumption"
    ]
    for s in scenarios:
        lines.append(
            f"{s['registered_users']},{s['active_users_mau']},{s['buyers']},"
            f"{s['gmv_usd']},{s['platform_revenue_usd']},{s['opex_total_usd']},"
            f"{s['operating_result_usd']},true"
        )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"Wrote {csv_path}")
    be = out["break_even"]["at_100k_cost_base"]
    print(
        f"Break-even @100k cost base (ASSUMPTION): GMV~${be.get('gmv_break_even_usd')} "
        f"users~{be.get('registered_users_break_even')}"
    )


if __name__ == "__main__":
    main()
