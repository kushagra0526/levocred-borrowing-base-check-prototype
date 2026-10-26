# bbcheck: recompute and check an AI-drafted borrowing base certificate

Levocred's site shows a borrowing-base workflow: a tape goes in, 12 eligibility tests run, an over-cap obligor is excluded, the advance rate is confirmed against the agreement, and a certificate is drafted for CFO signature (https://levocred.com/). The step that matters before signature is whether every line of the draft equals what the tape and the agreement give. This prototype is one way to check that, on synthetic data.

## What it does
Input: a receivables tape (obligor, invoice/due dates, amount, currency, credit memos, affiliate, dispute, country), agreement terms as data (aging basis and days, cross-aging %, concentration cap and rated-obligor caps, advance rate, dilution threshold, contra, commitment, loans), and the draft certificate lines.
It recomputes 15 lines (gross, seven ineligible buckets, eligible, advance rate, dilution reserve, borrowing base, availability) and returns `SIGN`, `FIX` or `HOLD` (availability overstated), with the differing lines and a cause. The cause is named by re-running the engine with each known drafting mistake switched on and keeping the one that reproduces the draft exactly; otherwise `UNEXPLAINED`.

## Results (synthetic deals, one planted mistake each, 20% clean)
Dev: seeds 0-299. Held-out: seeds 1000-1399 with new agreement variants (aging by due date, 25% cross-aging, rated-obligor cap tier, 25% EUR invoices) and two mistakes the diagnosis list does not contain; code and seeds committed before the first run.

| Held-out | tie-out only | bbcheck |
|---|---|---|
| planted mistakes caught (322) | 148 | 322 |
| cause named correctly | - | 239 |
| clean certificates stopped (78) | 0 | 0 |
| availability overstated and signed | $32.41M | $0 |

Per kind, bbcheck caught every kind; the unseen kinds (`rated_cap_missed` 18, `fx_not_converted` 65) came back `UNEXPLAINED` (stopped with the differing lines, cause not named). "Tie-out only" = gross ties to the tape and the certificate's own arithmetic adds up; it misses every rule-level mistake (aging, cross-aging, concentration base, contra, credit memos, dilution, advance rate, affiliates) but catches the fx mistake because its gross no longer ties. Dev: 226/226 caught and named, 0/74 clean stopped, tie-out 103.

## Read this before believing the table
It is near-circular. The "AI draft" is my own engine with one rule switched off, and the checker is the same engine with the rules on, so catching it is close to guaranteed; the held-out set shows only that unseen mistakes are still stopped, not named. Real agreements have clauses this model does not (rolling reserves, progress billing, rated-obligor ladders, eligibility by country lists, period-end vs daily cutoffs), and a real tape has messy fields. The agreement here is already structured data; turning a PDF into those terms is the hard part and is not built. Nothing uses a real tape, agreement or Levocred system.

## Run it (3 commands)
```
pip install pytest
python -m pytest -q tests
python -m bbcheck.run
```
Standard library only. 4 tests.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with Levocred.
