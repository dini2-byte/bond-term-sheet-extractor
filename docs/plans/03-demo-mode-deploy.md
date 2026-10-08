# Slice 3: Demo mode and public deploy

**Implementer**: agy
**Reviewer**: Claude Code
**Branch**: `slice-03-demo-mode`, cut from `master` after slice 2 merged (`897076f`)
**Due**: 2026-10-20

Read `CONTEXT.md` first and use its terms.

## Goal

AINA reviewers open one link in an incognito window. The app must show the benchmark deals at once, with no API key and no setup. A stranger must not be able to spend the owner's Gemini quota. The app must say plainly how accurate it is and where the code lives.

## Rules

- Write each test before its code change where the logic is testable outside Streamlit. Put that logic in plain functions in a new module `demo.py` so it can be tested. `app.py` only calls it.
- Do not commit. Claude commits after review.
- Do not touch: `fields.py`, `extract.py`, `evaluate.py`, `structure.py`, `data/answer_key.json`, `data/fixtures/`, `SUBMISSION.md`, `README.md`, any `.md` file in the repo root.
- No Gemini API calls while building this slice.

## Task A: Demo mode is the default

1. The sidebar source options become "Benchmark deals" (default) and "Upload a term sheet".
2. "Benchmark deals" lists only deals that have a fixture in `data/fixtures/`. Label each by issuer and trade date, not by file name. Example: `Apple Inc. - May 5, 2025`.
3. Selecting a deal loads its fixture and shows the comps table at once. No button press, no API call.
4. Remove the "Extract Bond Terms" button from demo mode.
5. Put the deal-listing and label logic in `demo.py` with tests (`tests/test_demo.py`).

## Task B: Source highlighting works from the fixture

`output/*.html` is gitignored, so the deployed app has no visualization file. Build the highlighted-source view at runtime from the fixture JSONL with `langextract.visualize`. Check whether `lx.visualize` accepts a JSONL path or needs loaded documents, and use whichever works. Cache the result with `st.cache_data`.

## Task C: Password-gated live upload

1. "Upload a term sheet" shows a password field first. Compare it with `st.secrets["APP_PASSWORD"]` using `hmac.compare_digest`.
2. If `APP_PASSWORD` is not set in secrets, the upload option shows "Live extraction is disabled on this deployment" and nothing else.
3. Only after a correct password does the file uploader and the "Extract Bond Terms" button appear.
4. Read the Gemini key from `st.secrets["GEMINI_API_KEY"]` first, then from the environment. Never print or log it.
5. Save the uploaded file under a fixed name inside a temp directory (`tempfile.mkdtemp()`). Never use `uploaded.name` in a path.
6. Reject uploads over 500 KB with a clear message.
7. Put the password check and size check in `demo.py` with tests.

## Task D: Say how accurate it is

1. Add a section "How accurate is this?" under the title. It shows the headline line from `output/accuracy_benchmark_report.md` (the line that starts with `Field accuracy:`), followed by the grounded and not-in-source lines.
2. If the report has a "Scoring changes after the first run" section, show one line under the headline for each change, built from `data/fixtures/scoring_changes.jsonl`: "First scored at <headline_before number> before this fix: <change>." Read the file with `evaluate.load_scoring_changes`.
3. Below that, one line: "Benchmark: 4 deals, 25 tranches, answer keys written before each deal was run. Each deal was run through Gemini once." Take the deal and tranche counts from the headline line, not hardcoded.
4. If the report file is missing, hide the section. Do not show a placeholder number.
5. Add a footer link: "Code and benchmark: https://github.com/dini2-byte/bond-term-sheet-extractor".
6. `output/accuracy_benchmark_report.md` must be tracked in git so the deployed app can read it. Check `.gitignore`.

## Task E: Use the glossary's words

1. Replace the sidebar text "Any ungrounded or hallucinated value is automatically flagged" with: "Every value links to the exact text it came from. Values that are not an exact match are flagged as not grounded. Fields not stated in the filing show Not found."
2. Remove the word "hallucinated" and "hallucination" from `app.py`.
3. Label the grounding card "Grounded", not "Exact Grounding".

## Task F: Deploy files

1. Add `.streamlit/secrets.toml.example` with `APP_PASSWORD = ""` and `GEMINI_API_KEY = ""`. The real `secrets.toml` stays gitignored.
2. Pin versions in `requirements.txt` to what is installed in `.venv` (`pip freeze` for the listed packages only, plus `python-dateutil`).
3. Add `runtime.txt` only if Streamlit Community Cloud needs it for Python 3.12. Check the current docs and say what you found.

## Deliverable

Leave changes uncommitted on `slice-03-demo-mode`. Report:
1. `git status --short` and `git diff --stat`
2. Failing then passing output for each new test
3. Full `python3 -m pytest -q`
4. Output of `streamlit run app.py --server.headless true` for 15 seconds, showing it starts with no errors
5. Anything you were unsure about

## After agy: Aidin deploys

Claude gives Aidin the exact steps: create the app on share.streamlit.io from the private repo, paste the secrets, open the URL in incognito. Deploying needs Aidin's Streamlit account, so Claude cannot do it.
