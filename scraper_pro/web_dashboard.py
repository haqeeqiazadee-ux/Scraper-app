"""
🕷️ SCRAPLING PRO - Web Dashboard v3.0
=======================================
AI-Powered Web Scraping Dashboard with Google Gemini integration.

Features:
- AI-powered extraction (Google Gemini - FREE!)
- Traditional template-based extraction
- Real-time progress logging
- Smart Excel export
- Session management

Run: python web_dashboard.py
Then open: http://localhost:5000
"""

import os
import sys
import json
import threading
import time
import logging
import traceback
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Dashboard")

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Gemini API Key (FREE tier)
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "AIzaSyAj_pmZsfw3-fQwVXzd3K6Ldb18odTMk54"

try:
    from flask import Flask, render_template_string, request, jsonify, send_file
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask not installed. Run: pip install flask")

# Check for AI availability
AI_AVAILABLE = False
try:
    from google import genai
    AI_AVAILABLE = True
    logger.info("✅ Google Gemini AI available")
except ImportError:
    try:
        import google.generativeai
        AI_AVAILABLE = True
        logger.info("✅ Google Generative AI available (legacy)")
    except ImportError:
        logger.warning("⚠️ Google AI not installed. Run: pip install google-genai")

# Import from local modules
try:
    from engine import ScrapingEngine, ScrapedItem, Exporter, quick_scrape
    from templates import EcommerceScraper, NewsScraper, JobScraper, CustomScraper
    
    TEMPLATES = {
        "ecommerce": EcommerceScraper,
        "news": NewsScraper,
        "jobs": JobScraper,
        "custom": CustomScraper,
    }
    
    def list_templates():
        """Return template info for HTML rendering"""
        templates = [
            {"name": "ai", "class": "🤖 AI-Powered", "description": "Let AI extract ALL data automatically (Recommended!)"},
            {"name": "ecommerce", "class": "E-Commerce", "description": "Products, prices, images, ratings"},
            {"name": "news", "class": "News/Articles", "description": "Headlines, content, dates, authors"},
            {"name": "jobs", "class": "Job Listings", "description": "Titles, companies, salaries, locations"},
            {"name": "custom", "class": "Custom", "description": "Define your own selectors"},
        ]
        return templates
        
except ImportError as e:
    print(f"Warning: Could not import scrapers: {e}")
    TEMPLATES = {}
    def list_templates():
        return [
            {"name": "ecommerce", "class": "E-Commerce", "description": "Products, prices, images"},
            {"name": "news", "class": "News", "description": "Articles, headlines"},
            {"name": "jobs", "class": "Jobs", "description": "Job listings"},
            {"name": "custom", "class": "Custom", "description": "Custom selectors"},
        ]

# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__)

# Store for active jobs and results
jobs = {}
results_store = {}


# ============================================================================
# HTML TEMPLATE
# ============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🕷️ Scrapling Pro Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 5px rgba(34, 197, 94, 0.5); }
            50% { box-shadow: 0 0 20px rgba(34, 197, 94, 0.8); }
        }
        .pulse-glow { animation: pulse-glow 2s infinite; }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        .animate-spin { animation: spin 1s linear infinite; }
        
        .gradient-bg {
            background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 50%, #1e1b4b 100%);
        }
        
        .glass {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .card-hover:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        }
        
        pre { white-space: pre-wrap; word-wrap: break-word; }
    </style>
