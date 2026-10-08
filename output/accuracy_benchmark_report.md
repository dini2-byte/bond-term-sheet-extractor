Field accuracy: 88.0% (308/350 fields, 4 deals, 25 tranches)
Grounded: 55.8% (183/328 extracted fields)
Not-in-source: 0.0% (0/328 extracted fields)
Unmatched extracted tranches: 2

### Per-Deal Breakdown

| Deal                           |   Tranches |   Fields |   Correct |   Accuracy (%) |   Grounded (%) |   Unmatched Extracted Tranches |
|:-------------------------------|-----------:|---------:|----------:|---------------:|---------------:|-------------------------------:|
| AAPL_FWP_TermSheet_2025-05-06  |          4 |       56 |        56 |          100   |           92.9 |                              0 |
| MSFT_FWP_TermSheet_2017-01-31  |          7 |       98 |        91 |           92.9 |           32.2 |                              0 |
| ORCL_FWP_TermSheet_2025-09-24  |          6 |       84 |        72 |           85.7 |          100   |                              0 |
| GOOGL_FWP_TermSheet_2026-08-07 |          8 |      112 |        89 |           79.5 |           23.1 |                              2 |

### Per-Field Breakdown

| Field              |   Total |   Correct |   Grounded |   Accuracy (%) |   Grounded (%) |
|:-------------------|--------:|----------:|-----------:|---------------:|---------------:|
| Benchmark Treasury |      25 |        23 |         13 |             92 |             52 |
| CUSIP              |      25 |         4 |         19 |             16 |             76 |
| Coupon (%)         |      25 |        23 |         12 |             92 |             48 |
| Day Count          |      25 |        23 |         11 |             92 |             44 |
| Issue Price        |      25 |        23 |         10 |             92 |             40 |
| Issuer             |      25 |        25 |         18 |            100 |             72 |
| Maturity Date      |      25 |        25 |         12 |            100 |             48 |
| Par Call Date      |      25 |        18 |          4 |             72 |             16 |
| Principal ($M)     |      25 |        23 |         12 |             92 |             48 |
| Ratings            |      25 |        25 |         18 |            100 |             72 |
| Settlement Date    |      25 |        25 |         13 |            100 |             52 |
| Spread (bps)       |      25 |        23 |         13 |             92 |             52 |
| Trade Date         |      25 |        25 |         17 |            100 |             68 |
| Yield (%)          |      25 |        23 |         11 |             92 |             44 |

### Discrepancy Log

