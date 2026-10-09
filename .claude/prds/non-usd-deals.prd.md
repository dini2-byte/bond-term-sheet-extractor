# Non-Dollar Deals in Company Search

## Problem
Visitors who use "Search company" on large US issuers get euro and sterling bond term sheets mixed in with dollar ones, and the app treats every deal as US dollars. A euro deal shows "$500.0M" for what is likely a €500M bond, the picker counts the wrong number of bonds and the benchmark column labels a German Bund as a US Treasury. These values look confidently wrong, which undercuts the project's core claim that every number is trustworthy and traced to the filing.

## Evidence
- Live run on the deployed app, 2026-10-09: KO term sheet filed 2024-08-09 showed "$500.0M" sizes, a "DBR" (Bund) benchmark under a column whose tooltip says "US Treasury", and "4 bonds" in the picker for a 2-bond deal. The 9-digit Common Codes in euro term sheets are counted as CUSIPs.
- EDGAR scan, 2026-10-09, using the app's own search on 7 tickers: 44 of 118 bond term sheets (37%) are non-dollar. KO 13 of 25, PG 12 of 24, IBM 11 of 23, T 8 of 19, AAPL 0 of 18, CAT 0 of 9. Mostly EUR, with a few GBP and one JPY.
- The currency check in that scan is a regex on the first page of each filing, so the 37% is an estimate. Needs validation via a hand check of a sample of flagged filings.

## Users
- **Primary**: AINA scholarship reviewers and other first-time visitors who try "Search company" on a well-known US issuer, often during or after watching the demo video. They are finance or accounting people, not bond desk analysts, and will not spot a currency mix-up on their own.
- **Not for**: bond desk analysts who need cross-currency comps, converted sizes or swap-spread analysis.

## Hypothesis
We believe **extracting and showing each deal's currency and benchmark** will **stop non-dollar deals from showing wrong dollar values** for **visitors using Search company**.
We'll know we're right when **a fixed test set of about 10 EUR and GBP term sheets shows the right currency, size, bond count and benchmark label for every deal, and the 4 saved USD deals still score 98.3% field accuracy**.

## Success Metrics
| Metric | Target | How measured |
|---|---|---|
| Currency shown correctly on EUR and GBP test deals | 10 of 10 | Hand-checked test set of about 10 filings, picked before any run |
| Bond count correct in the search picker | 100% of the test set | Compare picker count to the bonds listed in each filing |
| Benchmark labelled correctly (Treasury, Bund, Gilt) | 100% of the test set | Hand check |
| Field accuracy on the 4 saved USD deals | Stays at 98.3% (344/350) | Re-run the existing benchmark report |
| Non-USD, non-EUR, non-GBP deals shown in search | 0 | Search results for the 7 scanned tickers |

## Scope
**MVP**
- EUR and GBP deals show sizes in their own currency ("€500.0M", "£500.0M").
- The table column now called "Treasury" becomes "Benchmark", with help text that covers US Treasuries, German Bunds and UK Gilts.
- The bond count in the search picker ignores Common Codes and counts each bond once.
- The deal line names the currency.
- Deals in any other currency are left out of search results, with no message on the page.
- USD deals look and behave exactly as they do today.
- No "not supported" or "coming soon" text anywhere on the page.

**Out of scope for this PRD (planned for later milestones)**
- Currency conversion to a common currency. Later: needs a rate source and a pricing date rule.
- JPY, CHF and other currencies. Later: same approach once EUR and GBP are proven.
- Floating-rate notes. Later: they need their own fields (index, margin, reset dates).
- Adding non-dollar deals to the scored benchmark. Later: needs hand-checked answer keys written before any run.

## Delivery Milestones
| # | Milestone | Outcome | Status | Plan |
|---|---|---|---|---|
| 1 | Test set | About 10 EUR and GBP term sheets picked and hand-keyed for currency, size, bond count and benchmark before any run | pending | none yet |
| 2 | Correct non-dollar display | EUR and GBP deals from search show the right currency, sizes, bond count and benchmark; other currencies drop out of search; USD unchanged and still 98.3% | pending | none yet |
| 3 | Other currencies | JPY and CHF deals handled the same way | deferred | none yet |
| 4 | Floating-rate notes | FRN tranches extracted and shown with their own fields | deferred | none yet |
| 5 | Non-dollar benchmark | Euro and sterling deals added to the scored benchmark with answer keys | deferred | none yet |
| 6 | Currency conversion | Optional view with sizes converted to USD | deferred | none yet |

## Open Questions
- [ ] Do euro term sheets quote spreads over mid-swaps instead of a government bond? If so, what should the Spread and Benchmark columns show? Needs validation via reading the test set.
- [ ] Does teaching the extraction about currency change field accuracy on the 4 saved USD deals? Needs one benchmark re-run (4 Gemini calls).
- [ ] Do euro conventions (annual coupons, ACT/ACT day count) trip the current validation checks and mark every euro row for checking?
- [ ] Does the 2026-10-31 deadline leave time for milestone 2, or should search hide non-dollar deals until it ships?

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Prompt change lowers the 98.3% on USD deals | Medium | High: the headline number in the writeup and video | Re-run the benchmark before merging; keep the old prompt if accuracy drops |
| Currency detection misses or mislabels a deal | Medium | High: wrong values again, now with a confident currency symbol | Hand-checked test set; leave a deal out of search when its currency is unclear |
| Euro spreads over mid-swaps confuse the Spread column | Medium | Medium | Settle in open questions before planning milestone 2 |
| Not done before 2026-10-31 | Medium | Medium | Interim option: hide non-dollar deals from search until milestone 2 ships |

---
*Status: DRAFT. Requirements only. Implementation planning pending via /plan.*
