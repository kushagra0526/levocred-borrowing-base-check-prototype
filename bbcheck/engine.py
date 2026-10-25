"""Borrowing base recomputation from a receivables tape and agreement terms (data).

Lines are in USD. Each invoice amount is assigned to the first ineligible
bucket it hits, so nothing is counted twice. `modes` switch one rule off to
reproduce a known drafting mistake (used for diagnosis, never for the check).
"""
import datetime as dt

AS_OF = dt.date(2026, 6, 30)
LINES = ["gross", "inel_credit", "inel_aging", "inel_cross", "inel_affiliate", "inel_disputed", "inel_foreign",
         "inel_contra", "inel_conc", "eligible", "adv_rate", "gross_avail", "dil_reserve", "bb", "availability"]
KNOWN = ["aging_basis", "no_cross", "conc_on_gross", "no_contra", "no_dil", "adv90", "no_credit", "affiliate_in"]


def compute(tape, terms, modes=()):
    fx = terms["fx"]
    inel = dict.fromkeys(LINES, 0.0)
    elig_by_ob, aged_by_ob, gross_by_ob = {}, {}, {}
    basis = "due" if (terms["aging_basis"] == "invoice") == ("aging_basis" in modes) else "invoice"
    days = terms["aging_days"]

    def aged(r):
        d = r["inv"] if basis == "invoice" else r["due"]
        return (AS_OF - d).days > days

    for r in tape:
        usd = r["amt"] * fx[r["ccy"]]
        gross_by_ob[r["obligor"]] = gross_by_ob.get(r["obligor"], 0) + usd
        if aged(r):
            aged_by_ob[r["obligor"]] = aged_by_ob.get(r["obligor"], 0) + usd
        inel["gross"] += usd
    cross = {o for o, a in aged_by_ob.items() if "no_cross" not in modes and a > terms["cross_pct"] * gross_by_ob[o]}
    for r in tape:
        rem = r["amt"] * fx[r["ccy"]]
        if "no_credit" not in modes:
            c = min(r["credit"] * fx[r["ccy"]], rem)
            inel["inel_credit"] += c
            rem -= c
        for key, hit in (("inel_aging", aged(r)), ("inel_cross", r["obligor"] in cross),
                         ("inel_affiliate", r["affiliate"] and "affiliate_in" not in modes),
                         ("inel_disputed", r["disputed"]), ("inel_foreign", r["country"] not in ("US", "CA"))):
            if hit:
                inel[key] += rem
                rem = 0
                break
        elig_by_ob[r["obligor"]] = elig_by_ob.get(r["obligor"], 0) + rem
    if "no_contra" not in modes:
        for o, pay in terms["contra"].items():
            c = min(pay, elig_by_ob.get(o, 0))
            inel["inel_contra"] += c
            elig_by_ob[o] -= c
    pre = sum(elig_by_ob.values())
    denom = inel["gross"] if "conc_on_gross" in modes else pre
    for o, e in elig_by_ob.items():
        cap = terms["rated_cap"].get(o, terms["cap_pct"])
        x = max(0.0, e - cap * denom)
        inel["inel_conc"] += x
        elig_by_ob[o] = e - x
    inel["eligible"] = sum(elig_by_ob.values())
    inel["adv_rate"] = 0.90 if "adv90" in modes else terms["adv"]
    inel["gross_avail"] = inel["adv_rate"] * inel["eligible"]
    inel["dil_reserve"] = 0.0 if "no_dil" in modes else max(0.0, terms["dilution"] - terms["dil_thresh"]) * inel["eligible"]
    inel["bb"] = inel["gross_avail"] - inel["dil_reserve"]
    inel["availability"] = min(inel["bb"], terms["commitment"]) - terms["loans"]
    return {k: round(v, 2) if k != "adv_rate" else v for k, v in inel.items()}
