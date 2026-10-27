#!/usr/bin/env python3
"""Run a bounded JudyRecords bulk collection loop through Spider."""
import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from v2.proxy.config import get_proxy
from v1.scrape.judyrecords_bulk import DEFAULT_OUT, run_bulk


def load_queries(path):
    text = Path(path).read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [line.strip() for line in text.splitlines() if line.strip()]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("queries file must be a JSON list of strings or one query per line")
    return [item.strip() for item in value if item.strip()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", action="append", default=[], help="JudyRecords search query; repeat or use --queries-file")
    parser.add_argument("--queries-file", help="JSON list or newline-delimited JudyRecords search queries")
    parser.add_argument("--seed", action="append", default=[], help="HTTPS JudyRecords seed URL for links/crawl discovery")
    parser.add_argument("--discovery-mode", choices=["links", "crawl"], default="links")
    parser.add_argument("--limit-per-query", type=int, default=50)
    parser.add_argument("--target", type=int, default=10, help="Unique record jobs to complete this run")
    parser.add_argument("--concurrency", type=int, default=3, help="Spider Unlimited concurrent scrapes (1-3)")
    parser.add_argument("--batch-size", type=int, default=50, help="Queue claim batch size")
    parser.add_argument("--enqueue-batch", type=int, default=500, help="Queue insert batch size")
    parser.add_argument("--ai-per-second", type=float, default=1.0, help="Serialized Spider AI rate (max 1.0 on the current plan)")
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--lease-seconds", type=int, default=300)
    parser.add_argument("--rounds", type=int, default=1, help="Repeat the full process after the target is complete")
    parser.add_argument("--run-id", default="judy")
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--webhook-listen", help="Local webhook bind address, for example 127.0.0.1:8787")
    parser.add_argument("--webhook-url", help="Public Spider webhook URL; required if the listener is local-only")
    parser.add_argument("--webhook-token", default=os.environ.get("SPIDER_WEBHOOK_TOKEN", ""))
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--allow-partial", action="store_true", help="Exit 0 even if discovery did not reach the target")
    args = parser.parse_args(argv)

    queries = list(args.query)
    if args.queries_file:
        try:
            queries.extend(load_queries(args.queries_file))
        except (OSError, ValueError) as error:
            parser.error(str(error))
    seeds = [seed.strip() for seed in args.seed if seed.strip()]
    if not queries and not seeds:
        parser.error("provide at least one --query/--queries-file or --seed")
    if not 1 <= args.target <= 1_000_000:
        parser.error("target must be between 1 and 1,000,000")
    if not 1 <= args.concurrency <= 3:
        parser.error("concurrency must be 1-3 for the Unlimited plan")
    if not 1 <= args.batch_size <= 500:
        parser.error("batch-size must be 1-500")
    if not 1 <= args.enqueue_batch <= 5000:
        parser.error("enqueue-batch must be 1-5000")
    if not 1 <= args.limit_per_query <= 100:
        parser.error("limit-per-query must be 1-100")
    if not 0 < args.ai_per_second <= 1:
        parser.error("ai-per-second must be greater than 0 and at most 1 on the current plan")
    if not 1 <= args.max_attempts <= 10:
        parser.error("max-attempts must be 1-10")
    if not 30 <= args.lease_seconds <= 3600:
        parser.error("lease-seconds must be 30-3600")
    if not 1 <= args.rounds <= 24:
        parser.error("rounds must be 1-24")
    if not args.webhook_token and args.webhook_listen:
        parser.error("SPIDER_WEBHOOK_TOKEN or --webhook-token is required when --webhook-listen is set")

    key = os.environ.get("SPIDER_API_KEY", "")
    if not key:
        parser.error("SPIDER_API_KEY is required")
    try:
        proxy = get_proxy(required=True)
    except ValueError as error:
        parser.error(str(error))

    code, _ = run_bulk(
        key=key,
        proxy=proxy,
        out_dir=args.out,
        target=args.target,
        concurrency=args.concurrency,
        batch_size=args.batch_size,
        enqueue_batch=args.enqueue_batch,
        queries=queries,
        seeds=seeds,
        discovery_mode=args.discovery_mode,
        limit_per_query=args.limit_per_query,
        ai_per_second=args.ai_per_second,
        max_attempts=args.max_attempts,
        lease_seconds=args.lease_seconds,
        rounds=args.rounds,
        run_id=args.run_id,
        webhook_listen=args.webhook_listen,
        webhook_url=args.webhook_url,
        webhook_token=args.webhook_token,
        progress_every=args.progress_every,
        allow_partial=args.allow_partial,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
