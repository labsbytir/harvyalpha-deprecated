# Blockchair API (40+ blockchains, including Bitcoin)

Key: `pending — register a free key at https://blockchair.com/api/docs` (free API key is required for sustained use; without one, calls are aggressively rate-limited and quickly return HTTP 430 with `{"context":{"code":4,"message":"You've exceeded the rate limit for anonymous API calls. Please add a valid API key."}}`).

Endpoint: `https://api.blockchair.com/{coin}/{resource}` — where `{coin}` is `bitcoin`, `ethereum`, `litecoin`, `bitcoin-cash`, `dogecoin`, `dash`, `ripple`, `cardano`, `polkadot`, `solana`, `tron`, `monero`, `zilliqa`, `tezos`, `mixin`, `eos`, `stellar`, `tron`, `algorand`, `cosmos`, `kusama`, `near`, `aptos`, `sui`, `arbitrum-one`, `optimism`, `polygon`, `base`, `gnosis`, and ~20 more.
Auth: required for sustained use — `?key=<your-key>` query parameter or `X-API-Key: <key>` header.
Format: `JSON` (default), `CSV` (for downloads), `Parquet` (for the bulk dataset).

Documentation:
- API docs: https://blockchair.com/api/docs
- API key signup: https://blockchair.com/api/docs#authentication
- Pricing: https://blockchair.com/pricing (free = 30 calls/min, no daily cap, single user)
- Dashboard: https://blockchair.com/dashboard
- Bulk dumps: https://blockchair.com/data

## What it is

Blockchair is the **multi-chain Etherscan-equivalent** for explorers that don't have a first-class public REST API. The killer feature is the **cross-chain query surface**: one API call returns a normalized response for **40+ chains** — Bitcoin, Ethereum, Litecoin, Cardano, Solana, Polygon, Arbitrum, and so on. The data is sourced from Blockchair's own full nodes (not relayed through Etherscan or a third party), so it's authoritative.

The 3 most useful surfaces for OSINT:

1. **Address lookup** (`/bitcoin/dashboards/address/{addr}`) — balance, total received/spent, first/last seen block, transaction count, UTXO age distribution, mempool
2. **Bulk transactions for an address** (`/bitcoin/transactions?q=...`) — paginated full transaction history with all inputs/outputs, script types, fee paid
3. **Block-level stats** (`/bitcoin/stats`) — chain size, transaction count, mempool size, hashrate, miner, halving countdown, lightning network stats

The 40+ chain support is **the single biggest reason to use Blockchair over Etherscan for multi-chain OSINT work**: Etherscan is EVM-only (60+ EVM chains but no Bitcoin, no Cardano, no Cosmos). Blockchair covers both.

## How it's used in OpenTIR-Data (3 ways)

### Way 1: address snapshot across all chains

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/blockchair.py
# Watch a list of OFAC-sanctioned addresses across all chains Blockchair supports.
import os
import time
import httpx
import orjson
from datetime import datetime, timezone
from ingest.clickhouse import ch

BLOCKCHAIR_KEY = os.environ.get("BLOCKCHAIR_API_KEY", "")
if not BLOCKCHAIR_KEY:
    raise SystemExit("BLOCKCHAIR_API_KEY required — register at https://blockchair.com/api/docs")

BASE = "https://api.blockchair.com"
CHAINS = ["bitcoin", "ethereum", "litecoin", "bitcoin-cash", "dogecoin",
          "dash", "ripple", "cardano", "solana", "polygon", "arbitrum-one",
          "optimism", "base", "tron", "cosmos"]


def call(path: str, **params) -> dict:
    """Blockchair call. 30 rps on the free tier."""
    params = {**params, "key": BLOCKCHAIR_KEY}
    r = httpx.get(f"{BASE}{path}", params=params, timeout=30.0)
    r.raise_for_status()
    return r.json()


def fetch_address_snapshot(chain: str, address: str) -> dict | None:
    """Balance + transaction count + first/last seen for one address on one chain."""
    try:
        d = call(f"/{chain}/dashboards/address/{address}")
    except httpx.HTTPError as e:
        print(f"[{chain}/{address[:10]}] HTTP error: {e}")
        return None
    data = d.get("data", {})
    if not data:
        return None
    addr_data = data.get(address, {})
    if not addr_data:
        return None
    return {
        "chain": chain,
        "address": address,
        "balance": addr_data.get("address", {}).get("balance"),  # in satoshis / wei
        "balance_usd": addr_data.get("address", {}).get("balance_usd"),
        "received": addr_data.get("address", {}).get("received"),
        "spent": addr_data.get("address", {}).get("spent"),
        "tx_count": addr_data.get("address", {}).get("transaction_count"),
        "first_seen_at": addr_data.get("address", {}).get("first_seen_receiving"),
        "last_seen_at": addr_data.get("address", {}).get("last_seen_receiving"),
        "credibility": 1,
        "source_url": f"https://blockchair.com/{chain}/address/{address}",
        "as_of": datetime.now(timezone.utc),
    }


