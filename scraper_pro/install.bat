@echo off
REM ============================================================
REM Scrapling Pro - Windows Install Script
REM ============================================================
REM Usage: 
REM   install.bat minimal    - Core only
REM   install.bat standard   - Core + Phase 1-2 (default)
REM   install.bat full       - Everything
REM   install.bat ecommerce  - E-commerce vertical
REM   install.bat influencer - Influencer vertical
REM   install.bat trends     - Trend analysis vertical
REM ============================================================

echo.
echo 🕷️ Scrapling Pro Installer
echo ==========================
echo.

set INSTALL_TYPE=%1
if "%INSTALL_TYPE%"=="" set INSTALL_TYPE=standard

if "%INSTALL_TYPE%"=="minimal" goto :minimal
if "%INSTALL_TYPE%"=="standard" goto :standard
if "%INSTALL_TYPE%"=="full" goto :full
if "%INSTALL_TYPE%"=="ecommerce" goto :ecommerce
if "%INSTALL_TYPE%"=="influencer" goto :influencer
if "%INSTALL_TYPE%"=="trends" goto :trends

echo Usage: install.bat {minimal^|standard^|full^|ecommerce^|influencer^|trends}
goto :eof

:core
echo 📦 Installing core dependencies...
pip install scrapling[all] flask openpyxl beautifulsoup4 lxml
echo 🌐 Installing browser for JavaScript rendering...
scrapling install
goto :eof

:phase1
echo 📦 Installing Phase 1: Data Extraction...
pip install extruct pyld w3lib price-parser ftfy
goto :eof

:phase2
echo 📦 Installing Phase 2: Intelligence Layer...
pip install vaderSentiment textblob pytrends
python -m textblob.download_corpora
goto :eof

:phase3
echo 📦 Installing Phase 3: Social ^& Influencer...
pip install instaloader
goto :eof

:phase4
echo 📦 Installing Phase 4: Commerce ^& Analytics...
pip install ShopifyAPI woocommerce python-stdnum
pip install scikit-learn pandas numpy
goto :eof

:minimal
call :core
echo ✅ Minimal installation complete!
goto :done

:standard
call :core
call :phase1
call :phase2
echo ✅ Standard installation complete!
goto :done

:full
call :core
call :phase1
call :phase2
call :phase3
call :phase4
echo ✅ Full installation complete!
goto :done

:ecommerce
call :core
call :phase1
echo 📦 Installing e-commerce extras...
pip install vaderSentiment textblob pytrends
pip install ShopifyAPI woocommerce
echo ✅ E-commerce installation complete!
goto :done

:influencer
call :core
call :phase1
call :phase2
call :phase3
echo ✅ Influencer installation complete!
goto :done

:trends
call :core
call :phase1
call :phase2
echo ✅ Trends installation complete!
goto :done

:done
echo.
echo 🎉 Installation complete!
echo.
echo Next steps:
echo   1. Run: python test_setup.py
echo   2. Check: python -c "from scraper_pro import print_availability; print_availability()"
echo   3. Start: python examples.py
echo.
