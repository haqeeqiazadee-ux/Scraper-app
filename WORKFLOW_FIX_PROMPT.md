# WORKFLOW FIX PROMPT — Every Feature Must Actually Work

## RULES (NON-NEGOTIABLE)

1. **"Working" means a user can click through the ENTIRE flow on https://myscraper.netlify.app and get useful output.** Not "the module imports", not "the API returns 200", not "tests pass". A REAL USER getting REAL DATA.

2. **Every fix must be verified on the LIVE deployed site** — not localhost, not a unit test, not "I checked the code". Screenshot or API response from myscraper.netlify.app or it didn't happen.

3. **Do NOT mark anything complete until you have proof.** If you can't verify it live, say "BLOCKED: [reason]" and move on.

4. **Challenge clause:** For each workflow, define a specific challenge that MUST pass before claiming done. If the challenge fails, the workflow is BROKEN regardless of what the code looks like.

---

## WORKFLOW 1: Quick Scrape

**Current state:** Only extracts pricing/product items. Misses all page content. Results not saved.

**What "working" means:**
- User enters ANY URL (not just e-commerce)
- System asks: "What do you want to extract?" — options: Everything, Products, Text Content, Custom Fields
- Returns meaningful structured data for ANY website
- Results are SAVED and appear in Results & Export page

**Challenge:** Scrape `https://yousell.online` and return:
- Page title, description, all section headings
- All pricing plans with features
- All testimonials/stats
- All CTAs and links
- Minimum 20 data points, not 4

**Fix scope:**
- Add extraction mode selector to ScrapeTestPage.tsx (Everything / Products / Content / Custom)
- "Everything" mode uses trafilatura + deterministic combined
- Save results to database via POST /results after scrape
- Show "Saved to Results" confirmation

---

## WORKFLOW 2: Web Crawl

