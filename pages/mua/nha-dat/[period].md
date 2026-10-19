---
title: Giá mua nhà đất
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
join bds_real.nd_meta m using (period)
where p.period = '${params.period}'
```

```sql prev
select p.period, p.label
from bds_real.periods p
join bds_real.nd_meta m using (period)
where p.period < '${params.period}'
order by p.period desc
limit 1
```

```sql types
-- Loại hình, nhãn ngắn, ngân sách giả định (tỷ) và cột đếm tương ứng: theo bài nhà đất tháng 7/2026.
select * from (values
  ('nhà riêng', 'Nhà riêng', 1, 5),
  ('nhà mặt phố', 'Nhà mặt phố', 2, 10),
  ('nhà biệt thự liền kề', 'Biệt thự liền kề', 3, 20),
  ('shophouse nhà phố thương mại', 'Shophouse', 4, 20)
) t(type, type_label, type_order, budget_ty)
```

```sql kpi
select t.type_label, t.type_order, t.budget_ty, k.*,
  case t.budget_ty when 5 then k.n_lt5 when 10 then k.n_lt10 else k.n_lt20 end as n_budget
from bds_real.nd_type_kpi k
join ${types} t using (type)
where k.period = '${params.period}'
```

```sql kpi_tbl
select type_label, city,
  replace(format('{:,}', cast(n as bigint)), ',', '.') as n_txt,
  printf('%.2f', avg_price_ty) as ty_t,
  printf('%.1f', avg_price_1m2) as m2_t,
  printf('%.1f', avg_area) as area_t
from ${kpi}
order by type_order, city desc
```

```sql vs_cc
-- So với chung cư cùng kỳ (nếu kỳ này có dữ liệu chung cư).
select k.city,
  printf('%.1f', min(k.avg_price_1m2 / c.avg_price_1m2)) as min_x,
  printf('%.1f', max(k.avg_price_1m2 / c.avg_price_1m2)) as max_x,
  printf('%.1f', max(case when k.type = 'nhà riêng' then k.avg_price_1m2 / c.avg_price_1m2 end)) as rieng_x,
  printf('%.1f', c.avg_price_1m2) as cc_m2
from ${kpi} k
join bds_real.cc_city_kpi c on c.city = k.city and c.period = k.period
group by k.city, c.avg_price_1m2
order by k.city desc
```

```sql hn_dearer
select
  count(*) filter (where hn.avg_price_1m2 > hcm.avg_price_1m2) as n_hn_dearer,
  count(*) as n_types,
  string_agg(case when hn.avg_price_1m2 <= hcm.avg_price_1m2 then hn.type_label end, ', ') as hcm_dearer_types
from ${kpi} hn
join ${kpi} hcm on hcm.type = hn.type and hcm.city = 'Hồ Chí Minh'
where hn.city = 'Hà Nội'
```

```sql soft
select type_label, type_order,
  'dưới ' || cast(budget_ty as varchar) || ' tỷ' as budget,
  max(case when city = 'Hồ Chí Minh' then printf('%.1f%%', 100.0 * n_budget / n) end) as hcm,
  max(case when city = 'Hà Nội' then printf('%.1f%%', 100.0 * n_budget / n) end) as hn
from ${kpi}
group by 1, 2, 3
union all
select 'Chung cư (so sánh)', 0, 'dưới 3 tỷ',
  max(case when city = 'Hồ Chí Minh' then printf('%.1f%%', 100.0 * n_lt3 / n) end),
  max(case when city = 'Hà Nội' then printf('%.1f%%', 100.0 * n_lt3 / n) end)
from bds_real.cc_city_kpi
where period = '${params.period}'
having count(*) > 0
order by type_order
```

```sql sec
-- Mỗi loại hình x thành phố: tỷ lệ vừa ngân sách và 4 quận nhiều tin nhất.
with d as (
  select d.type, d.city, d.district, d.n, d.avg_price_ty, d.avg_price_1m2, k.n as n_tot,
    row_number() over (partition by d.type, d.city order by d.n desc) as rk
  from bds_real.nd_district d
  join ${kpi} k on k.type = d.type and k.city = d.city
  where d.period = '${params.period}'
)
select k.type, k.type_label, k.city,
  printf('%.1f', 100.0 * k.n_budget / k.n) as p_budget,
  replace(format('{:,}', cast(k.n_budget as bigint)), ',', '.') as n_budget_txt,
  replace(format('{:,}', cast(k.n as bigint)), ',', '.') as n_txt,
  printf('%.1f', 100.0 * k.n_lt10 / k.n) as p_lt10,
  (select string_agg(district || ' (' || printf('%.1f', 100.0 * n / n_tot) || '%, TB ' || printf('%.2f', avg_price_ty) || ' tỷ)', ', ' order by rk)
     from d where d.type = k.type and d.city = k.city and rk <= 4) as top4
