# Slice 10 UI Overhaul Report

## Tasks

| Task | Description | Commit |
|---|---|---|
| Task 1 | Tests use their own disk store | `90debae` |
| Task 2 | Theme tokens, config and CSS | `081dfb5` |
| Task 3 | Uploads run through the runner | `205f1d5` |
| Task 4 | Results view shared by Search and Upload | `440a96c` |
| Task 5 | Search and Upload tab views | `1677cac` |
| Task 6 | Rebuild page as a search tool and drop legacy code | `3d3dd28` |
| Task 7 | Documentation, environment updates and final report | (pending) |

## Tests added

- `tests/test_cache.py`:
  - `test_default_disk_root_reads_the_env`: verifies reading `TERM_SHEET_CACHE_DIR`.
  - `test_default_disk_root_falls_back_to_dot_cache`: verifies fallback to `.cache`.
  - `test_tests_never_use_the_repo_cache`: verifies `isolated_store` fixture redirects `make_store`.
- `tests/test_theme.py`:
  - `test_config_section_matches_tokens[light]`: checks config toml matches light tokens.
  - `test_config_section_matches_tokens[dark]`: checks config toml matches dark tokens.
  - `test_tokens_match_the_spec`: verifies light and dark color hex values match specification.
  - `test_fonts_are_inter_tight_and_jetbrains_mono`: verifies Google Fonts links in config.
  - `test_css_uses_only_mode_neutral_colors`: ensures no `prefers-color-scheme` and allowed hexes only.
  - `test_css_has_the_pieces_the_page_uses`: verifies all required selectors and styles exist.
- `tests/test_runner.py`:
  - `test_upload_charges_one_run_and_never_touches_the_cache`: verifies upload execution, charge and cache isolation.
  - `test_failed_upload_charges_nothing`: verifies failure refunds run budget.
  - `test_upload_without_key_or_budget_is_blocked`: verifies key and budget checks.
  - `test_extractor_that_writes_nothing_is_a_failure`: verifies handling when output file is missing.
- `tests/test_views.py`:
  - `TestBuildDealLine` (4 tests moved from `test_app_ui.py`): tests for USD, EUR, GBP and multi-currency deal lines.
  - `test_status_tags`: verifies mapping to uppercase status chip labels.
  - `test_source_panel_escapes_text_and_keeps_the_quote_html`: tests card HTML formatting.
  - `test_source_panel_without_quote_has_no_quote_block`: tests missing quote omission.
  - `test_column_config_uses_the_deal_currency`: tests dynamic size column currency label.
  - `test_excel_bytes_is_an_xlsx_file`: verifies valid openxml xlsx export output.
  - `test_sheet_labels_name_the_currency`: tests currency naming logic in radio labels.
  - `test_saved_sheets_carry_the_tag`: tests `SAVED` chip presence on cached term sheets.
  - `test_runs_hint`: verifies daily run counter text format.
- `tests/test_app_ui.py`:
  - `test_opens_on_the_search_tab`: tests initial state, tab names, top bar, input box and budget hint.
  - `test_no_saved_deal_picker_password_or_sidebar`: verifies removal of selectbox, password, sidebar and expanders.
  - `test_upload_tab_has_an_uploader`: verifies presence of file uploader in second tab.
  - `test_search_not_set_up_without_identity`: verifies info alert when EDGAR identity is missing.
  - `test_saved_filing_opens_free`: verifies clicking saved filing opens comps table without spending a run.
  - `test_unsaved_filing_extracts_charges_and_saves`: verifies unsaved filing extract button charges one run and saves result.
  - `test_budget_exhausted_blocks_extract`: verifies cap error message blocks extraction.
  - `test_no_gemini_key_shows_message`: verifies missing API key blocks extraction.
  - `test_page_text_rules`: enforces no emoji, no em or en dashes, banned words list and no accuracy report stats.
  - `test_how_it_works_is_short`: enforces dialog length between 1 and 5 sentences.
  - `test_font_family_only_in_theme`: ensures no `font-family` CSS leakage in application views.
  - `test_headings_have_no_link_anchor`: verifies header anchor link icons are hidden.

