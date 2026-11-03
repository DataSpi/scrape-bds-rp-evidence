---
title: Thuê hay mua?
---

```sql latest
-- kỳ mới nhất có cả dữ liệu mua lẫn thuê
select e.period, p.label
from bds_real.cc_entry e join bds_real.periods p using (period)
where e.period in (select period from bds_real.rent_entry)
order by e.period desc limit 1
```

```sql mac
-- số liệu vĩ mô nhập tay, nguồn ghi ở cuối trang
select * from macro.context order by as_of desc limit 1
```

```sql assume
-- người đọc chọn: lãi vay, vốn tự có, tốc độ tăng giá nhà
-- cố định: tiền dư đem gửi tiết kiệm với lãi Big4, gia đình thu nhập 50 tr, sinh hoạt 20 tr
select
  cast('${inputs.rate.value}' as double) / 100 as rate,
  cast('${inputs.down.value}' as double) / 100 as down_pct,
  cast('${inputs.growth.value}' as double) / 100 as g,
  (select save_big4 from ${mac}) / 100 as inv,
  25 as years, 30 as horizon,
  50.0 as inc, 0.05 as inc_g,
  20.0 as spend, 0.04 as spend_g,
  0.04 as rent_g, 0.005 as maint, 0.02 as buy_cost, 0.04 as infl
```

```sql base
-- đơn vị tiền: triệu đồng
with p as (select * from ${assume}),
b as (
  select p25_ty from bds_real.cc_entry
  where period = (select period from ${latest}) and city = '${inputs.city.value}' and segment = '2PN'
),
r as (
  select p25_rent, area_p50 from bds_real.rent_entry
  where period = (select period from ${latest}) and city = '${inputs.city.value}' and segment = '2PN'
),
c as (
  select b.p25_ty * 1000 as price, r.p25_rent as rent, r.area_p50 as rent_area, p.*,
    b.p25_ty * 1000 * (1 - p.down_pct) as loan, b.p25_ty * 1000 * p.down_pct as down,
    p.rate / 12 as rm, p.years * 12 as nm, p.horizon * 12 as nh,
    pow(1 + p.inv, 1 / 12.0) - 1 as im
  from b, r, p
)
select *,
  loan * rm * pow(1 + rm, nm) / (pow(1 + rm, nm) - 1) as pmt,
  loan * rm as int1,
  down * im as opp1
from c
```

```sql sim
-- mô phỏng từng tháng trong 30 năm; tiền dư mỗi tháng của cả hai bên đem gửi tiết kiệm
with b as (select * from ${base}),
flow as (
  select m,
    b.inc * pow(1 + b.inc_g, floor(m / 12)) - b.spend * pow(1 + b.spend_g, floor(m / 12)) as free,
    case when m < b.nm then b.pmt else 0 end + b.price * pow(1 + b.g, (m + 1) / 12.0) * b.maint / 12 as buy_out,
    b.rent * pow(1 + b.rent_g, floor(m / 12)) as rent_out
  from range(0, (select cast(nh as int) from b)) t(m), b
),
acc as (
  select y.t as year,
    sum((f.free - f.buy_out) * pow(1 + b.im, y.t * 12 - 1 - f.m)) as s_buy,
    sum((f.free - f.rent_out) * pow(1 + b.im, y.t * 12 - 1 - f.m)) as s_rent
  from range(1, (select horizon + 1 from b)) y(t)
  join flow f on f.m < y.t * 12
  cross join b
  group by y.t
)
select acc.year,
  (b.price * pow(1 + b.g, acc.year)
    - case when acc.year * 12 >= b.nm then 0
           else b.loan * (pow(1 + b.rm, b.nm) - pow(1 + b.rm, acc.year * 12)) / (pow(1 + b.rm, b.nm) - 1) end
    - b.price * b.buy_cost * pow(1 + b.im, acc.year * 12)
    + acc.s_buy) / 1000 as nw_buy,
  (b.down * pow(1 + b.im, acc.year * 12) + acc.s_rent) / 1000 as nw_rent,
  pow(1 + b.infl, acc.year) as deflator,
  -- các thành phần để trang in ra cách tính (tỷ đồng)
  b.price * pow(1 + b.g, acc.year) / 1000 as house,
  case when acc.year * 12 >= b.nm then 0
       else b.loan * (pow(1 + b.rm, b.nm) - pow(1 + b.rm, acc.year * 12)) / (pow(1 + b.rm, b.nm) - 1) end / 1000 as debt,
  b.price * b.buy_cost * pow(1 + b.im, acc.year * 12) / 1000 as cost,
  acc.s_buy / 1000 as s_buy,
  b.down * pow(1 + b.im, acc.year * 12) / 1000 as down_fv,
  acc.s_rent / 1000 as s_rent
from acc, b
order by acc.year
```

```sql nw
select year, 'Mua' as who, round(nw_buy, 2) as nw from ${sim}
union all select year, 'Thuê', round(nw_rent, 2) from ${sim}
order by year
```

```sql even
-- tốc độ tăng giá nhà thấp nhất để sau 30 năm người mua giàu bằng người thuê (quét 0-15%, bước 0,25%)
with b as (select * from ${base}),
gs as (select r / 400.0 as g from range(0, 61) t(r)),
fin as (
  select gs.g,
    b.price * pow(1 + gs.g, b.horizon)
      - b.price * b.buy_cost * pow(1 + b.im, b.nh)
      + sum((b.inc * pow(1 + b.inc_g, floor(m / 12)) - b.spend * pow(1 + b.spend_g, floor(m / 12))
             - case when m < b.nm then b.pmt else 0 end
             - b.price * pow(1 + gs.g, (m + 1) / 12.0) * b.maint / 12) * pow(1 + b.im, b.nh - 1 - m)) as nw_buy
  from gs, b, range(0, (select cast(nh as int) from b)) t(m)
  group by gs.g, b.price, b.horizon, b.buy_cost, b.im, b.nh
)
select
  min(g) filter (where fin.nw_buy >= s.nw_rent * 1000) as g_star,
  coalesce(translate(format('{:,.1f}', 100 * min(g) filter (where fin.nw_buy >= s.nw_rent * 1000)), ',.', '.,'), 'hơn 15') as g_star_t
from fin, (select nw_rent from ${sim} order by year desc limit 1) s
```