</head>
<body class="gradient-bg min-h-screen text-white">
    <!-- Header -->
    <header class="glass border-b border-white/10">
        <div class="container mx-auto px-6 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <span class="text-3xl">🕷️</span>
                    <div>
                        <h1 class="text-2xl font-bold bg-gradient-to-r from-green-400 to-blue-500 bg-clip-text text-transparent">
                            Scrapling Pro
                        </h1>
                        <p class="text-sm text-gray-400">Professional Web Scraping Dashboard</p>
                    </div>
                </div>
                <div class="flex items-center space-x-4">
                    <div id="status-indicator" class="flex items-center space-x-2 px-3 py-1 rounded-full bg-green-500/20 border border-green-500/50">
                        <div class="w-2 h-2 rounded-full bg-green-500 pulse-glow"></div>
                        <span class="text-sm text-green-400">Ready</span>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <main class="container mx-auto px-6 py-8">
        <!-- Quick Stats -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="glass rounded-xl p-4 card-hover transition-all duration-300">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-400 text-sm">Total Scraped</p>
                        <p id="stat-total" class="text-2xl font-bold text-green-400">0</p>
                    </div>
                    <div class="p-3 bg-green-500/20 rounded-lg">
                        <i data-lucide="database" class="w-6 h-6 text-green-400"></i>
                    </div>
                </div>
            </div>
            <div class="glass rounded-xl p-4 card-hover transition-all duration-300">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-400 text-sm">Success Rate</p>
                        <p id="stat-success" class="text-2xl font-bold text-blue-400">100%</p>
                    </div>
                    <div class="p-3 bg-blue-500/20 rounded-lg">
                        <i data-lucide="check-circle" class="w-6 h-6 text-blue-400"></i>
                    </div>
                </div>
            </div>
            <div class="glass rounded-xl p-4 card-hover transition-all duration-300">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-400 text-sm">Active Jobs</p>
                        <p id="stat-jobs" class="text-2xl font-bold text-purple-400">0</p>
                    </div>
                    <div class="p-3 bg-purple-500/20 rounded-lg">
                        <i data-lucide="activity" class="w-6 h-6 text-purple-400"></i>
                    </div>
                </div>
            </div>
            <div class="glass rounded-xl p-4 card-hover transition-all duration-300">
                <div class="flex items-center justify-between">
                    <div>
                        <p class="text-gray-400 text-sm">Templates</p>
                        <p class="text-2xl font-bold text-orange-400">{{ template_count }}</p>
                    </div>
                    <div class="p-3 bg-orange-500/20 rounded-lg">
                        <i data-lucide="layout-template" class="w-6 h-6 text-orange-400"></i>
                    </div>
                </div>
            </div>
        </div>

        <!-- Main Content Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Left Column: Scraper Form -->
            <div class="lg:col-span-2">
                <div class="glass rounded-xl p-6">
                    <h2 class="text-xl font-semibold mb-4 flex items-center">
                        <i data-lucide="rocket" class="w-5 h-5 mr-2 text-green-400"></i>
                        New Scraping Job
                    </h2>
                    
                    <form id="scrape-form" class="space-y-4">
                        <!-- URL Input -->
                        <div>
                            <label class="block text-sm text-gray-400 mb-2">Target URL</label>
                            <input type="url" id="url" required
                                class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-green-500 transition"
                                placeholder="https://example.com/products">
                        </div>
                        
                        <!-- Template Selection -->
                        <div>
                            <label class="block text-sm text-gray-400 mb-2">Template</label>
                            <select id="template" 
                                class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-green-500 transition">
                                {% for t in templates %}
                                <option value="{{ t.name }}">{{ t.class }} - {{ t.description }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        
                        <!-- Custom Selectors (for custom template) -->
                        <div id="custom-selectors" class="hidden space-y-3">
                            <div>
                                <label class="block text-sm text-gray-400 mb-2">Item Container Selector</label>
                                <input type="text" id="container-selector"
                                    class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
                                    placeholder=".product-card">
                            </div>
                            <div>
                                <label class="block text-sm text-gray-400 mb-2">Fields (JSON format)</label>
                                <textarea id="fields-json" rows="3"
                                    class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-green-500 font-mono text-sm"
                                    placeholder='{"title": "h2", "price": ".cost", "image": "img @src"}'></textarea>
                            </div>
                        </div>
                        
                        <!-- Options Grid -->
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm text-gray-400 mb-2">Mode</label>
                                <select id="mode" 
                                    class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500">
                                    <option value="stealthy">Stealthy (Anti-Bot)</option>
                                    <option value="dynamic">Dynamic (JavaScript)</option>
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm text-gray-400 mb-2">Max Pages</label>
                                <input type="number" id="max-pages" value="1" min="1" max="100"
                                    class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500">
                            </div>
                        </div>
                        
                        <!-- Pagination Pattern -->
                        <div>
                            <label class="block text-sm text-gray-400 mb-2">Pagination URL Pattern (optional)</label>
                            <input type="text" id="url-pattern"
                                class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
                                placeholder="?page={} or /page/{}/  (use {} for page number)">
                        </div>
                        
                        <!-- Proxy (optional) -->
                        <div>
                            <label class="block text-sm text-gray-400 mb-2">Proxy (optional)</label>
                            <input type="text" id="proxy"
                                class="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-green-500"
                                placeholder="http://user:pass@proxy:8080">
                        </div>
                        
                        <!-- Submit Button -->
                        <button type="submit" id="submit-btn"
                            class="w-full bg-gradient-to-r from-green-500 to-blue-600 hover:from-green-600 hover:to-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-300 flex items-center justify-center space-x-2">
                            <i data-lucide="play" class="w-5 h-5"></i>
                            <span>Start Scraping</span>
                        </button>
                    </form>
                </div>
                
                <!-- Results Section -->
                <div class="glass rounded-xl p-6 mt-6">
                    <div class="flex items-center justify-between mb-4">
                        <h2 class="text-xl font-semibold flex items-center">
                            <i data-lucide="table" class="w-5 h-5 mr-2 text-blue-400"></i>
                            Results
                        </h2>
                        <div class="flex space-x-2">
                            <button onclick="exportResults('csv')" class="px-3 py-1 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition">
                                CSV
                            </button>
                            <button onclick="exportResults('json')" class="px-3 py-1 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition">
                                JSON
                            </button>
                            <button onclick="exportResults('excel')" class="px-3 py-1 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition">
                                Excel
                            </button>
                        </div>
                    </div>
                    
                    <div id="results-container" class="overflow-x-auto">
                        <div class="text-center text-gray-500 py-8">
                            <i data-lucide="inbox" class="w-12 h-12 mx-auto mb-3 opacity-50"></i>
                            <p>No results yet. Start a scraping job above.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Right Column: Templates & Logs -->
            <div class="space-y-6">
                <!-- Templates -->
                <div class="glass rounded-xl p-6">
                    <h2 class="text-xl font-semibold mb-4 flex items-center">
                        <i data-lucide="layout-template" class="w-5 h-5 mr-2 text-orange-400"></i>
                        Templates
                    </h2>
                    <div class="space-y-2">
                        {% for t in templates %}
                        <div class="p-3 bg-white/5 rounded-lg hover:bg-white/10 transition cursor-pointer"
                             onclick="selectTemplate('{{ t.name }}')">
                            <div class="flex items-center justify-between">
                                <span class="font-medium">{{ t.class }}</span>
                                <span class="text-xs px-2 py-1 bg-white/10 rounded">{{ t.name }}</span>
                            </div>
                            <p class="text-sm text-gray-400 mt-1">{{ t.description }}</p>
                        </div>
                        {% endfor %}
                    </div>
                </div>
                
                <!-- Live Logs -->
                <div class="glass rounded-xl p-6">
                    <h2 class="text-xl font-semibold mb-4 flex items-center">
                        <i data-lucide="terminal" class="w-5 h-5 mr-2 text-green-400"></i>
                        Live Logs
                    </h2>
                    <div id="logs" class="h-64 overflow-y-auto bg-black/30 rounded-lg p-3 font-mono text-xs text-green-400 space-y-1">
                        <div>[System] Dashboard ready</div>
                        <div>[System] Scrapling engine loaded</div>
                    </div>
                </div>
                
                <!-- Quick Actions -->
                <div class="glass rounded-xl p-6">
                    <h2 class="text-xl font-semibold mb-4 flex items-center">
                        <i data-lucide="zap" class="w-5 h-5 mr-2 text-yellow-400"></i>
                        Quick Actions
                    </h2>
                    <div class="grid grid-cols-2 gap-2">
                        <button onclick="testConnection()" class="p-3 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition">
                            🔍 Test URL
                        </button>
                        <button onclick="clearResults()" class="p-3 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition">
                            🗑️ Clear
                        </button>
                        <button onclick="loadDemo()" class="p-3 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition">
                            📦 Demo
                        </button>
                        <button onclick="showHelp()" class="p-3 bg-white/5 hover:bg-white/10 rounded-lg text-sm transition">
                            ❓ Help
                        </button>
                    </div>
                </div>
                
                <!-- Authenticated Scraping -->
                <div class="glass rounded-xl p-6">
                    <h2 class="text-xl font-semibold mb-4 flex items-center">
                        <i data-lucide="lock" class="w-5 h-5 mr-2 text-red-400"></i>
                        Authenticated Scraping
                    </h2>
                    <p class="text-sm text-gray-400 mb-4">Scrape sites that require login</p>
                    
                    <div class="space-y-3">
                        <input type="text" id="auth-site-name" placeholder="Site name (e.g., amazon)"
                            class="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-red-500">
                        
                        <input type="url" id="auth-login-url" placeholder="Login page URL"
                            class="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-red-500">
                        
                        <button onclick="startAuthLogin()" class="w-full p-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 rounded-lg text-sm text-red-400 transition">
                            🔐 Open Login Browser
                        </button>
                        
                        <div id="auth-sessions" class="mt-3 space-y-2 hidden">
                            <p class="text-xs text-gray-500">Saved Sessions:</p>
                            <div id="sessions-list" class="space-y-1"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="glass border-t border-white/10 mt-8">
        <div class="container mx-auto px-6 py-4 text-center text-gray-500 text-sm">
            🕷️ Scrapling Pro Dashboard | Built with Scrapling + Flask
        </div>
    </footer>

    <script>
        // Initialize Lucide icons
        lucide.createIcons();
        
        let currentResults = [];
        
        // Template selection
        document.getElementById('template').addEventListener('change', function() {
            const customSection = document.getElementById('custom-selectors');
            if (this.value === 'custom') {
                customSection.classList.remove('hidden');
            } else {
                customSection.classList.add('hidden');
            }
        });
        
        function selectTemplate(name) {
            document.getElementById('template').value = name;
            document.getElementById('template').dispatchEvent(new Event('change'));
            addLog('Template selected: ' + name);
        }
        
        // Form submission
        document.getElementById('scrape-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const btn = document.getElementById('submit-btn');
            btn.disabled = true;
            btn.innerHTML = '<svg class="animate-spin w-5 h-5 mr-2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" opacity="0.25"></circle><path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Scraping...';
            
            const data = {
                url: document.getElementById('url').value,
                template: document.getElementById('template').value,
                mode: document.getElementById('mode').value,
                max_pages: parseInt(document.getElementById('max-pages').value),
                url_pattern: document.getElementById('url-pattern').value,
                proxy: document.getElementById('proxy').value,
            };
            
            if (data.template === 'custom') {
                data.container = document.getElementById('container-selector').value;
                try {
                    data.fields = JSON.parse(document.getElementById('fields-json').value || '{}');
                } catch(e) {
                    addLog('[Error] Invalid JSON in fields');
                    btn.disabled = false;
                    btn.innerHTML = '<i data-lucide="play" class="w-5 h-5"></i><span>Start Scraping</span>';
                    lucide.createIcons();
                    return;
                }
            }
            
            addLog('[Start] Scraping ' + data.url);
            
            try {
                const response = await fetch('/api/scrape', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    currentResults = result.items;
                    displayResults(result.items);
                    updateStats(result.items.length);
                    addLog('[Success] Scraped ' + result.items.length + ' items');
                } else {
                    addLog('[Error] ' + result.error);
                }
            } catch(err) {
                addLog('[Error] ' + err.message);
            }
            
            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="play" class="w-5 h-5"></i><span>Start Scraping</span>';
            lucide.createIcons();
        });
        
        function displayResults(items) {
            const container = document.getElementById('results-container');
            
            if (!items || items.length === 0) {
                container.innerHTML = '<div class="text-center text-gray-500 py-8">No items found</div>';
                return;
            }
            
            // Build table
            const keys = new Set();
            items.forEach(item => {
                Object.keys(item).forEach(k => keys.add(k));
            });
            const columns = Array.from(keys).filter(k => k !== 'scraped_at' && k !== 'success' && k !== 'error');
            
            let html = '<table class="w-full text-sm"><thead><tr class="border-b border-white/10">';
            columns.forEach(col => {
                html += '<th class="text-left py-2 px-3 text-gray-400">' + col + '</th>';
            });
            html += '</tr></thead><tbody>';
            
            items.slice(0, 50).forEach(item => {
                html += '<tr class="border-b border-white/5 hover:bg-white/5">';
                columns.forEach(col => {
                    let val = item[col] || '';
                    if (typeof val === 'object') val = JSON.stringify(val);
                    if (val.length > 50) val = val.substring(0, 50) + '...';
                    html += '<td class="py-2 px-3">' + val + '</td>';
                });
                html += '</tr>';
            });
            
            html += '</tbody></table>';
            if (items.length > 50) {
                html += '<div class="text-center text-gray-500 py-2 text-sm">Showing 50 of ' + items.length + ' items</div>';
            }
            
            container.innerHTML = html;
        }
        
        function updateStats(count) {
            document.getElementById('stat-total').textContent = count;
        }
        
        function addLog(message) {
            const logs = document.getElementById('logs');
            const time = new Date().toLocaleTimeString();
            logs.innerHTML += '<div>[' + time + '] ' + message + '</div>';
            logs.scrollTop = logs.scrollHeight;
        }
        
        async function exportResults(format) {
            if (!currentResults || currentResults.length === 0) {
                addLog('[Error] No results to export');
                return;
            }
            
            addLog('[Export] Exporting as ' + format.toUpperCase());
            
            const response = await fetch('/api/export', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({items: currentResults, format: format})
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'scraped_data.' + (format === 'excel' ? 'xlsx' : format);
                a.click();
                addLog('[Export] Download started');
            }
        }
        
        function clearResults() {
            currentResults = [];
            document.getElementById('results-container').innerHTML = 
                '<div class="text-center text-gray-500 py-8"><i data-lucide="inbox" class="w-12 h-12 mx-auto mb-3 opacity-50"></i><p>No results yet.</p></div>';
            document.getElementById('stat-total').textContent = '0';
            lucide.createIcons();
            addLog('[Clear] Results cleared');
        }
        
        function loadDemo() {
            document.getElementById('url').value = 'https://books.toscrape.com';
            document.getElementById('template').value = 'ecommerce';
            document.getElementById('max-pages').value = '2';
            document.getElementById('url-pattern').value = '/catalogue/page-{}.html';
            addLog('[Demo] Loaded demo configuration');
        }
        
        async function testConnection() {
            const url = document.getElementById('url').value;
            if (!url) {
                addLog('[Error] Enter a URL first');
                return;
            }
            
            addLog('[Test] Testing ' + url);
            
            const response = await fetch('/api/test', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url: url})
            });
            
            const result = await response.json();
            if (result.success) {
                addLog('[Test] ✓ Status ' + result.status + ' - ' + result.title);
            } else {
                addLog('[Test] ✗ ' + result.error);
            }
        }
        
        function showHelp() {
            alert(`🕷️ Scrapling Pro Help

1. Enter the URL you want to scrape
2. Select a template that matches your target site
3. For pagination, use {} as placeholder for page number
   Example: ?page={} or /page/{}/
4. Click "Start Scraping"

Templates:
• E-Commerce: Products, prices, images
• News: Articles, headlines, dates
• Jobs: Job listings, companies, salaries
• Custom: Define your own selectors

Selector Syntax:
• "h2" - Get text content
• "img @src" - Get attribute value

Tips:
• Use "Stealthy" mode for sites with bot detection
• Use "Dynamic" mode for JavaScript-heavy sites
• Start with 1 page to test your selectors`);
        }
        
        // Auth scraping functions
        async function startAuthLogin() {
            const siteName = document.getElementById('auth-site-name').value;
            const loginUrl = document.getElementById('auth-login-url').value;
            
            if (!siteName || !loginUrl) {
                addLog('[Auth] Enter site name and login URL');
                return;
            }
            
            addLog('[Auth] Opening browser for login...');
            
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name: siteName, login_url: loginUrl})
            });
            
            const result = await response.json();
            if (result.success) {
                addLog('[Auth] ' + result.message);
                addLog('[Auth] After logging in, press Enter in terminal');
            } else {
                addLog('[Auth] Error: ' + result.error);
            }
        }
        
        async function loadSavedSessions() {
            const response = await fetch('/api/auth/sessions');
            const result = await response.json();
            
            if (result.success && result.sessions.length > 0) {
                document.getElementById('auth-sessions').classList.remove('hidden');
                const list = document.getElementById('sessions-list');
                list.innerHTML = result.sessions.map(s => 
                    `<div class="p-2 bg-white/5 rounded text-xs flex justify-between">
                        <span>🔐 ${s.name} (${s.domain})</span>
                        <span class="text-gray-500">${s.cookies_count} cookies</span>
                    </div>`
                ).join('');
            }
        }
        
        // Load sessions on page load
        loadSavedSessions();
    </script>
