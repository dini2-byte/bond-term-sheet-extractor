# Draft answer keys: MSFT, ORCL, GOOGL

Drafted by Claude from the filing text on 2026-10-07, before any extraction was run on these deals. Every value cites its line in `data/raw_filings/<deal>.txt`. Aidin checks each value against the filing, then slice 2 merges `data/answer_key_draft.json` into `data/answer_key.json`.

Conventions copied from the AAPL key: text fields are the filing's own wording, numbers are normalised (principal in millions of the deal currency, spread in bps), a field the filing does not state is `null` (the extractor should report Not found).

## MSFT_FWP_TermSheet_2017-01-31

### 1.850% Notes due 2020

| Field | Value | Line |
|---|---|---|
| Tranche | 1.850% Notes due 2020 | 28 |
| Issuer | Microsoft Corporation | 27 |
| Ratings | Aaa / AAA | 191 |
| Trade Date | January 30, 2017 | 151 |
| Settlement Date | February 6, 2017 | 152 |
| Principal ($M) | 1500.0 | 50 |
| Coupon (%) | 1.85 | 72 |
| Issue Price | 99.933 | 57 |
| Yield (%) | 1.873 | 103 |
| Spread (bps) | 40 | 78 |
| Benchmark Treasury | UST 1.375% due January 15, 2020 | 73 |
| Maturity Date | February 6, 2020 | 64 |
| Day Count | null | not stated in filing |
| Par Call Date | null | 113 (make-whole to maturity, no par call) |
| CUSIP | 594918BV5 | 184 |

### 2.400% Notes due 2022

| Field | Value | Line |
|---|---|---|
| Tranche | 2.400% Notes due 2022 | 31 |
| Issuer | Microsoft Corporation | 27 |
| Ratings | Aaa / AAA | 191 |
| Trade Date | January 30, 2017 | 151 |
| Settlement Date | February 6, 2017 | 152 |
| Principal ($M) | 1750.0 | 51 |
| Coupon (%) | 2.4 | 83 |
| Issue Price | 99.785 | 58 |
| Yield (%) | 2.446 | 104 |
| Spread (bps) | 50 | 91 |
| Benchmark Treasury | UST 1.875% due January 31, 2022 | 89 |
| Maturity Date | February 6, 2022 | 65 |
| Day Count | null | not stated in filing |
| Par Call Date | January 6, 2022 | 115 |
| CUSIP | 594918BW3 | 185 |

### 2.875% Notes due 2024

| Field | Value | Line |
|---|---|---|
| Tranche | 2.875% Notes due 2024 | 34 |
| Issuer | Microsoft Corporation | 27 |
| Ratings | Aaa / AAA | 191 |
| Trade Date | January 30, 2017 | 151 |
| Settlement Date | February 6, 2017 | 152 |
| Principal ($M) | 2250.0 | 52 |
| Coupon (%) | 2.875 | 84 |
| Issue Price | 99.272 | 59 |
| Yield (%) | 2.991 | 105 |
| Spread (bps) | 70 | 92 |
| Benchmark Treasury | UST 2.250% due January 31, 2024 | 90 |
| Maturity Date | February 6, 2024 | 66 |
| Day Count | null | not stated in filing |
| Par Call Date | December 6, 2023 | 117 |
| CUSIP | 594918BX1 | 186 |

### 3.300% Notes due 2027

| Field | Value | Line |
|---|---|---|
| Tranche | 3.300% Notes due 2027 | 38 |
| Issuer | Microsoft Corporation | 27 |
| Ratings | Aaa / AAA | 191 |
| Trade Date | January 30, 2017 | 151 |
| Settlement Date | February 6, 2017 | 152 |
| Principal ($M) | 4000.0 | 53 |
| Coupon (%) | 3.3 | 85 |
| Issue Price | 99.645 | 60 |
| Yield (%) | 3.342 | 106 |
| Spread (bps) | 85 | 93 |
| Benchmark Treasury | UST 2.000% due November 15, 2026 | 74 |
| Maturity Date | February 6, 2027 | 67 |
| Day Count | null | not stated in filing |
| Par Call Date | November 6, 2026 | 120 |
| CUSIP | 594918BY9 | 187 |

