# Local Website Audit

![license: MIT](https://img.shields.io/badge/license-MIT-2f5d4b) ![type: skill plugin](https://img.shields.io/badge/plugin-skill--only-2f5d4b)

A skill-only plugin by **[Halcyon Days](https://halcyondaylight.com)** that turns any local small-business
website into a friendly, plain-English, one-page audit (Markdown + PDF) with the top 3 fixes.

## What it checks

- **Website vs listings:** whether the hours, phone, address and website link match Google Business Profile (and Yelp/Apple Maps)
- **Phones:** phone-friendliness and tap-to-call
- **Speed:** a Lighthouse mobile score when available, otherwise page and image weight
- **Security:** SSL certificate and HTTPS
- **Links:** broken links, with care not to blame bot-blocking platforms
- **Basic local SEO:** title, meta description, LocalBusiness schema, robots/sitemap
- **Reviews:** a snapshot against nearby competitors (public data only)
- **Next step:** a clear call to action (Call, Book, Order, Quote)

## Install

From the marketplace: install **Local Website Audit**. Or clone this repo into your plugins folder; the
manifest is `.cursor-plugin/plugin.json` and the skill is in `skills/local-website-audit/`.

Requirements:
- Python 3.9+ (standard library only, no pip installs)
- Chrome or Chromium for screenshots, browser rendering and PDF output (Markdown works without it)
- Optional: Node 18+ for local Lighthouse (`npx lighthouse@12`, fetched on first use). Without it, the
  PageSpeed Insights API is used (free, rate-limited; set `PSI_KEY` to use your own key)
- Optional: web search, for looking up the business's listings and reviews

## Use

In chat:

> Audit https://example-bakery.com. Their Google listing says 7am–3pm daily, (555) 010-0199.

The agent follows `SKILL.md`. To run the scripts yourself:

```bash
cd skills/local-website-audit/scripts
python3 site_check.py https://example-bakery.com > facts.json        # exit 2 = site unreachable / SSL error
python3 capture.py   https://example-bakery.com --out ./shots       # Lighthouse + screenshots
python3 render_report.py example-bakery-audit.md example-bakery-audit.pdf
```

`render_report.py` adds the logo title bar and footer, shrinks text to fit one Letter page, and never prints
a `### Notes for…` section.

## Example output

`examples/example-output/` holds a full sample run on a public small-business site (checked Oct 2026),
labeled as an example and unaffiliated with the business: the PDF, the Markdown source, and the raw JSON.

## Limits

- **Public data only.** It never logs into anyone's Google account. If listing data can't be confirmed,
  the report says "not verified".
- **Link failures.** A link that times out or is refused by a social platform is reported as "didn't load for us", not
  "broken".
- **Speed scores.** They're lab measurements, so they vary from run to run and network to network.
- **Reviews.** It never writes, buys or incentivizes reviews.

## Layout

```
.cursor-plugin/plugin.json          manifest
skills/local-website-audit/         SKILL.md + scripts/ (site_check, capture, render_report)
assets/logo.svg, logo.png           1:1 logo on cream plate
examples/example-output/            labeled sample run
```

## License

MIT © 2026 Halcyon Days · Free audit format by Halcyon Days · halcyondaylight.com
