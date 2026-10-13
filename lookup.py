"""
lookup.py: SEC EDGAR company lookup and rate limiting for live term sheet extraction.
No Streamlit imports; all functions are independently testable.
"""

from datetime import date
import json
import os
import re
from typing import Any, Callable

from cache import ObjectStore

try:
    import edgar
    DEFAULT_COMPANY_CLS = edgar.Company
except ImportError:
    DEFAULT_COMPANY_CLS = None  # type: ignore

FETCH_PLACEHOLDER = "Baruch Student bstudent@baruch.cuny.edu"

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def edgar_filing_url(accession: str) -> str:
    """Returns SEC EDGAR filing index page URL for a given accession number."""
    if "-" in accession:
        parts = accession.split("-")
        try:
            cik = int(parts[0])
            nodash = accession.replace("-", "")
            return f"https://www.sec.gov/Archives/edgar/data/{cik}/{nodash}/{accession}-index.htm"
        except ValueError:
            pass
    return f"https://www.sec.gov/edgar/search/#/q={accession}"



def normalize_ticker(raw: str | None) -> str:
    """
    Strips and upper-cases the input.
    Raises ValueError("Enter a stock ticker, for example KO.") when invalid.
    """
    if raw is None or not isinstance(raw, str):
        raise ValueError("Enter a stock ticker, for example KO.")
    cleaned = raw.strip().upper()
    if not TICKER_PATTERN.match(cleaned):
        raise ValueError("Enter a stock ticker, for example KO.")
    return cleaned


def is_bond_term_sheet(text: str) -> bool:
    """
    True when the first 4,000 characters match (pricing|final)\\s+term\\s+sheet (case-insensitive),
    the text contains CUSIP and it matches Notes due \\d{4}.
    """
    if not text or not isinstance(text, str):
        return False
    if not re.search(r"(pricing|final)\s+term\s+sheet", text[:4000], re.IGNORECASE):
        return False
    if "CUSIP" not in text:
        return False
    if not re.search(r"Notes due \d{4}", text, re.IGNORECASE):
        return False
    return True


