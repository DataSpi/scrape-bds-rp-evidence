---
title: Giá thuê chung cư
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
join bds_real.rent_meta m using (period)
where p.period = '${params.period}'
```

```sql prev
select p.period, p.label
from bds_real.periods p
join bds_real.rent_meta m using (period)
where p.period < '${params.period}'
order by p.period desc
limit 1
```

```sql city
-- P/R ratio = giá bán/m² ÷ (giá thuê/m²/tháng × 12), tính bằng năm; giá bán lấy từ chung cư bán cùng kỳ.
select r.city, r.n, r.avg_rent, r.avg_rent_m2, s.avg_price_1m2 as sale_m2,
  s.avg_price_1m2 / (r.avg_rent_m2 * 12) as pr
from bds_real.rent_city_kpi r
left join bds_real.cc_city_kpi s on s.city = r.city and s.period = r.period
where r.period = '${params.period}'
```

```sql city_tbl
select city,
  replace(format('{:,}', cast(n as bigint)), ',', '.') as n_txt,
  printf('%.2f', avg_rent) as rent_t,
  printf('%.3f', avg_rent_m2) as rent_m2_t,
  coalesce(printf('%.1f', sale_m2), '-') as sale_t,
  coalesce(printf('%.1f năm', pr), '-') as pr_t
from ${city}
order by city desc
```

```sql city_head
select
  printf('%.0f', abs(100.0 * (max(case when city = 'Hồ Chí Minh' then avg_rent_m2 end) / max(case when city = 'Hà Nội' then avg_rent_m2 end) - 1))) as gap_rent,
  case when max(case when city = 'Hồ Chí Minh' then avg_rent_m2 end) >= max(case when city = 'Hà Nội' then avg_rent_m2 end) then 'đắt hơn' else 'rẻ hơn' end as rent_dir,
  printf('%.1f', max(case when city = 'Hồ Chí Minh' then pr end)) as hcm_pr,
  printf('%.1f', max(case when city = 'Hà Nội' then pr end)) as hn_pr,
  count(pr) as n_pr
from ${city}
```

{#if per.length === 0}

Không có kỳ báo cáo <b>{params.period}</b> cho mảng này. <a href="/thue/chung-cu" class="text-primary hover:underline">Xem danh sách các kỳ</a>.

{:else}

Kỳ <b>{per[0].label}</b>: đợt scrape {per[0].win}, <b>{per[0].n_txt}</b> tin cho thuê căn hộ chung cư ở HCM & HN (sau lọc). <a href="/thue/chung-cu" class="text-primary hover:underline">Các kỳ khác</a>.

# Khai báo kĩ thuật

- Nguồn dữ liệu: [https://batdongsan.com.vn/](https://batdongsan.com.vn/), loại hình `cho thuê căn hộ chung cư`, thu thập {per[0].win}.
- Giá bán là trọn gói (tỷ), giá thuê là theo tháng (triệu/tháng), nên các bảng quy đổi cả hai về tr/m² (giá bán tr/m², giá thuê tr/m²/tháng) và tính thêm **P/R ratio** = giá bán/m² ÷ (giá thuê/m²/tháng × 12): số năm tiền thuê để bằng giá mua. Giá bán lấy từ tin chung cư rao bán cùng kỳ.
- Dữ liệu thuê chưa có bộ lọc outlier như dữ liệu bán. Trang này lọc thô diện tích 15-200 m² và giá thuê 1-200 tr/tháng trước khi tính, giống bài tháng 7/2026.
- Mỗi kỳ là ảnh chụp toàn bộ tin trong đợt scrape của kỳ đó, dựng lại từ dữ liệu thô. Địa giới hành chính cũ trước sáp nhập.

{#if prev.length > 0}

```sql cmp_city
with c as (select * from bds_real.rent_city_kpi where period = '${params.period}'),
p as (select * from bds_real.rent_city_kpi where period = (select period from ${prev}))
select c.city,
  printf('%+.0f%%', 100.0 * (c.n * 1.0 / p.n - 1)) as n_chg,
  printf('%+.1f%%', 100.0 * (c.avg_rent / p.avg_rent - 1)) as rent_chg
