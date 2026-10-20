#!/home/agent/agent/browser-venv/bin/python -I
"""Render a PNG preview (summary + top rows) of poidh_v1_wallets.csv for the poidh claim image."""
import csv, json, sys
from PIL import Image, ImageDraw, ImageFont
rows = list(csv.reader(open("poidh_v1_wallets.csv")))
summary = json.load(open("summary.json"))
W, H = 1600, 900
im = Image.new("RGB", (W, H), (14, 17, 23)); d = ImageDraw.Draw(im)
def font(sz, bold=False):
    for p in (["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"] if bold else []) + ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"]:
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
d.text((50, 40), "poidh v1 data (Arbitrum POIDHNFT 0xdffe...b940)", fill=(235, 235, 235), font=font(36, True))
d.text((50, 95), f"{summary['bounties']} bounties ({summary['completed']} completed, {summary['cancelled']} cancelled) · {summary['nft_supply']} NFTs · {summary['wallets']} wallets", fill=(160, 200, 160), font=font(24))
d.text((50, 130), f"ETH paid out (completed): {float(summary['total_paid_out_eth']):.4f} · ETH earned: {float(summary['total_earned_eth']):.4f} · snapshot block {summary.get('block','?')}", fill=(160, 200, 160), font=font(24))
y = 190
hdr = ["wallet", "eth_paid_out", "eth_earned", "v1_nfts_held"]
xs = [50, 760, 1010, 1260]
for x, h in zip(xs, hdr): d.text((x, y), h, fill=(255, 200, 90), font=font(24, True))
y += 40
for r in rows[1:24]:
    vals = [r[0], f"{float(r[1]):.4f}", f"{float(r[2]):.4f}", r[3]]
    for x, v in zip(xs, vals): d.text((x, y), v, fill=(220, 220, 220), font=font(22))
    y += 28
d.text((50, H - 45), f"full CSV: {len(rows)-1} rows · method + script in the repo", fill=(140, 140, 140), font=font(20))
im.save("preview.png"); print("preview.png", im.size)
