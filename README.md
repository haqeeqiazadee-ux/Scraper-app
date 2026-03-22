# 🤖 SCRAPLING PRO v3.0 - AI-Powered Web Scraper

## 🚀 Quick Start (5 minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
pip install google-genai
scrapling install
```

### Step 2: Run E2E Tests
```bash
python test_final.py
```
All tests should pass ✅

### Step 3: Start Scraping!

**Option A: Use the Dashboard (Recommended)**
```bash
python web_dashboard.py
```
Open http://localhost:5000 and select "🤖 AI-Powered" template.

**Option B: Use Command Line**
```bash
python ai_scraper_v3.py https://myshop.pk/laptops-desktops-computers/laptops
```

**Option C: Use in Code**
```python
from ai_scraper_v3 import AIScraperV3

scraper = AIScraperV3()
products = scraper.scrape("https://example.com/products")
scraper.export("products.xlsx")
```

---

## 🤖 AI Features

The scraper uses **Google Gemini AI (FREE!)** to:
- Automatically detect page structure
- Extract ALL product information
- Work on ANY e-commerce website
- No hardcoded selectors needed!

### What Gets Extracted:
| Field | Description |
|-------|-------------|
| name | Product name/title |
| sku | Product SKU/ID |
| price | Current price |
| original_price | Price before discount |
| discount | Discount percentage |
| description | Product description |
| brand | Brand name |
| category | Product category |
| rating | Customer rating |
| reviews_count | Number of reviews |
| stock_status | Availability |
| image_url | Product image |
| product_url | Link to product |
| specifications | All product specs |
| features | Product features |
| delivery_info | Shipping info |
| warranty | Warranty info |

---

## 📁 File Structure

```
scraper_pro/
├── ai_scraper_v3.py      # 🤖 AI-powered scraper (MAIN)
├── web_dashboard.py       # 🌐 Web interface
├── smart_exporter.py      # 📊 Excel export
├── engine_v2.py           # ⚙️ Scraping engine
├── test_final.py          # 🧪 E2E tests
├── requirements.txt       # 📦 Dependencies
└── README.md              # 📖 This file
```

---

## 🔧 Configuration

### API Key (Already Set!)
The Gemini API key is embedded in the code. You can also set your own:
```bash
set GOOGLE_API_KEY=your_key_here
```

### Timeout
Default is 60 seconds. Change in code:
```python
scraper = AIScraperV3(timeout=120000)  # 120 seconds in ms
```

---

## 📊 Output Formats

### Excel (.xlsx)
- Smart column ordering
- Clickable URLs (actual links, not "View Link")
- Summary sheet with statistics
- Deal highlighting

### JSON (.json)
- Full product data
- Easy to process programmatically

---

## 🆘 Troubleshooting

### "No module named 'scrapling'"
```bash
pip install scrapling[all]
scrapling install
```

### "AI extraction failed"
- Check internet connection
- Verify API key is valid
- Try again (rate limits reset quickly)

### "Timeout error"
Increase timeout in the scraper initialization.

---

## 📞 Support

Created with ❤️ by Scrapling Pro Team
Version: 3.0
Last Updated: March 2026
"# Scraper-app" 