```sql k
select
  translate(format('{:,.1f}', price / 1000), ',.', '.,') as price_t,
  translate(format('{:,.0f}', rent), ',.', '.,') as rent_t,
  translate(format('{:,.1f}', pmt), ',.', '.,') as pmt_t,
  translate(format('{:,.1f}', int1), ',.', '.,') as int1_t,
  translate(format('{:,.1f}', pmt - int1), ',.', '.,') as princ1_t,
  translate(format('{:,.1f}', opp1), ',.', '.,') as opp1_t,
  translate(format('{:,.1f}', int1 + opp1), ',.', '.,') as lost1_t,
  translate(format('{:,.1f}', (int1 + opp1) / rent), ',.', '.,') as lost_x,
  int1 + opp1 > rent as buyer_loses_more,
  translate(format('{:,.1f}', down / 1000), ',.', '.,') as down_t,
  translate(format('{:,.1f}', loan / 1000), ',.', '.,') as loan_t,
  translate(format('{:,.0f}', down_pct * 100), ',.', '.,') as down_pct_t,
  translate(format('{:,.0f}', price / (rent * 12)), ',.', '.,') as price_years,
  price / (rent * 12) as price_years_v,
  translate(format('{:,.1f}', rent * 12 / price * 100), ',.', '.,') as yield_t,
  translate(format('{:,.1f}', (g - maint) * 100), ',.', '.,') as gm_t,
  translate(format('{:,.1f}', (rent * 12 / price + g - maint) * 100), ',.', '.,') as total_t,
  translate(format('{:,.1f}', rate * (1 - down_pct) * 100), ',.', '.,') as cost_loan_t,
  translate(format('{:,.1f}', inv * down_pct * 100), ',.', '.,') as cost_down_t,
  translate(format('{:,.1f}', (rate * (1 - down_pct) + inv * down_pct) * 100), ',.', '.,') as cap_cost_t,
  rent * 12 / price + g - maint < rate * (1 - down_pct) + inv * down_pct as total_below_cost,
  translate(format('{:,.1f}', (rate * (1 - down_pct) + inv * down_pct - rent * 12 / price + maint) * 100), ',.', '.,') as g_simple_t,
  translate(format('{:,.1f}', inv * 100), ',.', '.,') as save_t,
  translate(format('{:,.0f}', rate * 100), ',.', '.,') as rate_t,
  translate(format('{:,.0f}', g * 100), ',.', '.,') as g_t,
  translate(format('{:,.0f}', inc), ',.', '.,') as inc_t,
  translate(format('{:,.0f}', spend), ',.', '.,') as spend_t,
  translate(format('{:,.0f}', rent_g * 100), ',.', '.,') as rent_g_t,
  translate(format('{:,.0f}', inc_g * 100), ',.', '.,') as inc_g_t,
  translate(format('{:,.0f}', spend_g * 100), ',.', '.,') as spend_g_t,
  translate(format('{:,.0f}', buy_cost * 100), ',.', '.,') as buy_cost_t,
  translate(format('{:,.1f}', maint * 100), ',.', '.,') as maint_t,
  translate(format('{:,.0f}', infl * 100), ',.', '.,') as infl_t,
  translate(format('{:,.1f}', inc - spend - rent), ',.', '.,') as rent_left_t,
  inc - spend - pmt - price * maint / 12 as buy_left_v,
  translate(format('{:,.1f}', inc - spend - pmt - price * maint / 12), ',.', '.,') as buy_left_t,
  translate(format('{:,.1f}', -(inc - spend - pmt - price * maint / 12)), ',.', '.,') as buy_short_t,
  pmt + price * maint / 12 > rent as buy_thinner,
  translate(format('{:,.1f}', pmt + price * maint / 12 - rent), ',.', '.,') as left_gap_t,
  cast(years as int) as years,
  cast(horizon as int) as horizon,
  cast(rent_area as int) as rent_area
from ${base}
```

```sql end30
select
  translate(format('{:,.1f}', nw_buy), ',.', '.,') as buy_t,
  translate(format('{:,.1f}', nw_rent), ',.', '.,') as rent_t,
  translate(format('{:,.1f}', nw_buy / deflator), ',.', '.,') as buy_real_t,
  translate(format('{:,.1f}', nw_rent / deflator), ',.', '.,') as rent_real_t,
  nw_buy >= nw_rent as buyer_wins
from ${sim} order by year desc limit 1
```

```sql m
select
  translate(format('{:,.1f}', cast(save_big4 as double)), ',.', '.,') as save_big4, translate(format('{:,.1f}', cast(save_top as double)), ',.', '.,') as save_top,
  translate(format('{:,.1f}', cast(promo_lo as double)), ',.', '.,') as promo_lo, translate(format('{:,.1f}', cast(promo_hi as double)), ',.', '.,') as promo_hi,
  translate(format('{:,.0f}', cast(float_lo as double)), ',.', '.,') as float_lo, translate(format('{:,.0f}', cast(float_hi as double)), ',.', '.,') as float_hi,
  translate(format('{:,.0f}', abs(cast(cbre_hn_primary_qoq as double))), ',.', '.,') as cbre_qoq,
  translate(format('{:,.0f}', abs(cast(cbre_hn_sales_yoy as double))), ',.', '.,') as cbre_sales
from ${mac}
```