### 4.100% Notes due 2037

| Field | Value | Line |
|---|---|---|
| Tranche | 4.100% Notes due 2037 | 41 |
| Issuer | Microsoft Corporation | 27 |
| Ratings | Aaa / AAA | 191 |
| Trade Date | January 30, 2017 | 151 |
| Settlement Date | February 6, 2017 | 152 |
| Principal ($M) | 2500.0 | 54 |
| Coupon (%) | 4.1 | 86 |
| Issue Price | 99.783 | 61 |
| Yield (%) | 4.116 | 107 |
| Spread (bps) | 100 | 94 |
| Benchmark Treasury | UST 2.250% due August 15, 2046 | 75 |
| Maturity Date | February 6, 2037 | 68 |
| Day Count | null | not stated in filing |
| Par Call Date | August 6, 2036 | 123 |
| CUSIP | 594918BZ6 | 188 |

### 4.250% Notes due 2047

| Field | Value | Line |
|---|---|---|
| Tranche | 4.250% Notes due 2047 | 44 |
| Issuer | Microsoft Corporation | 27 |
| Ratings | Aaa / AAA | 191 |
| Trade Date | January 30, 2017 | 151 |
| Settlement Date | February 6, 2017 | 152 |
| Principal ($M) | 3000.0 | 55 |
| Coupon (%) | 4.25 | 87 |
| Issue Price | 99.731 | 62 |
| Yield (%) | 4.266 | 108 |
| Spread (bps) | 115 | 95 |
| Benchmark Treasury | UST 2.250% due August 15, 2046 | 76 |
| Maturity Date | February 6, 2047 | 69 |
| Day Count | null | not stated in filing |
| Par Call Date | August 6, 2046 | 126 |
| CUSIP | 594918CA0 | 189 |

### 4.500% Notes due 2057

| Field | Value | Line |
|---|---|---|
| Tranche | 4.500% Notes due 2057 | 48 |
| Issuer | Microsoft Corporation | 27 |
| Ratings | Aaa / AAA | 191 |
| Trade Date | January 30, 2017 | 151 |
| Settlement Date | February 6, 2017 | 152 |
| Principal ($M) | 2000.0 | 56 |
| Coupon (%) | 4.5 | 88 |
| Issue Price | 99.705 | 63 |
| Yield (%) | 4.516 | 109 |
| Spread (bps) | 140 | 96 |
| Benchmark Treasury | UST 2.250% due August 15, 2046 | 77 |
| Maturity Date | February 6, 2057 | 70 |
| Day Count | null | not stated in filing |
| Par Call Date | August 6, 2056 | 129 |
| CUSIP | 594918CB8 | 190 |

## ORCL_FWP_TermSheet_2025-09-24

### 4.450% Notes due 2030

| Field | Value | Line |
|---|---|---|
| Tranche | 4.450% Notes due 2030 | 15 |
| Issuer | Oracle Corporation | 16 |
| Ratings | Baa2 / BBB / BBB | 49 |
| Trade Date | September 24, 2025 | 44 |
| Settlement Date | September 26, 2025 | 45 |
| Principal ($M) | 3000.0 | 17 |
| Coupon (%) | 4.45 | 19 |
| Issue Price | 99.938 | 20 |
| Yield (%) | 4.464 | 26 |
| Spread (bps) | 75 | 25 |
| Benchmark Treasury | 3.625% due August 31, 2030 | 23 |
| Maturity Date | September 26, 2030 | 18 |
| Day Count | 30/360 | 22 |
| Par Call Date | August 26, 2030 | 27 |
| CUSIP | 68389XDH5 | 46 |

