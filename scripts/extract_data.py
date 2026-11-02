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
    area_num,
    bin_price,
    bin_price_order,
    {BEDROOMS} as bedrooms
  from `{{project}}.re_gold.mart_real_estate_period`
  where length(period) = 7  -- chỉ kỳ tháng (YYYY-MM); seed còn có kỳ tuần (YYYY-MM-DD), site không dùng
    and real_estate_type = 'căn hộ chung cư'
    and intent = 'Sale'
    and city_name in ('Hồ Chí Minh', 'Hà Nội')
    and price_num is not null
    and not coalesce(expired, false)
)
"""

# Căn "sống được" cho người mua lần đầu: 1PN từ 35 m², 2PN từ 50 m² (loại studio/căn siêu nhỏ).
ENTRY = """
, entry as (
  select * from (
    select *,
      case when bedrooms = '1' and area_num >= 35 then '1PN'
           when bedrooms = '2' and area_num >= 50 then '2PN' end as segment
    from base
  ) where segment is not null
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
    # Trang "căn đầu tiên": giá đầu vào của căn "sống được" (định nghĩa ở ENTRY). Giá: tỷ đồng.
    "cc_entry": ENTRY + """
        , q as (
          select distinct period, city, segment,
            percentile_cont(price_num, 0.1) over w as p10,
            percentile_cont(price_num, 0.25) over w as p25,
            percentile_cont(price_num, 0.5) over w as p50
          from entry window w as (partition by period, city, segment)
        )
        select period, city, segment, count(*) as n,
          count(distinct if(e.district != 'Chưa rõ quận', e.district, null)) as n_district,
          round(q.p10 / 1000, 2) as p10_ty, round(q.p25 / 1000, 2) as p25_ty, round(q.p50 / 1000, 2) as p50_ty,
          countif(e.price_num <= q.p25) as n_entry,
          -- diện tích trung vị của nhóm 25% căn rẻ nhất: với giá đầu vào thì được căn cỡ nào
          round(approx_quantiles(if(e.price_num <= q.p25, e.area_num, null), 2)[offset(1)], 0) as area_entry
        from entry e join q using (period, city, segment)
        group by 1, 2, 3, q.p10, q.p25, q.p50 order by 1, 2, 3""",
    "cc_entry_district": ENTRY + """
        , q as (
          select distinct period, city, segment, district,
            count(*) over w as n,
            percentile_cont(price_num, 0.25) over w as p25,
            percentile_cont(price_num, 0.5) over w as p50
          from entry where district != 'Chưa rõ quận'
          window w as (partition by period, city, segment, district)
        )
        select period, city, segment, district, n,
          round(p25 / 1000, 2) as p25_ty, round(p50 / 1000, 2) as p50_ty
        from q where n >= 30 order by 1, 2, 3, p25""",
    "cc_entry_hist": ENTRY + """
        select period, city, segment,
          least(floor(price_num / 500) * 0.5, 8) as bin_lo, count(*) as n
        from entry group by 1, 2, 3, 4 order by 1, 2, 3, 4""",
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
  where length(period) = 7
    and real_estate_type in ('nhà riêng', 'nhà mặt phố', 'nhà biệt thự liền kề', 'shophouse nhà phố thương mại')
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
    area_num,
    {BEDROOMS} as bedrooms
  from `{{project}}.re_gold.mart_real_estate_rent_period`
  where length(period) = 7
    and city_name in ('Hồ Chí Minh', 'Hà Nội')
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
    # Trang "thuê hay mua": tiền thuê căn "sống được" cùng định nghĩa ENTRY với cc_entry. Đơn vị: triệu/tháng.
    "rent_entry": ENTRY + """
        , q as (
          select distinct period, city, segment,
            percentile_cont(rent, 0.25) over w as p25,
            percentile_cont(rent, 0.5) over w as p50
          from entry window w as (partition by period, city, segment)
        )
        select period, city, segment, count(*) as n,
          round(q.p25, 1) as p25_rent, round(q.p50, 1) as p50_rent,
          round(approx_quantiles(e.area_num, 2)[offset(1)], 0) as area_p50
        from entry e join q using (period, city, segment)
        group by 1, 2, 3, q.p25, q.p50 order by 1, 2, 3""",
    "rent_entry_district": ENTRY + """
        , q as (
          select distinct period, city, segment, district,
            count(*) over w as n,
            percentile_cont(rent, 0.25) over w as p25,
            percentile_cont(rent, 0.5) over w as p50
          from entry where district != 'Chưa rõ quận'
          window w as (partition by period, city, segment, district)
        )
        select period, city, segment, district, n,
          round(p25, 1) as p25_rent, round(p50, 1) as p50_rent
        from q where n >= 30 order by 1, 2, 3, p25""",
}

PERIODS_SQL = """
select period, label, start_date, end_date
from `{project}.re_bronze.dim_report_period`
where length(period) = 7
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