from c join p using (city)
```

```sql cmp_long
with c as (select * from bds_real.rent_city_kpi where period = '${params.period}'),
p as (select * from bds_real.rent_city_kpi where period = (select period from ${prev}))
select c.city, 1 as k, 'Số tin' as metric,
  replace(format('{:,}', cast(p.n as bigint)), ',', '.') as v_p,
  replace(format('{:,}', cast(c.n as bigint)), ',', '.') as v_c,
  printf('%+.0f%%', 100.0 * (c.n * 1.0 / p.n - 1)) as chg
from c join p using (city)
union all
select c.city, 2, 'Số quận có tin', cast(cast(p.n_district as int) as varchar), cast(cast(c.n_district as int) as varchar), ''
from c join p using (city)
union all
select c.city, 3, 'Thuê TB (tr/tháng)', printf('%.2f', p.avg_rent), printf('%.2f', c.avg_rent),
  printf('%+.1f%%', 100.0 * (c.avg_rent / p.avg_rent - 1))
from c join p using (city)
union all
select c.city, 4, 'Thuê TB (tr/m²/tháng)', printf('%.3f', p.avg_rent_m2), printf('%.3f', c.avg_rent_m2),
  printf('%+.1f%%', 100.0 * (c.avg_rent_m2 / p.avg_rent_m2 - 1))
from c join p using (city)
order by city desc, k
```

```sql cmp_head
select
  max(case when city = 'Hồ Chí Minh' then rent_chg end) as hcm_chg,
  max(case when city = 'Hà Nội' then rent_chg end) as hn_chg,
  max(case when city = 'Hồ Chí Minh' then n_chg end) as hcm_n_chg,
  max(case when city = 'Hà Nội' then n_chg end) as hn_n_chg
from ${cmp_city}
```

```sql cmp_bed
with c as (select * from bds_real.rent_bed where period = '${params.period}'),
p as (select * from bds_real.rent_bed where period = (select period from ${prev})),
j as (
  select c.city, c.bedrooms,
    case cast(cast(c.bedrooms as int) as varchar) when '1' then 'dưới 10 tr' when '2' then 'dưới 15 tr' else 'dưới 20 tr' end as budget,
    case cast(cast(c.bedrooms as int) as varchar) when '1' then p.n_lt10 when '2' then p.n_lt15 else p.n_lt20 end * 100.0 / p.n as pp,
    case cast(cast(c.bedrooms as int) as varchar) when '1' then c.n_lt10 when '2' then c.n_lt15 else c.n_lt20 end * 100.0 / c.n as pc,
    p.avg_rent as rp, c.avg_rent as rc
  from c join p using (city, bedrooms)
)
select city, cast(cast(bedrooms as int) as varchar) || 'PN ' || budget as seg,
  printf('%.2f → %.2f', rp, rc) as rent_txt,
  printf('%+.1f%%', 100.0 * (rc / rp - 1)) as rent_chg,
  printf('%.1f%% → %.1f%%', pp, pc) as pc_txt, printf('%+.1f điểm', pc - pp) as chg
from j
order by city desc, bedrooms
```

```sql cmp_dist
with c as (select * from bds_real.rent_district where period = '${params.period}' and n >= 30),
p as (select * from bds_real.rent_district where period = (select period from ${prev}) and n >= 30)
select c.city, c.district,
  round(100.0 * (c.avg_rent_m2 / p.avg_rent_m2 - 1), 1) as chg
from c join p using (city, district)
order by chg desc
```

```sql cmp_dist_t
select
  count(*) filter (where city = 'Hồ Chí Minh' and chg > 0) as hcm_up,
  count(*) filter (where city = 'Hồ Chí Minh') as hcm_d,
  count(*) filter (where city = 'Hà Nội' and chg > 0) as hn_up,
  count(*) filter (where city = 'Hà Nội') as hn_d
