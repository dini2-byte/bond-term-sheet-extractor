# Non-dollar test set

Hand-keyed euro and sterling bond term sheets used to check milestone 2 of `.claude/prds/non-usd-deals.prd.md`. This is a test set, not part of the benchmark: none of these deals feed the reported 98.3%.

## Selection rule

Written on 2026-10-09 before any filing in the set was read for values.

1. Run `lookup.find_term_sheets(ticker, scan=25)` for KO, PG, IBM, T, AAPL, CAT and MCD.
2. Tag each result's currency with a regex on its first 4,000 characters: `€` or `EUR` gives EUR, `£` or `GBP` or `sterling` gives GBP, `¥` or `JPY` or `yen` gives JPY, otherwise USD. When more than one matches, take the first match in the text.
3. Pick, in this order:
   - the 2 newest EUR term sheets from each of KO, PG, IBM and T (8 deals);
   - every GBP term sheet, up to 3, newest first;
   - the newest JPY term sheet (1 deal, the "left out of search" case).
4. If fewer than 2 GBP term sheets turn up, repeat the scan with `scan=50` for the same tickers and take GBP term sheets from that. Record the shortfall here.
5. A deal whose filing text is over 60,000 characters never reaches search, so `find_term_sheets` drops it already and the next newest is taken.
6. Currency check of the regex: from all results in scan order (ticker order above, newest first within a ticker), take every 4th regex-tagged non-dollar result until 10 are taken, and every 4th regex-tagged dollar result until 10 are taken. Read each first page by hand and record the true currency.

## Scan, 2026-10-09

