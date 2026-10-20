#!/usr/bin/env python3
"""poidh v1 (Arbitrum, POIDHNFT 0xdffe8a4a4103f968ffd61fd082d08c41dcf9b940) -> per-wallet CSV.
Read-only JSON-RPC (eth_call) against a public Arbitrum endpoint. No keys.
Columns: wallet, eth_paid_out (full bounty amounts of COMPLETED bounties this wallet issued),
eth_earned (full bounty amounts of completed bounties this wallet won, before the 2.5% fee),
v1_nfts_held (current balance of poidh v1 NFTs), bounties_completed_issued, bounties_won.
Completed = claimer != 0x0 (acceptClaim sets claimer; cancelBounty zeroes amount and leaves claimer 0x0)."""
import json, sys, time, urllib.request, csv, collections
from decimal import Decimal
from eth_abi import encode, decode
from eth_utils import keccak, to_checksum_address

RPC = sys.argv[1] if len(sys.argv) > 1 else "https://arbitrum-one-rpc.publicnode.com"
C = "0xdffe8a4a4103f968ffd61fd082d08c41dcf9b940"
ZERO = "0x0000000000000000000000000000000000000000"

BLOCK = "latest"
def rpc_batch(calls):
    body = [{"jsonrpc": "2.0", "id": i, "method": "eth_call", "params": [{"to": C, "data": d}, BLOCK]} for i, d in enumerate(calls)]
    for attempt in range(5):
        try:
            r = urllib.request.Request(RPC, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "User-Agent": "poidh-v1-data"})
            out = json.load(urllib.request.urlopen(r, timeout=60))
            out = sorted(out, key=lambda x: x["id"])
            return [o.get("result") for o in out]
        except Exception as e:
            print("rpc retry", attempt, str(e)[:80], file=sys.stderr, flush=True)
            time.sleep(3 + attempt * 5)
    raise SystemExit("rpc failed")

def sel(sig): return "0x" + keccak(text=sig)[:4].hex()
def call1(sig, types=(), args=()):
    return rpc_batch([sel(sig) + encode(list(types), list(args)).hex()])[0]

_r = urllib.request.Request(RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_blockNumber", "params": []}).encode(), headers={"Content-Type": "application/json", "User-Agent": "poidh-v1-data"})
START_BLOCK = json.load(urllib.request.urlopen(_r, timeout=30))["result"]  # snapshot start (v1 is retired, so state is static)
n_bounties = decode(["uint256"], bytes.fromhex(call1("getBountiesLength()")[2:]))[0]
supply = decode(["uint256"], bytes.fromhex(call1("totalSupply()")[2:]))[0]
print("bounties", n_bounties, "nft totalSupply", supply, file=sys.stderr)

BT = "(uint256,address,string,string,uint256,address,uint256,uint256)"
bounties = []
step = 5
for s in range(0, n_bounties, step):
    e = min(n_bounties - 1, s + step - 1)
    res = rpc_batch([sel("getBounties(uint256,uint256)") + encode(["uint256", "uint256"], [s, e]).hex()])[0]
    if res is None: raise SystemExit(f"getBounties {s}-{e} failed")
    print("bounties", e + 1, "/", n_bounties, file=sys.stderr, flush=True)
    for b in decode([BT + "[]"], bytes.fromhex(res[2:]))[0]:
        bounties.append({"id": b[0], "issuer": to_checksum_address(b[1]), "amount": b[4], "claimer": to_checksum_address(b[5]), "claimId": b[7]})

paid = collections.Counter(); earned = collections.Counter(); n_issued = collections.Counter(); n_won = collections.Counter()
wallets = set()
completed = 0
for b in bounties:
    wallets.add(b["issuer"])
    if b["claimer"] != to_checksum_address(ZERO) and b["amount"] > 0:
        completed += 1
        paid[b["issuer"]] += b["amount"]; n_issued[b["issuer"]] += 1
        earned[b["claimer"]] += b["amount"]; n_won[b["claimer"]] += 1
        wallets.add(b["claimer"])

# every claim submitter interacted with the protocol (claims(i) until the array ends; claim count == minted NFTs)
CT = "(uint256,address,uint256,address,string,string,uint256,uint256)"
claimers = set()
for s0 in range(0, supply, 25):
    res = rpc_batch([sel("claims(uint256)") + encode(["uint256"], [i]).hex() for i in range(s0, min(supply, s0 + 25))])
    for r in res:
        if r and len(r) > 2:
            claimers.add(to_checksum_address("0x" + r[2 + 64 + 24:2 + 128]))  # getter returns fields flat; word 1 = claim issuer
    print("claims", s0, file=sys.stderr, flush=True)
wallets |= claimers

# NFT holders via ERC721Enumerable: tokenByIndex -> ownerOf
token_ids = []
for s in range(0, supply, 25):
    res = rpc_batch([sel("tokenByIndex(uint256)") + encode(["uint256"], [i]).hex() for i in range(s, min(supply, s + 25))])
    print("tokens", s, file=sys.stderr, flush=True)
    token_ids += [decode(["uint256"], bytes.fromhex(r[2:]))[0] for r in res]
held = collections.Counter()
for s in range(0, len(token_ids), 25):
    res = rpc_batch([sel("ownerOf(uint256)") + encode(["uint256"], [t]).hex() for t in token_ids[s:s + 25]])
    for r in res:
        held[to_checksum_address(decode(["address"], bytes.fromhex(r[2:]))[0])] += 1
contract_cs = to_checksum_address(C)
pending_in_contract = held.pop(contract_cs, 0)  # claim NFTs on open bounties sit in the contract itself
wallets |= set(held)

def eth(wei):  # exact decimal ETH from integer wei
    q = (Decimal(wei) / Decimal(10**18)).normalize()
    return format(q, "f")

rows = []
for w in wallets:
    rows.append([w, paid[w], earned[w], held[w], n_issued[w], n_won[w]])
rows.sort(key=lambda r: (-r[2], -r[1], -r[3], r[0]))
with open(sys.argv[2] if len(sys.argv) > 2 else "poidh_v1_wallets.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["wallet", "eth_paid_out", "eth_earned", "v1_nfts_held", "bounties_completed_issued", "bounties_won"])
    for r in rows:
        w.writerow([r[0], eth(r[1]), eth(r[2]), r[3], r[4], r[5]])
summary = {"bounties": n_bounties, "completed": completed, "cancelled": sum(1 for b in bounties if b["amount"] == 0),
           "nft_supply": supply, "nfts_in_contract_pending": pending_in_contract, "wallets": len(rows),
           "total_paid_out_eth": eth(sum(paid.values())), "total_earned_eth": eth(sum(earned.values())), "claim_submitters": len(claimers),
           "holders": len(held), "block": int(START_BLOCK, 16), "chain": "arbitrum-one", "contract": C}
json.dump(summary, open("summary.json", "w"), indent=1)
print(json.dumps(summary))
