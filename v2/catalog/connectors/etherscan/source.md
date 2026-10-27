# Etherscan API (Ethereum + 60+ EVM chains)

Key: `none required` for the free tier (5 calls/sec, 100,000 calls/day, single Ethereum mainnet endpoint). For higher limits, additional EVM chains (Polygon, BNB, Arbitrum, Optimism, Base, etc.), and access to paid endpoints, register a free API key at https://etherscan.io/myapikey — no payment required for the basic tier.

Endpoint: `https://api.etherscan.io/api`
Auth: optional `apikey=<Etherscan API key>` query parameter. Free-tier limits without a key are still 5/sec and 100k/day, but a key bumps the daily limit and unlocks multi-chain endpoints under `https://api-<chain>.etherscan.io/api`.
Format: `JSON`

Documentation:
- API home: https://etherscan.io/apis
- API key signup: https://etherscan.io/myapikey
- API docs (chained by module): https://docs.etherscan.io/
- Plans: https://etherscan.io/apis#pricing
- Status: https://etherscan.io/statuspage (sub-second response is normal, free tier holds up under 5 rps)

## What it is

Etherscan runs an explorer for **60+ EVM-compatible chains** (Ethereum, Polygon PoS, BNB Smart Chain, Arbitrum One, Optimism, Base, Avalanche C-Chain, Fantom, Gnosis, Linea, Scroll, zkSync Era, …). The REST API exposes **read-only** chain data:

- **Account / address**: balance, normal & internal transactions, ERC-20 / ERC-721 / ERC-1155 token transfers, blocks validated, account creation
- **Block**: block reward, mining reward, uncle inclusion, block / uncle count by address
- **Transaction**: status, receipt status, gettxreceiptstatus
- **Contract**: ABI, source code (Solidity), verified contract status, contract creation
- **Token**: total supply, name / symbol / decimals
- **Logs / events**: filter by address + topic, up to 1,000 blocks per call
- **Stats**: ETH supply, ETH price, total nodes, daily transactions, network hashrate, market cap
- **Proxy / read**: read any public function on any contract via `eth_call`

This is the **default OSINT data source for on-chain activity**: who-funded-whom, treasury movements, contract upgrades, sanctions evasion patterns, exchange hot/cold wallet flows, NFT wash-trade detection.

## How it's used in OpenTIR-Data (3 ways)

### Way 1: chain analytics as a tier-1 data source

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/etherscan.py
# Daily snapshot of the Ethereum mainnet: supply, gas, last N blocks, top accounts.
import os
import time
import httpx
import orjson
from datetime import datetime, timezone
from ingest.clickhouse import ch

ETHERSCAN_KEY = os.environ.get("ETHERSCAN_API_KEY", "")  # optional
BASE = "https://api.etherscan.io/api"


def call(module: str, action: str, **params) -> dict:
    """Single-source Etherscan call. Respects 5 calls/sec."""
    params = {"module": module, "action": action, **params}
    if ETHERSCAN_KEY:
        params["apikey"] = ETHERSCAN_KEY
    r = httpx.get(BASE, params=params, timeout=20.0)
    r.raise_for_status()
    return r.json()


def fetch_daily_snapshot() -> list[dict]:
    """One row per (chain, metric, date). Cheap, idempotent."""
    now = datetime.now(timezone.utc)
    rows = []

    # 1. ETH total supply (single integer, very cheap)
    r = call("stats", "ethsupply")
    if r.get("status") == "1":
        rows.append({
            "chain": "ethereum",
            "metric": "eth_supply_wei",
            "value": int(r["result"]),
            "as_of": now,
            "credibility": 1,
            "source_url": "https://etherscan.io/statistics/supply",
        })

    # 2. Latest block number
    r = call("proxy", "eth_blockNumber")
    if r.get("status") == "1":
        rows.append({
            "chain": "ethereum",
            "metric": "block_number",
            "value": int(r["result"], 16),
            "as_of": now,
            "credibility": 1,
            "source_url": "https://etherscan.io/blocks",
        })

    # 3. ETH price (USD)
    r = call("stats", "ethprice")
    if r.get("status") == "1":
        p = r["result"]
        rows.append({
            "chain": "ethereum",
            "metric": "eth_usd",
            "value": float(p["ethusd"]),
            "as_of": now,
            "credibility": 1,
            "source_url": "https://etherscan.io/chart/etherprice",
        })

    return rows


