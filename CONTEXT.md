# Bond Term Sheet Extractor

Pulls pricing terms for investment-grade corporate bond deals out of SEC filings and builds a DCM comps table where every value points back to the exact text it came from.

## Filings and deals

**Deal**:
One bond offering by one issuer on one trade date, made up of one or more tranches.
_Avoid_: Issuance, offering (when you mean the whole deal)

**Tranche**:
One series of notes inside a deal, with its own coupon, maturity and CUSIP. Identified by its CUSIP.
_Avoid_: Note, bond, series

**Deal-level term**:
A term shared by every tranche in a deal, such as issuer, ratings, trade date, settlement date and bookrunners.
_Avoid_: Global field, common field

**Term sheet**:
The final pricing term sheet filed as Form FWP. The primary input.
_Avoid_: FWP (in prose), pricing supplement

**Prospectus supplement**:
The long-form 424B2/424B5 filing for a deal. Out of scope for scoring.

## Output

**Comps table**:
One row per tranche across one or more deals, with normalised pricing terms, built for side-by-side comparison.
_Avoid_: Comparables table, output table

**Not found**:
The value reported when a field is not stated in the filing. Preferred over any guess.

## Trust and evaluation

**Grounded**:
A value whose source span is an exact match in the filing and whose filing text equals the extracted text. Any looser alignment is not grounded.
_Avoid_: Anchored, verified

**Not-in-source**:
An extracted value that does not appear anywhere in the filing.
_Avoid_: Hallucination

**Answer key**:
Hand-keyed correct values for every tranche in a benchmark deal, written before the extractor is run on that deal.
_Avoid_: Ground truth, gold labels

**Benchmark**:
The set of deals that have an answer key. The only deals reported numbers come from.
_Avoid_: Test set, eval set

**Field accuracy**:
The share of answer-key fields where the extracted value equals the key after normalisation, with tranches matched by CUSIP. The headline number.
_Avoid_: Accuracy (unqualified), score

**Leakage**:
Any benchmark value that appears in the extraction prompt or its examples. A benchmark with leakage is invalid.