```sql month
-- tháng đầu tiên: tiền đi đâu
select 'Thuê' as option, 1 as o, 'Lãi vay' as kind, rent as v from ${base}
union all select 'Mua', 2, 'Lãi vay', int1 from ${base}
union all select 'Mua', 2, 'Lãi tiết kiệm bỏ lỡ', opp1 from ${base}
union all select 'Mua', 2, 'Gốc', pmt - int1 from ${base}
order by o
```

```sql yields
-- mỗi năm, tính theo % giá căn: chủ nhà được gì, so với gửi tiết kiệm và chi phí vốn của người mua
select 'Chủ nhà được' as kind, 'Tiền thuê' as part, 1 as o, round(rent * 12 / price * 100, 1) as v from ${base}
union all select 'Chủ nhà được', 'Giá nhà tăng (trừ bảo trì)', 2, round((g - maint) * 100, 1) from ${base}
union all select 'Gửi tiết kiệm', 'Lãi tiết kiệm', 3, round(inv * 100, 1) from ${base}
union all select 'Chi phí vốn người mua', 'Lãi vay', 4, round(rate * (1 - down_pct) * 100, 1) from ${base}
union all select 'Chi phí vốn người mua', 'Lãi tiết kiệm bỏ lỡ', 5, round(inv * down_pct * 100, 1) from ${base}
order by o
```

```sql budget
-- năm đầu tiên, mỗi tháng
select 'Thuê' as option, 1 as o, 'Sinh hoạt' as kind, spend as v from ${base}
union all select 'Thuê', 1, 'Tiền nhà', rent from ${base}
union all select 'Thuê', 1, 'Còn dư', inc - spend - rent from ${base}
union all select 'Mua', 2, 'Sinh hoạt', spend from ${base}
union all select 'Mua', 2, 'Tiền nhà', pmt + price * maint / 12 from ${base}
union all select 'Mua', 2, 'Còn dư', inc - spend - pmt - price * maint / 12 from ${base}
order by o
```

```sql cx
-- số trung gian để người đọc tự tính lại (triệu đồng, trừ chỗ ghi tỷ)
with b as (select *, price * maint / 12 as maint_m from ${base}),
e as (select * from ${sim} order by year desc limit 1)
select
  translate(format('{:,.1f}', b.price / 1000), ',.', '.,') as price_ty, translate(format('{:,.0f}', b.price), ',.', '.,') as price_tr, translate(format('{:,.0f}', b.rent), ',.', '.,') as rent,
  translate(format('{:,.0f}', b.down_pct * 100), ',.', '.,') as down_pct, translate(format('{:,.0f}', 100 - b.down_pct * 100), ',.', '.,') as loan_pct,
  translate(format('{:,.0f}', b.down), ',.', '.,') as down, translate(format('{:,.0f}', b.loan), ',.', '.,') as loan,
  translate(format('{:,.0f}', b.rate * 100), ',.', '.,') as rate_y, translate(format('{:,.1f}', b.rm * 100), ',.', '.,') as rate_m,
  cast(b.years as int) as years, cast(b.nm as int) as nm,
  translate(format('{:,.1f}', b.inv * 100), ',.', '.,') as inv_y, translate(format('{:,.1f}', b.im * 100), ',.', '.,') as inv_m,
  translate(format('{:,.0f}', b.inc), ',.', '.,') as inc, translate(format('{:,.0f}', b.spend), ',.', '.,') as spend, translate(format('{:,.0f}', b.g * 100), ',.', '.,') as g,
  translate(format('{:,.1f}', b.pmt), ',.', '.,') as pmt, translate(format('{:,.1f}', b.int1), ',.', '.,') as int1, translate(format('{:,.1f}', b.pmt - b.int1), ',.', '.,') as princ1, translate(format('{:,.1f}', b.opp1), ',.', '.,') as opp1,
  translate(format('{:,.1f}', b.int1 + b.opp1), ',.', '.,') as lost1, translate(format('{:,.1f}', (b.int1 + b.opp1) / b.rent), ',.', '.,') as lost_x,
  translate(format('{:,.0f}', b.rent * 12), ',.', '.,') as rent_y, translate(format('{:,.1f}', b.rent * 12 / b.price * 100), ',.', '.,') as yield,
  translate(format('{:,.0f}', b.price / (b.rent * 12)), ',.', '.,') as price_years,
  translate(format('{:,.1f}', b.maint * 100), ',.', '.,') as maint, translate(format('{:,.1f}', b.maint_m), ',.', '.,') as maint_m, translate(format('{:,.1f}', b.pmt + b.maint_m), ',.', '.,') as buy_house,
  translate(format('{:,.1f}', b.inc - b.spend - b.rent), ',.', '.,') as rent_left, translate(format('{:,.1f}', b.inc - b.spend - b.pmt - b.maint_m), ',.', '.,') as buy_left,
  translate(format('{:,.0f}', b.buy_cost * 100), ',.', '.,') as buy_cost, translate(format('{:,.0f}', b.price * b.buy_cost), ',.', '.,') as buy_cost_tr,
  translate(format('{:,.0f}', b.inc_g * 100), ',.', '.,') as inc_g, translate(format('{:,.0f}', b.spend_g * 100), ',.', '.,') as spend_g, translate(format('{:,.0f}', b.rent_g * 100), ',.', '.,') as rent_g,
  translate(format('{:,.0f}', b.infl * 100), ',.', '.,') as infl, cast(b.horizon as int) as horizon,
  translate(format('{:,.1f}', e.house), ',.', '.,') as house, translate(format('{:,.1f}', e.debt), ',.', '.,') as debt, translate(format('{:,.1f}', e.cost), ',.', '.,') as cost,
  e.s_buy < 0 as s_buy_neg, translate(format('{:,.1f}', abs(e.s_buy)), ',.', '.,') as s_buy_abs, translate(format('{:,.1f}', e.nw_buy), ',.', '.,') as nw_buy,
  translate(format('{:,.1f}', e.down_fv), ',.', '.,') as down_fv, e.s_rent < 0 as s_rent_neg, translate(format('{:,.1f}', abs(e.s_rent)), ',.', '.,') as s_rent_abs, translate(format('{:,.1f}', e.nw_rent), ',.', '.,') as nw_rent,
  translate(format('{:,.1f}', e.deflator), ',.', '.,') as deflator
from b, e
```

