import urllib.request
import re

def main():
    req = urllib.request.urlopen('http://127.0.0.1:5000/')
    html = req.read().decode('utf-8')

    print("=== 1. DESTINATIONS RENDERED ON BERANDA ===")
    matches = re.findall(r'<h5 class="card-title fw-bold text-dark mb-1">(.*?)</h5>', html)
    for idx, m in enumerate(matches):
        print(f"[{idx+1}] {m}")

    print("\n=== 2. PROMO CALLOUTS ON BERANDA ===")
    promos = re.findall(r'<span class="promo-title">(.*?)</span>', html, re.DOTALL)
    for idx, p in enumerate(promos):
        clean_p = re.sub(r'<.*?>', '', p).strip()
        print(f"[{idx+1}] {clean_p}")

    print("\n=== 3. PETUNJUK HARI & SPOTLIGHT BADGES ===")
    spotlight_part = html[html.find('id="spotlightSection"'):html.find('Wisata Favorit & Promo Berlangsung')]
    spotlight_badges = re.findall(r'class="badge (.*?)"', spotlight_part)
    for b in set(spotlight_badges):
        print(f"- Badge in Spotlight: {b}")

    print("\n=== 4. PROMO RIBBONS & PRICE BADGES ===")
    ribbons = re.findall(r'class="promo-badge-ribbon">(.*?)</span>', html, re.DOTALL)
    for idx, r in enumerate(ribbons):
        clean_r = re.sub(r'<.*?>', '', r).strip()
        print(f"[{idx+1}] Ribbon: {clean_r}")

    prices = re.findall(r'class="price-badge-modern">(.*?)</div>', html, re.DOTALL)
    for idx, pr in enumerate(prices):
        clean_pr = ' '.join(re.sub(r'<.*?>', ' ', pr).split())
        print(f"[{idx+1}] Price: {clean_pr}")

if __name__ == '__main__':
    main()
