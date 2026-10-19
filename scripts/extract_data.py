"""Trích dữ liệu ĐÃ TỔNG HỢP từ BigQuery re_gold ra CSV cho site (chạy local).

Chạy (cần quyền đọc BigQuery; dùng key qua biến môi trường, KHÔNG copy key vào repo này):

    export GOOGLE_APPLICATION_CREDENTIALS=../scrape-batdongsan-data/gcp_service_account.json
    python scripts/extract_data.py   # dùng conda env có google-cloud-bigquery

Nguyên tắc:
- Chỉ SELECT. Không ghi gì lên BigQuery.
- Output công khai (site + repo public) => chỉ bảng tổng hợp theo kỳ/thành phố/quận/khoảng giá.
  Không bao giờ xuất cột từng tin (title, link, product_id, số điện thoại...).
- Kỳ báo cáo lấy từ re_bronze.dim_report_period (seed ở repo scrape-batdongsan-data); dữ liệu từ
  mart_real_estate_period / mart_real_estate_rent_period: mỗi tin một dòng MỖI KỲ, dựng lại từ bronze.
  Không dùng mart_real_estate cho kỳ cũ: mart chỉ giữ bản cào mới nhất của mỗi tin, tin còn treo tới
  kỳ sau bị ghi đè nên lọc date_scraped của kỳ cũ chỉ ra phần tin đã biến mất (mẫu lệch).
- Mọi bảng có cột `period` đứng đầu. Thêm kỳ mới: thêm dòng vào seed bên repo scrape, `dbt seed` +
  `dbt run -s dim_report_period+`, rồi chạy lại script này.

TODO: chuyển các phép tổng hợp này thành mô hình dbt `mart_site_*` ở repo scrape-batdongsan-data.
"""

import csv
import sys
from pathlib import Path

from google.cloud import bigquery

OUT = Path(__file__).resolve().parent.parent / "sources" / "bds_real"
FORBIDDEN_COLUMNS = {"title", "link", "product_id", "agent_phone_hash", "phone", "url", "lat_long", "project_name"}
MAX_ROWS = 3000  # chốt chặn: bảng tổng hợp không thể lớn thế này nếu lỡ xuất nhầm dữ liệu từng tin

BEDROOMS = """
    case
      when bedrooms is null then null
      when safe_cast(bedrooms as int64) >= 4 then '4+'
      else bedrooms
    end"""

# --- Mua chung cư. price_num: triệu đồng; price_1m2: triệu đồng/m². -------------------------------
CC_BASE = f"""
with base as (
  select
    period,
    date_scraped,
    city_name as city,
    coalesce(district_name, 'Chưa rõ quận') as district,
    price_num,
    price_1m2,
    bin_price,
    bin_price_order,
    {BEDROOMS} as bedrooms
  from `{{project}}.re_gold.mart_real_estate_period`
  where real_estate_type = 'căn hộ chung cư'
    and intent = 'Sale'
    and city_name in ('Hồ Chí Minh', 'Hà Nội')
    and price_num is not null
    and not coalesce(expired, false)
)
"""

CC_QUERIES = {
    "cc_meta": """
        select period, min(date_scraped) as d0, max(date_scraped) as d1, count(*) as n_priced
        from base group by 1 order by 1""",
    "cc_price_bracket": """
        select period, city, bin_price, bin_price_order, count(*) as n
        from base group by 1, 2, 3, 4 order by 1, 2, 4""",
    "cc_bedroom_mix": """
        select period, city, bedrooms, count(*) as n
        from base where bedrooms is not null group by 1, 2, 3 order by 1, 2, 3""",
    "cc_city_kpi": """
        select
          period, city,
          count(*) as n,
          count(distinct if(district != 'Chưa rõ quận', district, null)) as n_district,
          round(avg(price_num) / 1000, 2) as avg_price_ty,
          round(avg(price_1m2), 1) as avg_price_1m2,
          countif(price_num < 2000) as n_lt2,
          countif(price_num < 3000) as n_lt3
        from base group by 1, 2 order by 1, 2""",
    "cc_district_count": """
        select period, city, district, count(*) as n
        from base group by 1, 2, 3 order by 1, 2, 4 desc""",
    "cc_district_price": """
        select
          period, city, district, count(*) as n,
          round(avg(price_1m2), 1) as avg_price_1m2,
          round(avg(price_num) / 1000, 2) as avg_price_ty
        from base
        where district != 'Chưa rõ quận' and price_1m2 is not null
        group by 1, 2, 3 having count(*) >= 10
        order by 1, 2, avg_price_1m2 desc""",
    "cc_afford": """
        select
          period, city, bedrooms, count(*) as n,
          round(avg(price_1m2), 1) as avg_price_1m2,
          countif(price_num < 2000) as n_lt2,
          countif(price_num < 3000) as n_lt3,
          countif(price_num < 5000) as n_lt5
        from base where bedrooms in ('1', '2', '3') group by 1, 2, 3 order by 1, 2, 3""",
    "cc_district_supply": """
        select
          period, city, bedrooms, district, count(*) as n,
          round(avg(price_1m2), 1) as avg_price_1m2,
          countif(price_num < 2000) as n_lt2,
          countif(price_num < 3000) as n_lt3,
          countif(price_num < 5000) as n_lt5
        from base where bedrooms in ('1', '2', '3') group by 1, 2, 3, 4 order by 1, 2, 3, 5 desc""",
}