`find_term_sheets(scan=25)` returned 118 term sheets: KO 25, PG 24, IBM 23, T 19, AAPL 18, CAT 9, MCD 0. The regex tagged 42 as non-dollar (the PRD's 44 came from an earlier, looser regex).

## Amendments made after the scan

Both were made after seeing currencies and tranche titles, before reading any value to key.

1. A deal counts as EUR only when a hand check of its principal amounts says so. PG `0001193125-25-251711` was tagged EUR because it mentions a concurrent euro offering, but its own notes are in dollars. The next newest hand-checked EUR deal was taken.
2. Deals made up only of floating-rate notes are skipped, since floating-rate notes are out of scope in the PRD. That skipped T `0001193125-26-340212` and T `0001193125-25-198872`. A deal with both fixed and floating notes stays in, and its floating note is keyed with `Coupon (%)` null.

## Picked deals

| Ticker | Accession | Filed | Currency | Bonds | Note |
|---|---|---|---|---|---|
| KO | 0001552781-24-000447 | 2024-08-09 | EUR | 2 | The live run that started this PRD |
| KO | 0001552781-24-000288 | 2024-05-07 | EUR | 2 | |
| PG | 0001193125-25-251694 | 2025-10-27 | EUR | 2 | |
| PG | 0001193125-24-104910 | 2024-04-22 | EUR | 2 | |
| IBM | 0001104659-26-007953 | 2026-01-29 | EUR | 4 | 3 fixed, 1 floating |
| IBM | 0001104659-25-009649 | 2025-02-05 | EUR | 4 | |
| T | 0001193125-26-318207 | 2026-07-27 | EUR and GBP | 5 | 4 euro bonds and 1 sterling bond in one deal |
| T | 0001193125-25-061322 | 2025-03-24 | EUR | 3 | |
| PG | 0001193125-17-143201 | 2017-04-27 | GBP | 2 | |
| IBM | 0001104659-15-054222 | 2015-07-29 | GBP | 1 | |
| PG | 0001193125-21-312459 | 2021-10-29 | JPY | 2 | Should be left out of search |

Bond counts above are from tranche titles and are checked again when keying. The T deal from 2026-07-27 mixes two currencies, so the key records currency per bond as well as per deal.

## Currency check of the regex

Every 4th result in scan order from each regex group, 10 per group.

| # | Ticker | Accession | Regex | Hand check |
|---|---|---|---|---|
| 0 | KO | 0001552781-24-000447 | EUR | EUR |
| 8 | KO | 0001552781-21-000063 | EUR | EUR |
| 17 | KO | 0001104659-17-012032 | EUR | EUR |
| 25 | PG | 0001193125-25-251711 | EUR | USD (mentions a concurrent euro deal) |
| 34 | PG | 0001193125-21-312459 | JPY | JPY |
| 41 | PG | 0001193125-17-316726 | EUR | EUR |
| 50 | IBM | 0001104659-26-007953 | EUR | EUR |
| 60 | IBM | 0001104659-20-010763 | EUR | EUR |
| 66 | IBM | 0001104659-16-101028 | EUR | EUR |
| 79 | T | 0001193125-25-198872 | EUR | EUR |
| 1 | KO | 0001552781-24-000436 | USD | USD |
| 9 | KO | 0001552781-20-000481 | USD | USD |
| 16 | KO | 0001104659-17-034331 | USD | USD |
| 23 | KO | 0001104659-15-072251 | USD | USD |
| 32 | PG | 0001193125-23-013260 | USD | USD |
| 38 | PG | 0001193125-20-082980 | USD | USD |
| 47 | PG | 0001193125-14-383435 | USD | USD |
| 54 | IBM | 0001104659-23-008150 | USD | USD |
| 61 | IBM | 0001104659-19-028047 | USD | USD |
| 70 | IBM | 0001104659-15-006576 | USD | USD |

The regex was right on 19 of 20. Its one miss was a dollar deal that mentions a euro deal, so it overcounts. Scaling the 1-in-10 false positive rate gives about 38 of 118 (32%) true non-dollar term sheets, down from the PRD's 37%. Currency detection in milestone 2 has to read the principal amounts, not the first currency word on the page.

## Filings on SEC EDGAR

Each link opens the filing index; click the document in the first row to read the term sheet.

- [KO_FWP_TermSheet_EUR_2024-08-09](https://www.sec.gov/Archives/edgar/data/21344/000155278124000447/0001552781-24-000447-index.htm)
- [KO_FWP_TermSheet_EUR_2024-05-07](https://www.sec.gov/Archives/edgar/data/21344/000155278124000288/0001552781-24-000288-index.htm)
- [PG_FWP_TermSheet_EUR_2025-10-27](https://www.sec.gov/Archives/edgar/data/80424/000119312525251694/0001193125-25-251694-index.htm)
- [PG_FWP_TermSheet_EUR_2024-04-22](https://www.sec.gov/Archives/edgar/data/80424/000119312524104910/0001193125-24-104910-index.htm)
- [IBM_FWP_TermSheet_EUR_2026-01-29](https://www.sec.gov/Archives/edgar/data/51143/000110465926007953/0001104659-26-007953-index.htm)
- [IBM_FWP_TermSheet_EUR_2025-02-05](https://www.sec.gov/Archives/edgar/data/51143/000110465925009649/0001104659-25-009649-index.htm)
- [T_FWP_TermSheet_EUR_GBP_2026-07-27](https://www.sec.gov/Archives/edgar/data/732717/000119312526318207/0001193125-26-318207-index.htm)
- [T_FWP_TermSheet_EUR_2025-03-24](https://www.sec.gov/Archives/edgar/data/732717/000119312525061322/0001193125-25-061322-index.htm)
- [PG_FWP_TermSheet_GBP_2017-04-27](https://www.sec.gov/Archives/edgar/data/80424/000119312517143201/0001193125-17-143201-index.htm)
- [IBM_FWP_TermSheet_GBP_2015-07-29](https://www.sec.gov/Archives/edgar/data/51143/000110465915054222/0001104659-15-054222-index.htm)
- [PG_FWP_TermSheet_JPY_2021-10-29](https://www.sec.gov/Archives/edgar/data/80424/000119312521312459/0001193125-21-312459-index.htm)

## Answer key

`answer_key.json`, keyed by file stem in `raw/`. Each deal has its `accession`, `currencies`, `bond_count` and one entry per bond. Conventions follow `data/answer_key.json`: text fields keep the filing's own wording, numbers are normalised and a field the filing does not state is `null`.

- `Size (M)` is in millions of the bond's own currency (¥50bn is `50000.0`).
- `Spread to mid-swaps (bps)` is the reoffer spread over the mid-swap rate. `Spread to benchmark (bps)` is the spread over the government bond in `Benchmark text`.
- `Benchmark kind` is one of `US Treasury`, `German government` (DBR and OBL), `UK government` (UKT and Gilt), `Government, not named` (the filing gives a coupon and date but not the issuer) or `None`.
- Every yield the filing states is kept. `Yield (%)` is the yield with no basis given or an annual one; `Semi-annual yield (%)` is a yield the filing labels semi-annual. PG 2017 states both (annual 1.394% and 1.809% on lines 26 and 70, semi-annual 1.389% and 1.801% on lines 25 and 69). IBM 2015 states only a semi-annual yield (2.662%, line 37), so its `Yield (%)` is `null`.
- The floating-rate note in IBM 2026-01-29 has `Coupon (%)`, `Yield (%)` and both spreads `null`. Its day count comes from the floating-rate terms (line 305), not the deal-wide line 80.

Drafted by Claude from the filing text on 2026-10-09, before any extraction run on these deals. Each value below is cited by line number in `raw/<stem>.txt`. Aidin confirmed the key and the judgment calls on 2026-10-09.

## Line citations


### KO_FWP_TermSheet_EUR_2024-08-09

- **3.375% notes due 2037**: Tranche 19, Size 24, Coupon 44, Price 53, Yield 40, MS spread 32, Benchmark 67, Bmk spread 82, Maturity 28, Par call 87, Day count 98, Frequency 48, ISIN 104, Common Code 104, CUSIP 105
- **3.750% notes due 2053**: Tranche 22, Size 27, Coupon 47, Price 56, Yield 43, MS spread 35, Benchmark 71, Bmk spread 86, Maturity 31, Par call 87, Day count 98, Frequency 52, ISIN 108, Common Code 108, CUSIP 108

### KO_FWP_TermSheet_EUR_2024-05-07

- **3.125% notes due 2032**: Tranche 17, Size 24, Coupon 54, Price 67, Yield 48, MS spread 36, Benchmark 85, Bmk spread 103, Maturity 30, Par call 110, Day count 148, Frequency 61, ISIN 153, Common Code 154, CUSIP 154
- **3.500% notes due 2044**: Tranche 21, Size 28, Coupon 58, Price 71, Yield 52, MS spread 40, Benchmark 89, Bmk spread 107, Maturity 34, Par call 111, Day count 148, Frequency 65, ISIN 157, Common Code 158, CUSIP 158

### PG_FWP_TermSheet_EUR_2025-10-27

- **2.900% Notes due 2033**: Tranche 18, Size 21, Coupon 26, Price 27, Yield 25, MS spread 24, Benchmark 28, Bmk spread 33, Maturity 22, Par call 36, Day count 35, Frequency 34, ISIN 42, Common Code 41, CUSIP 43
- **3.650% Notes due 2045**: Tranche 64, Size 66, Coupon 71, Price 72, Yield 70, MS spread 69, Benchmark 73, Bmk spread 75, Maturity 67, Par call 78, Day count 77, Frequency 76, ISIN 83, Common Code 82, CUSIP 84

### PG_FWP_TermSheet_EUR_2024-04-22

- **3.150% Notes due 2028**: Tranche 18, Size 21, Coupon 26, Price 27, Yield 25, MS spread 24, Benchmark 28, Bmk spread 30, Maturity 22, Par call 33, Day count 32, Frequency 31, ISIN 40, Common Code 39, CUSIP 41
- **3.200% Notes due 2034**: Tranche 90, Size 92, Coupon 97, Price 98, Yield 96, MS spread 95, Benchmark 99, Bmk spread 101, Maturity 93, Par call 104, Day count 103, Frequency 102, ISIN 109, Common Code 108, CUSIP 110

### IBM_FWP_TermSheet_EUR_2026-01-29

- **3.000% Notes Due 2031**: Tranche 9, Size 121, Coupon 92, Price 178, Yield 157, MS spread 150, Benchmark 128, Bmk spread 136, Maturity 85, Par call 171, Day count 80, Frequency 92, ISIN 200, Common Code 200, CUSIP 200
- **3.450% Notes Due 2034**: Tranche 12, Size 124, Coupon 95, Price 181, Yield 160, MS spread 153, Benchmark 131, Bmk spread 139, Maturity 88, Par call 174, Day count 80, Frequency 92, ISIN 203, Common Code 203, CUSIP 203
- **3.850% Notes Due 2038**: Tranche 15, Size 127, Coupon 98, Price 184, Yield 163, MS spread 156, Benchmark 134, Bmk spread 142, Maturity 91, Par call 177, Day count 80, Frequency 92, ISIN 206, Common Code 206, CUSIP 206
- **Floating Rate Notes Due 2028**: Tranche 21, Size 210, Coupon 213, Price 217, Maturity 212, Par call 220, Day count 305, Frequency 215, ISIN 221, Common Code 221, CUSIP 221

### IBM_FWP_TermSheet_EUR_2025-02-05

- **2.900% Notes Due 2030**: Tranche 5, Size 85, Coupon 96, Price 99, Yield 95, MS spread 94, Benchmark 89, Bmk spread 92, Maturity 86, Par call 98, Day count 102, Frequency 96, ISIN 104, Common Code 104, CUSIP 104
- **3.150% Notes Due 2033**: Tranche 8, Size 85, Coupon 96, Price 99, Yield 95, MS spread 94, Benchmark 89, Bmk spread 92, Maturity 86, Par call 98, Day count 102, Frequency 96, ISIN 104, Common Code 104, CUSIP 104
- **3.450% Notes Due 2037**: Tranche 11, Size 85, Coupon 96, Price 99, Yield 95, MS spread 94, Benchmark 89, Bmk spread 92, Maturity 86, Par call 98, Day count 102, Frequency 96, ISIN 104, Common Code 104, CUSIP 104
- **3.800% Notes Due 2045**: Tranche 14, Size 85, Coupon 96, Price 99, Yield 95, MS spread 94, Benchmark 89, Bmk spread 92, Maturity 86, Par call 98, Day count 102, Frequency 96, ISIN 104, Common Code 104, CUSIP 104

### T_FWP_TermSheet_EUR_GBP_2026-07-27

- **3.600% Global Notes due 2030**: Tranche 28, Size 57, Coupon 209, Price 137, Yield 152, MS spread 81, Benchmark 93, Bmk spread 123, Maturity 43, Par call 255, Day count 309, Frequency 225, ISIN 264, Common Code 293, CUSIP 279
- **4.150% Global Notes due 2034**: Tranche 31, Size 60, Coupon 212, Price 140, Yield 155, MS spread 85, Benchmark 96, Bmk spread 126, Maturity 46, Par call 256, Day count 309, Frequency 228, ISIN 268, Common Code 296, CUSIP 282
- **4.550% Global Notes due 2038**: Tranche 34, Size 63, Coupon 216, Price 144, Yield 158, MS spread 88, Benchmark 100, Bmk spread 130, Maturity 49, Par call 257, Day count 309, Frequency 231, ISIN 271, Common Code 299, CUSIP 286
- **5.050% Global Notes due 2045**: Tranche 37, Size 67, Coupon 219, Price 147, Yield 161, MS spread 92, Benchmark 103, Bmk spread 133, Maturity 53, Par call 258, Day count 309, Frequency 234, ISIN 275, Common Code 302, CUSIP 289
- **7.050% Global Notes due 2052**: Tranche 40, Size 70, Coupon 223, Price 151, Yield 164, Benchmark 106, Bmk spread 136, Maturity 56, Par call 259, Day count 309, Frequency 237, ISIN 278, Common Code 305, CUSIP 292

### T_FWP_TermSheet_EUR_2025-03-24

- **3.150% Global Notes due 2030**: Tranche 21, Size 38, Coupon 124, Price 83, Yield 91, MS spread 53, Benchmark 60, Bmk spread 76, Maturity 30, Par call 155, Day count 190, Frequency 132, ISIN 162, Common Code 179, CUSIP 170
- **3.600% Global Notes due 2033**: Tranche 24, Size 41, Coupon 128, Price 86, Yield 94, MS spread 56, Benchmark 63, Bmk spread 79, Maturity 33, Par call 156, Day count 190, Frequency 135, ISIN 166, Common Code 182, CUSIP 173
- **4.050% Global Notes due 2037**: Tranche 27, Size 44, Coupon 131, Price 90, Yield 97, MS spread 59, Benchmark 66, Bmk spread 82, Maturity 36, Par call 157, Day count 190, Frequency 138, ISIN 169, Common Code 185, CUSIP 177

### PG_FWP_TermSheet_GBP_2017-04-27

- **1.375% Notes due 2025**: Tranche 18, Size 21, Coupon 23, Price 24, Yield 26, Benchmark 28, Bmk spread 27, Maturity 22, Par call 32, Day count 31, Frequency 30, ISIN 39, Common Code 38, CUSIP 40
- **1.800% Notes due 2029**: Tranche 62, Size 64, Coupon 67, Price 68, Yield 70, Benchmark 72, Bmk spread 71, Maturity 65, Par call 76, Day count 75, Frequency 74, ISIN 81, Common Code 80, CUSIP 82

### IBM_FWP_TermSheet_GBP_2015-07-29

- **2.625% Notes Due 2022**: Tranche 5, Size 30, Coupon 38, Price 40, Semi-annual yield 37, Benchmark 34, Bmk spread 36, Maturity 31, Par call 39, Day count 43, Frequency 32, ISIN 45, Common Code 45, CUSIP 45

### PG_FWP_TermSheet_JPY_2021-10-29

- **0.110% Notes due 2026**: Tranche 17, Size 19, Coupon 21, Price 22, Yield 23, MS spread 25, Maturity 20, Par call 28, Day count 27, Frequency 26, ISIN 32, Common Code 31, CUSIP 34
- **0.230% Notes due 2031**: Tranche 53, Size 55, Coupon 57, Price 58, Yield 59, MS spread 61, Maturity 56, Par call 65, Day count 63, Frequency 62, ISIN 69, Common Code 68, CUSIP 70

Where `Par Call Date` is `null`, the cited line is the redemption term that shows there is no par call (make-whole only, or tax redemption only).

## Findings for the PRD's open questions

**1. Do euro deals price over mid-swaps?** Yes. All 22 fixed-rate euro bonds state a reoffer spread over mid-swaps, and all 22 also state a spread over a government bond. Of those, 18 name a German government bond (DBR or OBL) and 4 (both PG euro deals) give only a coupon and date. All 4 sterling bonds price over a UK government bond and have no mid-swap spread, including the sterling bond inside AT&T's euro deal. The two yen bonds price over yen mid-swaps (TONA) with no government bond. So a single "Spread" column means different things by currency: mid-swaps for euro and yen, government for sterling and dollars.

**3. Do euro conventions trip the validation checks?** No. `validate.py` has no day count or coupon frequency rule. Run on the keyed values, with either spread in the Spread column, every fixed-rate bond passes. The only flag is `MISSING_COUPON` on the IBM floating-rate note, which is out of scope. Conventions seen: euro bonds pay annually on ACT/ACT (ICMA), written four different ways; sterling bonds pay annually except AT&T's semiannual 2052 note; yen bonds pay semiannually on 30/360; the euro floating-rate note pays quarterly on Actual/360.

## Other findings for milestone 2

- One AT&T deal mixes euro and sterling bonds, so currency has to be per bond, not per deal.
- Currency detection must read the principal amounts. Both the dollar PG deal and the yen PG deal mention a concurrent euro offering near the top of the page.
- `count_bonds` overcounts every deal in the set: Common Codes are 9 digits and pass as CUSIPs. IBM 2026-01-29 counts 9 for 4 bonds.
- PG's euro deals name no government issuer, so a "Bund" label would be a guess. The page should show the benchmark as the filing writes it.

## Baseline extraction, 2026-10-09

The current extractor (`gemini-3.5-flash-lite`, prompt unchanged) on the 10 euro and sterling deals, saved in `extractions/` and scored with `python score_test_set.py`. Currency is 0 because the app has no currency column yet.

| Deal | Bonds (key / extracted / search count) | Currency | Size | Coupon | Price | Yield | Benchmark | Spread | Maturity | CUSIP |
|---|---|---|---|---|---|---|---|---|---|---|
| IBM_FWP_TermSheet_EUR_2025-02-05 | 4 / 4 / 9 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 0/4 | 4/4 | 4/4 |
| IBM_FWP_TermSheet_EUR_2026-01-29 | 4 / 4 / 9 | 0/4 | 4/4 | 3/3 | 4/4 | 3/3 | 3/3 | 0/3 | 4/4 | 4/4 |
| IBM_FWP_TermSheet_GBP_2015-07-29 | 1 / 1 / 3 | 0/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| KO_FWP_TermSheet_EUR_2024-05-07 | 2 / 2 / 4 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 0/2 |
| KO_FWP_TermSheet_EUR_2024-08-09 | 2 / 2 / 4 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 0/2 |
| PG_FWP_TermSheet_EUR_2024-04-22 | 2 / 2 / 4 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| PG_FWP_TermSheet_EUR_2025-10-27 | 2 / 2 / 4 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 0/2 | 2/2 | 2/2 |
| PG_FWP_TermSheet_GBP_2017-04-27 | 2 / 2 / 4 | 0/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| T_FWP_TermSheet_EUR_2025-03-24 | 3 / 3 / 6 | 0/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 3/3 | 3/3 |
| T_FWP_TermSheet_EUR_GBP_2026-07-27 | 5 / 5 / 10 | 0/5 | 5/5 | 5/5 | 5/5 | 5/5 | 5/5 | 0/5 | 5/5 | 5/5 |
| **All 10 deals** | | 0/27 | 27/27 | 26/26 | 27/27 | 26/26 | 22/26 | 3/26 | 27/27 | 23/27 |

Extracted spread on fixed-rate bonds: {'missing': 4, 'other': 15, 'benchmark': 3, 'mid-swaps': 4}

Why the spread is right on only 3 of 26 fixed-rate bonds:

- **Parser bug, 15 bonds.** Gemini picked the right spread text ("+108.2 bps"), but `clean_spread` reads only whole numbers and returns the digit after the decimal point (2). Every spread with a decimal is wrong.
- **Wrong spread, 4 bonds.** In both KO deals, Gemini took the mid-swap spread (+88 bps), which the filing lists first, while the benchmark column shows the Bund. The pair does not match.
- **Nothing extracted, 4 bonds.** IBM 2025-02-05 puts all four bonds side by side in one table, and Gemini returned no spread or benchmark for any of them.

The 4 CUSIP misses are both KO deals: `clean_cusip` takes the first 9-character code in "XS... / 287415494 / 191216 DW7", which is the Common Code.

With the parser fixed, the spread and benchmark would pair correctly on 14 of the 22 fixed-rate euro bonds, below the plan's gate of 18.