## Tests deleted or rewritten

- `tests/test_app_ui.py`:
  - `TestAppUi.test_app_runs_no_exceptions_and_defaults_to_aapl`: deleted because the saved deals picker was replaced by ticker search.
  - `TestAppUi.test_one_dataframe_with_single_cell_selection_mode`: rewritten into `test_saved_filing_opens_free` where table loads after filing selection.
  - `TestAppUi.test_step_3_card_shows_4_000_pct_on_first_load`: rewritten into `test_saved_filing_opens_free` for the updated source card format.
  - `TestAppUi.test_three_step_subheaders_in_order`: deleted because the old numbered step subheaders were removed.
  - `TestAppUi.test_no_emoji_and_no_never_show_words`: replaced by `test_page_text_rules` covering tabs and dialog.
  - `TestAppUi.test_single_select_enforced_on_multi_cell_click`: deleted because selection mode is tested directly via table configuration.
  - `TestAppUi.test_search_company_selects_and_runs`: replaced by `test_saved_filing_opens_free` and `test_unsaved_filing_extracts_charges_and_saves`.
  - `TestAppUi.test_budget_exhausted_shows_cap_message_and_blocks_extract`: replaced by `test_budget_exhausted_blocks_extract` using the new extract button.
  - `TestAppUi.test_lookup_extract_without_gemini_key_shows_message`: replaced by `test_no_gemini_key_shows_message` using the new extract button.
  - `TestBuildDealLine`: moved to `tests/test_views.py` because `build_deal_line` moved to `views/results.py`.
  - `TestSearchPickerCurrencyLabel`: moved to `tests/test_views.py` (`test_sheet_labels_name_the_currency`) for fast direct unit testing.
  - `test_headings_have_no_link_anchor`: rewritten to inspect `at.header` and `at.subheader` instead of `at.title`.
- `tests/test_demo.py`:
  - `TestDealListing.test_format_deal_label`: deleted because `format_deal_label` was removed from `demo.py`.
  - `TestDealListing.test_list_benchmark_deals_returns_known_fixtures`: deleted because `list_benchmark_deals` was removed from `demo.py`.
  - `TestDealListing.test_deal_labels_match_glossary_and_example`: deleted because `list_benchmark_deals` was removed from `demo.py`.
  - `TestDealListing.test_list_benchmark_deals_ignores_non_deal_jsonl`: deleted because `list_benchmark_deals` was removed from `demo.py`.
  - `TestSourceHighlighting.test_build_visualization_html`: deleted because `build_visualization_html` was removed from `demo.py`.
  - `TestVisualizationSrc.test_visualization_src_prefix_and_roundtrip`: deleted because `visualization_src` was removed from `demo.py`.
  - `TestVisualizationSrc.test_visualization_src_no_script_substring`: deleted because `visualization_src` was removed from `demo.py`.
  - `TestPasswordAndUpload.test_check_password_correct`: deleted because `check_password` was removed from `demo.py`.
  - `TestPasswordAndUpload.test_check_password_incorrect`: deleted because `check_password` was removed from `demo.py`.
  - `TestPasswordAndUpload.test_check_password_empty_or_none`: deleted because `check_password` was removed from `demo.py`.
  - `TestPasswordAndUpload.test_save_uploaded_filing_fixed_name`: deleted because `save_uploaded_filing` was removed from `demo.py`.
  - `TestAccuracyReport.test_extract_headline_number`: deleted because `extract_headline_number` was removed from `demo.py`.
  - `TestAccuracyReport.test_extract_deal_and_tranche_counts`: deleted because `extract_deal_and_tranche_counts` was removed from `demo.py`.
  - `TestAccuracyReport.test_format_scoring_change_line`: deleted because `format_scoring_change_line` was removed from `demo.py`.
  - `TestAccuracyReport.test_parse_accuracy_report_real_file`: deleted because `parse_accuracy_report` was removed from `demo.py`.
  - `TestAccuracyReport.test_parse_accuracy_report_missing_file`: deleted because `parse_accuracy_report` was removed from `demo.py`.
  - `TestStreamlitDeprecations.test_app_renders_iframe_without_deprecation_warnings`: deleted because the legacy iframe and langextract visualization were removed.
  - `TestLiveUploadG1.test_live_upload_passes_log_attempt_false_and_temp_output_dir`: deleted because the password protection flow was replaced by the unauthenticated upload tab.

