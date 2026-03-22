"""
🔧 SCRAPLING PRO - Timeout Debug Test
======================================
Run this to diagnose the timeout issue.

Usage: python debug_timeout.py
"""

import sys
print(f"Python: {sys.executable}")
print(f"Version: {sys.version}")
print()

# Test 1: Check what timeout value Scrapling actually receives
print("=" * 60)
print("TEST 1: Direct StealthyFetcher call with timeout=30000")
print("=" * 60)

try:
    from scrapling.fetchers import StealthyFetcher
    
    print("Attempting fetch with timeout=30000 (30 seconds)...")
    print("URL: https://httpbin.org/delay/2 (delays 2 seconds)")
    print()
    
    # This URL delays for 2 seconds - should work with 30 second timeout
    page = StealthyFetcher.fetch(
        "https://httpbin.org/delay/2",
        timeout=30000,  # 30 seconds in milliseconds
        network_idle=True
    )
    
    if page:
        print(f"✅ SUCCESS! Status: {page.status}")
        print(f"Content preview: {str(page.html)[:200]}...")
    else:
        print("❌ Page is None")
        
except Exception as e:
    print(f"❌ ERROR: {e}")
    print()
    
    # Check if it's the 30ms error
    if "30ms" in str(e):
        print("🔍 DIAGNOSIS: Still seeing 30ms timeout!")
        print("This suggests Scrapling might have a bug or different behavior.")
        print()
        print("Let's try with explicit milliseconds value...")

print()
print("=" * 60)
print("TEST 2: Try with different timeout values")
print("=" * 60)

for timeout_val in [30000, 60000, 30, 60]:
    print(f"\nTrying timeout={timeout_val}...")
    try:
        from scrapling.fetchers import StealthyFetcher
        
        page = StealthyFetcher.fetch(
            "https://httpbin.org/get",  # Fast endpoint
            timeout=timeout_val,
            network_idle=True
        )
        
        if page and page.status == 200:
            print(f"  ✅ timeout={timeout_val} WORKS!")
            break
        else:
            print(f"  ❌ timeout={timeout_val} - Page None or bad status")
            
    except Exception as e:
        error_msg = str(e)
        if "ms exceeded" in error_msg:
            # Extract the ms value from error
            import re
            match = re.search(r'Timeout (\d+)ms exceeded', error_msg)
            if match:
                actual_ms = match.group(1)
                print(f"  ❌ timeout={timeout_val} - Scrapling used {actual_ms}ms")
            else:
                print(f"  ❌ timeout={timeout_val} - {error_msg[:100]}")
        else:
            print(f"  ❌ timeout={timeout_val} - {error_msg[:100]}")

print()
print("=" * 60)
print("TEST 3: Check Scrapling version and config")
print("=" * 60)

try:
    import scrapling
    print(f"Scrapling version: {getattr(scrapling, '__version__', 'unknown')}")
    print(f"Scrapling location: {scrapling.__file__}")
except Exception as e:
    print(f"Could not get Scrapling info: {e}")

print()
print("=" * 60)
print("TEST 4: Try using StealthySession instead")
print("=" * 60)

try:
    from scrapling.fetchers import StealthySession
    
    print("Using StealthySession with timeout=30000...")
    
    with StealthySession(headless=True, timeout=30000) as session:
        page = session.fetch("https://httpbin.org/get")
        
        if page and page.status == 200:
            print("✅ StealthySession WORKS!")
        else:
            print("❌ StealthySession failed")
            
except Exception as e:
    print(f"❌ StealthySession error: {e}")

print()
print("=" * 60)
print("DONE - Check results above")
print("=" * 60)
