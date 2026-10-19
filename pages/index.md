---
title: Thị trường BĐS Việt Nam
---

<Alert status="warning">
  <b>Bản thử nghiệm: toàn bộ số liệu trên trang này là dữ liệu GIẢ</b>, sinh ngẫu nhiên để kiểm tra giao diện và quy trình xuất bản. Không dùng để tham khảo thị trường.
</Alert>

```sql cities
select distinct city from bds_demo.listings_monthly order by city
```

```sql types
select distinct property_type from bds_demo.listings_monthly order by property_type
```

<Dropdown name=city data={cities} value=city title="Thành phố" defaultValue="Hồ Chí Minh" />
<Dropdown name=ptype data={types} value=property_type title="Loại hình" defaultValue="Chung cư" />

```sql series
select
    cast(month as date) as month,
    listings,
    median_price_per_m2 as price
from bds_demo.listings_monthly
where city = '${inputs.city.value}'
  and property_type = '${inputs.ptype.value}'
order by month
```

```sql kpi
with latest as (select * from ${series} order by month desc limit 1),
     prev3  as (select * from ${series} order by month desc limit 1 offset 3),
     first  as (select * from ${series} order by month asc limit 1)
select
    latest.price                      as price,
    latest.listings                   as listings,
    latest.price / prev3.price - 1    as price_chg_3m,
    latest.listings / prev3.listings - 1 as listings_chg_3m,
    latest.price / first.price - 1    as price_chg_all,
    strftime(latest.month, '%m/%Y')   as latest_month
from latest, prev3, first
```

```sql districts
select
    district,
    median_price_per_m2 as price,
    listings,
    change_3m
from bds_demo.district_summary
where city = '${inputs.city.value}'
  and property_type = '${inputs.ptype.value}'
order by price desc
```

## Tóm tắt tháng <Value data={kpi} column=latest_month />

<BigValue
    data={kpi}
    value=price
    title="Giá trung vị (triệu đồng/m²)"
    fmt="#,##0.0"
    comparison=price_chg_3m
    comparisonFmt=pct1
    comparisonTitle="so với 3 tháng trước"
/>

<BigValue
    data={kpi}
    value=listings
    title="Số tin đang đăng"
    fmt="#,##0"
    comparison=listings_chg_3m
    comparisonFmt=pct1
    comparisonTitle="so với 3 tháng trước"
/>

## Giá {inputs.ptype.label} tại {inputs.city.label} đã tăng <Value data={kpi} column=price_chg_all fmt=pct1 /> trong 12 tháng

<LineChart
    data={series}
    x=month
    y=price
    xFmt="mmm yyyy"
    yFmt="#,##0"
    yAxisTitle="triệu đồng/m²"
    yScale=true
/>

## <Value data={districts} column=district row=0 /> đắt nhất, <Value data={districts} column=district row={districts.length - 1} /> rẻ nhất

<BarChart
    data={districts}
    x=district
    y=price
    swapXY=true
    sort=false
    yFmt="#,##0"
    yAxisTitle="triệu đồng/m²"
/>

## Số tin đăng theo tháng

<AreaChart
    data={series}
    x=month
    y=listings
    xFmt="mmm yyyy"
    yFmt="#,##0"
    yAxisTitle="số tin"
/>

## Chi tiết theo quận

<DataTable data={districts} rows=10>
    <Column id=district title="Quận" />
    <Column id=price title="Giá tr/m²" fmt="#,##0.0" />
    <Column id=change_3m title="3 tháng" fmt=pct1 contentType=delta />
    <Column id=listings title="Số tin" fmt="#,##0" />
</DataTable>

---

**Nguồn dữ liệu:** dữ liệu giả sinh bởi `scripts/gen_dummy_data.py`. Bản thật sẽ lấy từ tin rao trên batdongsan.com.vn, cập nhật hàng tuần.
**Hạn chế (áp dụng cho bản thật):** đây là giá rao, không phải giá giao dịch; tin rao có thể trùng hoặc không còn hiệu lực.