## Skipped or changed from plan

None. All steps were carried out as specified.
Note on Streamlit server startup: Streamlit 1.64 emits a warning on startup noting that `theme.light.base` and `theme.dark.base` are not valid config options in `.streamlit/config.toml`. The options were preserved to strictly follow the plan and test specifications, and the server runs normally.

## What a reviewer should look at first

1. `views/results.py`: shared results component used by both tabs, including single cell table selection, source panel card formatting and Excel download.
2. `views/search.py`: EDGAR search tab, ticker normalization, cached term sheet search, saved status check and extraction workflow.
3. `views/upload.py`: upload tab, size limits, SHA-256 digest session state check and live upload runner invocation.
4. `theme.py` and `.streamlit/config.toml`: Ramp-style light and dark theme configuration with mode-neutral transparent CSS.
5. `app.py`: slim top bar with How it works dialog, tabs and resource caching with startup seeding for disk stores.

## Verification outputs

### pytest

```
........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 68%]
........................................................................ [ 91%]
...........................                                              [100%]
315 passed in 8.74s
```

### evaluate.py

```
Field accuracy: 98.3% (344/350 fields, 4 deals, 25 tranches)
Grounded: 55.5% (186/335 extracted fields)
Not-in-source: 0.0% (0/335 extracted fields)
```

### Streamlit smoke test (timeout 15s)

```
2026-10-13 21:54:03.742 "theme.light.base" is not a valid config option. If you previously had this config option set, it may have been removed.
2026-10-13 21:54:03.743 "theme.dark.base" is not a valid config option. If you previously had this config option set, it may have been removed.

Collecting usage statistics. To deactivate, set browser.gatherUsageStats to false.

2026-10-13 21:54:03.976 Uvicorn server started on :::8501

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://172.27.178.62:8501
  External URL: http://141.155.149.171:8501

  Detected WSL. Using poll-based file watching for better compatibility. To force watchdog, set server.fileWatcherType = "watchdog".
  Stopping...
```

### git log --oneline master..slice-10-ui

```
3d3dd28 feat: rebuild the page as a search tool
1677cac feat: add search and upload tabs
440a96c feat: add shared results view
205f1d5 feat: run uploads through the run budget
081dfb5 feat: add light and dark theme tokens
90debae test: give each test its own disk store
```

### git diff --stat master

```
 .env.example                    |   1 +
 .streamlit/config.toml          |  37 ++-
 .streamlit/secrets.toml.example |   1 -
 README.md                       |  16 +-
 app.py                          | 698 ++--------------------------------------
 cache.py                        |  13 +-
 demo.py                         | 208 +-----------
 runner.py                       |  70 ++--
 tests/conftest.py               |  18 ++
 tests/test_app_ui.py            | 520 ++++++++++--------------------
 tests/test_cache.py             |  17 +
 tests/test_demo.py              | 196 +----------
 tests/test_runner.py            |  34 ++
 tests/test_theme.py             |  49 +++
 tests/test_views.py             | 109 +++++++
 theme.py                        |  65 ++++
 views/__init__.py               |   1 +
 views/about.py                  |  10 +
 views/results.py                | 235 ++++++++++++++
 views/search.py                 | 174 ++++++++++
 views/upload.py                 |  70 ++++
 21 files changed, 1103 insertions(+), 1439 deletions(-)
```
