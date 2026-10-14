# Bond Term Sheet Extractor

Pulls pricing terms for investment-grade corporate bond deals out of SEC term sheets and builds a comps table where every value points back to the exact text it came from. It groups values into tranches, normalizes pricing terms and flags any value that does not match the source text exactly.

Live app: https://bond-term-sheet-extractor-diwsf7fvsovutxsajuanis.streamlit.app/. Search a company's recent bond term sheets on SEC EDGAR or upload your own. The four benchmark deals are saved and open without a Gemini call; any other filing uses one of 20 shared runs a day, and its result is saved for the next visitor.

## Results

- Field accuracy: 98.3% (344/350 fields, 4 deals, 25 tranches)
- Grounded: 55.5% (186/335 extracted fields)
- Not-in-source: 0.0% (0/335 extracted fields)

First scored at 88.0% (308/350); a CUSIP formatting bug in the comps table was fixed after the run, with no new extraction, which gave 98.3%.

| Deal | Tranches | Fields | Correct | Accuracy (%) | Grounded (%) |
|:---|---:|---:|---:|---:|---:|
| AAPL_FWP_TermSheet_2025-05-06 | 4 | 56 | 56 | 100.0 | 92.9 |
| MSFT_FWP_TermSheet_2017-01-31 | 7 | 98 | 98 | 100.0 | 32.2 |
| ORCL_FWP_TermSheet_2025-09-24 | 6 | 84 | 78 | 92.9 | 100.0 |
| GOOGL_FWP_TermSheet_2026-08-07 | 8 | 112 | 112 | 100.0 | 24.3 |

The 6 misses are all ORCL par call dates the extractor did not return. Grounding is low on MSFT (32.2%) and GOOGL (24.3%), whose terms sit in wide tables, and 100% on ORCL; a value that is not grounded is flagged in the app, not hidden. The 2 unmatched GOOGL tranches are floating-rate notes, which the answer key does not score.

## How the benchmark was built

The benchmark contains four deals: AAPL 2025-05-06, MSFT 2017-01-31, ORCL 2025-09-24 and GOOGL 2026-08-07. Filings are pinned by accession number in `fetch.py`. Answer keys were written and checked before each deal was run. Each deal was run once through Gemini and logged in `data/fixtures/attempts.jsonl`. Prompt collisions are listed in the leakage test; see [CONTEXT.md](CONTEXT.md) for the definition. See [ADR 0001](docs/adr/0001-exact-match-grounding.md) for what grounded means.

## How it works

- `fetch.py`: Downloads pinned SEC EDGAR term sheets by accession number and saves raw text.
- `fields.py`: Defines the debt capital markets field taxonomy and few-shot examples for extraction.
- `extract.py`: Runs LangExtract with Gemini, logs each attempt and writes extractions with character offsets to JSONL.
- `structure.py`: Groups extractions into tranche rows, spreads deal-level fields, normalizes financial values and records source spans.
- `validate.py`: Checks financial bounds, date ordering and source grounding status for each tranche.
- `evaluate.py`: Scores extracted comps tables against the answer key across benchmark deals and generates the accuracy report.
- `app.py`: Streamlit page: top bar and the Search filings and Upload term sheet tabs.
- `views/`: the two tabs, the shared results view (deal line, comps table, source panel and Excel download) and the How it works text.
- `theme.py`: colors and styling for the light and dark themes.
- `lookup.py`: finds a company's recent bond term sheets on SEC EDGAR and keeps the daily run limit.
- `cache.py`: saves each extraction by prompt version and SEC accession number, on Cloudflare R2 or local disk.
- `runner.py`: loads a saved extraction or runs a new one, and counts a run only for a real Gemini call.
- `seed_cache.py`: saves the four benchmark extractions into the cache.
- `demo.py`: upload size check and Gemini key lookup.

## Run it locally

```bash
git clone https://github.com/dini2-byte/bond-term-sheet-extractor.git
cd bond-term-sheet-extractor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

`streamlit run app.py` opens the tool. Search needs `EDGAR_IDENTITY` (your name and email, as SEC asks) in `.env`. The four benchmark deals load from `data/fixtures/` without an API key; any other filing or an upload needs `GEMINI_API_KEY`.

Reproduce the report from the committed fixtures:

```bash
python3 evaluate.py
```

Run the test suite:

```bash
python3 -m pytest -q
```

## Limits

Fixed-rate senior notes only; floating-rate notes are extracted but not scored. Term sheets (FWP) only; prospectus supplements are out of scope. Four deals is a small benchmark. Each deal was run once, so run-to-run variation is not measured. The hosted app allows 20 Gemini runs a day across all visitors and 3 per visit; saved results do not count.

## Built on

- [google/langextract](https://github.com/google/langextract) (Apache-2.0): Provides extraction with character-level source grounding intervals and document visualization.
- [dgunning/edgartools](https://github.com/dgunning/edgartools) (MIT): Connects to SEC EDGAR to download Form FWP term sheets with required identity headers.