from ${cmp_dist}
```

```sql cmp_dist_hcm
select district, chg from ${cmp_dist} where city = 'Hồ Chí Minh' order by chg desc
```

```sql cmp_dist_hn
select district, chg from ${cmp_dist} where city = 'Hà Nội' order by chg desc
```

# So với {prev[0].label}

**Giá thuê TB: HCM {cmp_head[0].hcm_chg}, HN {cmp_head[0].hn_chg} so với {prev[0].label}.**

Hai kỳ cùng cào theo danh sách quận như nhau, nhưng số tin mỗi kỳ không bằng nhau (HCM {cmp_head[0].hcm_n_chg}, HN {cmp_head[0].hn_n_chg} số tin), nên đọc kèm dòng số tin.

<DataTable data={cmp_long} rows=all groupBy=city>
    <Column id=metric title="Chỉ số" />
    <Column id=v_p title={prev[0].label} align=right />
    <Column id=v_c title={per[0].label} align=right />
    <Column id=chg title="Thay đổi" align=right />
</DataTable>

**Theo phân khúc phòng ngủ:**

<DataTable data={cmp_bed} rows=all>
    <Column id=city title="TP" />
    <Column id=seg title="Phân khúc" />
    <Column id=rent_txt title="Thuê TB (tr/tháng)" align=right />
    <Column id=rent_chg title="Δ thuê TB" align=right />
    <Column id=pc_txt title="% vừa ngân sách" align=right />
    <Column id=chg title="Δ điểm %" align=right />
</DataTable>

**Theo quận: giá thuê/m² tăng ở {cmp_dist_t[0].hcm_up}/{cmp_dist_t[0].hcm_d} quận HCM và {cmp_dist_t[0].hn_up}/{cmp_dist_t[0].hn_d} quận HN** (chỉ tính quận có từ 30 tin trở lên ở cả hai kỳ).

<BarChart data={cmp_dist_hcm} x=district y=chg swapXY=true sort=false labels=true yFmt="0.0" yAxisTitle="% thay đổi giá thuê/m² TB" title="HCM: thay đổi giá thuê/m² TB theo quận (%)" />

<BarChart data={cmp_dist_hn} x=district y=chg swapXY=true sort=false labels=true yFmt="0.0" yAxisTitle="% thay đổi giá thuê/m² TB" title="HN: thay đổi giá thuê/m² TB theo quận (%)" />

{/if}

# Tổng quan

## Nguồn cung

```sql bracket
select city, bin, bin_order, n,
  round(100.0 * n / sum(n) over (partition by city), 1) as pct
from bds_real.rent_bracket
where period = '${params.period}'
order by bin_order, city
```

```sql bracket_head
select
  printf('%.1f', sum(case when city = 'Hồ Chí Minh' and bin_order = 2 then pct end)) as hcm_mid,
  printf('%.1f', sum(case when city = 'Hà Nội' and bin_order = 2 then pct end)) as hn_mid,
  printf('%.1f', sum(case when city = 'Hồ Chí Minh' and bin_order >= 4 then pct end)) as hcm_hi,
  printf('%.1f', sum(case when city = 'Hà Nội' and bin_order >= 4 then pct end)) as hn_hi
from ${bracket}
```

**Khoảng 10-20 tr/tháng chiếm {bracket_head[0].hcm_mid}% tin ở HCM và {bracket_head[0].hn_mid}% ở HN; tin trên 30 tr: HCM {bracket_head[0].hcm_hi}%, HN {bracket_head[0].hn_hi}%.**

<BarChart
    data={bracket}
    x=bin
    y=pct
    series=city
    type=grouped
    sort=false
    yFmt="0.0"
    xAxisTitle="triệu đồng/tháng"
    yAxisTitle="% số tin của từng thành phố"
    title="Tỷ trọng tin cho thuê theo khoảng giá"
/>

## Giá: HCM vs HN

{#if city_head[0].n_pr === 2}

**Giá thuê/m² HCM {city_head[0].rent_dir} HN {city_head[0].gap_rent}%; P/R ratio HCM {city_head[0].hcm_pr} năm, HN {city_head[0].hn_pr} năm.**

{:else}

**Giá thuê/m² HCM {city_head[0].rent_dir} HN {city_head[0].gap_rent}%.** Kỳ này chưa có dữ liệu chung cư bán cùng đợt nên chưa tính P/R.

{/if}

<DataTable data={city_tbl} rows=all>
    <Column id=city title="TP" />
    <Column id=n_txt title="Số tin" align=right />
    <Column id=rent_t title="Thuê TB (tr/tháng)" align=right />
    <Column id=rent_m2_t title="Thuê TB (tr/m²/tháng)" align=right />
    <Column id=sale_t title="Giá bán TB (tr/m²)" align=right />
    <Column id=pr_t title="P/R ratio" align=right />
</DataTable>

## Phân hóa theo vị trí

```sql top_dist
with r as (
  select city, district, n, avg_rent_m2,
    row_number() over (partition by city order by avg_rent_m2 desc) as rk
  from bds_real.rent_district
  where period = '${params.period}' and n >= 30
)
select r.city, r.district,
  printf('%.3f', r.avg_rent_m2) as rent_m2_t,
  coalesce(printf('%.1f', s.avg_price_1m2), '-') as sale_t,
  coalesce(printf('%.1f năm', s.avg_price_1m2 / (r.avg_rent_m2 * 12)), '-') as pr_t,
  replace(format('{:,}', cast(r.n as bigint)), ',', '.') as n_txt
