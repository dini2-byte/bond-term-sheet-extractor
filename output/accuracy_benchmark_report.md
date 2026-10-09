Field accuracy: 98.3% (344/350 fields, 4 deals, 25 tranches)
Grounded: 55.5% (186/335 extracted fields)
Not-in-source: 0.0% (0/335 extracted fields)
Unmatched extracted tranches: 2

### Scoring changes after the first run

| Date       | Change                                                                                                                             | Headline Before                                              |
|:-----------|:-----------------------------------------------------------------------------------------------------------------------------------|:-------------------------------------------------------------|
| 2026-10-08 | CUSIP cell keeps only the 9-character CUSIP; it had kept the ISIN too, which failed every CUSIP and broke tranche pairing in GOOGL | Field accuracy: 88.0% (308/350 fields, 4 deals, 25 tranches) |

### Per-Deal Breakdown

| Deal                           |   Tranches |   Fields |   Correct |   Accuracy (%) |   Grounded (%) |   Unmatched Extracted Tranches |
|:-------------------------------|-----------:|---------:|----------:|---------------:|---------------:|-------------------------------:|
| AAPL_FWP_TermSheet_2025-05-06  |          4 |       56 |        56 |          100   |           92.9 |                              0 |
| MSFT_FWP_TermSheet_2017-01-31  |          7 |       98 |        98 |          100   |           32.2 |                              0 |
| ORCL_FWP_TermSheet_2025-09-24  |          6 |       84 |        78 |           92.9 |          100   |                              0 |
| GOOGL_FWP_TermSheet_2026-08-07 |          8 |      112 |       112 |          100   |           24.3 |                              2 |

### Per-Field Breakdown

| Field              |   Total |   Correct |   Grounded |   Accuracy (%) |   Grounded (%) |
|:-------------------|--------:|----------:|-----------:|---------------:|---------------:|
| Benchmark Treasury |      25 |        25 |         14 |            100 |             56 |
| CUSIP              |      25 |        25 |         18 |            100 |             72 |
| Coupon (%)         |      25 |        25 |         13 |            100 |             52 |
| Day Count          |      25 |        25 |         11 |            100 |             44 |
| Issue Price        |      25 |        25 |         10 |            100 |             40 |
| Issuer             |      25 |        25 |         18 |            100 |             72 |
| Maturity Date      |      25 |        25 |         12 |            100 |             48 |
| Par Call Date      |      25 |        19 |          4 |             76 |             16 |
| Principal ($M)     |      25 |        25 |         12 |            100 |             48 |
| Ratings            |      25 |        25 |         18 |            100 |             72 |
| Settlement Date    |      25 |        25 |         13 |            100 |             52 |
| Spread (bps)       |      25 |        25 |         14 |            100 |             56 |
| Trade Date         |      25 |        25 |         17 |            100 |             68 |
| Yield (%)          |      25 |        25 |         12 |            100 |             48 |

### Discrepancy Log

| Deal                          | Tranche               | Field         | Expected        | Extracted   |
|:------------------------------|:----------------------|:--------------|:----------------|:------------|
| ORCL_FWP_TermSheet_2025-09-24 | 4.450% Notes due 2030 | Par Call Date | August 26, 2030 |             |
| ORCL_FWP_TermSheet_2025-09-24 | 4.800% Notes due 2032 | Par Call Date | July 26, 2032   |             |
| ORCL_FWP_TermSheet_2025-09-24 | 5.200% Notes due 2035 | Par Call Date | June 26, 2035   |             |
| ORCL_FWP_TermSheet_2025-09-24 | 5.875% Notes due 2045 | Par Call Date | March 26, 2045  |             |
| ORCL_FWP_TermSheet_2025-09-24 | 5.950% Notes due 2055 | Par Call Date | March 26, 2055  |             |
| ORCL_FWP_TermSheet_2025-09-24 | 6.100% Notes due 2065 | Par Call Date | March 26, 2065  |             |

### Extraction Attempts

AAPL: produced 2026-09-24 before the attempt log existed

| Deal                           | Timestamp            | Model                 | Outcome   | Error   |
|:-------------------------------|:---------------------|:----------------------|:----------|:--------|
| MSFT_FWP_TermSheet_2017-01-31  | 2026-10-08T01:48:36Z | gemini-3.5-flash-lite | ok        |         |
| ORCL_FWP_TermSheet_2025-09-24  | 2026-10-08T01:49:02Z | gemini-3.5-flash-lite | ok        |         |
| GOOGL_FWP_TermSheet_2026-08-07 | 2026-10-08T01:51:09Z | gemini-3.5-flash-lite | ok        |         |
| AAPL_FWP_TermSheet_2025-05-06  | 2026-10-09T16:12:21Z | gemini-3.5-flash-lite | ok        |         |
| MSFT_FWP_TermSheet_2017-01-31  | 2026-10-09T16:12:34Z | gemini-3.5-flash-lite | ok        |         |
| ORCL_FWP_TermSheet_2025-09-24  | 2026-10-09T16:12:44Z | gemini-3.5-flash-lite | ok        |         |
| GOOGL_FWP_TermSheet_2026-08-07 | 2026-10-09T16:13:00Z | gemini-3.5-flash-lite | ok        |         |