def is_valid_cusip(s: str) -> bool:
    """Validates 9-character CUSIP check digit using standard Mod 10 Luhn-like algorithm."""
    if len(s) != 9:
        return False
    chars = s.upper()
    total = 0
    for i, c in enumerate(chars[:8]):
        if "0" <= c <= "9":
            val = ord(c) - ord("0")
        elif "A" <= c <= "Z":
            val = ord(c) - ord("A") + 10
        elif c == "*":
            val = 36
        elif c == "@":
            val = 37
        elif c == "#":
            val = 38
        else:
            return False
        weight = 2 if (i % 2 == 1) else 1
        prod = val * weight
        total += (prod // 10) + (prod % 10)
    check = (10 - (total % 10)) % 10
    return chars[8] == str(check)


def count_bonds(text: str) -> int:
    """
    Counts number of distinct 9-character tokens that pass the CUSIP check digit
    and are not the 9 middle characters of an XS ISIN in the same text.
    Handles standard CUSIP format: 6 alphanumeric + optional space + 3 alphanumeric.
    """
    if not text:
        return 0
    xs_isins = re.findall(r"XS[0-9A-Za-z]{10}", text.upper())
    xs_middle_9 = {isin[2:11] for isin in xs_isins}

    matches = re.findall(r"(?<![A-Za-z0-9])([A-Za-z0-9]{6})\s*([A-Za-z0-9]{3})(?![A-Za-z0-9])", text)
    cusips = set()
    for a, b in matches:
        token = f"{a}{b}".upper()
        if token in xs_middle_9:
            continue
        if is_valid_cusip(token):
            cusips.add(token)
    return len(cusips)


IGNORE_PATTERNS = [
    re.compile(r"concurrent\s+offering", re.IGNORECASE),
    re.compile(r"use\s+of\s+proceeds", re.IGNORECASE),
    re.compile(r"expenses", re.IGNORECASE),
    re.compile(r"credit\s+agreement", re.IGNORECASE),
]

CURRENCY_SYMBOLS = {
    "$": "USD",
    "USD": "USD",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
    "¥": "JPY",
    "JPY": "JPY",
}


def _parse_principal_amount(num_str: str, unit_str: str | None) -> float:
    cleaned = num_str.replace(",", "")
    try:
        val = float(cleaned)
    except ValueError:
        return 0.0
    if unit_str:
        u = unit_str.lower()
        if "b" in u:
            val *= 1_000_000_000
        elif "m" in u:
            val *= 1_000_000
    return val


def deal_currencies(text: str) -> list[str]:
    """
    Returns sorted list of currencies of principal amounts of 1,000,000 or more,
    ignoring lines that mention a concurrent offering, use of proceeds, expenses,
    or a credit agreement.
    """
    if not text:
        return []
    found_currencies = set()
    for line in text.splitlines():
        if any(p.search(line) for p in IGNORE_PATTERNS):
            continue

        for m in re.finditer(
            r"([$€£¥]|(?:USD|EUR|GBP|JPY))\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(billion|bn|b|million|mn|mm)?\b",
            line,
            re.IGNORECASE,
        ):
            cur = CURRENCY_SYMBOLS.get(m.group(1).upper() if len(m.group(1)) > 1 else m.group(1))
            amt = _parse_principal_amount(m.group(2), m.group(3))
            if amt >= 1_000_000 and cur:
                found_currencies.add(cur)

        for m in re.finditer(
            r"\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(billion|bn|b|million|mn|mm)?\s*(USD|EUR|GBP|JPY)\b",
            line,
            re.IGNORECASE,
        ):
            amt = _parse_principal_amount(m.group(1), m.group(2))
            cur = CURRENCY_SYMBOLS.get(m.group(3).upper())
            if amt >= 1_000_000 and cur:
                found_currencies.add(cur)

    return sorted(found_currencies)


def find_term_sheets(
    ticker: str,
    scan: int = 25,
    max_chars: int = 60_000,
    company_cls: Any = DEFAULT_COMPANY_CLS,
) -> list[dict[str, Any]]:
    """
    Looks at the latest `scan` FWP filings for the ticker and keeps those
    where is_bond_term_sheet is True and the text is at most max_chars long.
    Each result has accession, filing_date (ISO string), chars, bond_count, currencies, and text.
    Silently drops results with a currency outside USD, EUR and GBP or with no currency found.
    Newest first.
    An unknown ticker raises LookupError("No SEC filer found for <TICKER>.").
    """
    norm_ticker = normalize_ticker(ticker)
    if company_cls is None:
        raise RuntimeError("edgartools is not available and no company_cls was provided.")

    try:
        company = company_cls(norm_ticker)
    except LookupError as e:
        raise LookupError(f"No SEC filer found for {norm_ticker}.") from e
    except Exception as e:
        raise LookupError(f"No SEC filer found for {norm_ticker}.") from e

    if company is None or getattr(company, "not_found", False):
        raise LookupError(f"No SEC filer found for {norm_ticker}.")

    if hasattr(company, "get_filings"):
        filings = company.get_filings(form="FWP")
    elif hasattr(company, "filings"):
        filings = company.filings
    else:
        filings = []

    filings_list: list[Any] = []
    if filings is not None:
        if hasattr(filings, "latest") and callable(filings.latest):
            res = filings.latest(scan)
            if res is None:
                filings_list = []
            elif hasattr(res, "__iter__") and not isinstance(res, (str, bytes)):
                filings_list = list(res)
            else:
                filings_list = [res]
        elif hasattr(filings, "__iter__"):
            filings_list = list(filings)[:scan]
        else:
            filings_list = [filings]

    filings_list = filings_list[:scan]

    # Ensure newest first by filing date
    filings_list.sort(
        key=lambda f: str(getattr(f, "filing_date", None) or getattr(f, "date", "") or "")[:10],
        reverse=True,
    )

    results: list[dict[str, Any]] = []
    for f in filings_list:
        text_val = f.text() if callable(getattr(f, "text", None)) else getattr(f, "text", "")
        if not isinstance(text_val, str):
            text_val = str(text_val)

        if not is_bond_term_sheet(text_val):
            continue

        chars = len(text_val)
        if chars > max_chars:
            continue

        curs = deal_currencies(text_val)
        if not curs or not set(curs).issubset({"USD", "EUR", "GBP"}):
            continue

        raw_date = getattr(f, "filing_date", None) or getattr(f, "date", None)
        if hasattr(raw_date, "isoformat"):
            date_str = raw_date.isoformat()
        elif raw_date:
            date_str = str(raw_date)[:10]
        else:
            date_str = ""

        accession = (
            getattr(f, "accession", None)
            or getattr(f, "accession_number", None)
            or getattr(f, "accession_no", None)
            or ""
        )

        results.append({
            "accession": str(accession),
            "filing_date": date_str,
            "chars": chars,
            "bond_count": count_bonds(text_val),
            "currencies": curs,
            "text": text_val,
        })

    return results


def get_edgar_identity(secrets: Any = None) -> str | None:
    """
    EDGAR_IDENTITY from Streamlit secrets, then the environment.
    Returns None when neither is set.
    Never falls back to the placeholder in fetch.py.
    """
    val = None
    if secrets is not None:
        try:
            if isinstance(secrets, dict) and "EDGAR_IDENTITY" in secrets:
                val = secrets["EDGAR_IDENTITY"]
            elif hasattr(secrets, "get"):
                val = secrets.get("EDGAR_IDENTITY")
            elif hasattr(secrets, "__getitem__"):
                val = secrets["EDGAR_IDENTITY"]
        except (KeyError, TypeError):
            pass

    if not val:
        val = os.getenv("EDGAR_IDENTITY")

    if not val or not str(val).strip():
        return None

    cleaned = str(val).strip()
    if cleaned == FETCH_PLACEHOLDER:
        return None
    return cleaned


class RunBudget:
    """
    Tracks runs per calendar day across the whole site.
    With a store, the day's count is kept in it so it survives restarts.
    Without one, the count lives in memory and resets when today() changes.
    """

    def __init__(
        self,
        daily_limit: int = 20,
        session_limit: int = 3,
        today: Callable[[], date] = date.today,
        store: ObjectStore | None = None,
    ):
        self.daily_limit = daily_limit
        self.session_limit = session_limit
        self.today = today
        self.store = store
        self._current_date = self.today()
        self._daily_count = 0

    def _key(self) -> str:
        return f"budget/{self.today().isoformat()}.json"

    def _check_reset(self) -> None:
        current = self.today()
        if current != self._current_date:
            self._current_date = current
            self._daily_count = 0

    def _count(self) -> int:
        if self.store is None:
            self._check_reset()
            return self._daily_count
        text = self.store.get_text(self._key())
        if not text:
            return 0
        try:
            return int(json.loads(text)["count"])
        except (ValueError, KeyError, TypeError):
            return 0

    def remaining(self) -> int:
        return max(0, self.daily_limit - self._count())

    def can_run(self, session_runs: int = 0) -> tuple[bool, str | None]:
        if self._count() >= self.daily_limit:
            return False, f"Today's {self.daily_limit} free runs are used up. Try again tomorrow."
        if session_runs >= self.session_limit:
            return False, f"You've used your {self.session_limit} runs for this visit."
        return True, None

    def record_run(self) -> None:
        if self.store is None:
            self._check_reset()
            self._daily_count += 1
            return
        self.store.put_text(self._key(), json.dumps({"count": self._count() + 1}))

