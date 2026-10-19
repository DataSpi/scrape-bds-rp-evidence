"""Trích dữ liệu ĐÃ TỔNG HỢP từ BigQuery re_gold ra CSV cho site (chạy local).

Chạy (cần quyền đọc BigQuery; dùng key qua biến môi trường, KHÔNG copy key vào repo này):

    export GOOGLE_APPLICATION_CREDENTIALS=../scrape-batdongsan-data/gcp_service_account.json
    python scripts/extract_data.py [--snapshot-start 2026-10-16]   # dùng conda env có google-cloud-bigquery

Nguyên tắc:
- Chỉ SELECT. Không ghi gì lên BigQuery.
- Output công khai (site + repo public) => chỉ bảng tổng hợp theo thành phố/quận/khoảng giá.
  Không bao giờ xuất cột từng tin (title, link, product_id, số điện thoại...).
- Snapshot = các tin được scrape từ --snapshot-start trở đi. mart_real_estate chỉ giữ bản mới nhất
  của mỗi tin, trộn nhiều đợt scrape và có tin không có date_scraped; lọc theo ngày để ra một lát cắt
  nhất quán.

TODO: chuyển các phép tổng hợp này thành mô hình dbt `mart_site_*` ở repo scrape-batdongsan-data.
"""

import argparse
import csv
import sys
from pathlib import Path

from google.cloud import bigquery

OUT = Path(__file__).resolve().parent.parent / "sources" / "bds_real"
FORBIDDEN_COLUMNS = {"title", "link", "product_id", "agent_phone_hash", "phone", "url", "lat_long", "project_name"}
MAX_ROWS = 2000  # chốt chặn: bảng tổng hợp không thể lớn thế này nếu lỡ xuất nhầm dữ liệu từng tin

CITIES = ("Hồ Chí Minh", "Hà Nội")

# Mỗi bảng: tên file -> SQL (dùng CTE `base` ở dưới). price_num: triệu đồng; price_1m2: triệu đồng/m².
BASE = """
with base as (
  select
    city_name as city,
    coalesce(district_name, 'Chưa rõ quận') as district,
    price_num,
    price_1m2,
    bin_price,
    bin_price_order,
    case
      when bedrooms is null then null
      when safe_cast(bedrooms as int64) >= 4 then '4+'
      else bedrooms
    end as bedrooms
  from `{project}.re_gold.mart_real_estate`
  where real_estate_type = 'căn hộ chung cư'
    and intent = 'Sale'
    and city_name in ('Hồ Chí Minh', 'Hà Nội')
    and price_num is not null
    and not coalesce(expired, false)
    and date_scraped >= date '{snapshot_start}'
)
"""

QUERIES = {
    "price_bracket": """
        select city, bin_price, bin_price_order, count(*) as n
        from base group by 1, 2, 3 order by 1, 3""",
    "bedroom_mix": """
        select city, bedrooms, count(*) as n
        from base where bedrooms is not null group by 1, 2 order by 1, 2""",
    "city_kpi": """
        select
          city,
          count(*) as n,
          round(avg(price_num) / 1000, 2) as avg_price_ty,
          round(avg(price_1m2), 1) as avg_price_1m2,
          countif(price_num < 2000) as n_lt2,
          countif(price_num < 3000) as n_lt3
        from base group by 1 order by 1""",
    "district_count": """
        select city, district, count(*) as n
        from base group by 1, 2 order by 1, 3 desc""",
    "district_price": """
        select
          city, district, count(*) as n,
          round(avg(price_1m2), 1) as avg_price_1m2,
          round(avg(price_num) / 1000, 2) as avg_price_ty
        from base
        where district != 'Chưa rõ quận' and price_1m2 is not null
        group by 1, 2 having count(*) >= 10
        order by 1, avg_price_1m2 desc""",
    "afford": """
        select
          city, bedrooms, count(*) as n,
          countif(price_num < 2000) as n_lt2,
          countif(price_num < 3000) as n_lt3,
          countif(price_num < 5000) as n_lt5
        from base where bedrooms in ('1', '2', '3') group by 1, 2 order by 1, 2""",
    "district_supply": """
        select
          city, bedrooms, district, count(*) as n,
          countif(price_num < 2000) as n_lt2,
          countif(price_num < 3000) as n_lt3,
          countif(price_num < 5000) as n_lt5
        from base where bedrooms in ('1', '2', '3') group by 1, 2, 3 order by 1, 2, 4 desc""",
}

META_SQL = """
select
  date '{snapshot_start}' as snapshot_start,
  max(date_scraped) as snapshot_end,
  count(*) as n_priced
from `{project}.re_gold.mart_real_estate`
where real_estate_type = 'căn hộ chung cư' and intent = 'Sale'
  and city_name in ('Hồ Chí Minh', 'Hà Nội') and price_num is not null
  and not coalesce(expired, false) and date_scraped >= date '{snapshot_start}'
"""


def write_csv(name, result):
    cols = [f.name for f in result.schema]
    bad = {c for c in cols if c.lower() in FORBIDDEN_COLUMNS}
    if bad:
        sys.exit(f"Từ chối ghi {name}: có cột không được phép công khai: {sorted(bad)}")
    rows = [list(r.values()) for r in result]
    if len(rows) > MAX_ROWS:
        sys.exit(f"Từ chối ghi {name}: {len(rows)} dòng > {MAX_ROWS}, có vẻ không phải bảng tổng hợp")
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(rows)
    print(f"  {name}.csv: {len(rows)} dòng, cột {cols}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot-start", default="2026-10-16", help="chỉ lấy tin scrape từ ngày này (YYYY-MM-DD)")
    args = ap.parse_args()

    client = bigquery.Client()  # key lấy từ GOOGLE_APPLICATION_CREDENTIALS; không đọc/in nội dung key
    fmt = {"project": client.project, "snapshot_start": args.snapshot_start}
    print("Snapshot từ", args.snapshot_start)

    write_csv("meta", client.query(META_SQL.format(**fmt)).result())
    base = BASE.format(**fmt)
    for name, sql in QUERIES.items():
        write_csv(name, client.query(base + sql).result())


if __name__ == "__main__":
    main()
