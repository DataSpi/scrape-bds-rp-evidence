---
title: Giá mua chung cư
---

```sql per
select
  p.period, p.label,
  strftime(cast(m.d0 as date), '%d/%m') as d0,
  strftime(cast(m.d1 as date), '%d/%m/%Y') as d1,
  case when m.d0 = m.d1 then 'ngày ' || strftime(cast(m.d1 as date), '%d/%m/%Y')
    else strftime(cast(m.d0 as date), '%d/%m') || ' đến ' || strftime(cast(m.d1 as date), '%d/%m/%Y') end as win,
  replace(format('{:,}', cast(m.n_priced as bigint)), ',', '.') as n_txt
from bds_real.periods p
join bds_real.cc_meta m using (period)
where p.period = '${params.period}'
```

```sql prev
select p.period, p.label
from bds_real.periods p
join bds_real.cc_meta m using (period)
where p.period < '${params.period}'
order by p.period desc
limit 1
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
from bds_real.cc_city_kpi
where period = '${params.period}'
```

```sql kpi2
select
  replace(format('{:,}', cast(hcm_n as bigint)), ',', '.') as hcm_n_txt,
  replace(format('{:,}', cast(hn_n as bigint)), ',', '.') as hn_n_txt,
  printf('%.2f', hcm_ty) as hcm_ty_t,
  printf('%.2f', hn_ty) as hn_ty_t,
  printf('%.1f', hcm_m2) as hcm_m2_t,
  printf('%.1f', hn_m2) as hn_m2_t,
  case when hn_m2 >= hcm_m2 then 'HN cao hơn' else 'HN thấp hơn' end as m2_dir,
  printf('%.1f', abs(100.0 * (hn_m2 / hcm_m2 - 1))) as gap_m2_t,
  case when hn_ty >= hcm_ty then 'HN cao hơn' else 'HN thấp hơn' end as ty_dir,
  printf('%.1f', abs(100.0 * (hn_ty / hcm_ty - 1))) as gap_ty_t,
  replace(format('{:,}', cast(hcm_lt3 as bigint)), ',', '.') as hcm_lt3_txt,
  replace(format('{:,}', cast(hn_lt3 as bigint)), ',', '.') as hn_lt3_txt,
  printf('%.1f', 100.0 * hcm_lt3 / hcm_n) as hcm_lt3_p,
  printf('%.1f', 100.0 * hn_lt3 / hn_n) as hn_lt3_p,
  printf('%.1f', (hcm_lt3 * 1.0 / hcm_n) / (hn_lt3 * 1.0 / hn_n)) as lt3_ratio_t
from ${kpi}
```