**Current state:** Form works, job starts, but crawl returns 0 pages on Netlify (serverless can't run long-lived HTTP fetches).

**What "working" means:**
- User enters URL + depth + max pages
- Crawl actually fetches pages and extracts data
- Progress updates in real-time
- Results viewable + exportable

**Challenge:** Crawl `https://books.toscrape.com/` with depth=1, max_pages=5 and return data from at least 3 pages.

**Fix scope:**
- The crawl_manager uses our HttpCollector which requires curl_cffi — verify this works on the deployed backend
- If serverless can't do it, document clearly: "Requires self-hosted backend"
- At minimum: single-page crawl (depth=0) should work like Quick Scrape

---

## WORKFLOW 3: Web Search

**Current state:** Serper API key set, endpoint switched from Brave. Untested on live site.

**What "working" means:**
- User enters search query
- System searches via Serper, gets URLs
- Scrapes each URL and returns structured data
- Results shown with title, URL, extracted data per result

**Challenge:** Search "best gaming laptops 2026" and return at least 3 results with titles and URLs. At least 1 result must have extracted product/article data.

**Fix scope:**
- Verify Serper API key works on deployed backend
- Test the full search → scrape → display pipeline
- Handle Serper errors gracefully (show message, not crash)

---

## WORKFLOW 4: Structured Extract

**Current state:** Form exists with URL + JSON schema. Untested end-to-end.

**What "working" means:**
- User enters URL + defines fields they want (name, price, description, etc.)
- System extracts EXACTLY those fields
- Returns structured key-value data matching the schema
- Confidence score reflects how many fields were found

**Challenge:** Extract from `https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html` with schema `{"title": "string", "price": "number", "description": "string", "availability": "string"}` and get all 4 fields populated.

**Fix scope:**
- Verify /extract endpoint works end-to-end
- Ensure schema mapping actually matches fields
- Show clear error if URL can't be fetched

---

## WORKFLOW 5: Amazon

**Current state:** Templates say lane=api (Keepa). Keepa key is set. Untested on live site via template click flow.

**What "working" means:**
- User goes to Amazon page, enters ASIN
- System calls Keepa API
- Returns product name, price, rating, reviews, image, sales rank
- Data displayed in product card format

**Challenge:** Look up ASIN `B09V3KXJPB` on Amazon US and return product title containing "iPad" with a price and rating.

**Fix scope:**
- Verify Keepa API key is set on deployed backend
- Test Amazon page ASIN lookup end-to-end on live site
- Verify the /keepa/query endpoint returns proper data

---

## WORKFLOW 6: Google Maps

**Current state:** Switched to Serper Places (free). Tested locally, returns data. Untested on live site.

**What "working" means:**
- User selects category + enters location
- System searches via Serper Places
- Returns businesses with name, rating, address, phone
- Data displayed in card/table format

**Challenge:** Search "restaurants in Dubai" and return at least 5 businesses with names and ratings.

**Fix scope:**
- Verify SERPER_API_KEY is available on deployed backend
- Test Google Maps page end-to-end on live site
- Verify the connector uses Serper Places as tier 1

---

## WORKFLOW 7: Facebook Groups

**Current state:** Works with CDP Chrome + cookies locally (996 posts extracted). Cannot work from web UI alone — needs browser on server side.

**What "working" means:**
- User uploads cookies via UI
- User enters group URL
- System scrapes group posts
- Results shown in table + exportable to Excel

**Challenge:** This CANNOT work on Netlify (needs server-side browser). Document honestly: "Requires self-hosted backend with Chrome/Playwright installed."

**Fix scope:**
- Make the UI show a clear message when backend can't run browser
- Don't let users click "Scrape Group" and get a silent failure
- Add a "Requirements" note on the page: "Needs self-hosted backend"

---

## WORKFLOW 8: Templates

**Current state:** 55 templates display. Click → configure → Start Scrape creates Policy + Tasks + Execute. Untested if execution actually works on live site.

**What "working" means:**
- User clicks a template (e.g., "eBay Items Scraper")
- Configures URL
- Clicks Start Scrape
- Gets redirected to task detail with results

**Challenge:** Use "Trustpilot Reviews Scraper" template with URL `https://www.trustpilot.com/review/amazon.com`, click Start Scrape, and see extracted review data on the task detail page.

**Fix scope:**
- Test one template end-to-end on live site
- Verify task execution pipeline works on deployed backend
- Fix any errors in the apply → create task → execute chain

---

## WORKFLOW 9: Results & Export

**Current state:** Shows 1 old result from httpbin. Quick Scrape results NOT saved here. Export untested.

**What "working" means:**
- ALL scrape results appear here automatically
- Can filter by confidence
- Can click "View" to see full extracted data
- Can click "Export Results" to download CSV/JSON
- Export downloads a real file with real data

**Challenge:** After running a Quick Scrape, the result must appear in this page within 5 seconds. Export to CSV must produce a downloadable file.

**Fix scope:**
- Quick Scrape must POST results to /results endpoint after extraction
- Verify export endpoints return proper files
- Test download in browser

---

## WORKFLOW 10: Change Detection

**Current state:** UI works (textareas + compare). Client-side comparison logic. Untested with realistic data.

**What "working" means:**
- User pastes two JSON snapshots
- Clicks Compare
- Sees summary cards (added, removed, price changes)
- Sees detailed change table with old/new values

**Challenge:** Paste old data with Widget at $19.99, new data with Widget at $14.99 + new Gadget at $29.99. Must show: 1 added (Gadget), 1 price change (Widget -25%), correct summary counts.

**Fix scope:**
- Test with realistic product data
- Verify price delta percentage calculates correctly
- Verify summary cards show correct counts

---

## WORKFLOW 11: Schedules

**Current state:** CRUD works. Untested if scheduled tasks actually fire.

**What "working" means:**
- User creates a schedule (e.g., scrape URL every hour)
- Schedule appears in list
- Can edit/delete schedules

**Challenge:** Create a schedule, verify it appears in the list, verify it can be deleted. (Execution requires backend — document if not possible on Netlify.)

**Fix scope:**
- Test create + list + delete on live site
- Document that schedule execution needs self-hosted backend

---

## WORKFLOW 12: MCP Server

**Current state:** Informational page with copy buttons. No live connection.

**What "working" means:**
- Page shows all 5 MCP tools with descriptions
- Copy buttons work (copy to clipboard)
- Connection config is correct JSON

**Challenge:** Click "Copy" on the Claude Desktop config. Paste it — must be valid JSON with correct command/args.

**Fix scope:**
- Verify copy buttons actually copy to clipboard
- Verify JSON configs are syntactically valid
- This is informational — no backend needed

---

## EXECUTION ORDER

1. **Quick Scrape** — most visible, most broken
2. **Results & Export** — depends on Quick Scrape saving
3. **Change Detection** — client-side, quickest to verify
4. **MCP Server** — informational, quick to verify
5. **Web Search** — needs Serper API verification
6. **Structured Extract** — needs endpoint verification
7. **Amazon** — needs Keepa on live site
8. **Google Maps** — needs Serper Places on live site
9. **Templates** — needs full pipeline test
10. **Schedules** — CRUD only
11. **Web Crawl** — may need self-hosted backend
12. **Facebook Groups** — definitely needs self-hosted backend

---

## DEFINITION OF DONE

A workflow is DONE when:
1. The challenge passes on the LIVE site (myscraper.netlify.app)
2. A screenshot or API response proves it
3. The data is useful (not empty, not garbage, not 4 items when there should be 50)
4. Error states are handled (show message, not blank screen)
5. Git committed and pushed

A workflow is BLOCKED when:
1. It fundamentally cannot work on Netlify (needs server-side browser, long-running process)
2. Documented with clear "Requirements" message in the UI
3. Works when self-hosted (proven locally)