```sql assumptions
-- bảng thông số đầu trang, đổi theo dropdown
select 5 as o, 'Lãi vay' as item, rate_y || '%/năm ÷ 12 = ' || rate_m || '%/tháng' as val, 'Ô "Lãi vay"' as src from ${cx}
union all select 6, 'Thời hạn vay', years || ' năm = ' || nm || ' tháng', 'Giả định' from ${cx}
union all select 7, 'Lãi gửi tiết kiệm', inv_y || '%/năm ≈ ' || inv_m || '%/tháng', 'Big4, kỳ hạn 12 tháng; quy ra tháng theo lãi kép' from ${cx}
union all select 8, 'Thu nhập, sinh hoạt', inc || ' tr, ' || spend || ' tr mỗi tháng', 'Giả định' from ${cx}
union all select 9, 'Giá nhà tăng', g || '%/năm', 'Ô "Giá nhà tăng mỗi năm"' from ${cx}
union all select 10, 'Thu nhập, sinh hoạt, tiền thuê tăng', inc_g || '%, ' || spend_g || '%, ' || rent_g || '% mỗi năm', 'Giả định' from ${cx}
union all select 11, 'Phí khi mua, bảo trì', buy_cost || '% giá căn, ' || maint || '% giá nhà mỗi năm', 'Giả định' from ${cx}
union all select 12, 'Lạm phát', infl || '%/năm', 'Giả định, chỉ để quy về sức mua hôm nay' from ${cx}
order by o
```

```sql dcmp
-- phần mất tháng đầu ở vốn tự có 30% và 70%, cùng lãi vay
with b as (select * from ${base}),
d as (select d, b.price * (1 - d) * b.rm + b.price * d * b.im as lost, b.rent from b, (values (0.3), (0.7)) t(d))
select
  translate(format('{:,.1f}', (select lost from d where d = 0.3)), ',.', '.,') as lost30,
  translate(format('{:,.1f}', (select lost from d where d = 0.7)), ',.', '.,') as lost70,
  translate(format('{:,.1f}', (select lost / rent from d where d = 0.7)), ',.', '.,') as x70,
  (select lost > rent from d where d = 0.7) as still_more
```

```sql dist
with buy as (
  select district, p25_ty from bds_real.cc_entry_district
  where period = (select period from ${latest}) and city = '${inputs.city.value}' and segment = '2PN'
),
rent as (
  select district, p25_rent from bds_real.rent_entry_district
  where period = (select period from ${latest}) and city = '${inputs.city.value}' and segment = '2PN'
),
city as (select price / (rent * 12) as city_years from ${base})
select buy.district,
  round(buy.p25_ty * 1000 / (rent.p25_rent * 12), 0) as years,
  case when buy.p25_ty * 1000 / (rent.p25_rent * 12) <= city.city_years
    then 'Bằng hoặc ít năm hơn mức chung' else 'Nhiều năm hơn mức chung' end as grp
from buy join rent using (district), city
order by years
```

```sql dist_head
select
  (select district from ${dist} order by years limit 1) as lo_d,
  (select cast(years as int) from ${dist} order by years limit 1) as lo_y,
  (select district from ${dist} order by years desc limit 1) as hi_d,
  (select cast(years as int) from ${dist} order by years desc limit 1) as hi_y,
  (select count(*) from ${dist}) as n_d
```

<div class="flex flex-wrap gap-4">

<Dropdown name=city title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" valueLabel="TP.HCM" />
    <DropdownOption value="Hà Nội" valueLabel="Hà Nội" />
</Dropdown>

<Dropdown name=rate title="Lãi vay (sau ưu đãi)" defaultValue="12">
    <DropdownOption value="10" valueLabel="10%/năm" />
    <DropdownOption value="11" valueLabel="11%/năm" />
    <DropdownOption value="12" valueLabel="12%/năm" />
    <DropdownOption value="13" valueLabel="13%/năm" />
    <DropdownOption value="14" valueLabel="14%/năm" />
    <DropdownOption value="15" valueLabel="15%/năm" />
    <DropdownOption value="16" valueLabel="16%/năm" />
</Dropdown>

<Dropdown name=down title="Vốn tự có" defaultValue="30">
    <DropdownOption value="30" valueLabel="30% giá căn" />
    <DropdownOption value="50" valueLabel="50% giá căn" />
    <DropdownOption value="70" valueLabel="70% giá căn" />
</Dropdown>

<Dropdown name=growth title="Giá nhà tăng mỗi năm" defaultValue="4">
    <DropdownOption value="0" valueLabel="0%" />
    <DropdownOption value="2" valueLabel="2%" />
    <DropdownOption value="3" valueLabel="3%" />
    <DropdownOption value="4" valueLabel="4%" />
    <DropdownOption value="5" valueLabel="5%" />
    <DropdownOption value="6" valueLabel="6%" />
    <DropdownOption value="8" valueLabel="8%" />
</Dropdown>

</div>

Từ đầu 2026, ngân hàng bị giới hạn cho vay bất động sản. Lãi vay mua nhà hết ưu đãi lên {m[0].float_lo}-{m[0].float_hi}%/năm. Gửi tiết kiệm 12 tháng ở các ngân hàng lớn được {m[0].save_big4}%. CBRE ghi nhận giá chung cư mới ở Hà Nội quý 3 giảm {m[0].cbre_qoq}% so với quý trước. Số căn bán được giảm {m[0].cbre_sales}% so với cùng kỳ.

