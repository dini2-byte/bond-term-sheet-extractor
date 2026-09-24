"""
fields.py: Prompt descriptions and few-shot examples for bond term sheet extraction using LangExtract.
Defines debt capital markets (DCM) fields, multi-tranche tagging, and grounding constraints.
"""

import langextract as lx

# Target fields to extract for debt capital markets (DCM) comps tables
BOND_FIELDS = [
    "tranche_name",
    "issuer",
    "ratings",
    "trade_date",
    "settlement_date",
    "principal_amount",
    "coupon",
    "issue_price",
    "yield_to_maturity",
    "spread_bps",
    "benchmark_treasury",
    "maturity_date",
    "interest_payment_dates",
    "day_count",
    "make_whole_call",
    "par_call_date",
    "ranking",
    "cusip",
    "bookrunners",
]

PROMPT_DESCRIPTION = """
You are an expert Debt Capital Markets (DCM) analyst extracting key pricing terms from corporate bond term sheets (FWP) and prospectus supplements (424B2 / 424B5).

Instructions:
1. Extract all pricing and structural terms for each bond tranche present in the document.
2. Documents often contain multiple tranches (e.g., 3-year, 5-year, 10-year notes). For EVERY extraction, you MUST populate the 'tranche' attribute specifying which tranche the term belongs to (e.g., '2028 Notes', '2030 Notes'). For deal-level terms that apply to all tranches (like Issuer or Trade Date), set attributes={'tranche': 'all'}.
3. STRICT GROUNDING: Extract ONLY text that appears verbatim in the document. Do not calculate, extrapolate, guess, or rephrase numbers or dates.
4. If a field is absent from the text, DO NOT extract it. A missing field must remain absent.
5. Standard fields to extract:
   - tranche_name: Title of the specific bond tranche
   - issuer: Legal entity issuing the debt
   - ratings: Credit ratings from Moody's, S&P, or Fitch if stated
   - trade_date: Pricing or trade date
   - settlement_date: Closing or settlement date (including T-plus convention if mentioned)
   - principal_amount: Face value / aggregate principal amount offered for this tranche
   - coupon: Stated annual fixed interest rate (e.g. 5.125%)
   - issue_price: Price to public expressed as percentage of par (e.g. 99.612%)
   - yield_to_maturity: Reoffer yield / yield to maturity (e.g. 5.214%)
   - spread_bps: Spread to the benchmark Treasury in basis points (e.g. 85 basis points or +85 bps)
   - benchmark_treasury: Underlying benchmark Treasury note/bond used for pricing
   - maturity_date: Stated date when principal is repaid
   - interest_payment_dates: Schedule / dates when coupon payments occur
   - day_count: Day count convention (e.g. 30/360)
   - make_whole_call: Optional redemption terms prior to par call (e.g. Treasury Rate plus 5 bps)
   - par_call_date: Date on or after which issuer can redeem notes at 100% of par
   - ranking: Seniority ranking (e.g. Senior Unsecured Notes)
   - cusip: CUSIP or ISIN identifier
   - bookrunners: Joint book-running managers / underwriters
""".strip()

SAMPLE_TERM_SHEET = """
ACME CORP.
FINAL PRICING TERM SHEET
$2,000,000,000 Senior Notes

Issuer: Acme Corp.
Ratings: A2 / A
Trade Date: March 10, 2025
Settlement Date: March 17, 2025 (T+5)
Joint Bookrunners: Morgan Stanley, J.P. Morgan, Citigroup

3.850% Notes due 2028 ("2028 Notes")
Principal Amount: $1,250,000,000
Maturity Date: March 15, 2028
Coupon: 3.850%
Price to Public: 99.750%
Yield: 3.938%
Benchmark Treasury: 3.500% due February 28, 2028
Spread to Benchmark: +45 bps
Interest Payment Dates: March 15 and September 15, commencing September 15, 2025
Day Count: 30/360
Make-Whole Call: Treasury Rate + 10 bps prior to February 15, 2028
Par Call: On or after February 15, 2028
CUSIP: 001234AA1

5.375% Notes due 2035 ("2035 Notes")
Principal Amount: $750,000,000
Maturity Date: March 15, 2035
Coupon: 5.375%
Price to Public: 99.500%
Yield: 4.262%
Benchmark Treasury: 3.875% due February 15, 2035
Spread to Benchmark: +65 bps
Interest Payment Dates: March 15 and September 15, commencing September 15, 2025
Day Count: 30/360
Make-Whole Call: Treasury Rate + 15 bps prior to December 15, 2034
Par Call: On or after December 15, 2034
CUSIP: 001234AB9
""".strip()

FEW_SHOT_EXAMPLES = [
    lx.data.ExampleData(
        text=SAMPLE_TERM_SHEET,
        extractions=[
            # Deal-level extractions
            lx.data.Extraction(extraction_class="issuer", extraction_text="Acme Corp.", attributes={"tranche": "all"}),
            lx.data.Extraction(extraction_class="ranking", extraction_text="Senior Notes", attributes={"tranche": "all"}),
            lx.data.Extraction(extraction_class="ratings", extraction_text="A2 / A", attributes={"tranche": "all"}),
            lx.data.Extraction(extraction_class="trade_date", extraction_text="March 10, 2025", attributes={"tranche": "all"}),
            lx.data.Extraction(extraction_class="settlement_date", extraction_text="March 17, 2025 (T+5)", attributes={"tranche": "all"}),
            lx.data.Extraction(extraction_class="bookrunners", extraction_text="Morgan Stanley, J.P. Morgan, Citigroup", attributes={"tranche": "all"}),
            
            # Tranche 1: 2028 Notes
            lx.data.Extraction(extraction_class="tranche_name", extraction_text="3.850% Notes due 2028", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="principal_amount", extraction_text="$1,250,000,000", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="maturity_date", extraction_text="March 15, 2028", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="coupon", extraction_text="3.850%", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="issue_price", extraction_text="99.750%", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="yield_to_maturity", extraction_text="3.938%", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="benchmark_treasury", extraction_text="3.500% due February 28, 2028", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="spread_bps", extraction_text="+45 bps", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="interest_payment_dates", extraction_text="March 15 and September 15, commencing September 15, 2025", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="day_count", extraction_text="30/360", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="make_whole_call", extraction_text="Treasury Rate + 10 bps prior to February 15, 2028", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="par_call_date", extraction_text="On or after February 15, 2028", attributes={"tranche": "2028 Notes"}),
            lx.data.Extraction(extraction_class="cusip", extraction_text="001234AA1", attributes={"tranche": "2028 Notes"}),
            
            # Tranche 2: 2035 Notes
            lx.data.Extraction(extraction_class="tranche_name", extraction_text="5.375% Notes due 2035", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="principal_amount", extraction_text="$750,000,000", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="maturity_date", extraction_text="March 15, 2035", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="coupon", extraction_text="5.375%", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="issue_price", extraction_text="99.500%", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="yield_to_maturity", extraction_text="4.262%", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="benchmark_treasury", extraction_text="3.875% due February 15, 2035", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="spread_bps", extraction_text="+65 bps", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="interest_payment_dates", extraction_text="March 15 and September 15, commencing September 15, 2025", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="day_count", extraction_text="30/360", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="make_whole_call", extraction_text="Treasury Rate + 15 bps prior to December 15, 2034", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="par_call_date", extraction_text="On or after December 15, 2034", attributes={"tranche": "2035 Notes"}),
            lx.data.Extraction(extraction_class="cusip", extraction_text="001234AB9", attributes={"tranche": "2035 Notes"}),
        ]
    )
]
