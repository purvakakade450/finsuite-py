"""The bank-statement importer is plain JavaScript; run it under Node (skipped if Node is missing)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "frontend" / "js" / "statement.js"
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")


def run(js: str):
    code = f"const s = require({json.dumps(str(SCRIPT))}); const out = ({js}); console.log(JSON.stringify(out));"
    result = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


HDFC_STYLE = """Account Number: 5010XXXX1234
Statement From: 01/09/2025 To: 31/10/2025

Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance
01/09/25,SALARY CREDIT ACME PVT LTD,N1,01/09/25,,"85,000.00","92,000.00"
02/09/25,UPI-LANDLORD RENT SEPT,N2,02/09/25,"22,000.00",,"70,000.00"
03/09/25,UPI-BIGBASKET-ORDER,N3,03/09/25,"2,350.50",,"67,649.50"
05/09/25,UPI-SWIGGY,N4,05/09/25,640.00,,"67,009.50"
07/09/25,NACH HDFC HOME LOAN EMI,N5,07/09/25,"14,500.00",,"52,509.50"
10/09/25,ZERODHA MUTUAL FUND SIP,N6,10/09/25,"10,000.00",,"42,509.50"
20/09/25,UPI-RAHUL SHARMA,N7,20/09/25,"1,500.00",,"41,009.50"
25/09/25,TRANSFER TO SELF SAVINGS,N8,25/09/25,"5,000.00",,"36,009.50"
01/10/25,SALARY CREDIT ACME PVT LTD,N9,01/10/25,,"85,000.00","121,009.50"
02/10/25,UPI-LANDLORD RENT OCT,N10,02/10/25,"22,000.00",,"99,009.50"
13/10/25,NACH HDFC HOME LOAN EMI,N11,13/10/25,"14,500.00",,"84,509.50"

Opening Balance,Debits,Credits,Closing
"""

ONE_AMOUNT_COLUMN = """Transaction Date;Description;Amount;Dr/Cr
03-Nov-2025;NETFLIX.COM;649.00;Dr
05-Nov-2025;SALARY NOV;60000.00;Cr
08-Nov-2025;UBER INDIA;320.00;Dr
"""


def test_finds_the_header_below_account_details_and_reads_quoted_amounts():
    r = run(f"s.analyseStatement({json.dumps(HDFC_STYLE)})")
    assert r["ok"] and r["months"] == 2 and r["transactions"] == 11
    assert r["income_monthly"] == pytest.approx(85_000) and r["income_source"] == "salary credits"
    by = {c["category"]: c for c in r["categories"]}
    assert by["Rent"]["total"] == 44_000 and by["Rent"]["monthly"] == 22_000
    assert by["Loan EMI"]["total"] == 29_000
    assert by["Groceries"]["total"] == pytest.approx(2350.50)
    assert by["Investments (SIP, stocks, FD)"]["kind"] == "saving"
    assert by["Dining out"]["kind"] == "want"


def test_transfers_between_own_accounts_are_ignored_and_unknown_payees_grouped():
    r = run(f"s.analyseStatement({json.dumps(HDFC_STYLE)})")
    assert r["skipped"] == 1
    assert r["other"]["total"] == 1_500 and "RAHUL SHARMA".split()[0].lower() in " ".join(r["other"]["examples"]).lower()


def test_single_amount_column_with_a_debit_credit_flag_and_semicolons():
    r = run(f"s.analyseStatement({json.dumps(ONE_AMOUNT_COLUMN)})")
    assert r["ok"] and r["months"] == 1 and r["income_monthly"] == 60_000
    by = {c["category"]: c["total"] for c in r["categories"]}
    assert by["Subscriptions"] == 649 and by["Transport"] == 320


def test_unreadable_files_give_a_clear_message():
    assert run("s.analyseStatement('hello world')")["ok"] is False
    assert run("s.analyseStatement('Date,Narration,Debit\\nnot a date,x,5')")["ok"] is False


@pytest.mark.parametrize("text,expected", [
    ("03/11/2025", {"y": 2025, "m": 11, "d": 3}), ("3-11-25", {"y": 2025, "m": 11, "d": 3}),
    ("2025-11-03", {"y": 2025, "m": 11, "d": 3}), ("03-Nov-2025", {"y": 2025, "m": 11, "d": 3}),
    ("3 Nov 25", {"y": 2025, "m": 11, "d": 3}), ("31/13/2025", None), ("hello", None),
])
def test_date_formats(text, expected):
    assert run(f"s.parseDate({json.dumps(text)})") == expected


@pytest.mark.parametrize("text,expected", [
    ("1,234.56", 1234.56), ("₹ 500", 500), ("(250.00)", -250), ("-75.5", -75.5), ("1200 Dr", -1200), ("", None), ("abc", None),
])
def test_amounts(text, expected):
    assert run(f"s.parseAmount({json.dumps(text)})") == expected


def test_csv_parser_handles_quotes_commas_and_blank_lines():
    rows = run("s.parseCsv('a,\"b, c\",d\\r\\n\\r\\n\"say \"\"hi\"\"\",2,3\\n')")
    assert rows == [["a", "b, c", "d"], ['say "hi"', "2", "3"]]