Bài này mình viết để cùng tính với các bạn bài toán tài chính khi mua nhà. Với giả định 1 trước hợp điển hình: 
- Thu nhập gia đình hàng tháng 50tr, chi tiêu 20tr
- Căn bds định mua là căn 2PN ở mức P25 (25% thị trường) mà ta đã tìm ra ở [bài trước](/can-nha-dau-tien) tìm ra ở {inputs.city.label}: mua **{k[0].price_t} tỷ**, thuê **{k[0].rent_t} triệu/tháng**. 
- Các biến số: *Lãi vay, vốn tự thân trước khi mua nhà, % tăng giá nhà mỗi năm* bạn có thể tùy chỉnh trong phần drop down ở đầu bài để phân tích các TH khác nhau. 


<div class="grid grid-cols-2 sm:grid-cols-4 gap-3 my-6">

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Giá căn hộ</div>
<div class="text-2xl font-semibold">{k[0].price_t} tỷ</div>
</div>

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Vốn ({k[0].down_pct_t}% căn nhà)</div>
<div class="text-2xl font-semibold">{k[0].down_t} tỷ</div>
</div>

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Nợ</div>
<div class="text-2xl font-semibold">{k[0].loan_t} tỷ</div>
</div>


<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Giá thuê tháng</div>
<div class="text-2xl font-semibold">{k[0].rent_t} tr</div>
</div>


</div>


Thông thường khi trả nợ ngân hàng sẽ có 2 cách như sau:

1. **Gốc, lãi chia đều hàng tháng**
2. **Gốc cố định, lãi giảm dần**

Để đơn giản hóa bài toán tài chính, phân tích này sẽ sử dụng phương pháp số (1) trong tính toán. Phương pháp này tính số tiền phải trả hàng tháng bằng công thức dưới đây:

<div class="my-6 text-center text-lg">
Trả mỗi tháng = <span class="inline-flex flex-col items-center align-middle mx-1">
<span class="px-2">P × r × (1 + r)<sup>n</sup></span>
<span class="w-full border-t border-base-content"></span>
<span class="px-2">(1 + r)<sup>n</sup> − 1</span>
</span>
</div>

Trong đó: **P** là số tiền vay, **r** là lãi suất mỗi tháng (lãi năm chia 12), **n** là số tháng trả góp.