### 4.800% Notes due 2032

| Field | Value | Line |
|---|---|---|
| Tranche | 4.800% Notes due 2032 | 67 |
| Issuer | Oracle Corporation | 16 |
| Ratings | Baa2 / BBB / BBB | 100 |
| Trade Date | September 24, 2025 | 96 |
| Settlement Date | September 26, 2025 | 97 |
| Principal ($M) | 3000.0 | 69 |
| Coupon (%) | 4.8 | 71 |
| Issue Price | 99.965 | 72 |
| Yield (%) | 4.806 | 78 |
| Spread (bps) | 90 | 77 |
| Benchmark Treasury | 3.875% due August 31, 2032 | 75 |
| Maturity Date | September 26, 2032 | 70 |
| Day Count | 30/360 | 74 |
| Par Call Date | July 26, 2032 | 79 |
| CUSIP | 68389XDK8 | 98 |

### 5.200% Notes due 2035

| Field | Value | Line |
|---|---|---|
| Tranche | 5.200% Notes due 2035 | 129 |
| Issuer | Oracle Corporation | 16 |
| Ratings | Baa2 / BBB / BBB | 162 |
| Trade Date | September 24, 2025 | 158 |
| Settlement Date | September 26, 2025 | 159 |
| Principal ($M) | 4000.0 | 131 |
| Coupon (%) | 5.2 | 133 |
| Issue Price | 99.985 | 134 |
| Yield (%) | 5.202 | 140 |
| Spread (bps) | 105 | 139 |
| Benchmark Treasury | 4.250% due August 15, 2035 | 137 |
| Maturity Date | September 26, 2035 | 132 |
| Day Count | 30/360 | 136 |
| Par Call Date | June 26, 2035 | 141 |
| CUSIP | 68389XDM4 | 160 |

### 5.875% Notes due 2045

| Field | Value | Line |
|---|---|---|
| Tranche | 5.875% Notes due 2045 | 181 |
| Issuer | Oracle Corporation | 16 |
| Ratings | Baa2 / BBB / BBB | 214 |
| Trade Date | September 24, 2025 | 210 |
| Settlement Date | September 26, 2025 | 211 |
| Principal ($M) | 2500.0 | 183 |
| Coupon (%) | 5.875 | 185 |
| Issue Price | 99.953 | 186 |
| Yield (%) | 5.879 | 192 |
| Spread (bps) | 115 | 191 |
| Benchmark Treasury | 4.875% due August 15, 2045 | 189 |
| Maturity Date | September 26, 2045 | 184 |
| Day Count | 30/360 | 188 |
| Par Call Date | March 26, 2045 | 193 |
| CUSIP | 68389XDP7 | 212 |

### 5.950% Notes due 2055

| Field | Value | Line |
|---|---|---|
| Tranche | 5.950% Notes due 2055 | 233 |
| Issuer | Oracle Corporation | 16 |
| Ratings | Baa2 / BBB / BBB | 266 |
| Trade Date | September 24, 2025 | 262 |
| Settlement Date | September 26, 2025 | 263 |
| Principal ($M) | 3500.0 | 235 |
| Coupon (%) | 5.95 | 237 |
| Issue Price | 99.02 | 238 |
| Yield (%) | 6.021 | 244 |
| Spread (bps) | 125 | 243 |
| Benchmark Treasury | 4.750% due May 15, 2055 | 241 |
| Maturity Date | September 26, 2055 | 236 |
| Day Count | 30/360 | 240 |
| Par Call Date | March 26, 2055 | 245 |
| CUSIP | 68389XDR3 | 264 |

### 6.100% Notes due 2065

