---
title: Soi giá chung cư cùng data analyst (cập nhật 10/2026)
---

```sql meta
select
  strftime(cast(snapshot_start as date), '%d/%m') as d0,
  strftime(cast(snapshot_end as date), '%d/%m/%Y') as d1,
  replace(format('{:,}', cast(n_priced as bigint)), ',', '.') as n_txt
from bds_real.meta
```

```sql kpi
select
  max(case when city = 'Hồ Chí Minh' then n end) as hcm_n,
  max(case when city = 'Hà Nội' then n end) as hn_n,
  max(case when city = 'Hồ Chí Minh' then avg_price_ty end) as hcm_ty,
  max(case when city = 'Hà Nội' then avg_price_ty end) as hn_ty,
  max(case when city = 'Hồ Chí Minh' then avg_price_1m2 end) as hcm_m2,
  max(case when city = 'Hà Nội' then avg_price_1m2 end) as hn_m2,
  max(case when city = 'Hồ Chí Minh' then n_lt3 end) as hcm_lt3,
  max(case when city = 'Hà Nội' then n_lt3 end) as hn_lt3
from bds_real.city_kpi
```

```sql kpi2
select
  replace(format('{:,}', cast(hcm_n as bigint)), ',', '.') as hcm_n_txt,
  replace(format('{:,}', cast(hn_n as bigint)), ',', '.') as hn_n_txt,
  printf('%.2f', hcm_ty) as hcm_ty_t,
  printf('%.2f', hn_ty) as hn_ty_t,
  printf('%.1f', hcm_m2) as hcm_m2_t,
  printf('%.1f', hn_m2) as hn_m2_t,
  printf('%.1f', 100.0 * (hn_m2 / hcm_m2 - 1)) as gap_m2_t,
  printf('%.1f', 100.0 * (hn_ty / hcm_ty - 1)) as gap_ty_t,
  replace(format('{:,}', cast(hcm_lt3 as bigint)), ',', '.') as hcm_lt3_txt,
  replace(format('{:,}', cast(hn_lt3 as bigint)), ',', '.') as hn_lt3_txt,
  printf('%.1f', 100.0 * hcm_lt3 / hcm_n) as hcm_lt3_p,
  printf('%.1f', 100.0 * hn_lt3 / hn_n) as hn_lt3_p,
  printf('%.1f', (hcm_lt3 * 1.0 / hcm_n) / (hn_lt3 * 1.0 / hn_n)) as lt3_ratio_t
from ${kpi}
```

