"""Writes docs/FinSuite_Project_Report_Supplement_v2.pdf: Chapter 9 and Appendix D of the project
report (the version 2.0 material), taken from docs/FinSuite_Project_Report.docx.

    python docs/export_supplement_pdf.py

For the whole report as one PDF, open the .docx in Word and choose File > Save as PDF.
"""
import base64
import html
from pathlib import Path

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

HERE = Path(__file__).resolve().parent
d = docx.Document(HERE / "FinSuite_Project_Report.docx")
body = list(d.element.body)
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def is_heading1(el, text):
    return el.tag.endswith("}p") and Paragraph(el, d).style.name == "Heading 1" and Paragraph(el, d).text.strip().startswith(text)


def index_of(text):
    return next(i for i, el in enumerate(body) if is_heading1(el, text))


i9, iref, iappd = index_of("Chapter 9:"), index_of("References"), index_of("Appendix D:")
elements = body[i9:iref] + body[iappd:]
out, in_list = [], False
for el in elements:
    if el.tag.endswith("}tbl"):
        if in_list: out.append("</ul>"); in_list = False
        t = Table(el, d)
        rows = ["<tr>" + "".join(f"<{'th' if r == 0 else 'td'}>{html.escape(c.text)}</{'th' if r == 0 else 'td'}>" for c in row.cells) + "</tr>"
                for r, row in enumerate(t.rows)]
        out.append("<table>" + "".join(rows) + "</table>")
        continue
    if not el.tag.endswith("}p"):
        continue
    p = Paragraph(el, d)
    style, text = p.style.name, html.escape(p.text)
    blips = el.findall(".//a:blip", NS)
    if style == "List Bullet":
        if not in_list: out.append("<ul>"); in_list = True
        out.append(f"<li>{text}</li>")
        continue
    if in_list: out.append("</ul>"); in_list = False
    if blips:
        for b in blips:
            blob = d.part.related_parts[b.get("{%s}embed" % NS["r"])].blob
            out.append(f"<p class='img'><img src='data:image/png;base64,{base64.b64encode(blob).decode()}'></p>")
    elif style == "Heading 1":
        out.append(f"<h1>{text}</h1>")
    elif style == "Heading 2":
        out.append(f"<h2>{text}</h2>")
    elif style == "Heading 3":
        out.append(f"<h3>{text}</h3>")
    elif style == "Caption":
        out.append(f"<p class='cap'>{text}</p>")
    elif text.strip():
        out.append(f"<p>{text}</p>")
if in_list: out.append("</ul>")

CSS = """
@page { size: A4; margin: 22mm 22mm 24mm 28mm; }
body { font-family: 'Times New Roman', serif; font-size: 11.5pt; line-height: 1.45; text-align: justify; }
h1 { font-size: 17pt; margin: 0 0 6mm; break-before: page; break-after: avoid; }
h1:first-of-type { break-before: auto; }
h2 { font-size: 13pt; margin: 6mm 0 2mm; break-after: avoid; }
p { margin: 0 0 3mm; orphans: 3; widows: 3; }
.cap { font-size: 10pt; font-weight: bold; margin: 4mm 0 1.5mm; break-after: avoid; text-align: left; }
p.img { text-align: center; margin: 4mm 0 1mm; break-inside: avoid; break-after: avoid; }
p.img + p.cap { text-align: center; font-weight: normal; font-style: italic; break-before: avoid; }
img { max-width: 100%; max-height: 215mm; }
table { width: 100%; border-collapse: collapse; font-size: 9.6pt; margin-bottom: 4mm; }
th, td { border: 0.6px solid #000; padding: 1.2mm 1.8mm; vertical-align: top; text-align: left; }
th { background: #eee; }
tr { break-inside: avoid; }
ul { margin: 0 0 3mm 6mm; padding: 0; }
"""
doc = (f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
       "<p style='text-align:center;font-size:10pt;margin-bottom:8mm;'><i>FinSuite Project Report: supplement for version 2.0 (Chapter 9 and Appendix D). "
       "The complete report is FinSuite_Project_Report.docx.</i></p>" + "".join(out) + "</body></html>")

from playwright.sync_api import sync_playwright
footer = ("<div style=\"width:100%;text-align:center;font-family:'Times New Roman',serif;font-size:9px;\">"
          "Supplement, page <span class='pageNumber'></span> of <span class='totalPages'></span></div>")
with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page()
    page.set_content(doc)
    page.pdf(path=str(HERE / "FinSuite_Project_Report_Supplement_v2.pdf"), format="A4", print_background=True,
             display_header_footer=True, header_template="<div></div>", footer_template=footer,
             margin={"top": "22mm", "bottom": "24mm", "left": "28mm", "right": "22mm"})
    browser.close()
print("written", HERE / "FinSuite_Project_Report_Supplement_v2.pdf")