| Field | Value | Line |
|---|---|---|
| Tranche | 6.100% Notes due 2065 | 285 |
| Issuer | Oracle Corporation | 16 |
| Ratings | Baa2 / BBB / BBB | 318 |
| Trade Date | September 24, 2025 | 314 |
| Settlement Date | September 26, 2025 | 315 |
| Principal ($M) | 2000.0 | 287 |
| Coupon (%) | 6.1 | 289 |
| Issue Price | 99.392 | 290 |
| Yield (%) | 6.141 | 296 |
| Spread (bps) | 137 | 295 |
| Benchmark Treasury | 4.750% due May 15, 2055 | 293 |
| Maturity Date | September 26, 2065 | 288 |
| Day Count | 30/360 | 292 |
| Par Call Date | March 26, 2065 | 297 |
| CUSIP | 68389XDT9 | 316 |

## GOOGL_FWP_TermSheet_2026-08-07

### 4.500% Notes due 2028

| Field | Value | Line |
|---|---|---|
| Tranche | 4.500% Notes due 2028 | 40 |
| Issuer | Alphabet Inc. | 36 |
| Ratings | Aa2 / AA+ | 71 |
| Trade Date | August 6, 2026 | 68 |
| Settlement Date | August 10, 2026 | 69 |
| Principal ($M) | 1250.0 | 316 |
| Coupon (%) | 4.5 | 342 |
| Issue Price | 99.858 | 368 |
| Yield (%) | 4.575 | 475 |
| Spread (bps) | 33 | 497 |
| Benchmark Treasury | 4.250% due July 31, 2028 | 520 |
| Maturity Date | August 10, 2028 | 289 |
| Day Count | 30/360 | 641 |
| Par Call Date | null | 598 (make-whole to maturity, no par call) |
| CUSIP | 02079KCL9 | 645 |

### 4.625% Notes due 2029

| Field | Value | Line |
|---|---|---|
| Tranche | 4.625% Notes due 2029 | 47 |
| Issuer | Alphabet Inc. | 36 |
| Ratings | Aa2 / AA+ | 71 |
| Trade Date | August 6, 2026 | 68 |
| Settlement Date | August 10, 2026 | 69 |
| Principal ($M) | 2000.0 | 319 |
| Coupon (%) | 4.625 | 345 |
| Issue Price | 99.698 | 372 |
| Yield (%) | 4.734 | 478 |
| Spread (bps) | 43 | 500 |
| Benchmark Treasury | 4.125% due July 15, 2029 | 523 |
| Maturity Date | August 10, 2029 | 292 |
| Day Count | 30/360 | 641 |
| Par Call Date | July 10, 2029 | 620 |
| CUSIP | 02079KCN5 | 648 |

### 4.875% Notes due 2031

| Field | Value | Line |
|---|---|---|
| Tranche | 4.875% Notes due 2031 | 50 |
| Issuer | Alphabet Inc. | 36 |
| Ratings | Aa2 / AA+ | 71 |
| Trade Date | August 6, 2026 | 68 |
| Settlement Date | August 10, 2026 | 69 |
| Principal ($M) | 3500.0 | 323 |
| Coupon (%) | 4.875 | 349 |
| Issue Price | 99.49 | 376 |
| Yield (%) | 4.991 | 481 |
| Spread (bps) | 60 | 504 |
| Benchmark Treasury | 4.375% due July 31, 2031 | 527 |
| Maturity Date | August 15, 2031 | 296 |
| Day Count | 30/360 | 641 |
| Par Call Date | July 15, 2031 | 624 |
| CUSIP | 02079KCQ8 | 652 |

### 5.200% Notes due 2033

| Field | Value | Line |
|---|---|---|
| Tranche | 5.200% Notes due 2033 | 53 |
| Issuer | Alphabet Inc. | 36 |
| Ratings | Aa2 / AA+ | 71 |
| Trade Date | August 6, 2026 | 68 |
| Settlement Date | August 10, 2026 | 69 |
| Principal ($M) | 2500.0 | 326 |
| Coupon (%) | 5.2 | 352 |
| Issue Price | 99.564 | 380 |
| Yield (%) | 5.275 | 484 |
| Spread (bps) | 75 | 507 |
| Benchmark Treasury | 4.375% due July 31, 2033 | 530 |
| Maturity Date | August 15, 2033 | 299 |
| Day Count | 30/360 | 641 |
| Par Call Date | June 15, 2033 | 627 |
| CUSIP | 02079KCR6 | 655 |

