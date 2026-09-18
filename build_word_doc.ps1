# build_word_doc.ps1
$ErrorActionPreference = "Stop"

$jsonFile = "c:\Users\Veon Admin\Downloads\Roffice_Appeal\doc_data.json"
$docxFile = "c:\Users\Veon Admin\Downloads\Roffice_Appeal\Registrator_Ofisi_Murojaatlar_Tizimi_Konsepsiya.docx"

Write-Host "Reading JSON data..."
$jsonBytes = [System.IO.File]::ReadAllBytes($jsonFile)
$jsonContent = [System.Text.Encoding]::UTF8.GetString($jsonBytes)
$data = $jsonContent | ConvertFrom-Json

Write-Host "Initializing Word COM object..."
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    $doc = $word.Documents.Add()

    # Page Margins: Left 3cm (85pt), Right 1.5cm (42.5pt), Top 2cm (56.7pt), Bottom 2cm (56.7pt)
    $doc.PageSetup.LeftMargin = 85.0
    $doc.PageSetup.RightMargin = 42.5
    $doc.PageSetup.TopMargin = 56.7
    $doc.PageSetup.BottomMargin = 56.7

    $selection = $word.Selection

    function Write-Para {
        param(
            [string]$text,
            [int]$size = 14,
            [int]$bold = 0,
            [int]$italic = 0,
            [int]$align = 3,
            [float]$indent = 28.35,
            [float]$spBefore = 0,
            [float]$spAfter = 4
        )
        $selection.Font.Name = "Times New Roman"
        $selection.Font.Size = $size
        $selection.Font.Bold = $bold
        $selection.Font.Italic = $italic
        $selection.ParagraphFormat.Alignment = $align
        $selection.ParagraphFormat.FirstLineIndent = $indent
        $selection.ParagraphFormat.SpaceBefore = $spBefore
        $selection.ParagraphFormat.SpaceAfter = $spAfter
        $selection.ParagraphFormat.LineSpacing = 16.0
        $selection.TypeText($text)
        $selection.TypeParagraph()
    }

    # Document Header
    Write-Para -text $data.meta.org -size 12 -bold 1 -align 1 -indent 0 -spAfter 2
    Write-Para -text $data.meta.recipient -size 12 -bold 1 -align 1 -indent 0 -spAfter 14

    # Title & Subtitle
    Write-Para -text $data.title -size 14 -bold 1 -align 1 -indent 0 -spBefore 6 -spAfter 8
    Write-Para -text $data.subtitle -size 13 -bold 1 -italic 1 -align 1 -indent 0 -spAfter 16

    # Iterate through sections
    foreach ($section in $data.sections) {
        # Section Heading
        Write-Para -text $section.title -size 14 -bold 1 -align 1 -indent 0 -spBefore 14 -spAfter 8

        foreach ($sub in $section.subsections) {
            # Subsection Heading
            Write-Para -text $sub.title -size 14 -bold 1 -align 0 -indent 0 -spBefore 8 -spAfter 4

            if ($sub.title -like "*3.1*") {
                # First paragraph
                Write-Para -text $sub.paragraphs[0] -size 14 -align 3 -indent 28.35 -spAfter 6

                # Insert SLA Table from JSON data
                Write-Host "Creating SLA Table..."
                $rowCount = $data.sla_table.Count
                $colCount = $data.sla_table[0].Count
                $table = $doc.Tables.Add($selection.Range, $rowCount, $colCount)
                $table.Borders.Enable = 1
                $table.Rows.Item(1).Range.Font.Name = "Times New Roman"
                $table.Rows.Item(1).Range.Font.Bold = 1
                $table.Rows.Item(1).Range.Font.Size = 13
                $table.Rows.Item(1).Range.ParagraphFormat.Alignment = 1

                for ($r = 0; $r -lt $rowCount; $r++) {
                    for ($c = 0; $c -lt $colCount; $c++) {
                        $cellVal = $data.sla_table[$r][$c]
                        $cell = $table.Cell($r + 1, $c + 1)
                        $cell.Range.Font.Name = "Times New Roman"
                        $cell.Range.Font.Size = 13
                        $cell.Range.Text = $cellVal
                    }
                }

                # Move selection past table
                $selection.SetRange($table.Range.End + 1, $table.Range.End + 1)
                $selection.TypeParagraph()

                # Remaining paragraphs
                for ($p = 1; $p -lt $sub.paragraphs.Count; $p++) {
                    $pText = $sub.paragraphs[$p]
                    if ($pText.StartsWith([char]0x2022)) {
                        Write-Para -text $pText -size 14 -align 3 -indent 0 -spAfter 3
                    } else {
                        Write-Para -text $pText -size 14 -align 3 -indent 28.35 -spAfter 4
                    }
                }
            }
            else {
                foreach ($pText in $sub.paragraphs) {
                    if ($pText.StartsWith([char]0x2022) -or $pText -match "^\d+\.") {
                        Write-Para -text $pText -size 14 -align 3 -indent 0 -spAfter 3
                    } else {
                        Write-Para -text $pText -size 14 -align 3 -indent 28.35 -spAfter 4
                    }
                }
            }
        }
    }

    # Final signature and date
    Write-Para -text "" -spBefore 14 -indent 0
    Write-Para -text $data.meta.author_title -size 14 -bold 1 -align 0 -indent 0 -spBefore 10 -spAfter 4
    Write-Para -text $data.meta.date_str -size 14 -italic 1 -align 0 -indent 0 -spAfter 4

    # Save as DOCX (wdFormatDocumentDefault = 16)
    Write-Host "Saving document to $docxFile..."
    $doc.SaveAs([ref]$docxFile, [ref]16)
    Write-Host "SUCCESS: Word document created successfully!"
}
catch {
    Write-Host ("Error: " + $_.Exception.Message)
    throw $_
}
finally {
    if ($doc) { $doc.Close([ref]$false) }
    if ($word) {
        $word.Quit()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    }
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
