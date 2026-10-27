#!/usr/bin/env python3
"""Setup Cloudflare Logpush jobs to stream logs into R2 bucket 'harvy-logs'.

References:
- https://developers.cloudflare.com/logs/
- https://developers.cloudflare.com/logs/r2-logpush/
- https://developers.cloudflare.com/logs/reference/logpush-api-configuration/
"""
import argparse
import json
import os
import urllib.request
import urllib.error


def make_cf_request(endpoint: str, token: str, method: str = "GET", data: dict = None) -> dict:
    url = f"https://api.cloudflare.com/client/v4{endpoint}"
    payload = json.dumps(data).encode("utf-8") if data else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        err_body = err.read().decode("utf-8", errors="replace")
        try:
            return json.loads(err_body)
        except Exception:
            return {"success": False, "errors": [{"message": f"HTTP {err.code}: {err_body}"}]}


def generate_curl_commands(account_id: str, zone_id: str, bucket_name: str = "harvy-logs") -> str:
    return f"""# 1. Create R2 Bucket (via Wrangler or API):
npx wrangler r2 bucket create {bucket_name}

# 2. Setup Workers Trace Events Logpush (Account level):
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/{account_id}/logpush/jobs" \\
     -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{{
       "name": "harvy-workers-trace-logs",
       "dataset": "workers_trace_events",
       "destination_conf": "r2://{bucket_name}/cloudflare/workers/{{DATE}}?account-id={account_id}&access-key-id=$R2_ACCESS_KEY_ID&secret-access-key=$R2_SECRET_ACCESS_KEY",
       "enabled": true
     }}'

# 3. Setup HTTP Requests Logpush (Zone level):
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/{zone_id}/logpush/jobs" \\
     -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{{
       "name": "harvy-zone-http-logs",
       "dataset": "http_requests",
       "destination_conf": "r2://{bucket_name}/cloudflare/http/{{DATE}}?account-id={account_id}&access-key-id=$R2_ACCESS_KEY_ID&secret-access-key=$R2_SECRET_ACCESS_KEY",
       "enabled": true
     }}'
"""


def main():
    parser = argparse.ArgumentParser(description="Configure Cloudflare Logs (Logpush) to R2 bucket 'harvy-logs'")
    parser.add_argument("--account-id", default=os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), help="Cloudflare Account ID")
    parser.add_argument("--zone-id", default=os.environ.get("CLOUDFLARE_ZONE_ID", ""), help="Cloudflare Zone ID (optional)")
    parser.add_argument("--bucket", default="harvy-logs", help="R2 Bucket name (default: harvy-logs)")
    parser.add_argument("--dry-run", action="store_true", help="Print API commands and payload without executing")
    args = parser.parse_args()

    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    acc_id = args.account_id or "<ACCOUNT_ID>"
    zone_id = args.zone_id or "<ZONE_ID>"

    if args.dry_run or not token or not args.account_id:
        print("Cloudflare Logpush configuration commands for R2 'harvy-logs':\n")
        print(generate_curl_commands(acc_id, zone_id, args.bucket))
        if not token:
            print("Note: Set CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY to execute directly.")
        return

    # 1. Ensure bucket exists
    print(f"Checking/creating R2 bucket '{args.bucket}'...")
    bucket_res = make_cf_request(f"/accounts/{args.account_id}/r2/buckets/{args.bucket}", token, method="PUT")
    if bucket_res.get("success"):
        print(f"Bucket '{args.bucket}' ready.")
    else:
        print(f"Bucket check note: {bucket_res.get('errors')}")

    # 2. Setup Workers trace logpush job
    r2_key = os.environ.get("R2_ACCESS_KEY_ID", "")
    r2_secret = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    auth_query = f"&access-key-id={r2_key}&secret-access-key={r2_secret}" if r2_key and r2_secret else ""
    dest_workers = f"r2://{args.bucket}/cloudflare/workers/{{DATE}}?account-id={args.account_id}{auth_query}"

    print("Configuring account-level Workers Trace Events Logpush job...")
    workers_job = {
        "name": "harvy-workers-trace-logs",
        "dataset": "workers_trace_events",
        "destination_conf": dest_workers,
        "enabled": True,
    }
    w_res = make_cf_request(f"/accounts/{args.account_id}/logpush/jobs", token, method="POST", data=workers_job)
    print("Workers Trace Logpush result:", "Success" if w_res.get("success") else w_res.get("errors"))

    # 3. Setup Zone HTTP logpush job if zone given
    if args.zone_id:
        dest_http = f"r2://{args.bucket}/cloudflare/http/{{DATE}}?account-id={args.account_id}{auth_query}"
        print(f"Configuring zone-level HTTP Requests Logpush job for zone {args.zone_id}...")
        http_job = {
            "name": "harvy-zone-http-logs",
            "dataset": "http_requests",
            "destination_conf": dest_http,
            "enabled": True,
        }
        h_res = make_cf_request(f"/zones/{args.zone_id}/logpush/jobs", token, method="POST", data=http_job)
        print("Zone HTTP Logpush result:", "Success" if h_res.get("success") else h_res.get("errors"))


if __name__ == "__main__":
    main()