from r
left join bds_real.cc_district_price s on s.city = r.city and s.district = r.district and s.period = '${params.period}'
where r.rk <= 5
order by r.city desc, r.rk
```

**Top 5 quận theo giá thuê/m² mỗi thành phố** (quận có từ 30 tin trở lên):

<DataTable data={top_dist} rows=all>
    <Column id=city title="TP" />
    <Column id=district title="Quận" />
    <Column id=rent_m2_t title="Thuê TB (tr/m²/tháng)" align=right />
    <Column id=sale_t title="Giá bán TB (tr/m²)" align=right />
    <Column id=pr_t title="P/R ratio" align=right />
    <Column id=n_txt title="Số tin thuê" align=right />
</DataTable>

# Phương pháp phân tích

Giữ 3 nhóm khách điển hình từ bài chung cư, đổi từ ngân sách *mua* sang ngân sách *thuê hàng tháng*. Mốc ngân sách là ước lượng chủ quan, không phải khảo sát:

1. Người độc thân, hoặc vợ chồng chưa/không có con → thường thuê căn 1PN. Ngân sách: **10 tr/tháng**.
2. Gia đình nhỏ, vợ chồng và 1-2 con → thường thuê căn 2PN. Ngân sách: **15 tr/tháng**.
3. Gia đình 3 thế hệ cùng sinh sống → thường thuê căn 3PN. Ngân sách: **20 tr/tháng**.

```sql bed
select r.city, r.bedrooms,
  replace(format('{:,}', cast(r.n as bigint)), ',', '.') as n_txt,
  printf('%.2f', r.avg_rent) as rent_t,
  printf('%.3f', r.avg_rent_m2) as rent_m2_t,
  coalesce(printf('%.1f', s.avg_price_1m2), '-') as sale_t,
  coalesce(printf('%.1f năm', s.avg_price_1m2 / (r.avg_rent_m2 * 12)), '-') as pr_t,
  case cast(cast(r.bedrooms as int) as varchar) when '1' then r.n_lt10 when '2' then r.n_lt15 else r.n_lt20 end as n_budget,
  printf('%.1f', 100.0 * case cast(cast(r.bedrooms as int) as varchar) when '1' then r.n_lt10 when '2' then r.n_lt15 else r.n_lt20 end / r.n) as p_budget
from bds_real.rent_bed r
left join bds_real.cc_afford s on s.city = r.city and s.bedrooms = r.bedrooms and s.period = r.period
where r.period = '${params.period}'
```

```sql bed_tbl
select *, replace(format('{:,}', cast(n_budget as bigint)), ',', '.') || '/' || n_txt || ' ≈ ' || p_budget || '%' as budget_txt
from ${bed}
order by bedrooms, city desc
```

```sql bed1
select * from ${bed_tbl} where bedrooms = 1
```

```sql bed2
select * from ${bed_tbl} where bedrooms = 2
```

```sql bed3
select * from ${bed_tbl} where bedrooms = 3
```

```sql bed_head
select bedrooms,
  max(case when city = 'Hồ Chí Minh' then p_budget end) as hcm_p,
  max(case when city = 'Hà Nội' then p_budget end) as hn_p
from ${bed}
group by 1
order by 1
```

```sql dist_bed
with d as (
  select city, bedrooms, district, n, avg_rent_m2,
    sum(n) over (partition by city, bedrooms) as n_tot,
    row_number() over (partition by city, bedrooms order by n desc) as rk
  from bds_real.rent_district_bed
  where period = '${params.period}'
)
select city, bedrooms, district,
  printf('%.1f%%', 100.0 * n / n_tot) as share_t,
  printf('%.3f', avg_rent_m2) as rent_m2_t,
  rk
