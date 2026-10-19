"""Sinh dữ liệu GIẢ cho prototype. Không phải số liệu thật của thị trường.

Chạy: python3 scripts/gen_dummy_data.py
Ghi 2 file CSV vào sources/bds_demo/. Seed cố định nên kết quả lặp lại được.
"""

import csv
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "sources" / "bds_demo"
rng = random.Random(42)

MONTHS = [f"{y}-{m:02d}-01" for y, m in [(2025, 11), (2025, 12)] + [(2026, m) for m in range(1, 11)]]

# (thành phố, loại hình) -> (giá nền triệu đ/m², % tăng mỗi tháng, số tin nền)
BASE = {
    ("Hồ Chí Minh", "Chung cư"): (68.0, 0.008, 5200),
    ("Hồ Chí Minh", "Nhà phố"): (145.0, 0.004, 2100),
    ("Hà Nội", "Chung cư"): (72.0, 0.011, 4700),
    ("Hà Nội", "Nhà phố"): (160.0, 0.006, 1800),
}

# thành phố -> [(quận, hệ số giá so với trung bình thành phố)]
DISTRICTS = {
    "Hồ Chí Minh": [("Quận 1", 1.85), ("Quận 7", 1.05), ("Bình Thạnh", 1.0), ("Tân Bình", 0.95), ("Gò Vấp", 0.78), ("Thủ Đức", 0.88)],
    "Hà Nội": [("Hoàn Kiếm", 1.9), ("Cầu Giấy", 1.1), ("Đống Đa", 1.05), ("Nam Từ Liêm", 0.92), ("Hà Đông", 0.74), ("Long Biên", 0.82)],
}


def monthly_rows():
    for (city, ptype), (price0, growth, listings0) in BASE.items():
        for i, month in enumerate(MONTHS):
            price = price0 * (1 + growth) ** i * rng.uniform(0.985, 1.015)
            listings = listings0 * rng.uniform(0.92, 1.08)
            yield [month, city, ptype, round(listings), round(price, 1)]


def district_rows():
    for (city, ptype), (price0, growth, listings0) in BASE.items():
        latest_price = price0 * (1 + growth) ** (len(MONTHS) - 1)
        for district, factor in DISTRICTS[city]:
            price = latest_price * factor * rng.uniform(0.97, 1.03)
            change_3m = growth * 3 * rng.uniform(0.4, 1.9)
            listings = listings0 / len(DISTRICTS[city]) * rng.uniform(0.6, 1.5)
            yield [city, district, ptype, round(price, 1), round(listings), round(change_3m, 4)]


def write(name, header, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


if __name__ == "__main__":
    write("listings_monthly.csv", ["month", "city", "property_type", "listings", "median_price_per_m2"], monthly_rows())
    write("district_summary.csv", ["city", "district", "property_type", "median_price_per_m2", "listings", "change_3m"], district_rows())
    print("wrote", OUT)
