---
name: local-website-audit
description: Run a free, plain-English website and Google listing audit for a local small business and produce a one-page report (Markdown + PDF) with the top 3 fixes. Use when someone gives a local business website (optionally with its Google Business Profile details) and asks for an audit, website review, local SEO check, "why isn't my site getting calls", or a report to send a business owner.
---

# Local Website Audit

Turn one local business URL into a friendly one-page report an owner can read in two minutes.
Write for a busy owner, not a developer: no jargon without a plain explanation, no scare tactics,
every problem tied to a lost call, visit, booking or order.

## Inputs

- **Required:** the business website URL.
- **Optional:** business name, city, Google Business Profile link or the hours / phone / address / website
  shown on it, review rating and count, top competitors, who the report is for.
- If Google listing details aren't provided, look them up with web search (search "<name> <city>").
  If you still can't confirm them, say "not verified" in the report. Never guess a rating, review
  count, phone number or hours.

## Workflow

1. **Collect site facts.** Run the bundled checker (Python 3 standard library only):
   `python3 scripts/site_check.py <url> > facts.json`
   It reports SSL/HTTPS, redirects, response time and HTML size, viewport/mobile hints, tap-to-call
   links, title/meta/H1, robots.txt and sitemap, JSON-LD schema types and any NAP inside them, phones /
   addresses / hours found on the page, copyright year, sample image sizes, calls to action, and
   broken links (first 40). If Python can't run, gather the same facts by fetching the page.
   If it prints `rendered_with_browser`, the plain fetch got a challenge or empty page and facts came from a
   headless-browser render. `bot_challenge_suspected` means checks may be incomplete. Say so in the report.
   Link `verdict`s other than "likely broken" are NOT proof of a broken link; say "didn't load for us".
   Exit code 2 means the site couldn't be fetched; read `hint` (an SSL failure is itself a top finding).
2. **Speed + screenshots.** Run `python3 scripts/capture.py <url> --out <folder>`. It runs Lighthouse
   locally (`npx lighthouse@12`, mobile) and falls back to the PageSpeed Insights API, and saves
   `phone-emulated.jpg` (true mobile emulation from Lighthouse), `phone.png` (390 px window, which is
   NOT device emulation) and `desktop.png`. Use `phone-emulated.jpg` for phone claims. If both speed sources fail, use
   the checker's response time and page/image sizes and label speed "estimate".
3. **Look at it like a customer on a phone.** View the screenshots: are the phone number and a main
   button visible without scrolling? Are hours/menu/prices readable without zooming or a PDF?
   Anything cut off, overlapping or tiny?
4. **Compare website vs Google listing (NAP+).** Check name, phone, address, hours, and that the
   listing's website link points to this site. Every mismatch is a finding: customers trust Google
   first and call the number they see there.
5. **Basic local SEO.** Does the page title say what they do and where (e.g. "Plumber in Springfield, IL")?
   Is there a meta description? A LocalBusiness-type schema (or a subtype like Restaurant, Dentist,
   HomeAndConstructionBusiness) with address, phone and hours? Is the city mentioned in the page text?
6. **Reviews snapshot.** From public sources only: Google rating and count, plus one or two other
   platforms if easy to find (Yelp, Facebook). Note whether the owner replies. Quote at most 1–2 short
   phrases. Compare to 2–3 nearby competitors' review counts if you can find them.
7. **Calls to action.** Is there one obvious next step (Call, Book, Order, Get a quote) on mobile, near
   the top, and does it work (tel: link, working booking link)?
8. **Write the report** with the template below, save as `<business-slug>-audit.md` next to the
   screenshots (optionally add up to two `![caption](file)` lines under "What's working"), then render:
   `python3 scripts/render_report.py <business-slug>-audit.md <business-slug>-audit.pdf`
   The renderer needs Chrome/Chromium; it shrinks text until the report fits one Letter page.
   If the PDF is still 2 pages, cut words, not findings.
9. **Check your work.** Go claim by claim against the JSON and pages you actually fetched. Every number
   has a source and date. Nothing is invented. Anything you couldn't confirm says "not verified". One page.

## Tone rules

- Start with something the business does well (real, specific).
- Plain English: "your site takes about 6 seconds to show up on a phone" not "LCP 6.1s".
- Explain why each issue costs them customers in one short clause.
- Top 3 fixes must be concrete and doable, ordered by impact for effort. Mark which ones the owner
  can do themselves for free (e.g. fixing hours on Google).
- No fear-mongering, no guarantees about rankings, never suggest fake or incentivized reviews.
- If a check couldn't be done, say so briefly rather than dropping it silently.

## Report template

```markdown
# Website & Google Listing Check: <Business Name>

**<Category>** · <City, State> · <website> · Checked <Mon D, YYYY>

**What's working:** <1–2 sentences of genuine praise.>

## At a glance

| Check | Result | Note |
|---|---|---|
| Google listing matches site | ✅ / ⚠️ / ❌ | <hours, phone, address, link> |
| Phone-friendly | ✅ / ⚠️ / ❌ | <one line> |
| Speed on mobile | ✅ / ⚠️ / ❌ | <score or seconds, source> |
| Secure (https) | ✅ / ❌ | <cert expiry> |
| Broken links | ✅ / ⚠️ | <n checked, n broken> |
| Shows up for local searches | ✅ / ⚠️ / ❌ | <title / schema / city mention> |
| Reviews | <rating ★ · count> | <vs competitors, replies> |
| Clear next step | ✅ / ⚠️ / ❌ | <call / book button> |

## What we found

- <3–6 short bullets, each: what's wrong → why it costs customers.>

## Top 3 fixes

1. **<Fix>**: <how, in one or two sentences>. _(Free, ~10 min)_
2. **<Fix>**: <how>.
3. **<Fix>**: <how>.

_How we checked: public website and listings only, on <date>. Ratings and listings change; anything
marked "not verified" should be confirmed on the live listing._

Free audit format by Halcyon Days · halcyondaylight.com
```

Always keep that last footer line exactly as written. Anything under a heading `### Notes for` is
treated as private and is not printed in the PDF.
