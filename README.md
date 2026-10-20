# poidh v1 data: ETH paid out, ETH earned and v1 NFTs held, per wallet

Answer to poidh bounty [#1497 "poidh v1 data"](https://poidh.xyz/base/bounty/1497).

**CSV:** [`poidh_v1_wallets.csv`](poidh_v1_wallets.csv) (one row per wallet that interacted with poidh v1).

Source: the poidh v1 contract on Arbitrum One, `POIDHNFT` at
[`0xdffe8a4a4103f968ffd61fd082d08c41dcf9b940`](https://arbiscan.io/address/0xdffe8a4a4103f968ffd61fd082d08c41dcf9b940)
(bounties, claims and the claim NFTs all live in this one contract). Read directly from chain state with `eth_call`
(no indexer, no API), at the block in the "Snapshot" line below.

| column | meaning |
|---|---|
| `wallet` | checksummed address: every bounty issuer, every claim submitter (accepted or not) and every current v1 NFT holder |
| `eth_paid_out` | total ETH this wallet paid out as a bounty issuer, counting only **completed** bounties (a claim was accepted). Full bounty amount, fee included. Cancelled and still-open bounties are not counted. |
| `eth_earned` | total ETH this wallet won as a claimer of completed bounties, credited at the **full bounty amount** (the 2.5% protocol fee is not removed: a 1 ETH bounty counts as 1 ETH) |
| `v1_nfts_held` | how many poidh v1 NFTs (claim NFTs) this wallet holds right now |
| `bounties_completed_issued`, `bounties_won` | counts behind the two ETH columns |

How "completed" is decided (from the verified source): `acceptClaim` sets `bounty.claimer` and keeps `bounty.amount`;
`cancelBounty` sets `amount` to 0 and leaves `claimer` empty. So completed = `claimer != 0x0 && amount > 0`.

NFT holders come from ERC721Enumerable (`totalSupply`, `tokenByIndex`, `ownerOf`). Claim NFTs on bounties that are still open
are held by the contract itself; that address is left out of the holder rows and reported in the summary instead.

Amounts are exact: summed in wei and printed as decimal ETH (no float rounding).

Re-run: `python3 extract.py [ARBITRUM_RPC_URL] [out.csv]` (needs `eth-abi` and `eth-utils`).