# --- Mua nhà đất: 4 loại hình như bài tháng 7. ------------------------------------------------------
ND_BASE = """
with base as (
  select
    period,
    date_scraped,
    city_name as city,
    coalesce(district_name, 'Chưa rõ quận') as district,
    real_estate_type as type,
    price_num,
    price_1m2,
    area_num
  from `{project}.re_gold.mart_real_estate_period`
  where real_estate_type in ('nhà riêng', 'nhà mặt phố', 'nhà biệt thự liền kề', 'shophouse nhà phố thương mại')
    and intent = 'Sale'
    and city_name in ('Hồ Chí Minh', 'Hà Nội')
    and price_num is not null
    and not coalesce(expired, false)
)
"""

ND_QUERIES = {
    "nd_meta": """
        select period, min(date_scraped) as d0, max(date_scraped) as d1, count(*) as n_priced
        from base group by 1 order by 1""",
    "nd_type_kpi": """
        select
          period, city, type,
          count(*) as n,
          count(distinct if(district != 'Chưa rõ quận', district, null)) as n_district,
          round(avg(price_num) / 1000, 2) as avg_price_ty,
          round(avg(price_1m2), 1) as avg_price_1m2,
          round(avg(area_num), 1) as avg_area,
          countif(price_num < 5000) as n_lt5,
          countif(price_num < 10000) as n_lt10,
          countif(price_num < 20000) as n_lt20
        from base group by 1, 2, 3 order by 1, 2, 3""",
    "nd_district": """
        select
          period, city, type, district, count(*) as n,
          round(avg(price_num) / 1000, 2) as avg_price_ty,
          round(avg(price_1m2), 1) as avg_price_1m2
        from base
        where district != 'Chưa rõ quận'
        group by 1, 2, 3, 4 having count(*) >= 10
        order by 1, 2, 3, 5 desc""",
}

# --- Thuê chung cư. price_per_month: triệu đồng/tháng. -----------------------------------------------
# Lọc thô như bài tháng 7: diện tích 15-200 m², giá thuê 1-200 tr/tháng (mart thuê chưa có cờ outlier).
RENT_BASE = f"""
with base as (
  select
    period,
    date_scraped,
    city_name as city,
    coalesce(district_name, 'Chưa rõ quận') as district,
    price_per_month as rent,
    price_per_m2_per_month as rent_m2,
    {BEDROOMS} as bedrooms
  from `{{project}}.re_gold.mart_real_estate_rent_period`
  where city_name in ('Hồ Chí Minh', 'Hà Nội')
    and price_per_month between 1 and 200
    and area_num between 15 and 200
    and not coalesce(expired, false)
)
"""

RENT_QUERIES = {
    "rent_meta": """
        select period, min(date_scraped) as d0, max(date_scraped) as d1, count(*) as n_priced
        from base group by 1 order by 1""",
    "rent_bracket": """
        select
          period, city,
          case
            when rent < 10 then '< 10' when rent < 20 then '10-20' when rent < 30 then '20-30'
            when rent < 50 then '30-50' else '> 50'
          end as bin,
          case
            when rent < 10 then 1 when rent < 20 then 2 when rent < 30 then 3
            when rent < 50 then 4 else 5
          end as bin_order,
          count(*) as n
        from base group by 1, 2, 3, 4 order by 1, 2, 4""",
    "rent_city_kpi": """
        select
          period, city,
          count(*) as n,
          count(distinct if(district != 'Chưa rõ quận', district, null)) as n_district,
          round(avg(rent), 2) as avg_rent,
          round(avg(rent_m2), 3) as avg_rent_m2
        from base group by 1, 2 order by 1, 2""",
    "rent_bed": """
        select
          period, city, bedrooms, count(*) as n,
          round(avg(rent), 2) as avg_rent,
          round(avg(rent_m2), 3) as avg_rent_m2,
          countif(rent < 10) as n_lt10,
          countif(rent < 15) as n_lt15,
          countif(rent < 20) as n_lt20
        from base where bedrooms in ('1', '2', '3') group by 1, 2, 3 order by 1, 2, 3""",
    "rent_district": """
        select period, city, district, count(*) as n, round(avg(rent_m2), 3) as avg_rent_m2
        from base where district != 'Chưa rõ quận' and rent_m2 is not null
        group by 1, 2, 3 having count(*) >= 10
        order by 1, 2, avg_rent_m2 desc""",
    "rent_district_bed": """
        select period, city, bedrooms, district, count(*) as n, round(avg(rent_m2), 3) as avg_rent_m2
        from base where bedrooms in ('1', '2', '3') and district != 'Chưa rõ quận'
        group by 1, 2, 3, 4 order by 1, 2, 3, 5 desc""",
}

PERIODS_SQL = """
select period, label, start_date, end_date
from `{project}.re_bronze.dim_report_period`
order by period
"""

# CSV đời cũ (một snapshot, không có cột period), đã thay bằng cc_* ở trên.
LEGACY_FILES = ["meta", "price_bracket", "bedroom_mix", "city_kpi", "district_count", "district_price", "afford",
                "district_supply"]


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
    client = bigquery.Client()  # key lấy từ GOOGLE_APPLICATION_CREDENTIALS; không đọc/in nội dung key
    fmt = {"project": client.project}

    write_csv("periods", client.query(PERIODS_SQL.format(**fmt)).result())
    for base_sql, queries in [(CC_BASE, CC_QUERIES), (ND_BASE, ND_QUERIES), (RENT_BASE, RENT_QUERIES)]:
        base = base_sql.format(**fmt)
        for name, sql in queries.items():
            write_csv(name, client.query(base + sql).result())

    for name in LEGACY_FILES:
        (OUT / f"{name}.csv").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