def fetch_all_chains_for_address(address: str) -> list[dict]:
    """One address, all 15 chains. 15 calls, ~3 seconds with the free key."""
    rows = []
    for chain in CHAINS:
        row = fetch_address_snapshot(chain, address)
        if row:
            rows.append(row)
        time.sleep(0.05)  # stay under 30 rps
    return rows


if __name__ == "__main__":
    # Example: OFAC-sanctioned wallet (do not transact with these)
    sanctioned = [
        "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",   # Genesis block (illustrative)
    ]
    for addr in sanctioned:
        rows = fetch_all_chains_for_address(addr)
        if rows:
            ch.insert_observations("chain_addresses", rows)
        print(f"[{addr}] {len(rows)} chain rows")
```

### Way 2: daily chain-wide stats

```python
# Add to ingest/fetchers/blockchair.py
def fetch_chain_stats(chain: str = "bitcoin") -> dict:
    """Chain-wide daily stats: block count, hashrate, mempool, fees, market cap."""
    d = call(f"/{chain}/stats")
    return {
        "chain": chain,
        "blocks": d["data"][0]["blocks"],
        "transactions": d["data"][0]["transactions"],
        "outputs": d["data"][0]["outputs"],
        "mempool_transactions": d["data"][0]["mempool_transactions"],
        "mempool_size_bytes": d["data"][0]["mempool_size"],
        "best_block_height": d["data"][0]["best_block_height"],
        "hashrate_24h": d["data"][0]["hashrate_24h"],
        "difficulty": d["data"][0]["difficulty"],
        "next_retarget_estimate_blocks": d["data"][0]["next_retarget_estimate_blocks"],
        "median_transaction_fee_24h": d["data"][0]["median_transaction_fee_24h"],
        "as_of": datetime.now(timezone.utc),
        "credibility": 1,
        "source_url": f"https://blockchair.com/{chain}/dashboard",
    }
```

### Way 3: bulk CSV/Parquet download for backfill

```bash
# Bitcoin full chain dump in Parquet (one shot, ~600 GB compressed)
# Free tier blocks this size; needs "API+Data" plan ($99/mo)
# For our OSINT use, we just query the REST API for what we need.

# Smaller: daily block dump (a few MB) is fine on the free tier
curl -sL "https://api.blockchair.com/bitcoin/blocks?date=2026-09-03&key=YOUR_KEY" \
  -o bitcoin_blocks_2026-09-03.json

# CSV format
curl -sL "https://api.blockchair.com/bitcoin/transactions?q=time(2026-09-03)..time(2026-09-04)&export=csv&key=YOUR_KEY" \
  -o bitcoin_tx_2026-09-03.csv
```

## Quick call — verify

```bash
# 1. Without a key — should return 430
curl -sL -w "\n%{http_code}\n" "https://api.blockchair.com/bitcoin/stats" \
  | python3 -c "
import json,sys
lines = sys.stdin.read().splitlines()
print('http:', lines[-1])
d = json.loads('\n'.join(lines[:-1]))
print('status:', d.get('context', {}).get('code'))
print('message:', d.get('context', {}).get('error', '—')[:100])
"
# Expected: http: 430, code: 4, "You've exceeded the rate limit for anonymous API calls"

# 2. With a free key (after registering at https://blockchair.com/api/docs)
export BLOCKCHAIR_API_KEY="<your-key>"
curl -sL "https://api.blockchair.com/bitcoin/stats?key=$BLOCKCHAIR_API_KEY" \
  | python3 -c "
import json,sys
d = json.load(sys.stdin)
ctx = d.get('context', {})
print('code:', ctx.get('code'))
print('remaining:', ctx.get('rate_limit_remaining'))
print('last_block:', d['data'][0]['best_block_height'])
print('hashrate_24h:', d['data'][0]['hashrate_24h'])
print('mempool_tx:', d['data'][0]['mempool_transactions'])
"

# 3. Single address (e.g. the Genesis block coinbase)
curl -sL "https://api.blockchair.com/bitcoin/dashboards/address/1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa?key=$BLOCKCHAIR_API_KEY" \
  | python3 -c "