### 5.450% Notes due 2036

| Field | Value | Line |
|---|---|---|
| Tranche | 5.450% Notes due 2036 | 57 |
| Issuer | Alphabet Inc. | 36 |
| Ratings | Aa2 / AA+ | 71 |
| Trade Date | August 6, 2026 | 68 |
| Settlement Date | August 10, 2026 | 69 |
| Principal ($M) | 4500.0 | 330 |
| Coupon (%) | 5.45 | 356 |
| Issue Price | 99.466 | 384 |
| Yield (%) | 5.52 | 487 |
| Spread (bps) | 85 | 510 |
| Benchmark Treasury | 4.375% due May 15, 2036 | 533 |
| Maturity Date | August 15, 2036 | 303 |
| Day Count | 30/360 | 641 |
| Par Call Date | May 15, 2036 | 630 |
| CUSIP | 02079KCS4 | 658 |

### 6.250% Notes due 2046

| Field | Value | Line |
|---|---|---|
| Tranche | 6.250% Notes due 2046 | 60 |
| Issuer | Alphabet Inc. | 36 |
| Ratings | Aa2 / AA+ | 71 |
| Trade Date | August 6, 2026 | 68 |
| Settlement Date | August 10, 2026 | 69 |
| Principal ($M) | 3000.0 | 333 |
| Coupon (%) | 6.25 | 359 |
| Issue Price | 99.626 | 388 |
| Yield (%) | 6.283 | 490 |
| Spread (bps) | 105 | 513 |
| Benchmark Treasury | 5.000% due May 15, 2046 | 537 |
| Maturity Date | August 15, 2046 | 306 |
| Day Count | 30/360 | 641 |
| Par Call Date | February 15, 2046 | 633 |
| CUSIP | 02079KCT2 | 662 |

### 6.375% Notes due 2056

| Field | Value | Line |
|---|---|---|
| Tranche | 6.375% Notes due 2056 | 63 |
| Issuer | Alphabet Inc. | 36 |
| Ratings | Aa2 / AA+ | 71 |
| Trade Date | August 6, 2026 | 68 |
| Settlement Date | August 10, 2026 | 69 |
| Principal ($M) | 4500.0 | 337 |
| Coupon (%) | 6.375 | 363 |
| Issue Price | 99.972 | 392 |
| Yield (%) | 6.377 | 493 |
| Spread (bps) | 115 | 516 |
| Benchmark Treasury | 4.750% due February 15, 2056 | 540 |
| Maturity Date | August 15, 2056 | 310 |
| Day Count | 30/360 | 641 |
| Par Call Date | February 15, 2056 | 636 |
| CUSIP | 02079KCU9 | 665 |

### 6.500% Notes due 2066

| Field | Value | Line |
|---|---|---|
| Tranche | 6.500% Notes due 2066 | 67 |
| Issuer | Alphabet Inc. | 36 |
| Ratings | Aa2 / AA+ | 71 |
| Trade Date | August 6, 2026 | 68 |
| Settlement Date | August 10, 2026 | 69 |
| Principal ($M) | 2500.0 | 340 |
| Coupon (%) | 6.5 | 366 |
| Issue Price | 99.617 | 396 |
| Yield (%) | 6.527 | 496 |
| Spread (bps) | 130 | 519 |
| Benchmark Treasury | 4.750% due February 15, 2056 | 543 |
| Maturity Date | August 15, 2066 | 313 |
| Day Count | 30/360 | 641 |
| Par Call Date | February 15, 2066 | 639 |
| CUSIP | 02079KCV7 | 669 |
