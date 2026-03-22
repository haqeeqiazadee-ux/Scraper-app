#!/bin/bash
# ============================================================
# Scrapling Pro - Quick Install Scripts
# ============================================================
# Usage: 
#   ./install.sh minimal    # Core only
#   ./install.sh standard   # Core + Phase 1-2
#   ./install.sh full       # Everything
#   ./install.sh ecommerce  # E-commerce vertical
#   ./install.sh influencer # Influencer vertical
#   ./install.sh trends     # Trend analysis vertical
# ============================================================

set -e

echo "🕷️ Scrapling Pro Installer"
echo "=========================="

install_core() {
    echo "📦 Installing core dependencies..."
    pip install scrapling[all] flask openpyxl beautifulsoup4 lxml
    echo "🌐 Installing browser for JavaScript rendering..."
    scrapling install || echo "⚠️ Browser install failed - run 'scrapling install' manually"
}

install_phase1() {
    echo "📦 Installing Phase 1: Data Extraction..."
    pip install extruct pyld w3lib price-parser ftfy
}

install_phase2() {
    echo "📦 Installing Phase 2: Intelligence Layer..."
    pip install vaderSentiment textblob pytrends
    python -m textblob.download_corpora || true
}

install_phase3() {
    echo "📦 Installing Phase 3: Social & Influencer..."
    pip install instaloader
    # snscrape requires special install
    # pip install git+https://github.com/JustAnotherArchivist/snscrape.git
}

install_phase4() {
    echo "📦 Installing Phase 4: Commerce & Analytics..."
    pip install ShopifyAPI woocommerce python-stdnum
    pip install scikit-learn pandas numpy
}

install_minimal() {
    install_core
    echo "✅ Minimal installation complete!"
}

install_standard() {
    install_core
    install_phase1
    install_phase2
    echo "✅ Standard installation complete!"
}

install_full() {
    install_core
    install_phase1
    install_phase2
    install_phase3
    install_phase4
    echo "✅ Full installation complete!"
}

install_ecommerce() {
    install_core
    install_phase1
    echo "📦 Installing e-commerce extras..."
    pip install vaderSentiment textblob pytrends
    pip install ShopifyAPI woocommerce
    echo "✅ E-commerce installation complete!"
}

install_influencer() {
    install_core
    install_phase1
    install_phase2
    install_phase3
    echo "✅ Influencer installation complete!"
}

install_trends() {
    install_core
    install_phase1
    install_phase2
    echo "✅ Trends installation complete!"
}

# Main
case "${1:-standard}" in
    minimal)
        install_minimal
        ;;
    standard)
        install_standard
        ;;
    full)
        install_full
        ;;
    ecommerce)
        install_ecommerce
        ;;
    influencer)
        install_influencer
        ;;
    trends)
        install_trends
        ;;
    *)
        echo "Usage: $0 {minimal|standard|full|ecommerce|influencer|trends}"
        exit 1
        ;;
esac

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Run: python test_setup.py"
echo "  2. Check: python -c \"from scraper_pro import print_availability; print_availability()\""
echo "  3. Start: python examples.py"
