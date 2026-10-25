import json
from collections import Counter

from . import check, gen


def score(seeds, held):
    t = Counter()
    per = {}
    for s in seeds:
        tape, terms, truth, cert, kind = gen.make_case(s, held)
        v, b = check.verify(cert, tape, terms), check.tie_out(cert, tape, terms)
        over = max(0.0, cert["availability"] - truth["availability"])
        if kind is None:
            t["clean"] += 1
            t["clean_flagged_mine"] += v["verdict"] != "SIGN"
            t["clean_flagged_tieout"] += b != "SIGN"
            continue
        t["planted"] += 1
        t["caught_mine"] += v["verdict"] != "SIGN"
        t["caught_tieout"] += b != "SIGN"
        t["named_mine"] += v["cause"] == kind
        t["unexplained_mine"] += v["cause"] == "UNEXPLAINED"
        t["over_total"] += over
        t["over_passed_tieout"] += over if b == "SIGN" else 0
        t["over_passed_mine"] += over if v["verdict"] == "SIGN" else 0
        p = per.setdefault(kind, Counter())
        p["n"] += 1
        p["caught"] += v["verdict"] != "SIGN"
        p["named"] += v["cause"] == kind
        p["tieout"] += b != "SIGN"
    return {"totals": {k: round(x, 2) if isinstance(x, float) else x for k, x in t.items()}, "by_kind": {k: dict(v) for k, v in per.items()}}


def main():
    out = {"dev": score(range(0, 300), False), "held_out": score(range(1000, 1400), True)}
    json.dump(out, open("out/result.json", "w"), indent=1)
    for k, v in out.items():
        print(k, json.dumps(v["totals"]))
        for kind, c in sorted(v["by_kind"].items()):
            print("   ", kind, c)


if __name__ == "__main__":
    main()
