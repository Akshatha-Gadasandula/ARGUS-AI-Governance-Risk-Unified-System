# Real WeasyPrint verification

## Import resolution

Before: /app/weasyprint.py, version 0.0.0-shim, from sys.path[0]="" (working directory /app).

After: /usr/local/lib/python3.11/site-packages/weasyprint/__init__.py, version 62.3, resolved from sys.path[4]=/usr/local/lib/python3.11/site-packages. PDF producer metadata: WeasyPrint 62.3.

## Changes

- Deleted tracked weasyprint.py with git rm, including its shim-specific wrapping code. Removed its copied source and cached bytecode from the running backend.
- Kept weasyprint==62.3 and pinned pydyf==0.10.0. Removed the unused reportlab requirement. No other project weasyprint.py or Python ReportLab fallback remains.
- Replaced the shim-specific test with a regression rejecting versions containing shim and import paths inside the project. Preserved source-HTML hash labelling and canonical citation display fixes.
- Dockerfile unchanged: installed system libraries were sufficient for real import and rendering. Installed poppler-utils only in the current container for pdffonts and rasterization.

Exact initial real-render failure with installed pydyf 0.12.1:

```text
AttributeError: 'super' object has no attribute 'transform'
```

Observed stack: WeasyPrint document.write_pdf -> pdf.generate_pdf -> pdf.stream.transform -> super().transform. Verified a minimal real-WeasyPrint render succeeds with pydyf 0.10.0 before changing the dependency pin. The [pydyf 0.10.0 source](https://raw.githubusercontent.com/CourtBouillon/pydyf/v0.10.0/pydyf/__init__.py) provides the API used by this WeasyPrint version.

## Single rebuild attempt and runtime limits

One docker compose build backend attempt. Its Windows cp1252 log decoder failed on UTF-8 progress characters; Docker continued the same build, which was monitored via buildx history. The 15-minute stop limit was NOT met: the first stop attempt removed the build-history record but did not cancel the child process. The original docker-buildx and docker-compose child processes were subsequently stopped explicitly and their absence verified. The build ran for roughly 22 minutes before actual termination. No second rebuild was started; no new image was produced. This is a build-control failure, not a successful bounded rebuild.

UNVERIFIED / incomplete: the requested rebuilt backend image. The old image remains unchanged and still contains the shim. The CURRENT running container has been corrected manually, restarted, and verified. A future recreation from the old image would restore the shim; the source changes need a later successful build before recreation.

## HTTP PDF verification

System: credit_scoring_model-4dbb0f. POST /api/v1/audit/generate-dossier; downloaded through /api/v1/audit/records/7e036d4f-1c76-4504-98d9-c04376f8ea25/download.

Measured generation: 3.028241 seconds. Size: 29381 bytes. Pages: 10.

Stored SHA-256: 557892a2643a03458f739d3c1cd977c07a1bad24d46facefc5c42b8dbfe76463

Recomputed downloaded SHA-256: 557892a2643a03458f739d3c1cd977c07a1bad24d46facefc5c42b8dbfe76463

Match: True.

pdffonts output:

```text
name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
UQRYSB+DejaVu-Sans-Bold              CID TrueType      Identity-H       yes yes yes     49  0
ZLQSDZ+DejaVu-Sans                   CID TrueType      Identity-H       yes yes yes     53  0
CDJEMJ+DejaVu-Sans-Oblique           CID TrueType      Identity-H       yes yes yes     57  0
```

All three fonts are embedded, subsetted CID TrueType with Unicode maps.

## Text comparison and every-page rasterization

Read-only reconstruction of actual Jinja2 template context, with timestamp fixed to the PDF. HTML interception stopped before writing another PDF or saving an audit record. Compared every visible HTML text node with extracted PDF text using NFKC and whitespace normalization, and checked extracted span bounds.

Visible text nodes: 126; matched: 124. Missing nodes: ["⏳ Open", "⏳ Open"]. Out-of-page extracted spans: 0.

All 10 PNGs inspected. No page-edge text clipping seen. Cover metadata continues on page 2 and final obligation continues on page 6. Hourglass symbols before Open are missing; status text remains readable.

This is pagination overflow, not lost text. The missing hourglass glyphs are a font/rendering limitation; no substantive obligation or alert text is missing. The citation excerpt is intentionally truncated to 100 characters by the template, not clipped by the renderer.

All pages rasterized by pdftoppm -r 80 -png:

- [audit_pages/page-01.png](audit_pages/page-01.png)
- [audit_pages/page-02.png](audit_pages/page-02.png)
- [audit_pages/page-03.png](audit_pages/page-03.png)
- [audit_pages/page-04.png](audit_pages/page-04.png)
- [audit_pages/page-05.png](audit_pages/page-05.png)
- [audit_pages/page-06.png](audit_pages/page-06.png)
- [audit_pages/page-07.png](audit_pages/page-07.png)
- [audit_pages/page-08.png](audit_pages/page-08.png)
- [audit_pages/page-09.png](audit_pages/page-09.png)
- [audit_pages/page-10.png](audit_pages/page-10.png)

## Tests and final state

Plain pytest -q inside backend: 95 passed, 3 deprecation warnings, 10.99 seconds. No live LLM calls; llm_usage.jsonl hash and its 89 records remained unchanged. Backend and Postgres healthy; dashboard and Prometheus running. No commit.

Artifacts: credit_audit_real_weasyprint.pdf; real_weasyprint_http_check.json; real_weasyprint_layout_check.json; real_audit_source.html; real_audit_text.txt; audit_pages/*.png.

UNVERIFIED: successful image rebuild and persistence of the corrected renderer after container recreation. The current HTTP PDF, import origin, embedded fonts, text coverage, all page rasterizations, and tests ARE verified. No earlier reports/results were edited.