Cập nhật số liệu thật cho [bài phân tích giá chung cư tháng 7/2026](https://spyno.substack.com/p/i-xem-chung-cu-cung-tho-so-p2) (tiếp nối [P1](https://spyno.substack.com/p/i-xem-nha-cung-data-analyst-p1) đăng tháng 9/2025). Bản này dùng đợt scrape ngày {meta[0].d0} đến {meta[0].d1} với <b>{meta[0].n_txt}</b> tin chung cư rao bán có giá ở HCM & HN, và là lần thử chuyển phần trình bày từ Looker Studio sang một trang web tĩnh viết bằng code. Chi tiết kĩ thuật mình sẽ viết bài riêng.

Mời mọi người lại soi giá cùng mình. Spoiler: số tháng 10 không khớp hoàn toàn với tháng 7, và mình sẽ nói thẳng chỗ nào khác, vì sao chưa dám kết luận.

# Khai báo kĩ thuật

- Nguồn dữ liệu: [https://batdongsan.com.vn/](https://batdongsan.com.vn/)
    - Chỉ lấy tin **căn hộ chung cư rao bán** ở HCM & HN, có giá, chưa hết hạn, thu thập từ {meta[0].d0} đến {meta[0].d1}. Vẫn gồm cả tin chưa xác thực như bài trước.
- Kỹ thuật:
    - Tool cào Python: HTTP Request, BeautifulSoup; xử lý bằng dbt + BigQuery
    - Github: [https://github.com/DataSpi/scrape-batdongsan-data](https://github.com/DataSpi/scrape-batdongsan-data) (pipeline) và [https://github.com/DataSpi/scrape-bds-rp-evidence](https://github.com/DataSpi/scrape-bds-rp-evidence) (trang này)
    - Data visualization: trang này (Evidence), và [Google Looker Studio](https://lookerstudio.google.com/reporting/9e21618f-97dc-4480-b101-cbda26b9b2a5) cho phần dự án
- Note:
    - Vẫn dùng địa giới hành chính cũ trước sáp nhập, vì mình quen, đọc địa giới mới chả biết đâu vào với đâu.
    - Số tháng 10 và số tháng 7 **không cùng điều kiện**. Mẫu thu thập lần này lớn hơn: HCM từ 12.067 lên {kpi2[0].hcm_n_txt} tin, HN từ 6.770 lên {kpi2[0].hn_n_txt} tin (số quận gần như giữ nguyên). Giá/m² trung bình theo quận ở HN thấp hơn tháng 7 ở hầu hết các quận. Mình chưa phân biệt được đó là giá thật sự đổi hay do mẫu thu thập đổi, nên mọi so sánh với bài cũ trong trang này chỉ để tham khảo.

# Tổng quan

## Nguồn cung

**Nguồn cung tập trung ở phân khúc 3-10 tỷ ở cả HCM & HN.**

```sql bracket
select city, bin_price, bin_price_order, n,
  round(100.0 * n / sum(n) over (partition by city), 1) as pct
from bds_real.price_bracket
order by bin_price_order, city
```

```sql bracket_head
select
  replace(format('{:,}', cast(sum(case when city = 'Hồ Chí Minh' and bin_price_order in (3, 4) then n end) as bigint)), ',', '.') as hcm_mid,
  replace(format('{:,}', cast(sum(case when city = 'Hồ Chí Minh' then n end) as bigint)), ',', '.') as hcm_tot,
  printf('%.1f', 100.0 * sum(case when city = 'Hồ Chí Minh' and bin_price_order in (3, 4) then n end) / sum(case when city = 'Hồ Chí Minh' then n end)) as hcm_pct,
  replace(format('{:,}', cast(sum(case when city = 'Hà Nội' and bin_price_order in (3, 4) then n end) as bigint)), ',', '.') as hn_mid,
  replace(format('{:,}', cast(sum(case when city = 'Hà Nội' then n end) as bigint)), ',', '.') as hn_tot,
  printf('%.1f', 100.0 * sum(case when city = 'Hà Nội' and bin_price_order in (3, 4) then n end) / sum(case when city = 'Hà Nội' then n end)) as hn_pct
from bds_real.price_bracket
```

- HCM: {bracket_head[0].hcm_mid}/{bracket_head[0].hcm_tot} ≈ <b>{bracket_head[0].hcm_pct}%</b> tin nằm trong khoảng 3-10 tỷ.
- HN: {bracket_head[0].hn_mid}/{bracket_head[0].hn_tot} ≈ <b>{bracket_head[0].hn_pct}%</b>.

<BarChart
    data={bracket}
    x=bin_price
    y=pct
    series=city
    type=grouped
    sort=false
    yFmt="0.0"
    yAxisTitle="% số tin của từng thành phố"
    title="Tỷ trọng tin theo khoảng giá"
/>

**Chung cư 2PN & 3PN chiếm phần lớn nguồn cung.**

```sql beds
select city,
  case when cast(bedrooms as varchar) = '4+' then '4PN+' else cast(bedrooms as varchar) || 'PN' end as label,
  n,
  round(100.0 * n / sum(n) over (partition by city), 1) as pct
from bds_real.bedroom_mix
order by bedrooms, city
```

```sql beds_head
select
  replace(format('{:,}', cast(sum(case when city = 'Hồ Chí Minh' and cast(bedrooms as varchar) in ('2', '3') then n end) as bigint)), ',', '.') as hcm_23,
  replace(format('{:,}', cast(sum(case when city = 'Hồ Chí Minh' then n end) as bigint)), ',', '.') as hcm_tot,
  printf('%.1f', 100.0 * sum(case when city = 'Hồ Chí Minh' and cast(bedrooms as varchar) in ('2', '3') then n end) / sum(case when city = 'Hồ Chí Minh' then n end)) as hcm_pct,
  replace(format('{:,}', cast(sum(case when city = 'Hà Nội' and cast(bedrooms as varchar) in ('2', '3') then n end) as bigint)), ',', '.') as hn_23,
  replace(format('{:,}', cast(sum(case when city = 'Hà Nội' then n end) as bigint)), ',', '.') as hn_tot,
  printf('%.1f', 100.0 * sum(case when city = 'Hà Nội' and cast(bedrooms as varchar) in ('2', '3') then n end) / sum(case when city = 'Hà Nội' then n end)) as hn_pct
from bds_real.bedroom_mix
```

- HCM: {beds_head[0].hcm_23}/{beds_head[0].hcm_tot} ≈ <b>{beds_head[0].hcm_pct}%</b> (tính trên số tin có ghi số phòng ngủ).
- HN: {beds_head[0].hn_23}/{beds_head[0].hn_tot} ≈ <b>{beds_head[0].hn_pct}%</b>.

<BarChart
    data={beds}
    x=label
    y=pct
    series=city
    type=grouped
    sort=false
    yFmt="0.0"
    yAxisTitle="% số tin của từng thành phố"
    title="Tỷ trọng tin theo số phòng ngủ"
/>

## Giá

**HCM vs HN: giá/m² trung bình gần như ngang nhau, nhưng cửa giá mềm vẫn chênh xa.**

- Giá/m² TB: HCM <b>{kpi2[0].hcm_m2_t}</b> tr/m², HN <b>{kpi2[0].hn_m2_t}</b> tr/m² (HN cao hơn {kpi2[0].gap_m2_t}%). Giá TB: HCM {kpi2[0].hcm_ty_t} tỷ, HN {kpi2[0].hn_ty_t} tỷ (HN cao hơn {kpi2[0].gap_ty_t}%).
- Tin dưới 3 tỷ: HCM {kpi2[0].hcm_lt3_txt}/{kpi2[0].hcm_n_txt} ≈ <b>{kpi2[0].hcm_lt3_p}%</b>, HN {kpi2[0].hn_lt3_txt}/{kpi2[0].hn_n_txt} ≈ <b>{kpi2[0].hn_lt3_p}%</b>, tức HCM gấp <b>{kpi2[0].lt3_ratio_t}</b> lần HN.
- Bài tháng 7 viết: *"Giá TB chung cư hai bên chỉ chênh khoảng 11% (HCM 8.22 tỷ / 86.8tr/m², HN 9.15 tỷ / 94.1tr/m²)."* Lần này khoảng cách thu hẹp đáng kể, nhưng xem lại ghi chú về mẫu thu thập ở trên trước khi kết luận HN đã rẻ đi.
- Nhìn riêng giá trung bình vẫn đánh giá thấp khoảng cách thật giữa hai thị trường: tỷ lệ tin dưới 3 tỷ cho thấy rõ hơn ai còn đường vào.

## Phân hóa theo vị trí

Các quận trung tâm ghi nhận mức giá/m² cao nhất, giảm dần khi dịch chuyển ra vùng ven. Bảng xếp hạng dưới đây chỉ tính quận có từ 30 tin trở lên, để tránh quận ít tin làm méo kết quả.

```sql loc
select
  max(case when city = 'Hồ Chí Minh' and district = 'Quận 1' then avg_price_1m2 end) as q1,
  max(case when city = 'Hồ Chí Minh' and district = 'Quận 1' then n end) as q1_n,
  max(case when city = 'Hà Nội' and district = 'Hoàn Kiếm' then avg_price_1m2 end) as hk,
  max(case when city = 'Hà Nội' and district = 'Hoàn Kiếm' then n end) as hk_n
from bds_real.district_price
```

```sql loc2
select
  printf('%.1f', q1) as q1_t,
  cast(cast(q1_n as bigint) as varchar) as q1_n_t,
  printf('%.1f', hk) as hk_t,
  cast(cast(hk_n as bigint) as varchar) as hk_n_t,
  printf('%.1f', 100.0 * (q1 / 233.5 - 1)) as q1_vs_jul_t,
  printf('%.2f', hk / q1) as hk_vs_q1_t
from ${loc}
```

```sql seven
select
  replace(format('{:,}', cast(sum(case when district in ('Quận 9', 'Quận 2', 'Quận 7', 'Bình Thạnh', 'Tân Phú', 'Bình Tân', 'Bình Chánh') then n end) as bigint)), ',', '.') as seven,
  replace(format('{:,}', cast(sum(n) as bigint)), ',', '.') as tot,
  printf('%.1f', 100.0 * sum(case when district in ('Quận 9', 'Quận 2', 'Quận 7', 'Bình Thạnh', 'Tân Phú', 'Bình Tân', 'Bình Chánh') then n end) / sum(n)) as pct
from bds_real.district_count
where city = 'Hồ Chí Minh'
```

### Hồ Chí Minh

- Tháng 9/2025: *"Số lượng căn hộ chung cư được rao bán nhiều nhất thuộc về các quận: Q9, Q2, Q7, Bình Thạnh, Tân Phú, Bình Tân, Bình Chánh. Tổng số 404/485 bài đăng, chiếm hơn 80%."*
    - Tháng 10/2026: 7 quận trên chiếm {seven[0].seven}/{seven[0].tot} ≈ <b>{seven[0].pct}%</b> (tháng 7/2026 là 67.4%).
- Các quận trung tâm vẫn có giá/m² cao nhất.
    - Tháng 9/2025: Quận 1, *"174 triệu/m²"*. Tháng 7/2026: *"233.5 triệu/m² — tăng gần 34%"*.
    - Tháng 10/2026: Quận 1 <b>{loc2[0].q1_t} tr/m²</b> ({loc2[0].q1_n_t} tin), thay đổi {loc2[0].q1_vs_jul_t}% so với tháng 7. Quận trung tâm là nơi số liệu hai đợt khớp nhất.

```sql top_hcm
select district, avg_price_1m2 as price, n
from bds_real.district_price
where city = 'Hồ Chí Minh' and n >= 30
order by avg_price_1m2 desc
limit 10
```

<BarChart
    data={top_hcm}
    x=district
    y=price
    swapXY=true
    sort=false
    labels=true
    yFmt="#,##0.0"
    title="Top 10 giá/m² trung bình, HCM (triệu đồng)"
/>

### Hà Nội

- Tháng 7/2026: *"Hoàn Kiếm: 338 triệu/m² — quận đắt nhất cả nước, gần gấp rưỡi Quận 1 HCM (233.5 triệu/m²)."*
    - Tháng 10/2026: Hoàn Kiếm <b>{loc2[0].hk_t} tr/m²</b>, gấp {loc2[0].hk_vs_q1_t} lần Quận 1 ({loc2[0].q1_t} tr/m²). Lưu ý Hoàn Kiếm chỉ có {loc2[0].hk_n_t} tin, mẫu nhỏ.

```sql top_hn
select district, avg_price_1m2 as price, n
from bds_real.district_price
where city = 'Hà Nội' and n >= 30
order by avg_price_1m2 desc
limit 10
```

<BarChart
    data={top_hn}
    x=district
    y=price
    swapXY=true
    sort=false
    labels=true
    yFmt="#,##0.0"
    title="Top 10 giá/m² trung bình, HN (triệu đồng)"
/>

# Phương pháp phân tích

Khi phân tích giá nhà, mình tạm chia người mua chung cư thành 3 nhóm với nhu cầu và túi tiền như sau:

1. Người độc thân, hoặc vợ chồng chưa/không có con → thường tìm căn 1PN.
    - Ngân sách giả định: dưới 2 tỷ.
2. Gia đình nhỏ, vợ chồng và 1–2 con → thường tìm căn 2PN.
    - Ngân sách giả định: 2–3 tỷ.
3. Gia đình 3 thế hệ cùng sinh sống → thường tìm căn 3PN.
    - Ngân sách giả định: 3–5 tỷ.

Các mốc ngân sách trên là ước lượng dựa trên kinh nghiệm cá nhân của mình, không phải khảo sát hay nghiên cứu. Mục đích nhằm trả lời câu hỏi của nhóm người mua điển hình: với từng túi tiền và nhu cầu, tôi có những lựa chọn nào?

```sql aff
select city, bedrooms, n, n_lt2, n_lt3, n_lt5,
  printf('%.1f', 100.0 * n_lt2 / n) as p2,
  printf('%.1f', 100.0 * n_lt3 / n) as p3,
  printf('%.1f', 100.0 * n_lt5 / n) as p5,
  replace(format('{:,}', cast(n as bigint)), ',', '.') as n_txt,
  replace(format('{:,}', cast(n_lt2 as bigint)), ',', '.') as lt2_txt,
  replace(format('{:,}', cast(n_lt3 as bigint)), ',', '.') as lt3_txt,
  replace(format('{:,}', cast(n_lt5 as bigint)), ',', '.') as lt5_txt
from bds_real.afford
```

```sql hcm1
select * from ${aff} where city = 'Hồ Chí Minh' and bedrooms = 1
```

```sql hn1
select * from ${aff} where city = 'Hà Nội' and bedrooms = 1
```

```sql hcm2
select * from ${aff} where city = 'Hồ Chí Minh' and bedrooms = 2
```

```sql hn2
select * from ${aff} where city = 'Hà Nội' and bedrooms = 2
```

```sql hcm3
select * from ${aff} where city = 'Hồ Chí Minh' and bedrooms = 3
```

```sql hn3
select * from ${aff} where city = 'Hà Nội' and bedrooms = 3
```

# 1 phòng ngủ

> Khách hàng điển hình:
> - Người độc thân, hoặc vợ chồng chưa/không có con
> - Ngân sách: 2 tỷ

- Tháng 9/2025: *"HCM: khả năng tìm được căn 1PN dưới 2 tỷ là 10/72 ≈ 14% (tổng 72 bài đăng 1PN)."*
- Tháng 7/2026: *"HCM: 198/3.358 ≈ 5.9%"*, *"HN: 39/1122 ≈ 3.5%"*.
- Tháng 10/2026, tỷ lệ 1 ngủ dưới 2 tỷ:
    - HCM: {hcm1[0].lt2_txt}/{hcm1[0].n_txt} ≈ <b>{hcm1[0].p2}%</b>.
    - HN: {hn1[0].lt2_txt}/{hn1[0].n_txt} ≈ <b>{hn1[0].p2}%</b>.
    - Cao hơn tháng 7 ở cả hai thành phố. Vì mẫu tháng 10 khác tháng 7 (xem ghi chú ở phần Khai báo kĩ thuật), mình chưa dám nói cửa giá mềm đang mở lại.

## Phân bổ

```sql sup1
with d as (
  select city, district, n, n_lt2 as cheap from bds_real.district_supply where bedrooms = 1
),
tot as (select city, sum(n) as n, sum(cheap) as cheap from d group by city),
s as (
  select d.city, d.district, d.n, d.cheap,
    row_number() over (partition by d.city order by d.n desc) as rs,
    row_number() over (partition by d.city order by d.cheap desc) as rc
  from d
),
agg as (
  select s.city,
    string_agg(case when rs <= 3 then s.district || ' (' || cast(round(100.0 * s.n / tot.n, 1) as varchar) || '%)' end, ', ' order by rs) as top_sup,
    printf('%.1f', 100.0 * sum(case when rs <= 3 then s.n end) / max(tot.n)) as top_sup_pct,
    string_agg(case when rc <= 3 then s.district || ' (' || cast(round(100.0 * s.cheap / tot.cheap, 1) as varchar) || '%)' end, ', ' order by rc) as top_cheap,
    printf('%.1f', 100.0 * sum(case when rc <= 3 then s.cheap end) / max(tot.cheap)) as top_cheap_pct
  from s join tot using (city)
  group by s.city
)
select
  max(case when city = 'Hồ Chí Minh' then top_sup end) as hcm_sup,
  max(case when city = 'Hồ Chí Minh' then top_sup_pct end) as hcm_sup_pct,
  max(case when city = 'Hồ Chí Minh' then top_cheap end) as hcm_cheap,
  max(case when city = 'Hồ Chí Minh' then top_cheap_pct end) as hcm_cheap_pct,
  max(case when city = 'Hà Nội' then top_sup end) as hn_sup,
  max(case when city = 'Hà Nội' then top_sup_pct end) as hn_sup_pct,
  max(case when city = 'Hà Nội' then top_cheap end) as hn_cheap,
  max(case when city = 'Hà Nội' then top_cheap_pct end) as hn_cheap_pct
from agg
```

- HCM: nguồn cung 1PN tập trung ở {sup1[0].hcm_sup} (3 quận này gộp <b>{sup1[0].hcm_sup_pct}%</b>). Cửa dưới 2 tỷ dồn về {sup1[0].hcm_cheap} (gộp <b>{sup1[0].hcm_cheap_pct}%</b> số tin rẻ).
- HN: nguồn cung 1PN tập trung ở {sup1[0].hn_sup} (gộp <b>{sup1[0].hn_sup_pct}%</b>). Cửa dưới 2 tỷ dồn về {sup1[0].hn_cheap} (gộp <b>{sup1[0].hn_cheap_pct}%</b>).

<Dropdown name=city1 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist1
with d as (
  select district, n, n_lt2 as cheap
  from bds_real.district_supply
  where city = '${inputs.city1.value}' and bedrooms = 1
),
t as (select sum(n) as tn, sum(cheap) as tc from d),
r as (
  select district, n, cheap,
    row_number() over (order by n desc) as rs,
    row_number() over (order by cheap desc) as rc
  from d
)
select district, rs as rk, 'Tỷ trọng nguồn cung 1PN' as kind, round(100.0 * n / tn, 1) as pct from r, t where rs <= 6 or rc <= 6
union all
select district, rs as rk, 'Tỷ trọng tin dưới 2 tỷ', round(100.0 * cheap / tc, 1) from r, t where rs <= 6 or rc <= 6
order by rk
```

<BarChart
    data={dist1}
    x=district
    y=pct
    series=kind
    type=grouped
    sort=false
    swapXY=true
    yFmt="0.0"
    title="Quận nào nhiều tin 1PN, quận nào nhiều tin 1PN dưới 2 tỷ ({inputs.city1.label})"
/>

# 2 phòng ngủ

> Khách hàng điển hình:
> - Gia đình nhỏ, vợ chồng và 1–2 con
> - Ngân sách: 2–3 tỷ

## Tỷ lệ kiếm được nhà

- Tháng 9/2025: *"dưới 2 tỷ là 5.3%, dưới 3 tỷ là 30%."*
- Tháng 7/2026: *"HCM: dưới 2 tỷ ≈ 3.0% (435/14.622), dưới 3 tỷ ≈ 16.8% (2.460/14.622)"*; *"HN: dưới 2 tỷ ≈ 0.2% (16/7475), dưới 3 tỷ ≈ 3% (225/7475)."*
- Tháng 10/2026:
    - HCM: dưới 2 tỷ {hcm2[0].lt2_txt}/{hcm2[0].n_txt} ≈ <b>{hcm2[0].p2}%</b>, dưới 3 tỷ {hcm2[0].lt3_txt}/{hcm2[0].n_txt} ≈ <b>{hcm2[0].p3}%</b>.
    - HN: dưới 2 tỷ {hn2[0].lt2_txt}/{hn2[0].n_txt} ≈ <b>{hn2[0].p2}%</b>, dưới 3 tỷ {hn2[0].lt3_txt}/{hn2[0].n_txt} ≈ <b>{hn2[0].p3}%</b>.
    - HN vẫn thấp hơn HCM rõ rệt ở mốc dưới 3 tỷ, dù cao hơn con số tháng 7. Cùng lưu ý về mẫu thu thập.

## Phân bổ

```sql sup2
with d as (
  select city, district, n, n_lt3 as cheap from bds_real.district_supply where bedrooms = 2
),
tot as (select city, sum(n) as n, sum(cheap) as cheap from d group by city),
s as (
  select d.city, d.district, d.n, d.cheap,
    row_number() over (partition by d.city order by d.n desc) as rs,
    row_number() over (partition by d.city order by d.cheap desc) as rc
  from d
),
agg as (
  select s.city,
    string_agg(case when rs <= 3 then s.district || ' (' || cast(round(100.0 * s.n / tot.n, 1) as varchar) || '%)' end, ', ' order by rs) as top_sup,
    printf('%.1f', 100.0 * sum(case when rs <= 3 then s.n end) / max(tot.n)) as top_sup_pct,
    string_agg(case when rc <= 3 then s.district || ' (' || cast(round(100.0 * s.cheap / tot.cheap, 1) as varchar) || '%)' end, ', ' order by rc) as top_cheap,
    printf('%.1f', 100.0 * sum(case when rc <= 3 then s.cheap end) / max(tot.cheap)) as top_cheap_pct
  from s join tot using (city)
  group by s.city
)
select
  max(case when city = 'Hồ Chí Minh' then top_sup end) as hcm_sup,
  max(case when city = 'Hồ Chí Minh' then top_sup_pct end) as hcm_sup_pct,
  max(case when city = 'Hồ Chí Minh' then top_cheap end) as hcm_cheap,
  max(case when city = 'Hồ Chí Minh' then top_cheap_pct end) as hcm_cheap_pct,
  max(case when city = 'Hà Nội' then top_sup end) as hn_sup,
  max(case when city = 'Hà Nội' then top_sup_pct end) as hn_sup_pct,
  max(case when city = 'Hà Nội' then top_cheap end) as hn_cheap,
  max(case when city = 'Hà Nội' then top_cheap_pct end) as hn_cheap_pct
from agg
```

- HCM: nguồn cung 2PN tập trung ở {sup2[0].hcm_sup} (gộp <b>{sup2[0].hcm_sup_pct}%</b>). Cửa dưới 3 tỷ dồn về {sup2[0].hcm_cheap} (gộp <b>{sup2[0].hcm_cheap_pct}%</b> số tin rẻ).
- HN: nguồn cung 2PN tập trung ở {sup2[0].hn_sup} (gộp <b>{sup2[0].hn_sup_pct}%</b>). Cửa dưới 3 tỷ dồn về {sup2[0].hn_cheap} (gộp <b>{sup2[0].hn_cheap_pct}%</b>).

> Quận có nhiều 2PN nhất chưa chắc là quận có 2PN rẻ nhất: so hai dòng trên với nhau, danh sách quận nhiều tin và danh sách quận nhiều tin rẻ khác nhau.

<Dropdown name=city2 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist2
with d as (
  select district, n, n_lt3 as cheap
  from bds_real.district_supply
  where city = '${inputs.city2.value}' and bedrooms = 2
),
t as (select sum(n) as tn, sum(cheap) as tc from d),
r as (
  select district, n, cheap,
    row_number() over (order by n desc) as rs,
    row_number() over (order by cheap desc) as rc
  from d
)
select district, rs as rk, 'Tỷ trọng nguồn cung 2PN' as kind, round(100.0 * n / tn, 1) as pct from r, t where rs <= 6 or rc <= 6
union all
select district, rs as rk, 'Tỷ trọng tin dưới 3 tỷ', round(100.0 * cheap / tc, 1) from r, t where rs <= 6 or rc <= 6
order by rk
```

<BarChart
    data={dist2}
    x=district
    y=pct
    series=kind
    type=grouped
    sort=false
    swapXY=true
    yFmt="0.0"
    title="Quận nào nhiều tin 2PN, quận nào nhiều tin 2PN dưới 3 tỷ ({inputs.city2.label})"
/>

# 3 phòng ngủ

> Khách hàng điển hình:
> - Gia đình 3 thế hệ cùng sinh sống
> - Ngân sách: 3–5 tỷ

- Tháng 9/2025: *"3 ngủ dưới 5 tỷ 29/134 ≈ 22% số căn 3PN."*
- Tháng 7/2026: *"HCM: 1260/6545 ≈ 19,2%."*; *"HN: 292/5822 ≈ 5%. Tệ hơn HCM rất nhiều."*
- Tháng 10/2026, tỷ lệ 3 ngủ dưới 5 tỷ:
    - HCM: {hcm3[0].lt5_txt}/{hcm3[0].n_txt} ≈ <b>{hcm3[0].p5}%</b>.
    - HN: {hn3[0].lt5_txt}/{hn3[0].n_txt} ≈ <b>{hn3[0].p5}%</b>.

## Phân bổ

```sql sup3
with d as (
  select city, district, n, n_lt5 as cheap from bds_real.district_supply where bedrooms = 3
),
tot as (select city, sum(n) as n, sum(cheap) as cheap from d group by city),
s as (
  select d.city, d.district, d.n, d.cheap,
    row_number() over (partition by d.city order by d.n desc) as rs,
    row_number() over (partition by d.city order by d.cheap desc) as rc
  from d
),
agg as (
  select s.city,
    string_agg(case when rs <= 3 then s.district || ' (' || cast(round(100.0 * s.n / tot.n, 1) as varchar) || '%)' end, ', ' order by rs) as top_sup,
    printf('%.1f', 100.0 * sum(case when rs <= 3 then s.n end) / max(tot.n)) as top_sup_pct,
    string_agg(case when rc <= 3 then s.district || ' (' || cast(round(100.0 * s.cheap / tot.cheap, 1) as varchar) || '%)' end, ', ' order by rc) as top_cheap,
    printf('%.1f', 100.0 * sum(case when rc <= 3 then s.cheap end) / max(tot.cheap)) as top_cheap_pct
  from s join tot using (city)
  group by s.city
)
select
  max(case when city = 'Hồ Chí Minh' then top_sup end) as hcm_sup,
  max(case when city = 'Hồ Chí Minh' then top_sup_pct end) as hcm_sup_pct,
  max(case when city = 'Hồ Chí Minh' then top_cheap end) as hcm_cheap,
  max(case when city = 'Hồ Chí Minh' then top_cheap_pct end) as hcm_cheap_pct,
  max(case when city = 'Hà Nội' then top_sup end) as hn_sup,
  max(case when city = 'Hà Nội' then top_sup_pct end) as hn_sup_pct,
  max(case when city = 'Hà Nội' then top_cheap end) as hn_cheap,
  max(case when city = 'Hà Nội' then top_cheap_pct end) as hn_cheap_pct
from agg
```

- HCM: nguồn cung 3PN tập trung ở {sup3[0].hcm_sup} (gộp <b>{sup3[0].hcm_sup_pct}%</b>). Cửa dưới 5 tỷ dồn về {sup3[0].hcm_cheap} (gộp <b>{sup3[0].hcm_cheap_pct}%</b> số tin rẻ).
- HN: nguồn cung 3PN tập trung ở {sup3[0].hn_sup} (gộp <b>{sup3[0].hn_sup_pct}%</b>). Cửa dưới 5 tỷ dồn về {sup3[0].hn_cheap} (gộp <b>{sup3[0].hn_cheap_pct}%</b>).

<Dropdown name=city3 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist3
with d as (
  select district, n, n_lt5 as cheap
  from bds_real.district_supply
  where city = '${inputs.city3.value}' and bedrooms = 3
),
t as (select sum(n) as tn, sum(cheap) as tc from d),
r as (
  select district, n, cheap,
    row_number() over (order by n desc) as rs,
    row_number() over (order by cheap desc) as rc
  from d
)
select district, rs as rk, 'Tỷ trọng nguồn cung 3PN' as kind, round(100.0 * n / tn, 1) as pct from r, t where rs <= 6 or rc <= 6
union all
select district, rs as rk, 'Tỷ trọng tin dưới 5 tỷ', round(100.0 * cheap / tc, 1) from r, t where rs <= 6 or rc <= 6
order by rk
```

<BarChart
    data={dist3}
    x=district
    y=pct
    series=kind
    type=grouped
    sort=false
    swapXY=true
    yFmt="0.0"
    title="Quận nào nhiều tin 3PN, quận nào nhiều tin 3PN dưới 5 tỷ ({inputs.city3.label})"
/>

# Hướng dẫn sử dụng trang này

1. Ở mỗi mục **Phân bổ** có ô chọn **Thành phố**: đổi giữa HCM và HN để biểu đồ bên dưới cập nhật theo.
2. Rê chuột vào cột để đọc số chính xác.
3. Muốn lọc theo khoảng giá hay xem theo dự án (phần này trang web chưa có), dùng [dashboard Looker Studio](https://lookerstudio.google.com/reporting/9e21618f-97dc-4480-b101-cbda26b9b2a5): chọn khoảng giá ở bộ lọc phía trên, rồi click vào quận hoặc dự án để lọc tiếp.

# Kết

Ở cả hai thành phố, cửa giá mềm nằm ngoài trung tâm, còn các quận trung tâm vẫn giữ giá cao nhất. Ở mốc dưới 3 tỷ, HCM vẫn rộng cửa hơn HN: {kpi2[0].hcm_lt3_p}% so với {kpi2[0].hn_lt3_p}% số tin. Còn câu hỏi "giá có đang đắt lên so với tháng 7" thì dữ liệu lần này chưa đủ sạch để trả lời, mình sẽ cố lấy mẫu cùng điều kiện cho lần sau.

Lại câu hỏi từ bài viết trước: anh em gom được mấy mét đất thành phố rồi nào?

> P/S: Trang web này còn đang thử nghiệm. Anh em thấy số nào sai sai cứ réo mình =)))

---

**Nguồn:** batdongsan.com.vn, tin rao bán căn hộ chung cư có giá ở HCM & HN, thu thập {meta[0].d0} đến {meta[0].d1}. **Hạn chế:** đây là giá rao, không phải giá giao dịch; tin rao có thể trùng hoặc không còn hiệu lực; địa giới theo trước sáp nhập.
