"""Synthetic ABL deals (tape + terms) and simulated AI-drafted certificates with a planted mistake."""
import datetime as dt
import random

from .engine import AS_OF, KNOWN, compute

DEV_KINDS = KNOWN + ["gross_not_tied", "arith"]
HELD_EXTRA = ["rated_cap_missed", "fx_not_converted"]  # not in the checker's diagnosis list


def make_deal(seed, held_out=False):
    rng = random.Random(seed)
    n_ob = rng.randint(10, 20)
    obs = [f"OB-{i:03d}" for i in range(n_ob)]
    w = [1 / (i + 1) ** 1.1 for i in range(n_ob)]
    terms = {
        "aging_basis": rng.choice(["invoice", "due"]) if held_out else "invoice",
        "aging_days": rng.choice([60, 90]),
        "cross_pct": rng.choice([0.25, 0.5]) if held_out else 0.5,
        "cap_pct": rng.choice([0.10, 0.15, 0.20]),
        "rated_cap": {},
        "adv": rng.choice([0.80, 0.85]),
        "dilution": round(rng.uniform(0.02, 0.09), 3),
        "dil_thresh": 0.05,
        "fx": {"USD": 1.0, "EUR": round(rng.uniform(1.05, 1.12), 4)},
        "contra": {},
        "commitment": 0, "loans": 0,
    }
    if held_out:
        terms["rated_cap"] = {obs[0]: terms["cap_pct"] + 0.05}
    aff = rng.choice(obs[1:]) if rng.random() < 0.5 else None
    tape = []
    for i in range(rng.randint(120, 260)):
        o = rng.choices(obs, w)[0]
        age = rng.choice([rng.randint(5, 80)] * 6 + [rng.randint(85, 140)])
        if o == obs[3]:
            age = rng.randint(70, 130)  # an obligor with many old invoices (cross-aging)
        inv = AS_OF - dt.timedelta(days=age)
        due = inv + dt.timedelta(days=rng.choice([30, 45, 60]))
        eur = rng.random() < (0.25 if held_out else 0.10)
        amt = round(rng.lognormvariate(10.2, 0.8), 2)
        tape.append({"id": f"INV-{i:04d}", "obligor": o, "inv": inv, "due": due, "amt": amt,
                     "ccy": "EUR" if eur else "USD", "credit": round(amt * rng.uniform(0.02, 0.2), 2) if rng.random() < 0.06 else 0.0,
                     "affiliate": o == aff, "disputed": rng.random() < 0.02,
                     "country": rng.choice(["US"] * 14 + ["CA", "DE"])})
    for o in rng.sample(obs[:6], 2):
        terms["contra"][o] = round(rng.uniform(20_000, 150_000), 2)
    base = compute(tape, terms)
    terms["commitment"] = round(base["bb"] * rng.choice([0.9, 1.2, 2.0]), -3)
    terms["loans"] = round(min(base["bb"], terms["commitment"]) * rng.uniform(0.5, 0.85), -3)
    return tape, terms


def draft(tape, terms, kind, rng):
    """The certificate an AI drafter would produce with one mistake; lines dict in the same shape as compute()."""
    if kind in KNOWN:
        return compute(tape, terms, (kind,))
    if kind == "rated_cap_missed":
        return compute(tape, dict(terms, rated_cap={}))
    if kind == "fx_not_converted":
        return compute(tape, dict(terms, fx={"USD": 1.0, "EUR": 1.0}))
    c = compute(tape, terms)
    if kind == "gross_not_tied":  # the certificate's gross double-counts a few tape rows
        extra = sum(r["amt"] * terms["fx"][r["ccy"]] for r in rng.sample(tape, 3))
        c["gross"] = round(c["gross"] + extra, 2)
        return c
    if kind == "arith":  # transposed digits in the final availability
        s = f"{int(abs(c['availability']))}"
        if len(s) > 3:
            s = s[:-3] + s[-2] + s[-3] + s[-1]
            c["availability"] = float(s) * (1 if c["availability"] >= 0 else -1)
        return c
    raise ValueError(kind)


def make_case(seed, held_out=False):
    rng = random.Random(seed * 7 + 1)
    tape, terms = make_deal(seed, held_out)
    truth = compute(tape, terms)
    kinds = DEV_KINDS + (HELD_EXTRA if held_out else [])
    kind, cert = None, dict(truth)
    if rng.random() > 0.2:
        for k in rng.sample(kinds, len(kinds)):
            c = draft(tape, terms, k, rng)
            if abs(c["availability"] - truth["availability"]) > 1 or c["gross"] != truth["gross"]:
                kind, cert = k, c
                break
    return tape, terms, truth, cert, kind