| Deal                           | Tranche               | Field              | Expected                 | Extracted                 |
|:-------------------------------|:----------------------|:-------------------|:-------------------------|:--------------------------|
| MSFT_FWP_TermSheet_2017-01-31  | 1.850% Notes due 2020 | CUSIP              | 594918BV5                | 594918 BV5 / US594918BV54 |
| MSFT_FWP_TermSheet_2017-01-31  | 2.400% Notes due 2022 | CUSIP              | 594918BW3                | 594918 BW3 / US594918BW38 |
| MSFT_FWP_TermSheet_2017-01-31  | 2.875% Notes due 2024 | CUSIP              | 594918BX1                | 594918 BX1 / US594918BX11 |
| MSFT_FWP_TermSheet_2017-01-31  | 3.300% Notes due 2027 | CUSIP              | 594918BY9                | 594918 BY9 / US594918BY93 |
| MSFT_FWP_TermSheet_2017-01-31  | 4.100% Notes due 2037 | CUSIP              | 594918BZ6                | 594918 BZ6 / US594918BZ68 |
| MSFT_FWP_TermSheet_2017-01-31  | 4.250% Notes due 2047 | CUSIP              | 594918CA0                | 594918 CA0 / US594918CA09 |
| MSFT_FWP_TermSheet_2017-01-31  | 4.500% Notes due 2057 | CUSIP              | 594918CB8                | 594918 CB8 / US594918CB81 |
| ORCL_FWP_TermSheet_2025-09-24  | 4.450% Notes due 2030 | Par Call Date      | August 26, 2030          |                           |
| ORCL_FWP_TermSheet_2025-09-24  | 4.450% Notes due 2030 | CUSIP              | 68389XDH5                | 68389XDH5 / US68389XDH52  |
| ORCL_FWP_TermSheet_2025-09-24  | 4.800% Notes due 2032 | Par Call Date      | July 26, 2032            |                           |
| ORCL_FWP_TermSheet_2025-09-24  | 4.800% Notes due 2032 | CUSIP              | 68389XDK8                | 68389XDK8 / US68389XDK81  |
| ORCL_FWP_TermSheet_2025-09-24  | 5.200% Notes due 2035 | Par Call Date      | June 26, 2035            |                           |
| ORCL_FWP_TermSheet_2025-09-24  | 5.200% Notes due 2035 | CUSIP              | 68389XDM4                | 68389XDM4 / US68389XDM48  |
| ORCL_FWP_TermSheet_2025-09-24  | 5.875% Notes due 2045 | Par Call Date      | March 26, 2045           |                           |
| ORCL_FWP_TermSheet_2025-09-24  | 5.875% Notes due 2045 | CUSIP              | 68389XDP7                | 68389XDP7 / US68389XDP78  |
| ORCL_FWP_TermSheet_2025-09-24  | 5.950% Notes due 2055 | Par Call Date      | March 26, 2055           |                           |
| ORCL_FWP_TermSheet_2025-09-24  | 5.950% Notes due 2055 | CUSIP              | 68389XDR3                | 68389XDR3 / US68389XDR35  |
| ORCL_FWP_TermSheet_2025-09-24  | 6.100% Notes due 2065 | Par Call Date      | March 26, 2065           |                           |
| ORCL_FWP_TermSheet_2025-09-24  | 6.100% Notes due 2065 | CUSIP              | 68389XDT9                | 68389XDT9 / US68389XDT90  |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.500% Notes due 2028 | Principal ($M)     | 1250.0                   | 750.0                     |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.500% Notes due 2028 | Coupon (%)         | 4.5                      | 0.44                      |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.500% Notes due 2028 | Issue Price        | 99.858                   | 100.0                     |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.500% Notes due 2028 | Yield (%)          | 4.575                    |                           |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.500% Notes due 2028 | Spread (bps)       | 33                       |                           |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.500% Notes due 2028 | Benchmark Treasury | 4.250% due July 31, 2028 |                           |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.500% Notes due 2028 | Day Count          | 30/360                   | Actual/360                |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.500% Notes due 2028 | CUSIP              | 02079KCL9                | 02079K CM7 / US02079KCM71 |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | Principal ($M)     | 2000.0                   | 500.0                     |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | Coupon (%)         | 4.625                    | 0.6                       |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | Issue Price        | 99.698                   | 100.0                     |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | Yield (%)          | 4.734                    |                           |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | Spread (bps)       | 43                       |                           |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | Benchmark Treasury | 4.125% due July 15, 2029 |                           |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | Day Count          | 30/360                   | Actual/360                |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | Par Call Date      | July 10, 2029            |                           |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.625% Notes due 2029 | CUSIP              | 02079KCN5                | 02079K CP0 / US02079KCP03 |
| GOOGL_FWP_TermSheet_2026-08-07 | 4.875% Notes due 2031 | CUSIP              | 02079KCQ8                | 02079K CQ8 / US02079KCQ85 |
| GOOGL_FWP_TermSheet_2026-08-07 | 5.200% Notes due 2033 | CUSIP              | 02079KCR6                | 02079K CR6 / US02079KCR68 |
| GOOGL_FWP_TermSheet_2026-08-07 | 5.450% Notes due 2036 | CUSIP              | 02079KCS4                | 02079K CS4 / US02079KCS42 |
| GOOGL_FWP_TermSheet_2026-08-07 | 6.250% Notes due 2046 | CUSIP              | 02079KCT2                | 02079K CT2 / US02079KCT25 |
| GOOGL_FWP_TermSheet_2026-08-07 | 6.375% Notes due 2056 | CUSIP              | 02079KCU9                | 02079K CU9 / US02079KCU97 |
| GOOGL_FWP_TermSheet_2026-08-07 | 6.500% Notes due 2066 | CUSIP              | 02079KCV7                | 02079K CV7 / US02079KCV70 |

### Extraction Attempts

AAPL: produced 2026-09-24 before the attempt log existed

| Deal                           | Timestamp            | Model                 | Outcome   | Error   |
|:-------------------------------|:---------------------|:----------------------|:----------|:--------|
| MSFT_FWP_TermSheet_2017-01-31  | 2026-10-08T01:48:36Z | gemini-3.5-flash-lite | ok        |         |
| ORCL_FWP_TermSheet_2025-09-24  | 2026-10-08T01:49:02Z | gemini-3.5-flash-lite | ok        |         |
| GOOGL_FWP_TermSheet_2026-08-07 | 2026-10-08T01:51:09Z | gemini-3.5-flash-lite | ok        |         |