def fetch_top_accounts(addresses: list[str]) -> list[dict]:
    """Sample known major addresses (Binance, Kraken, Tornado, etc.)."""
    now = datetime.now(timezone.utc)
    rows = []
    for addr in addresses:
        r = call("account", "balance", address=addr, tag="latest")
        if r.get("status") != "1":
            continue
        rows.append({
            "chain": "ethereum",
            "address": addr.lower(),
            "metric": "balance_wei",
            "value": int(r["result"]),
            "as_of": now,
            "credibility": 1,
            "source_url": f"https://etherscan.io/address/{addr}",
        })
        time.sleep(0.25)  # 4 rps — stay under the 5 rps free cap
    return rows


if __name__ == "__main__":
    rows = fetch_daily_snapshot()
    if rows:
        ch.insert_observations("chain_observations", rows)
    print(f"[{datetime.now(timezone.utc).isoformat()}] inserted {len(rows)} chain rows")
```

### Way 2: append-only event log of an address of interest

For OFAC-sanctioned wallets, exchange hot wallets, known hack drains:

```python
# Add to ingest/fetchers/etherscan.py
def fetch_token_transfers(address: str, from_block: int = 0) -> list[dict]:
    """All ERC-20 transfers involving `address` from `from_block` onwards.
    Up to 10,000 per call; paginate by moving from_block to last +1.
    """
    r = call(
        "account", "tokentx",
        address=address,
        startblock=from_block,
        endblock=99999999,
        sort="asc",
    )
    if r.get("status") != "1":
        return []
    rows = []
    for t in r["result"]:
        rows.append({
            "chain": "ethereum",
            "tx_hash": t["hash"],
            "block_number": int(t["blockNumber"]),
            "timestamp": datetime.fromtimestamp(int(t["timeStamp"]), tz=timezone.utc),
            "from": t["from"].lower(),
            "to": t["to"].lower(),
            "token": t["tokenSymbol"],
            "token_addr": t["contractAddress"].lower(),
            "value": int(t["value"]) / (10 ** int(t["tokenDecimal"])),
            "credibility": 1,
            "source_url": f"https://etherscan.io/tx/{t['hash']}",
        })
    return rows
```

### Way 3: contract verification status

```python
# Add to ingest/fetchers/etherscan.py
def fetch_contract_source(address: str) -> dict | None:
    """Returns the verified Solidity source for `address`, or None."""
    r = call("contract", "getsourcecode", address=address)
    if r.get("status") != "1" or r["result"][0]["SourceCode"] == "":
        return None
    return {
        "address": address.lower(),
        "name": r["result"][0]["ContractName"],
        "compiler": r["result"][0]["CompilerVersion"],
        "verified": 1,
        "source": r["result"][0]["SourceCode"],
        "credibility": 1,
        "source_url": f"https://etherscan.io/address/{address}#code",
    }
```

## Quick call — verify

```bash
# 1. Total ETH supply (no key required, but the call works either way)
curl -sL "https://api.etherscan.io/api?module=stats&action=ethsupply" \
  | python3 -c "
import json,sys
d = json.load(sys.stdin)
print('status:', d.get('status'), 'message:', d.get('message'))
print('result:', d.get('result', '—')[:60] + '...' if d.get('result') else '—')
"
# Expected: status:1, result: <integer wei of total ETH supply, ~120M * 10^18>

# 2. Latest block
curl -sL "https://api.etherscan.io/api?module=proxy&action=eth_blockNumber" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('block:', int(d['result'], 16))"
# Expected: block: <current Ethereum height, 18M+>

# 3. With a free key (after registering at https://etherscan.io/myapikey)
curl -sL "https://api.etherscan.io/api?module=account&action=balance&address=0xd8da6bf26964af9d7eed9e03e53415d37aa96045&tag=latest&apikey=YOUR_KEY" \
  | python3 -m json.tool
# Expected: vitalik.eth balance in wei