</body>
</html>
"""


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    templates = list_templates()
    return render_template_string(HTML_TEMPLATE, templates=templates, template_count=len(templates))


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    try:
        data = request.json
        url = data.get('url')
        template_name = data.get('template', 'ai')  # Default to AI
        mode = data.get('mode', 'stealthy')
        max_pages = data.get('max_pages', 1)
        url_pattern = data.get('url_pattern', '')
        proxy = data.get('proxy')
        
        # =====================================================================
        # AI-POWERED EXTRACTION (Recommended!)
        # =====================================================================
        if template_name == 'ai':
            logger.info("🤖 Using AI-powered extraction")
            
            try:
                from ai_scraper_v3 import AIScraperV3
                
                scraper = AIScraperV3(timeout=60000)
                products = scraper.scrape(url)
                
                if products:
                    # Convert to standard format
                    items_data = []
                    for p in products:
                        item = {
                            'url': p.get('product_url', url),
                            'title': p.get('name', ''),
                            **{k: v for k, v in p.items() if k not in ['product_url', 'name', '_source_url', '_extracted_at']}
                        }
                        items_data.append(item)
                    
                    return jsonify({'success': True, 'items': items_data, 'count': len(items_data), 'mode': 'ai'})
                else:
                    return jsonify({'success': False, 'error': 'AI extraction returned no products', 'mode': 'ai'})
                    
            except ImportError as e:
                logger.warning(f"AI scraper not available: {e}, falling back to template mode")
                template_name = 'ecommerce'
            except Exception as e:
                logger.error(f"AI extraction error: {e}")
                return jsonify({'success': False, 'error': f'AI extraction failed: {str(e)}', 'mode': 'ai'})
        
        # =====================================================================
        # TEMPLATE-BASED EXTRACTION (Fallback)
        # =====================================================================
        logger.info(f"Using template-based extraction: {template_name}")
        
        # Try to use engine_v2 first (has proper timeout handling)
        try:
            from engine_v2 import ScrapingEngine, ScrapedItem, Parsers
            logger.info("Using enhanced engine_v2")
        except ImportError:
            from engine import ScrapingEngine, ScrapedItem, Parsers
            logger.info("Using standard engine")
        
        # Engine kwargs with proper timeout (30 seconds)
        engine_kwargs = {
            'mode': mode,
            'timeout': 30,  # 30 seconds timeout
            'max_retries': 3,
        }
        if proxy:
            engine_kwargs['proxies'] = [proxy]
        
        # Create engine directly for more control
        engine = ScrapingEngine(**engine_kwargs)
        
        # Choose parser based on template
        if template_name == 'ecommerce':
            parser = Parsers.ecommerce_products
        elif template_name == 'custom':
            container = data.get('container', '.item')
            fields = data.get('fields', {'title': 'h2'})
            
            def custom_parser(page):
                items = []
                for element in page.css(container):
                    content = {}
                    title = ""
                    for field_name, selector in fields.items():
                        if " @" in selector:
                            sel, attr = selector.rsplit(" @", 1)
                            els = element.css(sel)
                            value = els[0].attrib.get(attr, "") if els else ""
                        else:
                            els = element.css(selector)
                            value = els[0].text.strip() if els and hasattr(els[0], 'text') else ""
                        if field_name == "title":
                            title = value
                        else:
                            content[field_name] = value
                    items.append(ScrapedItem(url=url, title=title, content=content))
                return items
            
            parser = custom_parser
        else:
            parser = Parsers.ecommerce_products
        
        # Scrape
        if max_pages > 1 and url_pattern:
            items = engine.scrape_with_pagination(url, parser, "url", url_pattern, max_pages=max_pages)
        else:
            items = engine.scrape_url(url, parser)
        
        # Convert to dicts
        items_data = [item.to_dict() for item in items]
        
        return jsonify({'success': True, 'items': items_data, 'count': len(items_data), 'mode': 'template'})
    
    except Exception as e:
        import traceback
        logger.error(f"Scrape error: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/test', methods=['POST'])
def api_test():
    try:
        # Try engine_v2 first
        try:
            from engine_v2 import ScrapingEngine
            engine = ScrapingEngine(mode='stealthy', timeout=30)
        except ImportError:
            from scrapling.fetchers import StealthyFetcher
            engine = None
        
        url = request.json.get('url')
        
        if engine:
            page = engine.fetch(url)
        else:
            # IMPORTANT: Scrapling timeout is in MILLISECONDS
            page = StealthyFetcher.fetch(url, timeout=30000)  # 30 seconds = 30000ms
        
        if not page:
            return jsonify({'success': False, 'error': 'Failed to fetch page'})
        
        # Get title
        title_els = page.css('title')
        title = title_els[0].text if title_els and hasattr(title_els[0], 'text') else 'No title'
        
        return jsonify({
            'success': True, 
            'status': page.status,
            'title': title[:100]
        })
    except Exception as e:
        import traceback
        logger.error(f"Test error: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/export', methods=['POST'])
def api_export():
    import tempfile
    import io
    
    data = request.json
    items_data = data.get('items', [])
    format = data.get('format', 'csv')
    smart_format = data.get('smart_format', True)  # Use smart formatting by default
    
    # Convert back to ScrapedItems
    items = []
    for d in items_data:
        item = ScrapedItem(
            url=d.get('url', ''),
            title=d.get('title', ''),
            content={k: v for k, v in d.items() if k not in ['url', 'title', 'scraped_at', 'success', 'error']}
        )
        items.append(item)
    
    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{format if format != "excel" else "xlsx"}') as f:
        filepath = f.name
    
    if format == 'csv':
        Exporter.to_csv(items, filepath)
        mimetype = 'text/csv'
    elif format == 'json':
        Exporter.to_json(items, filepath)
        mimetype = 'application/json'
    else:
        # Use smart exporter for Excel
        if smart_format:
            try:
                from smart_exporter import SmartExcelExporter
                exporter = SmartExcelExporter()
                exporter.export(
                    items=items,
                    filepath=filepath,
                    add_summary=True,
                    highlight_deals=True,
                    auto_filter=True,
                )
            except ImportError:
                Exporter.to_excel(items, filepath)
        else:
            Exporter.to_excel(items, filepath)
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    return send_file(filepath, mimetype=mimetype, as_attachment=True)


@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    """Start manual login process"""
    try:
        from auth_scraper import AuthenticatedScraper
        
        data = request.json
        site_name = data.get('name', 'default')
        login_url = data.get('login_url')
        
        if not login_url:
            return jsonify({'success': False, 'error': 'login_url required'})
        
        scraper = AuthenticatedScraper(name=site_name)
        
        # This will open a browser - run in background
        import threading
        def do_login():
            scraper.login_manual(login_url)
        
        thread = threading.Thread(target=do_login)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Browser opened. Please login manually, then press Enter in the terminal.'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/auth/sessions', methods=['GET'])
def api_auth_sessions():
    """List saved sessions"""
    try:
        from auth_scraper import SessionManager
        
        manager = SessionManager()
        sessions = manager.list_sessions()
        
        return jsonify({'success': True, 'sessions': sessions})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/auth/scrape', methods=['POST'])
def api_auth_scrape():
    """Scrape using saved session"""
    try:
        from auth_scraper import AuthenticatedScraper
        
        data = request.json
        site_name = data.get('name')
        url = data.get('url')
        selectors = data.get('selectors', {})
        
        if not site_name or not url:
            return jsonify({'success': False, 'error': 'name and url required'})
        
        scraper = AuthenticatedScraper(name=site_name)
        
        if not scraper.is_session_valid():
            return jsonify({
                'success': False, 
                'error': 'Session expired or not found. Please login again.'
            })
        
        page = scraper.fetch(url)
        
        if not page:
            return jsonify({'success': False, 'error': 'Failed to fetch page'})
        
        # Extract data using provided selectors
        items = []
        
        if selectors:
            container_sel = selectors.get('container', 'body')
            containers = page.css(container_sel)
            
            for container in containers:
                item = {'url': url}
                for field, sel in selectors.items():
                    if field == 'container':
                        continue
                    try:
                        el = container.select_one(sel) if hasattr(container, 'select_one') else None
                        if el:
                            item[field] = el.get_text(strip=True)
                    except:
                        pass
                if len(item) > 1:
                    items.append(item)
        else:
            # Return raw HTML for manual inspection
            items = [{'url': url, 'html_preview': page.html[:5000]}]
        
        return jsonify({
            'success': True,
            'items': items,
            'count': len(items)
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Auth scrape error: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)})


# ============================================================================
# MAIN
# ============================================================================

def main():
    if not FLASK_AVAILABLE:
        print("Flask is required for the web dashboard.")
        print("Install it with: pip install flask")
        return
    
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║   🕷️  SCRAPLING PRO - Web Dashboard                          ║
    ║                                                               ║
    ║   Starting server at: http://localhost:5000                   ║
    ║                                                               ║
    ║   Press Ctrl+C to stop                                        ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()
