#!/usr/bin/env python3
"""
Check if AWS S3 and related services are accessible through the proxy.
"""
import os
import json
import base64

# Get the HTTPS_PROXY value
proxy_url = os.getenv('HTTPS_PROXY', '')

print("Checking AWS/S3 Access Through Proxy")
print("=" * 70)

if ':jwt_' in proxy_url:
    jwt_part = proxy_url.split(':jwt_')[1].split('@')[0]
    parts = jwt_part.split('.')

    if len(parts) >= 2:
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)

        try:
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)

            allowed_hosts = data.get('allowed_hosts', '')
            hosts_list = [h.strip() for h in allowed_hosts.split(',')]

            # Check for AWS/S3 related domains
            print("🔍 Checking for AWS/S3 domains...\n")

            aws_keywords = ['amazon', 'aws', 's3', 'cloudfront', 'elasticbeanstalk']
            aws_hosts = []

            for host in hosts_list:
                if any(keyword in host.lower() for keyword in aws_keywords):
                    aws_hosts.append(host)

            if aws_hosts:
                print(f"✅ Found {len(aws_hosts)} AWS-related hosts in allowlist:")
                for host in aws_hosts:
                    print(f"   ✓ {host}")

                print("\n📊 S3 Access Analysis:")
                s3_hosts = [h for h in aws_hosts if 's3' in h.lower()]
                if s3_hosts:
                    print(f"   ✅ S3 domains found: {', '.join(s3_hosts)}")
                    print(f"   → You CAN likely connect to S3!")
                else:
                    print(f"   ⚠️  No explicit S3 domains, but may work via amazonaws.com")

            else:
                print("❌ NO AWS/S3 domains found in allowed_hosts")
                print("   S3 connections likely blocked")

            # Also check for other cloud storage
            print("\n🔍 Checking other cloud storage providers...")

            cloud_providers = {
                'Google Cloud Storage': ['storage.googleapis.com', 'cloud.google.com'],
                'Azure Storage': ['azure.com', 'blob.core.windows.net'],
                'DigitalOcean Spaces': ['digitaloceanspaces.com'],
                'Cloudflare R2': ['cloudflare.com']
            }

            available_storage = []
            for provider, keywords in cloud_providers.items():
                for keyword in keywords:
                    if any(keyword in h.lower() for h in hosts_list):
                        available_storage.append(f"{provider} ({keyword})")
                        break

            if available_storage:
                print(f"✅ Available cloud storage options:")
                for storage in available_storage:
                    print(f"   ✓ {storage}")
            else:
                print("❌ No major cloud storage providers found")

        except Exception as e:
            print(f"❌ Error: {e}")
else:
    print("❌ No proxy configuration found")