# 4. ETH price
curl -sL "https://api.etherscan.io/api?module=stats&action=ethprice" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('eth_usd:', d['result']['ethusd'])"
# Expected: current price
```

## Endpoints used (verified live 2026-09-04)

```text
GET /api?module=stats&action=ethsupply              # total ETH in wei
GET /api?module=stats&action=ethprice               # ETH price + btc price
GET /api?module=stats&action=ethdailyprice          # historical daily price
GET /api?module=stats&action=dailyavgblocktime     # avg block time
GET /api?module=stats&action=totalnodes            # node count
GET /api?module=stats&action=chainsize             # chain size in bytes
GET /api?module=stats&action=nodecount             # active node count
GET /api?module=proxy&action=eth_blockNumber        # latest block (hex)
GET /api?module=proxy&action=eth_gasPrice          # current gas price
GET /api?module=account&action=balance&address=X&tag=latest
GET /api?module=account&action=balancemulti&address=X1,X2,...&tag=latest
GET /api?module=account&action=txlist&address=X&startblock=0&endblock=99999999
GET /api?module=account&action=txlistinternal&address=X
GET /api?module=account&action=tokentx&address=X&contractaddress=Y
GET /api?module=account&action=tokennfttx&address=X
GET /api?module=account&action=getminedblocks&address=X&blocktype=blocks
GET /api?module=block&action=getblockreward&blockno=N
GET /api?module=contract&action=getsourcecode&address=X
GET /api?module=contract&action=getabi&address=X
GET /api?module=transaction&action=gettxreceiptstatus&txhash=H
GET /api?module=logs&action=getLogs&fromBlock=N&toBlock=M&address=X&topic0=Y
GET /api?module=token&action=tokeninfo&contractaddress=X
GET /api?module=token&action=tokensupply&contractaddress=X
```

For 60+ EVM chains, swap the base URL:

```text
https://api.etherscan.io/api                # Ethereum mainnet
https://api-polygonscan.com/api             # Polygon
https://api.bscscan.com/api                 # BNB Smart Chain
https://api.arbiscan.io/api                 # Arbitrum One
https://api-optimistic.etherscan.io/api     # Optimism
https://api.basescan.org/api                # Base
https://api-avalanche.etherscan.io/api      # Avalanche C-Chain
https://api.ftmscan.com/api                 # Fantom Opera
https://api.gnosisscan.io/api               # Gnosis Chain
https://api.lineascan.build/api             # Linea
https://api.scrollscan.com/api              # Scroll
https://api-zkevm.polygonscan.com/api       # Polygon zkEVM
https://api.era.zksync.network/api          # zkSync Era
```

## Notes

- **Free tier is genuinely usable**: 5 calls/sec, 100k calls/day is enough to cover a daily snapshot of all chain stats (10 calls) + 100 addresses (1 call each = 100 calls) + 100k events at 10k/call = 10 calls. That's the whole daily ingest for ~210 calls. Comfortably under the limit. Add a free key for higher headroom.
- **Etherscan is the aggregator, not the chain source.** Etherscan runs its own full node for each chain; the data is what a real Ethereum node would return, just packaged in a JSON API. There is no canonical "Ethereum public API" — Etherscan is the de facto standard.
- **The big on-chain analytics alternative is the Graph** (decentralized subgraphs for specific protocols), but it's read-only for the indexed subgraphs, and Etherscan covers **all** addresses, not just ones someone has indexed. Etherscan is the "every address" source.
- **For multi-chain**: the Etherscan-family product suite (BscScan, PolygonScan, Arbiscan, etc.) shares the same API shape. One fetcher, one chain parameter, ~5 lines of code per chain to add. **The same free key from etherscan.io works on all of them.**
- **Rate-limit edges**: Etherscan tracks a 5-rps rolling window, not a daily window for rps. The 100k/day is daily UTC. Hitting 5 rps exactly (200 ms per call) is the safest pattern. A `429` returns `{"status":"0","message":"NOTOK","result":"Max rate limit reached"}` and should trigger a 30-second backoff.
- **Privacy / sanctions**: Etherscan publishes a `sanctioned` label for known OFAC-sanctioned addresses. We can ingest the OFAC SDN list (https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV) and cross-join with our on-chain observations. **This is one of the highest-OSINT-value features in the whole project** — the data, the sources, and the visualization are all off-the-shelf.
- **For the world dashboard**: this is a tier-1 "cyber / financial-crime" data source. Combine with sanctioned-address data, OFAC SDN, and labeled entity lists (Chainalysis free public tags at https://labels.chainalysis.com/ — free, with API key, JSON over HTTPS), and you can render live "sanctioned wallets received X ETH in the last 24 hours" — the exact kind of visualization that journalists and investigators pay for.
- **No web-scraping needed**: the API is the canonical way. Don't try to scrape etherscan.io — they ban IPs quickly, and the API is more reliable.
- **Credibility tier**: 1 (Etherscan is the industry reference; the data is the chain's own state).
- **Storage cost**: a daily snapshot of (chain × metric × day) is ~1 row per metric per chain per day. Even with all 60+ EVM chains, the daily snapshot is ~5,000 rows/year. Negligible. **Token transfer events** scale: 1M transfers/day across all chains = 365M rows/year. Compresses 10x in ClickHouse. Still under 1 GB/year on disk.
- **No key, no email, no signup**: the free tier (5 rps / 100k day) works **without** registering at all. The unauthenticated path is real and useful for low-volume use. The `apikey=` parameter is **optional**, not required, for most endpoints.

## License: no proprietary data, Etherscan API is free for OSINT use

Etherscan's API is **public and free for read-only use**. No special terms beyond their fair-use policy (https://etherscan.io/terms). The **data** returned is the public state of the blockchain — no licensing concerns. The **API client code** we write is Apache-2.0 (matches our project license). No copyleft, no attribution requirement beyond standard academic citation.

