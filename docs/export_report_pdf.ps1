# Opens docs\FinSuite_Project_Report.docx in Microsoft Word, refreshes the table of contents and page
# numbers, and saves it. Add -Pdf to also write docs\FinSuite_Project_Report.pdf (on some machines Word's
# PDF export hangs when started from a script; then use File > Save as PDF in Word, or
# docs/export_supplement_pdf.py for the version 2.0 part only).
param([switch]$Pdf)
$docs = $PSScriptRoot
function Log($m) { Write-Host ((Get-Date -Format "HH:mm:ss") + "  " + $m) }
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open((Join-Path $docs "FinSuite_Project_Report.docx"), $false, $false)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Save()
    Log ("saved; pages: " + $doc.ComputeStatistics(2))
    if ($Pdf) {
        $doc.ExportAsFixedFormat((Join-Path $docs "FinSuite_Project_Report.pdf"), 17)   # 17 = PDF
        Log "pdf written"
    }
    $doc.Close($false)
} finally {
    $word.Quit()
}