from ${kpi} k
order by k.type_order, k.city desc
```

```sql sec1
select * from ${sec} where type = 'nhà riêng'
```

```sql sec2
select * from ${sec} where type = 'nhà mặt phố'
```

```sql sec3
select * from ${sec} where type = 'nhà biệt thự liền kề'
```

```sql sec4
select * from ${sec} where type = 'shophouse nhà phố thương mại'
```

{#if per.length === 0}

Không có kỳ báo cáo <b>{params.period}</b> cho mảng này. <a href="/mua/nha-dat" class="text-primary hover:underline">Xem danh sách các kỳ</a>.

{:else}

Kỳ <b>{per[0].label}</b>: đợt scrape {per[0].win}, <b>{per[0].n_txt}</b> tin nhà đất rao bán có giá ở HCM & HN. <a href="/mua/nha-dat" class="text-primary hover:underline">Các kỳ khác</a>.

# Khai báo kĩ thuật

- Nguồn dữ liệu: [https://batdongsan.com.vn/](https://batdongsan.com.vn/), 4 loại hình `nhà riêng`, `nhà mặt phố`, `nhà biệt thự liền kề`, `shophouse nhà phố thương mại`, có giá, chưa hết hạn, thu thập {per[0].win}.
- Nhà đất có đuôi giá siêu cao (mặt phố, đất thương mại lớn). Trang này dùng số **trung bình** cho nhất quán với bài chung cư, nên giá TB bị đuôi này kéo lên; đọc kèm tỷ lệ tin vừa ngân sách.
- Mỗi kỳ là ảnh chụp toàn bộ tin trong đợt scrape của kỳ đó, dựng lại từ dữ liệu thô. Địa giới hành chính cũ trước sáp nhập.

{#if prev.length > 0}

```sql cmp
with c as (select * from bds_real.nd_type_kpi where period = '${params.period}'),
p as (select * from bds_real.nd_type_kpi where period = (select period from ${prev}))
select t.type_label, c.city,
  replace(format('{:,}', cast(p.n as bigint)), ',', '.') || ' → ' || replace(format('{:,}', cast(c.n as bigint)), ',', '.') as n_txt,
  printf('%.1f → %.1f', p.avg_price_1m2, c.avg_price_1m2) as m2_txt,
  printf('%+.1f%%', 100.0 * (c.avg_price_1m2 / p.avg_price_1m2 - 1)) as m2_chg
from c join p using (city, type) join ${types} t using (type)
order by t.type_order, c.city desc
```

# So với {prev[0].label}

Số tin mỗi kỳ không bằng nhau, đọc cột số tin trước khi đọc chênh lệch giá.

<DataTable data={cmp} rows=all>
    <Column id=type_label title="Loại hình" />
    <Column id=city title="TP" />
    <Column id=n_txt title="Số tin" align=right />
    <Column id=m2_txt title="Giá/m² TB (tr)" align=right />
    <Column id=m2_chg title="Thay đổi" align=right />
</DataTable>

{/if}

# Tổng quan

## Giá theo loại hình

**Hà Nội đắt hơn HCM (theo giá/m² TB) ở {hn_dearer[0].n_hn_dearer}/{hn_dearer[0].n_types} loại hình.**

<DataTable data={kpi_tbl} rows=all>
    <Column id=type_label title="Loại hình" />
    <Column id=city title="TP" />
    <Column id=n_txt title="Số tin" align=right />
    <Column id=ty_t title="Giá TB (tỷ)" align=right />
    <Column id=m2_t title="Giá/m² TB (tr)" align=right />
    <Column id=area_t title="Diện tích TB (m²)" align=right />
</DataTable>

{#if vs_cc.length > 0}

So với chung cư cùng kỳ, giá/m² nhà đất đắt hơn một bậc:

{#each vs_cc as v}

- {v.city}: nhà riêng (loại "rẻ" nhất nhóm) đắt gấp <b>{v.rieng_x}</b> lần chung cư ({v.cc_m2} tr/m²); cả 4 loại hình đắt gấp {v.min_x}-{v.max_x} lần.

{/each}

{:else}

Kỳ này chưa có dữ liệu chung cư cùng đợt để so.

{/if}

## Cửa giá mềm

Mỗi loại hình gán với một ngân sách giả định (xem mục Phương pháp phân tích). Hàng chung cư để so: dưới 3 tỷ.

<DataTable data={soft} rows=all>
    <Column id=type_label title="Loại hình" />
    <Column id=budget title="Ngưỡng" />
    <Column id=hcm title="HCM" align=right />
    <Column id=hn title="HN" align=right />
</DataTable>

# Phương pháp phân tích

Giống bài chung cư, mỗi loại hình gán cho một nhóm người mua và một ngân sách kỳ vọng. Đây là ước lượng chủ quan, không phải khảo sát:

1. **Nhà riêng** → gia đình phổ thông muốn có đất riêng để ở. Ngân sách giả định: **5 tỷ**.
2. **Nhà mặt phố** → hộ kinh doanh nhỏ, vừa ở vừa buôn bán mặt tiền. Ngân sách giả định: **10 tỷ**.
3. **Biệt thự liền kề** → gia đình khá giả, muốn không gian sống cao cấp hơn. Ngân sách giả định: **20 tỷ**.
4. **Shophouse nhà phố thương mại** → nhà đầu tư, mua để cho thuê mặt bằng. Ngân sách giả định: **20 tỷ**.

# Nhà riêng

> Gia đình phổ thông, muốn đất riêng để ở. Ngân sách: 5 tỷ.

{#each sec1 as s}

- {s.city}: <b>{s.p_budget}%</b> tin dưới 5 tỷ ({s.n_budget_txt}/{s.n_txt}), dưới 10 tỷ là {s.p_lt10}%. Nhiều tin nhất: {s.top4}.

{/each}

<Dropdown name=city_nd1 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist_nd1
select district, n, avg_price_1m2 from bds_real.nd_district
where period = '${params.period}' and type = 'nhà riêng' and city = '${inputs.city_nd1.value}'
order by n desc limit 8
```