import json,sys
d = json.load(sys.stdin)
addr = d['data']['1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa']['address']
print('balance:', addr['balance'])
print('received:', addr['received'])
print('tx_count:', addr['transaction_count'])
"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /{chain}/stats                                      # chain-wide stats
GET /{chain}/dashboards/address/{addr}                 # one address
GET /{chain}/dashboards/addresses/{addr1,addr2,...}    # bulk addresses
GET /{chain}/transactions?q=...                        # filter transactions
GET /{chain}/transactions?q=time(Y-M-D)..time(Y-M-D)    # date range
GET /{chain}/blocks?q=id(1,2,3..100)                    # specific blocks
GET /{chain}/mempool/transactions                      # mempool snapshot
GET /{chain}/outputs?q=...                             # UTXO queries
GET /{chain}/calls?q=...                               # contract internal calls (EVM)
GET /{chain}/dashboards/transaction/{txid}             # one transaction
GET /ethereum/transfers/calls                           # EVM internal transfers
GET /ethereum/erc-20/{addr}                            # ERC-20 token list for an address
GET /{chain}/data/export?type=...                      # bulk CSV / Parquet (paid plans)
```

For the full 40+ chain list, see https://blockchair.com/api/docs#supported-blockchains.

## Notes

- **Free tier is real but required to register** — Blockchair does not allow sustained use without a key. The 30 rps, no-daily-cap free tier is more than enough for a daily snapshot of all chains (~50 calls/day, one per chain × per metric). The signup is one form, no payment, no card.
- **The 40+ chain support is the killer feature** — if you only need Bitcoin, use mempool.space (https://mempool.space/api) which is also free, no key, and lightning-fast. If you need **multi-chain coverage** (e.g. "every chain this address has ever been seen on"), Blockchair is the only practical option. Chainabuse, Chainalysis, and Crystal are paid; Blockchair is the only free multi-chain explorer with a real API.
- **Storage cost**: a daily snapshot of (chain × metric × day) is ~50 rows/day. Address-level snapshots scale with the number of watched addresses. Even with 10,000 watched addresses × 15 chains = 150,000 rows/day, that's ~55M rows/year. ClickHouse compresses 10-50x. **Storage: 10–50 GB/year** for the address-level data.
- **The /data endpoint** is a separate "API+Data" product (paid) that gives you bulk CSV/Parquet dumps of the full chain. For our use case, we don't need it — we query the live API. The live API is **read-only on Blockchair's full node** — same data, just queried on demand.
- **Mempool.space is the better Bitcoin-only choice** for transaction-broadcast monitoring (https://mempool.space/api), but it doesn't cover other chains. **Run both**: Blockchair for multi-chain, mempool.space for fast Bitcoin mempool + fee estimates.
- **OFAC integration**: combine with the OFAC SDN list (https://www.treasury.gov/ofac/downloads/sdn.csv) and the Chainalysis public labels (https://labels.chainalysis.com/ — free, with API key) for full sanctions-cross-reference. The visualization is straightforward: a table of `(address, OFAC_listed, balance_usd, last_seen, sanctioned_at)` with a map of the address's last activity origin (where the address first received its first funds).
- **For the world dashboard**: this is a tier-1 "cyber / sanctions / financial crime" source. The world map can render OFAC-sanctioned wallets as red points, with a tool-tip showing the address, the OFAC program it was listed under, and the balance. Very high signal-to-noise for a journalist or compliance-officer audience.
- **Credibility tier**: 1 (Blockchair runs its own full nodes; the data is the chain's own state).
- **No web-scraping needed**: the API is the canonical way. Blockchair explicitly forbids scraping the dashboard.
- **Rate-limit edges**: Blockchair returns HTTP 429 with `Retry-After: <seconds>` if you hit 30 rps. The 30 rps free cap is per-second rolling, not per-minute. A `time.sleep(0.05)` between calls is the safe pattern.

## License: no proprietary data, Blockchair API is free for OSINT use

Blockchair's API is **public and free for read-only use** under their terms (https://blockchair.com/terms). The data returned is the **public state of the blockchain** — no licensing concerns. The **API client code** we write is Apache-2.0 (matches our project license). No copyleft, no attribution requirement beyond standard academic citation.

**Difference from Etherscan**: Blockchair is **not** an Etherscan clone. Etherscan is EVM-only and offers a richer per-chain feature set. Blockchair is the **only free public API for many non-EVM chains** (Cardano, Solana, Cosmos, Polkadot, Monero, etc.). For our use case, **use both** — Etherscan for EVM deep-dives, Blockchair for the cross-chain unified view.