from d
where rk <= 4
order by city desc, bedrooms, rk
```

```sql dist_bed1
select * from ${dist_bed} where bedrooms = 1
```

```sql dist_bed2
select * from ${dist_bed} where bedrooms = 2
```

```sql dist_bed3
select * from ${dist_bed} where bedrooms = 3
```

# 1 phòng ngủ

> Người độc thân, hoặc vợ chồng chưa/không có con. Ngân sách thuê: 10 tr/tháng.

**Căn 1PN dưới 10 tr/tháng: HCM {bed_head[0].hcm_p}%, HN {bed_head[0].hn_p}% số tin 1PN.**

<DataTable data={bed1} rows=all>
    <Column id=city title="TP" />
    <Column id=rent_t title="Thuê TB (tr/tháng)" align=right />
    <Column id=rent_m2_t title="Thuê TB (tr/m²/tháng)" align=right />
    <Column id=sale_t title="Giá bán TB (tr/m²)" align=right />
    <Column id=pr_t title="P/R ratio" align=right />
    <Column id=budget_txt title="Dưới 10 tr/tháng" align=right />
</DataTable>

## Phân bổ

4 quận nhiều tin 1PN nhất mỗi thành phố:

<DataTable data={dist_bed1} rows=all>
    <Column id=city title="TP" />
    <Column id=district title="Quận" />
    <Column id=share_t title="% nguồn cung" align=right />
    <Column id=rent_m2_t title="Thuê TB (tr/m²/tháng)" align=right />
</DataTable>

# 2 phòng ngủ

> Gia đình nhỏ, vợ chồng và 1-2 con. Ngân sách thuê: 15 tr/tháng.

**Căn 2PN dưới 15 tr/tháng: HCM {bed_head[1].hcm_p}%, HN {bed_head[1].hn_p}% số tin 2PN.**

<DataTable data={bed2} rows=all>
    <Column id=city title="TP" />
    <Column id=rent_t title="Thuê TB (tr/tháng)" align=right />
    <Column id=rent_m2_t title="Thuê TB (tr/m²/tháng)" align=right />
    <Column id=sale_t title="Giá bán TB (tr/m²)" align=right />
    <Column id=pr_t title="P/R ratio" align=right />
    <Column id=budget_txt title="Dưới 15 tr/tháng" align=right />
</DataTable>

## Phân bổ

4 quận nhiều tin 2PN nhất mỗi thành phố:

<DataTable data={dist_bed2} rows=all>
    <Column id=city title="TP" />
    <Column id=district title="Quận" />
    <Column id=share_t title="% nguồn cung" align=right />
    <Column id=rent_m2_t title="Thuê TB (tr/m²/tháng)" align=right />
</DataTable>

# 3 phòng ngủ

> Gia đình 3 thế hệ cùng sinh sống. Ngân sách thuê: 20 tr/tháng.

**Căn 3PN dưới 20 tr/tháng: HCM {bed_head[2].hcm_p}%, HN {bed_head[2].hn_p}% số tin 3PN.**

<DataTable data={bed3} rows=all>
    <Column id=city title="TP" />
    <Column id=rent_t title="Thuê TB (tr/tháng)" align=right />
    <Column id=rent_m2_t title="Thuê TB (tr/m²/tháng)" align=right />
    <Column id=sale_t title="Giá bán TB (tr/m²)" align=right />
    <Column id=pr_t title="P/R ratio" align=right />
    <Column id=budget_txt title="Dưới 20 tr/tháng" align=right />
</DataTable>

## Phân bổ

4 quận nhiều tin 3PN nhất mỗi thành phố:

<DataTable data={dist_bed3} rows=all>
    <Column id=city title="TP" />
    <Column id=district title="Quận" />
    <Column id=share_t title="% nguồn cung" align=right />
    <Column id=rent_m2_t title="Thuê TB (tr/m²/tháng)" align=right />
</DataTable>

---

**Nguồn:** batdongsan.com.vn, tin cho thuê căn hộ chung cư ở HCM & HN, thu thập {per[0].win}. **Hạn chế:** đây là giá rao, không phải giá giao dịch; tin rao có thể trùng hoặc không còn hiệu lực; địa giới theo trước sáp nhập.

{/if}