<BarChart data={dist_nd1} x=district y=n swapXY=true sort=false labels=true title="Nhà riêng: 8 quận nhiều tin nhất ({inputs.city_nd1.label})" />

# Nhà mặt phố

> Hộ kinh doanh nhỏ, vừa ở vừa buôn bán mặt tiền. Ngân sách: 10 tỷ.

{#each sec2 as s}

- {s.city}: <b>{s.p_budget}%</b> tin dưới 10 tỷ ({s.n_budget_txt}/{s.n_txt}). Nhiều tin nhất: {s.top4}.

{/each}

<Dropdown name=city_nd2 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist_nd2
select district, n, avg_price_1m2 from bds_real.nd_district
where period = '${params.period}' and type = 'nhà mặt phố' and city = '${inputs.city_nd2.value}'
order by n desc limit 8
```

<BarChart data={dist_nd2} x=district y=n swapXY=true sort=false labels=true title="Nhà mặt phố: 8 quận nhiều tin nhất ({inputs.city_nd2.label})" />

# Biệt thự liền kề

> Gia đình khá giả, muốn không gian sống cao cấp hơn. Ngân sách: 20 tỷ.

{#each sec3 as s}

- {s.city}: <b>{s.p_budget}%</b> tin dưới 20 tỷ ({s.n_budget_txt}/{s.n_txt}). Nhiều tin nhất: {s.top4}.

{/each}

<Dropdown name=city_nd3 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist_nd3
select district, n, avg_price_1m2 from bds_real.nd_district
where period = '${params.period}' and type = 'nhà biệt thự liền kề' and city = '${inputs.city_nd3.value}'
order by n desc limit 8
```

<BarChart data={dist_nd3} x=district y=n swapXY=true sort=false labels=true title="Biệt thự liền kề: 8 quận nhiều tin nhất ({inputs.city_nd3.label})" />

# Shophouse nhà phố thương mại

> Nhà đầu tư, mua để cho thuê mặt bằng trong khu đô thị mới. Ngân sách: 20 tỷ.

{#each sec4 as s}

- {s.city}: <b>{s.p_budget}%</b> tin dưới 20 tỷ ({s.n_budget_txt}/{s.n_txt}). Nhiều tin nhất: {s.top4}.

{/each}

<Dropdown name=city_nd4 title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" />
    <DropdownOption value="Hà Nội" />
</Dropdown>

```sql dist_nd4
select district, n, avg_price_1m2 from bds_real.nd_district
where period = '${params.period}' and type = 'shophouse nhà phố thương mại' and city = '${inputs.city_nd4.value}'
order by n desc limit 8
```

<BarChart data={dist_nd4} x=district y=n swapXY=true sort=false labels=true title="Shophouse: 8 quận nhiều tin nhất ({inputs.city_nd4.label})" />

---

**Nguồn:** batdongsan.com.vn, tin rao bán nhà đất có giá ở HCM & HN, thu thập {per[0].win}. **Hạn chế:** đây là giá rao, không phải giá giao dịch; tin rao có thể trùng hoặc không còn hiệu lực; địa giới theo trước sáp nhập.

{/if}
