"""Live Facebook group scrape via Chrome CDP connection."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright

COOKIES = [
    {"name": "c_user", "value": "523120300", "domain": ".facebook.com", "path": "/", "httpOnly": False, "secure": True, "sameSite": "None", "expires": 1806915458},
    {"name": "datr", "value": "pCDSaXTxbR4SKCM7tqI2Fb8D", "domain": ".facebook.com", "path": "/", "httpOnly": True, "secure": True, "sameSite": "None", "expires": 1809938596},
    {"name": "fr", "value": "1J788zl6vQv6ugm1h.AWfzUHg_uBj_D6yCKaiF8bqKWbIT6NGNqMY-nzf5SmG6gXJHXOk.Bp0iQC..AAA.0.0.Bp0iQC.AWeNS3O5Ye05Z6SJ2AmSGI-SCmQ", "domain": ".facebook.com", "path": "/", "httpOnly": True, "secure": True, "sameSite": "None", "expires": 1783155458},
    {"name": "ps_l", "value": "1", "domain": ".facebook.com", "path": "/", "httpOnly": True, "secure": True, "sameSite": "Lax", "expires": 1809939287},
    {"name": "ps_n", "value": "1", "domain": ".facebook.com", "path": "/", "httpOnly": True, "secure": True, "sameSite": "None", "expires": 1809939287},
    {"name": "sb", "value": "pCDSaUf6t9Wlsiur1cmbDYmf", "domain": ".facebook.com", "path": "/", "httpOnly": True, "secure": True, "sameSite": "None", "expires": 1809939456},
    {"name": "xs", "value": "28%3AiHY9gHVx-L45gQ%3A2%3A1775379455%3A-1%3A-1%3A%3AAczcxXHi-Ly5S3dvvtwiW5lSUxErPDh4wd2WoZJktg", "domain": ".facebook.com", "path": "/", "httpOnly": True, "secure": True, "sameSite": "None", "expires": 1806915458},
    {"name": "wd", "value": "1920x945", "domain": ".facebook.com", "path": "/", "httpOnly": False, "secure": True, "sameSite": "Lax", "expires": 1775984242},
]

GROUP_URL = "https://www.facebook.com/groups/367202228711807/"

CAPTURE_JS = """
() => {
    if (!window.__posts) { window.__posts = []; window.__seen = new Set(); }
    const articles = document.querySelectorAll('div[role="article"]');
    let n = 0;
    articles.forEach(el => {
        const text = el.innerText;
        if (!text || text.length < 20) return;
        const sig = text.substring(0, 100);
        if (window.__seen.has(sig)) return;
        window.__seen.add(sig);
        const post = {};
        const a = el.querySelector('strong a, h3 a, h4 a');
        if (a) post.author = a.innerText.trim();
        const lines = text.split('\\n').filter(l => l.trim());
        post.full_text = lines.join(' | ').substring(0, 800);
        const pm = text.match(/[\\u00a3$\\u20ac]\\s*[\\d,]+(?:\\.\\d{2})?/);
        if (pm) { post.price = pm[0]; post.type = 'sale'; }
        else post.type = 'discussion';
        const lm = text.match(/[A-Z]{3,}\\s*,\\s*[A-Z]{3,}/);
        if (lm) post.location = lm[0];
        post.images = el.querySelectorAll('img[src*="scontent"]').length;
        const tl = [...el.querySelectorAll('a')].filter(
            a => /^\\d+[hmd]$|yesterday|just now|^\\d+ (min|hour|day)/i.test(a.innerText.trim())
        );
        if (tl.length) post.time = tl[0].innerText.trim();
        window.__posts.push(post);
        n++;
    });
    return { newPosts: n, total: window.__posts.length };
}
"""

SCROLL_JS = """
() => {
    const feed = document.querySelector('div[role="feed"]');
    let el = feed;
    while (el && el !== document.body) {
        const s = getComputedStyle(el);
        if (s.overflowY === "auto" || s.overflowY === "scroll" || s.overflow === "auto") {
            el.scrollBy(0, 1200);
            return "container";
        }
        el = el.parentElement;
    }
    window.scrollBy(0, 1200);
    return "window";
}
"""


async def main():
    pw = await async_playwright().start()
    print("Connecting to Chrome CDP...")
    browser = await pw.chromium.connect_over_cdp("http://127.0.0.1:9222")
    context = browser.contexts[0] if browser.contexts else await browser.new_context()

    # Inject cookies
    await context.add_cookies(COOKIES)
    print(f"Injected {len(COOKIES)} cookies")

    page = await context.new_page()
    print(f"Navigating to {GROUP_URL}...")
    await page.goto(GROUP_URL, wait_until="domcontentloaded", timeout=60000)

    try:
        await page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        await page.wait_for_timeout(5000)

    title = await page.title()
    print(f"Page: {title}")

    # Wait for first article
    try:
        await page.wait_for_selector('div[role="article"]', timeout=15000)
        print("Feed loaded!")
    except Exception:
        print("No articles found, waiting more...")
        await page.wait_for_timeout(5000)

    # Scroll and collect loop
    stale = 0
    for scroll_num in range(1, 61):
        result = await page.evaluate(CAPTURE_JS)
        new_posts = result["newPosts"]
        total = result["total"]

        if new_posts == 0:
            stale += 1
        else:
            stale = 0

        print(f"  Scroll {scroll_num:2d}: +{new_posts} new | {total} total | stale={stale}")

        if stale >= 4:
            print("No new posts after 4 scrolls — done.")
            break

        await page.evaluate(SCROLL_JS)
        await page.wait_for_timeout(2500)

    # Get all posts
    posts_json = await page.evaluate("JSON.stringify(window.__posts)")
    posts = json.loads(posts_json)

    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE: {len(posts)} posts")
    print(f"{'='*60}")
    for i, p in enumerate(posts):
        author = p.get("author", "?")
        price = p.get("price", "-")
        location = p.get("location", "-")
        ptype = p.get("type", "?")
        text_preview = p.get("full_text", "")[:80]
        print(f"  {i+1:3d}. [{ptype:10s}] {author:20s} | {price:8s} | {location:25s} | {text_preview}")

    # Save raw JSON
    raw_path = os.path.join(os.path.dirname(__file__), "..", "fb_posts_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)
    print(f"\nSaved raw JSON: {raw_path}")

    # Export to Excel
    try:
        from packages.core.facebook_group_scraper import FacebookGroupScraper
        scraper = FacebookGroupScraper()
        xlsx_path = os.path.join(os.path.dirname(__file__), "..", "docs", "FB_Group_Pc_Parts_UK_LIVE.xlsx")
        scraper.export_to_excel(posts, xlsx_path)
        print(f"Saved Excel: {xlsx_path}")
    except Exception as e:
        print(f"Excel export error: {e}")

    await page.close()
    await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
