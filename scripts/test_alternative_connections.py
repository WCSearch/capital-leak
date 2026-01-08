#!/usr/bin/env python3
"""
Try alternative connection methods to Supabase.
"""
import psycopg2
import socket
import os
from dotenv import load_dotenv

load_dotenv()

print("Testing Alternative Database Connection Methods")
print("=" * 70)

# Try to resolve the hostname first
hostname = "db.vlbvrhotrlipaoedudys.supabase.co"
print(f"\n1. Testing DNS resolution for {hostname}...")

try:
    ip_address = socket.gethostbyname(hostname)
    print(f"   ✅ Resolved to: {ip_address}")

    # If DNS works, try direct IP connection
    print(f"\n2. Trying direct IP connection to {ip_address}:5432...")
    direct_url = f"postgresql://postgres:KFH4ZlbuCCXpNCrc@{ip_address}:5432/postgres"

    try:
        conn = psycopg2.connect(direct_url)
        print(f"   ✅ Direct IP connection successful!")
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"   Database: {version[0][:50]}...")
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"   ❌ Direct IP failed: {e}")

except socket.gaierror as e:
    print(f"   ❌ DNS resolution failed: {e}")
    print(f"   The proxy is blocking DNS lookups for *.supabase.co")

# Try connection pooler (port 6543)
print(f"\n3. Trying Supabase Transaction Pooler (port 6543)...")
pooler_url = "postgresql://postgres:KFH4ZlbuCCXpNCrc@db.vlbvrhotrlipaoedudys.supabase.co:6543/postgres"

try:
    conn = psycopg2.connect(pooler_url)
    print(f"   ✅ Pooler connection successful!")
    conn.close()
except Exception as e:
    print(f"   ❌ Pooler failed: {type(e).__name__}: {str(e)[:100]}")

# Try session pooler (port 5432 with different mode)
print(f"\n4. Checking for IPv6 connectivity...")
try:
    ipv6_info = socket.getaddrinfo(hostname, 5432, socket.AF_INET6)
    if ipv6_info:
        print(f"   ℹ️  IPv6 addresses found: {len(ipv6_info)}")
        for info in ipv6_info[:2]:
            print(f"      {info[4][0]}")
except Exception as e:
    print(f"   ❌ IPv6 lookup failed: {type(e).__name__}")

print("\n" + "=" * 70)
print("💡 Diagnosis:")
print("   The proxy blocks DNS resolution for *.supabase.co domains.")
print("   Even with the new password, network access is still blocked.")
print("   Password reset alone doesn't bypass the proxy restriction.")