Hoặc đơn giản hơn, bạn có thể để BIDV tính thay bạn bằng [công cụ này](https://bidv.com.vn/vn/premier/cong-cu-va-tien-ich/cong-cu-tinh-toan-tien-vay/!ut/p/z0/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziDQ0cLTyc_Q383N3DLAwC_Q2CvbxcvA0MnI30C7IdFQHZw3yw/). 

{#if k.length > 0}

Một vài giả định của bài phân tích bạn cần nắm trước khi bước vào phần tính toán:

<DataTable data={assumptions} rows=all>
    <Column id=item title="Thông số" />
    <Column id=val title="Giá trị" />
</DataTable>


{#if k[0].buyer_loses_more}

## Tháng đầu, người mua mất {k[0].lost1_t} triệu, gấp {k[0].lost_x} lần người thuê

{:else}

## Tháng đầu, người mua mất {k[0].lost1_t} triệu, ít hơn tiền thuê {k[0].rent_t} triệu

{/if}


<Details title="Cách tính">

- **Tiền lãi tháng đầu** = nợ × lãi tháng = {cx[0].loan} × {cx[0].rate_m}% = **{cx[0].int1} tr**.
- **Tổng trả hàng tháng** = **{cx[0].pmt} tr** ([công thức](https://www.vpbank.com.vn/bi-kip-va-chia-se/retail-story-and-tips/loans-category/cach-tinh-lai-suat-vay-ngan-hang)). Có thể tính lại bằng [công cụ của BIDV](https://bidv.com.vn/vn/premier/tinh-lai-tien-vay), chọn "Gốc, lãi chia đều hàng tháng".
- **Tiền gốc tháng đầu** = trả góp − tiền lãi = {cx[0].pmt} − {cx[0].int1} = **{cx[0].princ1} tr**.
- **Lãi tiết kiệm bỏ lỡ** = vốn tự có × lãi gửi tháng = {cx[0].down} × {cx[0].inv_m}% = **{cx[0].opp1} tr**. Lãi gửi tháng quy từ {cx[0].inv_y}%/năm theo lãi kép: (1 + {cx[0].inv_y}%)<sup>1/12</sup> − 1.
- **Người mua mất** = tiền lãi + lãi bỏ lỡ = {cx[0].int1} + {cx[0].opp1} = **{cx[0].lost1} tr**, bằng {cx[0].lost_x} lần tiền thuê {cx[0].rent} tr. Người thuê mất trọn tiền thuê.

</Details>


<BarChart
    data={month}
    x=option
    y=v
    series=kind
    seriesOrder={['Lãi vay', 'Lãi tiết kiệm bỏ lỡ', 'Gốc']}
    seriesColors={{'Lãi vay': '#c8691f', 'Lãi tiết kiệm bỏ lỡ': '#e8b48a', 'Gốc': '#236aa4'}}
    swapXY=true
    sort=false
    labels=true
    stackTotalLabel=false
    yFmt="0.0"
    yAxisTitle="triệu đồng/tháng"
    title="Một tháng tiền nhà đi đâu"
    subtitle="Tháng đầu tiên, lãi vay {k[0].rate_t}%, vốn tự có {k[0].down_pct_t}%"
/>

Trong {k[0].pmt_t} triệu trả góp, {k[0].princ1_t} triệu là tiền gốc, vẫn là của mình. Phần mất thật là {k[0].int1_t} triệu tiền lãi. Phần {k[0].opp1_t} triệu là chi phí cơ hội của việc không gửi ngân hàng {k[0].down_t} tỷ vốn ban đầu.

{#if dcmp[0].still_more}

Nâng vốn tự có từ 30% lên 70% thì phần mất tháng đầu giảm từ {dcmp[0].lost30} xuống {dcmp[0].lost70} triệu, vẫn gấp {dcmp[0].x70} lần tiền thuê: lãi vay giảm, nhưng lãi tiết kiệm bỏ lỡ tăng lên bù lại một phần.

{:else}

Nâng vốn tự có từ 30% lên 70% thì phần mất tháng đầu giảm từ {dcmp[0].lost30} xuống {dcmp[0].lost70} triệu, thấp hơn tiền thuê {k[0].rent_t} triệu: lãi vay giảm nhiều hơn phần lãi tiết kiệm bỏ lỡ tăng thêm.

{/if}

{#if k[0].total_below_cost}

## Kể cả khi giá nhà tăng {k[0].g_t}%/năm, chủ nhà chỉ lãi {k[0].total_t}%/năm, thấp hơn chi phí vốn {k[0].cap_cost_t}%

{:else}

## Giá nhà tăng {k[0].g_t}%/năm thì chủ nhà lãi {k[0].total_t}%/năm, cao hơn chi phí vốn {k[0].cap_cost_t}%

{/if}

<Details title="Cách tính">

Mọi số tính theo % giá căn mỗi năm.

- **Lãi tiền thuê** = tiền thuê một năm ÷ giá căn = {cx[0].rent} × 12 ÷ {cx[0].price_tr} = {cx[0].rent_y} ÷ {cx[0].price_tr} = **{cx[0].yield}%**.
- **Lãi do giá nhà tăng** = giá nhà tăng − bảo trì = {cx[0].g}% − {cx[0].maint}% = **{k[0].gm_t}%**. Đây là lãi trên giấy, chỉ thành tiền khi bán.
- **Chủ nhà lãi** = {cx[0].yield}% + {k[0].gm_t}% = **{k[0].total_t}%**.
- **Chi phí vốn** = lãi vay × phần vay + lãi tiết kiệm × phần vốn tự có = {cx[0].rate_y}% × {cx[0].loan_pct}% + {cx[0].inv_y}% × {cx[0].down_pct}% = {k[0].cost_loan_t}% + {k[0].cost_down_t}% = **{k[0].cap_cost_t}%**. Lãi vay chỉ tính trên phần vay, còn vốn tự có lẽ ra gửi tiết kiệm được.
- **Giá nhà phải tăng để hoà** = chi phí vốn − lãi tiền thuê + bảo trì = {k[0].cap_cost_t}% − {cx[0].yield}% + {cx[0].maint}% = **{k[0].g_simple_t}%/năm**.

</Details>

<BarChart
    data={yields}
    x=kind
    y=v
    series=part
    seriesOrder={['Tiền thuê', 'Giá nhà tăng (trừ bảo trì)', 'Lãi tiết kiệm', 'Lãi vay', 'Lãi tiết kiệm bỏ lỡ']}
    seriesColors={{'Tiền thuê': '#236aa4', 'Giá nhà tăng (trừ bảo trì)': '#9cc3e4', 'Lãi tiết kiệm': '#9a9a9a', 'Lãi vay': '#c8691f', 'Lãi tiết kiệm bỏ lỡ': '#e8b48a'}}
    swapXY=true
    sort=false
    labels=true
    yFmt="0.0"
    yAxisTitle="% giá căn mỗi năm"
    title="Một năm chủ nhà được bao nhiêu, vốn tốn bao nhiêu"
    subtitle="Giá nhà tăng {k[0].g_t}%/năm, lãi vay {k[0].rate_t}%, vốn tự có {k[0].down_pct_t}%"
/>

Riêng tiền thuê, chủ nhà chỉ thu {k[0].yield_t}% giá căn mỗi năm. Phần còn lại trông vào giá nhà tăng, mà phần đó chỉ thành tiền khi bán. Để tổng lãi bù được chi phí vốn, giá nhà phải tăng ít nhất {k[0].g_simple_t}%/năm. Đây là phép tính gọn cho một năm; mục cuối bài tính đủ {k[0].horizon} năm (lãi kép, tiền thuê và thu nhập tăng dần, phí khi mua) ra mức {even[0].g_star_t}%/năm.


### Theo quận: ở {dist_head[0].lo_d}, giá mua bằng {dist_head[0].lo_y} năm tiền thuê, ở {dist_head[0].hi_d} là {dist_head[0].hi_y} năm

<Details title="Cách tính">

- **Số năm tiền thuê** của một quận = giá mua mức 1/4 rẻ nhất của quận ÷ (tiền thuê mức 1/4 rẻ nhất của quận × 12).
- Mức chung cả thành phố: {cx[0].price_tr} ÷ ({cx[0].rent} × 12) = {cx[0].price_tr} ÷ {cx[0].rent_y} = **{cx[0].price_years} năm**. Đây cũng là nghịch đảo của lãi cho thuê {cx[0].yield}%/năm ở trên.

</Details>

<BarChart
    data={dist}
    x=district
    y=years
    series=grp
    seriesOrder={['Bằng hoặc ít năm hơn mức chung', 'Nhiều năm hơn mức chung']}
    seriesColors={{'Bằng hoặc ít năm hơn mức chung': '#236aa4', 'Nhiều năm hơn mức chung': '#c4c4c4'}}
    swapXY=true
    sort=false
    labels=true
    stackTotalLabel=false
    yFmt="0"
    yAxisTitle="số năm tiền thuê"
    title="Giá mua căn 2PN bằng bao nhiêu năm tiền thuê"
    subtitle="Căn mức 1/4 rẻ nhất, {dist_head[0].n_d} quận có từ 30 tin bán và 30 tin thuê"
>
    <ReferenceLine y={k[0].price_years_v} label="Mức chung: {k[0].price_years} năm" hideValue=true />
</BarChart>



Rule of thumb là nếu giá nhà nhỏ hơn 25 năm tiền thuê thì nên mua, còn lớn hơn 25 năm tiền thuê thì nên thuê. 

{#if k[0].buy_left_v < 0}

## Thu nhập {k[0].inc_t} triệu: thuê còn dư {k[0].rent_left_t} triệu, mua thì thiếu {k[0].buy_short_t} triệu mỗi tháng

{:else}

## Thu nhập {k[0].inc_t} triệu: thuê còn dư {k[0].rent_left_t} triệu, mua còn dư {k[0].buy_left_t} triệu mỗi tháng

{/if}

Giả sử gia đình thu nhập {k[0].inc_t} triệu/tháng, sinh hoạt {k[0].spend_t} triệu, phần dư sau tiền nhà đem gửi tiết kiệm.

<Details title="Cách tính">

- **Thuê**: còn dư = thu nhập − sinh hoạt − tiền thuê = {cx[0].inc} − {cx[0].spend} − {cx[0].rent} = **{cx[0].rent_left} tr**.
- **Mua**: tiền nhà = trả góp + bảo trì. Bảo trì = {cx[0].maint}% giá nhà mỗi năm, chia 12 = {cx[0].price_tr} × {cx[0].maint}% ÷ 12 = {cx[0].maint_m} tr. Tiền nhà = {cx[0].pmt} + {cx[0].maint_m} = {cx[0].buy_house} tr.
- Còn dư = {cx[0].inc} − {cx[0].spend} − {cx[0].buy_house} = **{cx[0].buy_left} tr**.

</Details>

<BarChart
    data={budget}
    x=option
    y=v
    series=kind
    seriesOrder={['Sinh hoạt', 'Tiền nhà', 'Còn dư']}
    seriesColors={{'Sinh hoạt': '#c4c4c4', 'Tiền nhà': '#c8691f', 'Còn dư': '#236aa4'}}
    swapXY=true
    sort=false
    labels=true
    stackTotalLabel=false
    yFmt="0.0"
    yAxisTitle="triệu đồng/tháng"
    title="Lương tháng đi về đâu?"
    subtitle="Gia đình thu nhập {k[0].inc_t} tr, sinh hoạt {k[0].spend_t} tr, năm đầu tiên"
/>


{#if k[0].buy_left_v < 0}

Ở {inputs.city.label}, gia đình này không gánh nổi cả căn rẻ nhất: trả góp xong là âm ngay năm đầu.

{:else}

{#if k[0].buy_thinner}

Bên mua dư ít hơn {k[0].left_gap_t} triệu mỗi tháng, tức là ít đệm hơn khi ốm đau, mất việc.

{:else}

Vốn tự có nhiều thì trả góp nhẹ, nhưng phần vốn đó đã thôi sinh lãi.

{/if}

{/if}

{#if end30[0].buyer_wins}

## Sau {k[0].horizon} năm, nếu nhà tăng {k[0].g_t}%/năm, người mua giàu hơn: {end30[0].buy_t} tỷ so với {end30[0].rent_t} tỷ

{:else}

## Sau {k[0].horizon} năm, nếu nhà tăng {k[0].g_t}%/năm, người thuê vẫn giàu hơn: {end30[0].rent_t} tỷ so với {end30[0].buy_t} tỷ

{/if}

<Details title="Cách tính">

Mô phỏng từng tháng trong {cx[0].horizon} năm, số dưới đây tính bằng **tỷ đồng** ở cuối năm thứ {cx[0].horizon}.

- **Mỗi tháng**, hai bên có tiền dư = thu nhập − sinh hoạt − tiền nhà, đem gửi tiết kiệm {cx[0].inv_y}%/năm và lãi nhập gốc tới cuối kỳ. Tháng nào âm thì coi như rút từ khoản đã gửi. Thu nhập tăng {cx[0].inc_g}%/năm, sinh hoạt tăng {cx[0].spend_g}%/năm.
  - Bên mua: tiền nhà = trả góp {cx[0].pmt} tr (trong {cx[0].years} năm đầu, sau đó hết) + bảo trì {cx[0].maint}%/năm tính trên giá nhà lúc đó.
  - Bên thuê: tiền thuê {cx[0].rent} tr, tăng {cx[0].rent_g}%/năm.
- **Tài sản người mua** = giá nhà lúc đó − nợ còn lại − phí mua ban đầu {cx[0].buy_cost_tr} tr (tính cả lãi lẽ ra được hưởng nếu gửi) {#if cx[0].s_buy_neg}− phần đã rút khỏi tiết kiệm{:else}+ tiền gửi tích lũy{/if}
  - Giá nhà = {cx[0].price_ty} × (1 + {cx[0].g}%)<sup>{cx[0].horizon}</sup> = {cx[0].house}
  - Tài sản = {cx[0].house} − {cx[0].debt} − {cx[0].cost} {#if cx[0].s_buy_neg}−{:else}+{/if} {cx[0].s_buy_abs} = **{cx[0].nw_buy} tỷ**
- **Tài sản người thuê** = vốn tự có {cx[0].down} tr đem gửi suốt {cx[0].horizon} năm {#if cx[0].s_rent_neg}− phần đã rút{:else}+ tiền gửi tích lũy{/if}
  - Tài sản = {cx[0].down_fv} {#if cx[0].s_rent_neg}−{:else}+{/if} {cx[0].s_rent_abs} = **{cx[0].nw_rent} tỷ**
- **Mức tăng giá hoà vốn** {even[0].g_star_t}%/năm: thử lần lượt mức tăng giá nhà từ 0% đến 15%, mỗi bước 0,25%, lấy mức thấp nhất mà tài sản người mua năm thứ {cx[0].horizon} không thua người thuê.
- **Sức mua hôm nay**: chia cho (1 + {cx[0].infl}%)<sup>{cx[0].horizon}</sup> = {cx[0].deflator}.

</Details>

<LineChart
    data={nw}
    x=year
    y=nw
    series=who
    seriesColors={{'Mua': '#236aa4', 'Thuê': '#6b6b6b'}}
    yFmt="0.0"
    xAxisTitle="Năm thứ"
    yAxisTitle="tỷ đồng"
    title="Tổng tài sản sau mỗi năm"
    subtitle="Mua: giá nhà trừ nợ còn lại, cộng tiền gửi. Thuê: tiền gửi."
/>

**Nhà phải tăng trên {even[0].g_star_t}%/năm, đều đặn {k[0].horizon} năm, người mua mới giàu hơn.** Thấp hơn, thuê thắng.

Hai điều cần nhớ:

- Chung cư {k[0].horizon} năm nữa là toà nhà cũ. Đất có thể tăng giá mãi, căn hộ thì khó.
- Người thuê chỉ thắng nếu tháng nào cũng gửi phần dư. Tiêu mất thì mua thắng xa. Trả góp thì ép người mua tiết kiệm.

Quy về sức mua hôm nay (lạm phát {k[0].infl_t}%/năm), hai con số đó chỉ còn: mua {end30[0].buy_real_t} tỷ, thuê {end30[0].rent_real_t} tỷ.


---

Túm lại, thuê nhà có phải ném tiền qua cửa sổ không?

{#if k[0].buyer_loses_more}

Ở lãi vay {k[0].rate_t}%, không. Mỗi tháng, người mua mới là người mất nhiều hơn.

{:else}

Ở lãi vay {k[0].rate_t}% và vốn tự có {k[0].down_pct_t}%, đúng một phần: tháng đầu người thuê mất nhiều hơn.

{/if}

Nhưng mua nhà cũng không phải ném tiền, mà là một ván cược vào giá nhà.

Còn những thứ bảng tính không đo được: không bị chủ nhà lấy lại nhà, được khoan tường không cần xin phép.

Nên chọn lãi vay ngân hàng báo cho bạn **sau ưu đãi** và mức tăng giá nhà bạn thật sự tin, rồi xem biểu đồ cuối. Thấy đáng thì gồng mua. Chưa thì cứ thuê, gửi đều phần dư, và đừng thấy có lỗi mỗi lần chuyển tiền nhà.

Còn mình, vẫn đang đi thuê, và giờ thì biết rõ tiền thuê đang mua được gì.

{/if}

---

**Cách tính.** Căn mua và căn thuê: chung cư 2PN từ 50m², mức 1/4 rẻ nhất (phân vị 25) của từng thành phố, từng quận. Trả góp đều trong {k[0].years} năm, lãi cố định ở mức sau ưu đãi. Mô phỏng {k[0].horizon} năm: thu nhập {k[0].inc_t} tr tăng {k[0].inc_g_t}%/năm, sinh hoạt {k[0].spend_t} tr tăng {k[0].spend_g_t}%/năm, tiền thuê tăng {k[0].rent_g_t}%/năm; người mua trả thêm phí mua {k[0].buy_cost_t}% giá căn và bảo trì {k[0].maint_t}% giá nhà mỗi năm; tiền dư hai bên gửi tiết kiệm lãi {k[0].save_t}%/năm (Big4, 12 tháng), đầu tư lãi cao hơn thì phía thuê càng lợi. Không tính thuế, phí quản lý, sửa nhà lớn, lãi suất đổi giữa chừng.

**Nguồn và hạn chế.** Giá rao bán và giá rao thuê căn hộ chung cư trên batdongsan.com.vn, kỳ {latest[0].label}. Đây là **giá rao, không phải giá giao dịch**. Căn thuê ở mức 1/4 rẻ nhất có thể nhỏ hơn căn mua tương ứng (căn 2PN cho thuê có diện tích trung vị khoảng {k[0].rent_area}m²). Dữ liệu tin rao của mình mới có vài kỳ, chưa đủ để nói giá đang lên hay xuống; số giảm giá ở đầu bài là của CBRE. Địa giới theo trước sáp nhập.

Số liệu thị trường: lãi vay mua nhà theo khảo sát DXS-FERI tháng 9/2026 ([Vietnamnet](https://vietnamnet.vn/vay-mua-nha-nam-2026-lai-suat-cao-dieu-kien-con-ngat-ngheo-hon-2487612.html)); lãi tiết kiệm tháng 10/2026 ([BankerPro](https://bankerpro.com.vn/tin-tuc/lai-suat-tiet-kiem-dau-thang-10-2026), [Vietnamnet](https://vietnamnet.vn/lai-suat-ngan-hang-hom-nay-5-10-2026-ngan-hang-dau-tien-tang-lai-suat-2561678.html)); giá và giao dịch chung cư Hà Nội quý 3/2026 theo CBRE ([Báo Pháp luật](https://doanhnhan.baophapluat.vn/nguon-cung-can-ho-ha-noi-quy-iii-2026-giam-40-thanh-khoan-di-xuong.html)); giới hạn tín dụng bất động sản 2026 ([Thời báo Tài chính](https://thoibaotaichinhvietnam.vn/tang-truong-tin-dung-2026-gioi-han-van-bat-dong-san-ngan-hang-vuot-rao-se-bi-tru-room-190385.html)). Mã nguồn: [scrape-batdongsan-data](https://github.com/DataSpi/scrape-batdongsan-data) (pipeline) và [scrape-bds-rp-evidence](https://github.com/DataSpi/scrape-bds-rp-evidence) (trang này).
