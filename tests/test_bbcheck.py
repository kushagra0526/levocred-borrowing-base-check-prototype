import datetime as dt

from bbcheck import check, engine, gen

D = dt.date
TERMS = {"aging_basis": "invoice", "aging_days": 90, "cross_pct": 0.5, "cap_pct": 0.5, "rated_cap": {}, "adv": 0.85,
         "dilution": 0.05, "dil_thresh": 0.05, "fx": {"USD": 1.0, "EUR": 1.1}, "contra": {}, "commitment": 10**9, "loans": 0}


def inv(i, ob, age, amt, **kw):
    d = engine.AS_OF - dt.timedelta(days=age)
    return dict({"id": i, "obligor": ob, "inv": d, "due": d + dt.timedelta(days=30), "amt": amt, "ccy": "USD", "credit": 0.0,
                 "affiliate": False, "disputed": False, "country": "US"}, **kw)


def test_aging_and_cross_aging():
    tape = [inv("a", "X", 100, 100), inv("b", "X", 10, 100), inv("c", "Y", 10, 100)]
    c = engine.compute(tape, TERMS)
    assert c["inel_aging"] == 100 and c["inel_cross"] == 0  # exactly 50% aged is not over the limit
    c = engine.compute([inv("a", "X", 100, 150), inv("b", "X", 10, 100)], TERMS)
    assert c["inel_aging"] == 150 and c["inel_cross"] == 100


def test_concentration_uses_eligible_not_gross():
    tape = [inv("a", "X", 10, 600), inv("b", "Y", 10, 400), inv("c", "Z", 100, 1000)]
    t = dict(TERMS, cap_pct=0.5)
    assert engine.compute(tape, t)["inel_conc"] == 100  # 600 - 0.5 * 1000
    assert engine.compute(tape, t, ("conc_on_gross",))["inel_conc"] == 0


def test_verify_names_the_mistake_and_passes_a_clean_certificate():
    tape = [inv("a", "X", 10, 600, ccy="EUR"), inv("b", "Y", 10, 400, credit=50.0)]
    clean = engine.compute(tape, TERMS)
    assert check.verify(clean, tape, TERMS)["verdict"] == "SIGN"
    bad = engine.compute(tape, TERMS, ("no_credit",))
    v = check.verify(bad, tape, TERMS)
    assert v["cause"] == "no_credit" and v["verdict"] == "HOLD"


def test_generator_plants_something_that_changes_the_certificate():
    for s in range(20):
        tape, terms, truth, cert, kind = gen.make_case(s)
        assert (kind is None) == (check.verify(cert, tape, terms)["verdict"] == "SIGN")