{#if per.length === 0}

Không có kỳ báo cáo <b>{params.period}</b> cho mảng này. <a href="/mua/chung-cu" class="text-primary hover:underline">Xem danh sách các kỳ</a>.

{:else}

Kỳ <b>{per[0].label}</b>: đợt scrape {per[0].win}, <b>{per[0].n_txt}</b> tin chung cư rao bán có giá ở HCM & HN. <a href="/mua/chung-cu" class="text-primary hover:underline">Các kỳ khác</a>.

# Khai báo kĩ thuật

- Nguồn dữ liệu: [https://batdongsan.com.vn/](https://batdongsan.com.vn/)
    - Chỉ lấy tin **căn hộ chung cư rao bán** ở HCM & HN, có giá, chưa hết hạn, thu thập {per[0].win}. Gồm cả tin chưa xác thực.
- Mỗi kỳ là ảnh chụp toàn bộ tin thấy được trong đợt scrape của kỳ đó, dựng lại từ dữ liệu thô. Một tin còn treo qua nhiều kỳ được tính ở mỗi kỳ, với giá của kỳ đó.
- Kỹ thuật:
    - Tool cào Python: HTTP Request, BeautifulSoup; xử lý bằng dbt + BigQuery
    - Github: [scrape-batdongsan-data](https://github.com/DataSpi/scrape-batdongsan-data) (pipeline) và [scrape-bds-rp-evidence](https://github.com/DataSpi/scrape-bds-rp-evidence) (trang này)
- Note: vẫn dùng địa giới hành chính cũ trước sáp nhập.

{#if prev.length > 0}

```sql cmp_kpi
with c as (select * from bds_real.cc_city_kpi where period = '${params.period}'),
p as (select * from bds_real.cc_city_kpi where period = (select period from ${prev}))
select c.city,
  printf('%+.0f%%', 100.0 * (c.n * 1.0 / p.n - 1)) as n_chg,
  printf('%+.1f%%', 100.0 * (c.avg_price_1m2 / p.avg_price_1m2 - 1)) as m2_chg
from c join p using (city)
```

```sql cmp_long
with c as (select * from bds_real.cc_city_kpi where period = '${params.period}'),
p as (select * from bds_real.cc_city_kpi where period = (select period from ${prev}))
select c.city, 1 as k, 'Số tin có giá' as metric,
  replace(format('{:,}', cast(p.n as bigint)), ',', '.') as v_p,
  replace(format('{:,}', cast(c.n as bigint)), ',', '.') as v_c,
  printf('%+.0f%%', 100.0 * (c.n * 1.0 / p.n - 1)) as chg
from c join p using (city)
union all
select c.city, 2, 'Số quận có tin', cast(cast(p.n_district as int) as varchar), cast(cast(c.n_district as int) as varchar), ''
from c join p using (city)
union all
select c.city, 3, 'Giá TB (tỷ)', printf('%.2f', p.avg_price_ty), printf('%.2f', c.avg_price_ty),
  printf('%+.1f%%', 100.0 * (c.avg_price_ty / p.avg_price_ty - 1))
from c join p using (city)
union all
select c.city, 4, 'Giá/m² TB (tr)', printf('%.1f', p.avg_price_1m2), printf('%.1f', c.avg_price_1m2),
  printf('%+.1f%%', 100.0 * (c.avg_price_1m2 / p.avg_price_1m2 - 1))
from c join p using (city)
union all
select c.city, 5, '% tin dưới 3 tỷ', printf('%.1f%%', 100.0 * p.n_lt3 / p.n), printf('%.1f%%', 100.0 * c.n_lt3 / c.n),
  printf('%+.1f điểm', 100.0 * c.n_lt3 / c.n - 100.0 * p.n_lt3 / p.n)
from c join p using (city)
order by city desc, k
```

```sql cmp_head
select
  max(case when city = 'Hồ Chí Minh' then m2_chg end) as hcm_m2_chg,
  max(case when city = 'Hà Nội' then m2_chg end) as hn_m2_chg,
  max(case when city = 'Hồ Chí Minh' then n_chg end) as hcm_n_chg,
  max(case when city = 'Hà Nội' then n_chg end) as hn_n_chg
from ${cmp_kpi}
```

```sql cmp_aff
with c as (select * from bds_real.cc_afford where period = '${params.period}'),
p as (select * from bds_real.cc_afford where period = (select period from ${prev})),
j as (
  select c.city, c.bedrooms,
    case cast(cast(c.bedrooms as int) as varchar) when '1' then 'dưới 2 tỷ' when '2' then 'dưới 3 tỷ' else 'dưới 5 tỷ' end as budget,
    case cast(cast(c.bedrooms as int) as varchar) when '1' then p.n_lt2 when '2' then p.n_lt3 else p.n_lt5 end * 100.0 / p.n as pp,
    case cast(cast(c.bedrooms as int) as varchar) when '1' then c.n_lt2 when '2' then c.n_lt3 else c.n_lt5 end * 100.0 / c.n as pc
  from c join p using (city, bedrooms)
)
select city, cast(cast(bedrooms as int) as varchar) || 'PN ' || budget as seg,
  printf('%.1f%% → %.1f%%', pp, pc) as pc_txt, printf('%+.1f điểm', pc - pp) as chg
from j
order by city desc, bedrooms
```

```sql cmp_dist
with c as (select * from bds_real.cc_district_price where period = '${params.period}' and n >= 30),
p as (select * from bds_real.cc_district_price where period = (select period from ${prev}) and n >= 30)
select c.city, c.district,
  round(100.0 * (c.avg_price_1m2 / p.avg_price_1m2 - 1), 1) as chg,
  p.avg_price_1m2 as m2_p, c.avg_price_1m2 as m2_c, p.n as n_p, c.n as n_c
from c join p using (city, district)
order by chg desc
```

```sql cmp_dist_head
select city,
  count(*) as n_d,
  count(*) filter (where chg > 0) as n_up,
  count(*) filter (where chg < 0) as n_down
from ${cmp_dist}
group by city
```

```sql cmp_dist_hcm
select district, chg from ${cmp_dist} where city = 'Hồ Chí Minh' order by chg desc
```

```sql cmp_dist_hn
select district, chg from ${cmp_dist} where city = 'Hà Nội' order by chg desc
```

```sql cmp_dist_t
select
  max(case when city = 'Hồ Chí Minh' then n_down end) as hcm_down,
  max(case when city = 'Hồ Chí Minh' then n_d end) as hcm_d,
  max(case when city = 'Hà Nội' then n_down end) as hn_down,
  max(case when city = 'Hà Nội' then n_d end) as hn_d
from ${cmp_dist_head}
```

# So với {prev[0].label}

**Giá/m² trung bình: HCM {cmp_head[0].hcm_m2_chg}, HN {cmp_head[0].hn_m2_chg} so với {prev[0].label}.**

Hai kỳ cùng cào theo danh sách quận như nhau, nhưng số tin mỗi kỳ không bằng nhau (HCM {cmp_head[0].hcm_n_chg}, HN {cmp_head[0].hn_n_chg} số tin). Số tin chênh nhiều thì chênh lệch giá có thể đến từ việc mẫu đổi chứ không hẳn giá đổi, nên đọc kèm dòng số tin.

<DataTable data={cmp_long} rows=all groupBy=city>
    <Column id=metric title="Chỉ số" />
    <Column id=v_p title={prev[0].label} align=right />
    <Column id=v_c title={per[0].label} align=right />
    <Column id=chg title="Thay đổi" align=right />
</DataTable>

**Tỷ lệ tin vừa ngân sách theo phân khúc phòng ngủ** (ngân sách giả định xem mục Phương pháp phân tích):

<DataTable data={cmp_aff} rows=all>
    <Column id=city title="TP" />
    <Column id=seg title="Phân khúc" />
    <Column id=pc_txt title="% vừa ngân sách" align=right />
    <Column id=chg title="Thay đổi" align=right />
</DataTable>

**Theo quận: giá/m² giảm ở {cmp_dist_t[0].hcm_down}/{cmp_dist_t[0].hcm_d} quận HCM và {cmp_dist_t[0].hn_down}/{cmp_dist_t[0].hn_d} quận HN** (chỉ tính quận có từ 30 tin trở lên ở cả hai kỳ).

<BarChart
    data={cmp_dist_hcm}
    x=district
    y=chg
    swapXY=true
    sort=false
    labels=true
    yFmt="0.0"
    yAxisTitle="% thay đổi giá/m² TB"
    title="HCM: thay đổi giá/m² TB theo quận (%)"
/>

<BarChart
    data={cmp_dist_hn}
    x=district
    y=chg
    swapXY=true
    sort=false
    labels=true
    yFmt="0.0"
    yAxisTitle="% thay đổi giá/m² TB"
    title="HN: thay đổi giá/m² TB theo quận (%)"
/>

{/if}

# Tổng quan

## Nguồn cung

```sql bracket
select city, bin_price, bin_price_order, n,
  round(100.0 * n / sum(n) over (partition by city), 1) as pct
from bds_real.cc_price_bracket
where period = '${params.period}'
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
from bds_real.cc_price_bracket
where period = '${params.period}'
```

**{bracket_head[0].hcm_pct}% tin ở HCM và {bracket_head[0].hn_pct}% tin ở HN nằm trong khoảng 3-10 tỷ.**

- HCM: {bracket_head[0].hcm_mid}/{bracket_head[0].hcm_tot} tin.
- HN: {bracket_head[0].hn_mid}/{bracket_head[0].hn_tot} tin.

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

```sql beds
select city,
  case when cast(bedrooms as varchar) = '4+' then '4PN+' else cast(bedrooms as varchar) || 'PN' end as label,
  n,
  round(100.0 * n / sum(n) over (partition by city), 1) as pct
from bds_real.cc_bedroom_mix
where period = '${params.period}'
order by bedrooms, city
```

```sql beds_head
select
  printf('%.1f', 100.0 * sum(case when city = 'Hồ Chí Minh' and cast(bedrooms as varchar) in ('2', '3') then n end) / sum(case when city = 'Hồ Chí Minh' then n end)) as hcm_pct,
  printf('%.1f', 100.0 * sum(case when city = 'Hà Nội' and cast(bedrooms as varchar) in ('2', '3') then n end) / sum(case when city = 'Hà Nội' then n end)) as hn_pct
from bds_real.cc_bedroom_mix
where period = '${params.period}'
```

**Căn 2PN & 3PN chiếm {beds_head[0].hcm_pct}% nguồn cung ở HCM và {beds_head[0].hn_pct}% ở HN** (tính trên số tin có ghi số phòng ngủ).

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

**Giá/m² TB: HCM {kpi2[0].hcm_m2_t}, HN {kpi2[0].hn_m2_t} tr/m², nhưng tin dưới 3 tỷ ở HCM nhiều gấp {kpi2[0].lt3_ratio_t} lần HN.**

- Giá/m² TB: HCM <b>{kpi2[0].hcm_m2_t}</b> tr/m², HN <b>{kpi2[0].hn_m2_t}</b> tr/m² ({kpi2[0].m2_dir} {kpi2[0].gap_m2_t}%). Giá TB: HCM {kpi2[0].hcm_ty_t} tỷ, HN {kpi2[0].hn_ty_t} tỷ ({kpi2[0].ty_dir} {kpi2[0].gap_ty_t}%).
- Tin dưới 3 tỷ: HCM {kpi2[0].hcm_lt3_txt}/{kpi2[0].hcm_n_txt} ≈ <b>{kpi2[0].hcm_lt3_p}%</b>, HN {kpi2[0].hn_lt3_txt}/{kpi2[0].hn_n_txt} ≈ <b>{kpi2[0].hn_lt3_p}%</b>.
- Nhìn riêng giá trung bình dễ đánh giá thấp khoảng cách giữa hai thị trường: tỷ lệ tin dưới 3 tỷ cho thấy rõ hơn ai còn đường vào.

## Phân hóa theo vị trí

Các quận trung tâm có giá/m² cao nhất, giảm dần ra vùng ven. Bảng xếp hạng chỉ tính quận có từ 30 tin trở lên.

```sql loc
select
  max(case when city = 'Hồ Chí Minh' and district = 'Quận 1' then avg_price_1m2 end) as q1,
  max(case when city = 'Hồ Chí Minh' and district = 'Quận 1' then n end) as q1_n,
  max(case when city = 'Hà Nội' and district = 'Hoàn Kiếm' then avg_price_1m2 end) as hk,
  max(case when city = 'Hà Nội' and district = 'Hoàn Kiếm' then n end) as hk_n
from bds_real.cc_district_price
where period = '${params.period}'
```

```sql loc2
select
  printf('%.1f', q1) as q1_t,
  cast(cast(q1_n as bigint) as varchar) as q1_n_t,
  printf('%.1f', hk) as hk_t,
  cast(cast(hk_n as bigint) as varchar) as hk_n_t,
  printf('%.2f', hk / q1) as hk_vs_q1_t
from ${loc}
```

```sql seven
select
  printf('%.1f', 100.0 * sum(case when district in ('Quận 9', 'Quận 2', 'Quận 7', 'Bình Thạnh', 'Tân Phú', 'Bình Tân', 'Bình Chánh') then n end) / sum(n)) as pct
from bds_real.cc_district_count
where city = 'Hồ Chí Minh' and period = '${params.period}'
```

### Hồ Chí Minh

- 7 quận Q9, Q2, Q7, Bình Thạnh, Tân Phú, Bình Tân, Bình Chánh chiếm <b>{seven[0].pct}%</b> số tin (bài tháng 9/2025 là hơn 80%).
- Quận 1: <b>{loc2[0].q1_t} tr/m²</b> ({loc2[0].q1_n_t} tin).

```sql top_hcm
select district, avg_price_1m2 as price, n
from bds_real.cc_district_price
where city = 'Hồ Chí Minh' and n >= 30 and period = '${params.period}'
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

- Hoàn Kiếm: <b>{loc2[0].hk_t} tr/m²</b>, gấp {loc2[0].hk_vs_q1_t} lần Quận 1 HCM. Hoàn Kiếm chỉ có {loc2[0].hk_n_t} tin, mẫu nhỏ.

```sql top_hn
select district, avg_price_1m2 as price, n
from bds_real.cc_district_price
where city = 'Hà Nội' and n >= 30 and period = '${params.period}'
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

Mình tạm chia người mua chung cư thành 3 nhóm với nhu cầu và túi tiền như sau:

1. Người độc thân, hoặc vợ chồng chưa/không có con → thường tìm căn 1PN.
    - Ngân sách giả định: dưới 2 tỷ.
2. Gia đình nhỏ, vợ chồng và 1–2 con → thường tìm căn 2PN.
    - Ngân sách giả định: 2–3 tỷ.
3. Gia đình 3 thế hệ cùng sinh sống → thường tìm căn 3PN.
    - Ngân sách giả định: 3–5 tỷ.

Các mốc ngân sách trên là ước lượng dựa trên kinh nghiệm cá nhân của mình, không phải khảo sát hay nghiên cứu. Mục đích là trả lời câu hỏi của nhóm người mua điển hình: với từng túi tiền và nhu cầu, tôi có những lựa chọn nào?

```sql aff
select city, bedrooms, n, n_lt2, n_lt3, n_lt5,
  printf('%.1f', 100.0 * n_lt2 / n) as p2,
  printf('%.1f', 100.0 * n_lt3 / n) as p3,
  printf('%.1f', 100.0 * n_lt5 / n) as p5,
  replace(format('{:,}', cast(n as bigint)), ',', '.') as n_txt,
  replace(format('{:,}', cast(n_lt2 as bigint)), ',', '.') as lt2_txt,
  replace(format('{:,}', cast(n_lt3 as bigint)), ',', '.') as lt3_txt,
  replace(format('{:,}', cast(n_lt5 as bigint)), ',', '.') as lt5_txt
from bds_real.cc_afford
where period = '${params.period}'
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

```sql sup
with d as (
  select city, bedrooms, district, n,
    case bedrooms when 1 then n_lt2 when 2 then n_lt3 else n_lt5 end as cheap
  from bds_real.cc_district_supply
  where period = '${params.period}'
),
tot as (select city, bedrooms, sum(n) as n, sum(cheap) as cheap from d group by 1, 2),
s as (
  select d.*,
    row_number() over (partition by d.city, d.bedrooms order by d.n desc) as rs,
    row_number() over (partition by d.city, d.bedrooms order by d.cheap desc) as rc
  from d
)
select s.city, s.bedrooms,
  string_agg(case when rs <= 3 then s.district || ' (' || cast(round(100.0 * s.n / tot.n, 1) as varchar) || '%)' end, ', ' order by rs) as top_sup,
  printf('%.1f', 100.0 * sum(case when rs <= 3 then s.n end) / max(tot.n)) as top_sup_pct,
  string_agg(case when rc <= 3 and s.cheap > 0 then s.district || ' (' || cast(round(100.0 * s.cheap / tot.cheap, 1) as varchar) || '%)' end, ', ' order by rc) as top_cheap,
  printf('%.1f', 100.0 * sum(case when rc <= 3 then s.cheap end) / nullif(max(tot.cheap), 0)) as top_cheap_pct
from s join tot using (city, bedrooms)
group by 1, 2
order by s.city desc, s.bedrooms
```

```sql sup1
select * from ${sup} where bedrooms = 1
```

```sql sup2
select * from ${sup} where bedrooms = 2
```

```sql sup3
select * from ${sup} where bedrooms = 3
```

# 1 phòng ngủ

> Khách hàng điển hình:
> - Người độc thân, hoặc vợ chồng chưa/không có con
> - Ngân sách: 2 tỷ

**Căn 1PN dưới 2 tỷ: HCM {hcm1[0].p2}%, HN {hn1[0].p2}% số tin 1PN.**

- HCM: {hcm1[0].lt2_txt}/{hcm1[0].n_txt} ≈ <b>{hcm1[0].p2}%</b>.
- HN: {hn1[0].lt2_txt}/{hn1[0].n_txt} ≈ <b>{hn1[0].p2}%</b>.
- Bài tháng 9/2025 (mẫu nhỏ, chỉ HCM): *"10/72 ≈ 14%"*.

## Phân bổ

{#each sup1 as s}

- {s.city}: nguồn cung 1PN tập trung ở {s.top_sup} (3 quận gộp <b>{s.top_sup_pct}%</b>). Tin dưới 2 tỷ dồn về {s.top_cheap} (gộp <b>{s.top_cheap_pct}%</b> số tin rẻ).

{/each}

<Dropdown name=city1 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist1
with d as (
  select district, n, n_lt2 as cheap
  from bds_real.cc_district_supply
  where city = '${inputs.city1.value}' and bedrooms = 1 and period = '${params.period}'
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

**Căn 2PN dưới 3 tỷ: HCM {hcm2[0].p3}%, HN {hn2[0].p3}% số tin 2PN.**

- HCM: dưới 2 tỷ {hcm2[0].lt2_txt}/{hcm2[0].n_txt} ≈ <b>{hcm2[0].p2}%</b>, dưới 3 tỷ {hcm2[0].lt3_txt}/{hcm2[0].n_txt} ≈ <b>{hcm2[0].p3}%</b>.
- HN: dưới 2 tỷ {hn2[0].lt2_txt}/{hn2[0].n_txt} ≈ <b>{hn2[0].p2}%</b>, dưới 3 tỷ {hn2[0].lt3_txt}/{hn2[0].n_txt} ≈ <b>{hn2[0].p3}%</b>.
- Bài tháng 9/2025: *"dưới 2 tỷ là 5.3%, dưới 3 tỷ là 30%."*

## Phân bổ

{#each sup2 as s}

- {s.city}: nguồn cung 2PN tập trung ở {s.top_sup} (gộp <b>{s.top_sup_pct}%</b>). Tin dưới 3 tỷ dồn về {s.top_cheap} (gộp <b>{s.top_cheap_pct}%</b> số tin rẻ).

{/each}

> Quận có nhiều 2PN nhất chưa chắc là quận có 2PN rẻ nhất: so hai danh sách trên với nhau.

<Dropdown name=city2 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist2
with d as (
  select district, n, n_lt3 as cheap
  from bds_real.cc_district_supply
  where city = '${inputs.city2.value}' and bedrooms = 2 and period = '${params.period}'
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

**Căn 3PN dưới 5 tỷ: HCM {hcm3[0].p5}%, HN {hn3[0].p5}% số tin 3PN.**

- HCM: {hcm3[0].lt5_txt}/{hcm3[0].n_txt} ≈ <b>{hcm3[0].p5}%</b>.
- HN: {hn3[0].lt5_txt}/{hn3[0].n_txt} ≈ <b>{hn3[0].p5}%</b>.
- Bài tháng 9/2025: *"3 ngủ dưới 5 tỷ 29/134 ≈ 22% số căn 3PN."*

## Phân bổ

{#each sup3 as s}

- {s.city}: nguồn cung 3PN tập trung ở {s.top_sup} (gộp <b>{s.top_sup_pct}%</b>). Tin dưới 5 tỷ dồn về {s.top_cheap} (gộp <b>{s.top_cheap_pct}%</b> số tin rẻ).

{/each}

<Dropdown name=city3 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist3
with d as (
  select district, n, n_lt5 as cheap
  from bds_real.cc_district_supply
  where city = '${inputs.city3.value}' and bedrooms = 3 and period = '${params.period}'
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

1. Ở mỗi mục **Phân bổ** có ô chọn **Thành phố**: đổi giữa HCM và HN để biểu đồ cập nhật theo.
2. Rê chuột vào cột để đọc số chính xác.
3. Muốn lọc theo khoảng giá hay xem theo dự án, dùng [dashboard Looker Studio](https://lookerstudio.google.com/reporting/9e21618f-97dc-4480-b101-cbda26b9b2a5).

---

**Nguồn:** batdongsan.com.vn, tin rao bán căn hộ chung cư có giá ở HCM & HN, thu thập {per[0].win}. **Hạn chế:** đây là giá rao, không phải giá giao dịch; tin rao có thể trùng hoặc không còn hiệu lực; địa giới theo trước sáp nhập.

{/if}
