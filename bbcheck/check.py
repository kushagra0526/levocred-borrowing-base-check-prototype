"""Check an AI-drafted borrowing base certificate against the tape and agreement terms."""
from .engine import KNOWN, LINES, compute

TOL = 1.0
CLAUSE = {"gross": "tape tie-out", "inel_credit": "credit memos", "inel_aging": "eligibility: aging", "inel_cross": "eligibility: cross-aging",
          "inel_affiliate": "eligibility: affiliates", "inel_disputed": "eligibility: disputes", "inel_foreign": "eligibility: foreign obligors",
          "inel_contra": "eligibility: contra", "inel_conc": "concentration cap", "eligible": "eligible total", "adv_rate": "advance rate",
          "gross_avail": "advance x eligible", "dil_reserve": "dilution reserve", "bb": "borrowing base", "availability": "availability"}


def same(a, b):
    return all(abs(a[k] - b[k]) <= (1e-9 if k == "adv_rate" else TOL) for k in LINES)


def verify(cert, tape, terms):
    truth = compute(tape, terms)
    diffs = {k: (cert[k], truth[k]) for k in LINES if abs(cert[k] - truth[k]) > (1e-9 if k == "adv_rate" else TOL)}
    if not diffs:
        return {"verdict": "SIGN", "diffs": {}, "cause": None, "overstated": 0.0}
    cause = next((m for m in KNOWN if same(cert, compute(tape, terms, (m,)))), None)
    if cause is None and set(diffs) == {"gross"}:
        cause = "gross_not_tied"
    if cause is None and set(diffs) == {"availability"}:
        cause = "arith"
    over = round(cert["availability"] - truth["availability"], 2)
    return {"verdict": "HOLD" if over > TOL else "FIX", "diffs": {CLAUSE[k]: v for k, v in diffs.items()},
            "cause": cause or "UNEXPLAINED", "overstated": over}


def tie_out(cert, tape, terms):
    """Baseline: gross ties to the tape and the certificate's own arithmetic adds up."""
    g = sum(r["amt"] * terms["fx"][r["ccy"]] for r in tape)
    inel = sum(cert[k] for k in LINES if k.startswith("inel_"))
    ok = (abs(cert["gross"] - g) <= TOL and abs(cert["gross"] - inel - cert["eligible"]) <= TOL
          and abs(cert["adv_rate"] * cert["eligible"] - cert["gross_avail"]) <= TOL
          and abs(cert["gross_avail"] - cert["dil_reserve"] - cert["bb"]) <= TOL
          and abs(min(cert["bb"], terms["commitment"]) - terms["loans"] - cert["availability"]) <= TOL)
    return "SIGN" if ok else "FIX"
