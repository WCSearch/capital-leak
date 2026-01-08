#!/usr/bin/env python3
"""
Check if Supabase domains are in the proxy allowed_hosts list.
"""
import os
import json
import base64

# Get the HTTPS_PROXY value
proxy_url = os.getenv('HTTPS_PROXY', '')

print("Checking Proxy Allowed Hosts Configuration")
print("=" * 70)

if not proxy_url:
    print("❌ No HTTPS_PROXY found")
    exit(1)

# Extract JWT token from proxy URL
if ':jwt_' in proxy_url:
    jwt_part = proxy_url.split(':jwt_')[1].split('@')[0]
    print(f"Found JWT token (length: {len(jwt_part)})")

    # Decode JWT payload (middle part between dots)
    parts = jwt_part.split('.')
    if len(parts) >= 2:
        # Add padding if needed
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)

        try:
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)

            print(f"\nProxy Configuration:")
            print(f"  Organization: {data.get('organization_uuid', 'N/A')}")
            print(f"  Session: {data.get('session_id', 'N/A')}")
            print(f"  Use Egress Gateway: {data.get('use_egress_gateway', 'N/A')}")

            # Get allowed hosts
            allowed_hosts = data.get('allowed_hosts', '')
            hosts_list = [h.strip() for h in allowed_hosts.split(',')]

            print(f"\n📋 Total allowed hosts: {len(hosts_list)}")

            # Check for Supabase
            print(f"\n🔍 Checking for Supabase domains...")
            supabase_hosts = [h for h in hosts_list if 'supabase' in h.lower()]

            if supabase_hosts:
                print(f"✅ Found {len(supabase_hosts)} Supabase-related hosts:")
                for host in supabase_hosts:
                    print(f"   - {host}")
            else:
                print(f"❌ NO Supabase domains found in allowed_hosts")
                print(f"\n   Your Supabase URL: vlbvrhotrlipaoedudys.supabase.co")
                print(f"   Database host: db.vlbvrhotrlipaoedudys.supabase.co")
                print(f"   Both are BLOCKED by the proxy\n")

            # Sample some hosts to show what IS allowed
            print(f"\n📌 Sample of allowed hosts (first 20):")
            for host in hosts_list[:20]:
                print(f"   - {host}")

            print(f"\n💡 Key Finding:")
            if not supabase_hosts:
                print(f"   The Pro tier upgrade did NOT add *.supabase.co to the whitelist.")
                print(f"   GitHub integration is for database branching (schema sync),")
                print(f"   NOT for network access to Supabase from Claude Code.")

        except Exception as e:
            print(f"❌ Error decoding JWT: {e}")
