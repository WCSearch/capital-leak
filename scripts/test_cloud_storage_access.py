#!/usr/bin/env python3
"""
Test actual connectivity to cloud storage providers.
"""
import requests
import time

print("Testing Cloud Storage Connectivity")
print("=" * 70)

# Test endpoints (public, read-only)
test_urls = {
    'Google Cloud Storage': 'https://storage.googleapis.com/storage/v1/b/gcp-public-data-landsat',
    'Azure Storage': 'https://azure.microsoft.com',
    'AWS S3 (blocked)': 'https://s3.amazonaws.com',
}

results = {}

for name, url in test_urls.items():
    print(f"\n🔍 Testing: {name}")
    print(f"   URL: {url}")

    try:
        start = time.time()
        response = requests.get(url, timeout=10)
        elapsed = time.time() - start

        results[name] = {
            'status': response.status_code,
            'accessible': True,
            'time': elapsed
        }

        print(f"   ✅ Accessible!")
        print(f"   Status: {response.status_code}")
        print(f"   Time: {elapsed:.2f}s")

    except requests.exceptions.ProxyError as e:
        results[name] = {'accessible': False, 'error': 'ProxyError'}
        print(f"   ❌ Blocked by proxy (403 Forbidden)")

    except requests.exceptions.Timeout:
        results[name] = {'accessible': False, 'error': 'Timeout'}
        print(f"   ❌ Connection timeout")

    except Exception as e:
        results[name] = {'accessible': False, 'error': str(type(e).__name__)}
        print(f"   ❌ Error: {type(e).__name__}")

print("\n" + "=" * 70)
print("📊 Summary:")
print("=" * 70)

accessible = [name for name, result in results.items() if result.get('accessible')]
blocked = [name for name, result in results.items() if not result.get('accessible')]

if accessible:
    print(f"\n✅ Accessible storage ({len(accessible)}):")
    for name in accessible:
        print(f"   • {name}")

    print(f"\n💡 Potential Workaround:")
    print(f"   1. Upload CSV files to accessible cloud storage")
    print(f"   2. Download them from cloud storage in this environment")
    print(f"   3. Ingest directly to Supabase")
    print(f"   OR")
    print(f"   4. Use cloud storage as intermediary for manual import")

if blocked:
    print(f"\n❌ Blocked storage ({len(blocked)}):")
    for name in blocked:
        error = results[name].get('error', 'Unknown')
        print(f"   • {name} ({error})")
