# Changelog

## 1.0.0 (2026-10-14)
- First release: `local-website-audit` skill, `site_check.py` fact collector, `render_report.py` one-page PDF renderer.

## 1.1.0 (2026-10-14)
- New `capture.py`: local Lighthouse (mobile) with a PageSpeed API fallback, plus phone-emulated, phone-width and desktop screenshots.
- `site_check.py`: parallel link checks; verdicts that separate truly broken links from bot-blocked or unreachable ones; headless-browser fallback for challenge or JS-only pages; clear exit code and hint for unreachable sites and SSL errors; charset handling.
- `render_report.py`: Halcyon cream/green design, logo title bar, screenshot row, styled footer.
- Example moved to `examples/example-output/` and clearly labeled.
