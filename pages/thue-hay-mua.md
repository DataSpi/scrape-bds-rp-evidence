---
title: Thuê tiếp hay gồng mua?
---

```sql latest
-- kỳ mới nhất có cả dữ liệu mua lẫn thuê
select e.period, p.label
from bds_real.cc_entry e join bds_real.periods p using (period)
where e.period in (select period from bds_real.rent_entry)
order by e.period desc limit 1
```

```sql assume
-- giả định vay: lãi suất do người đọc chọn, vay 70% giá căn, trả đều trong 25 năm
select cast('${inputs.rate.value}' as double) / 100 as rate, 0.7 as ltv, 25 as years
```

```sql base
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
  select b.p25_ty as price_ty, r.p25_rent as rent, r.area_p50 as rent_area,
    b.p25_ty * 1000 * p.ltv as loan, b.p25_ty * 1000 * (1 - p.ltv) as down,
    p.rate, p.ltv, p.years, p.rate / 12 as rm, p.years * 12 as nm
  from b, r, p
)
-- đơn vị tiền: triệu đồng
select *,
  loan * rm * pow(1 + rm, nm) / (pow(1 + rm, nm) - 1) as pmt,
  loan * rm as int1
from c
```

```sql k
select
  printf('%.2f', price_ty) as price_t,
  printf('%.0f', rent) as rent_t,
  rent as rent_v,
  printf('%.1f', pmt) as pmt_t,
  printf('%.1f', int1) as int1_t,
  printf('%.1f', pmt - int1) as princ1_t,
  printf('%.1f', pmt / rent) as pmt_x,
  printf('%.1f', int1 / rent) as int_x,
  int1 > rent as buyer_loses_more,
  printf('%.2f', down / 1000) as down_t,
  printf('%.0f', down / (rent * 12)) as down_years,
  printf('%.0f', price_ty * 1000 / (rent * 12)) as price_years,
  price_ty * 1000 / (rent * 12) as price_years_v,
  printf('%.1f', rent * 12 / (price_ty * 1000) * 100) as yield_t,
  printf('%.0f', rate * 100) as rate_t,
  printf('%.0f', ltv * 100) as ltv_t,
  printf('%.0f', (1 - ltv) * 100) as down_pct,
  cast(years as int) as years,
  cast(rent_area as int) as rent_area
from ${base}
```

```sql month
-- tháng đầu tiên: tiền đi đâu
select 'Thuê' as option, 1 as o, 'Tiền mất đi (thuê, lãi)' as kind, rent as v from ${base}
union all select 'Mua', 2, 'Tiền mất đi (thuê, lãi)', int1 from ${base}
union all select 'Mua', 2, 'Tiền thành của mình (gốc)', pmt - int1 from ${base}
order by o
```

```sql amort
-- tiền lãi trung bình mỗi tháng, theo từng năm của khoản vay
with b as (select * from ${base}),
m as (select range as month from range(1, (select cast(nm as int) from b) + 1))
select cast(cast(ceil(m.month / 12.0) as int) as varchar) as year, cast(ceil(m.month / 12.0) as int) as year_n,
  round(avg(b.loan * b.rm * (pow(1 + b.rm, b.nm) - pow(1 + b.rm, m.month - 1)) / (pow(1 + b.rm, b.nm) - 1)), 1) as interest
from m, b
group by 1, 2 order by 2
```

```sql cross
select cast(min(a.year_n) as varchar) as year from ${amort} a, ${base} b where a.interest < b.rent
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
city as (select price_ty * 1000 / (rent * 12) as city_years from ${base})
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

<Dropdown name=rate title="Lãi suất vay" defaultValue="12">
    <DropdownOption value="9" valueLabel="9%/năm" />
    <DropdownOption value="10" valueLabel="10%/năm" />
    <DropdownOption value="11" valueLabel="11%/năm" />
    <DropdownOption value="12" valueLabel="12%/năm" />
    <DropdownOption value="13" valueLabel="13%/năm" />
    <DropdownOption value="14" valueLabel="14%/năm" />
    <DropdownOption value="15" valueLabel="15%/năm" />
</Dropdown>

</div>

Cuối tháng, bấm chuyển khoản tiền nhà cho chủ nhà, nhìn số dư tụt xuống một khúc. Rồi trong đầu lại vang lên câu quen thuộc mà chắc ai đi thuê cũng từng nghe ít nhất một lần, từ bố mẹ, họ hàng, hoặc một người bạn vừa nhận nhà: *"Thuê nhà là ném tiền qua cửa sổ."*

Câu đó đúng không? Mình không muốn trả lời bằng cảm giác, nên lấy luôn số liệu ra tính. Bài trước mình đã tìm ra [căn 2PN "sống được" rẻ nhất](/can-dau-tien) giá bao nhiêu. Bài này đặt nó cạnh một căn 2PN tương đương đang cho thuê, rồi xem mỗi tháng tiền của bạn thật sự đi đâu.

{#if k.length > 0}

<div class="grid grid-cols-2 sm:grid-cols-4 gap-3 my-6">

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Thuê căn 2PN, mỗi tháng</div>
<div class="text-2xl font-semibold">{k[0].rent_t} tr</div>
</div>

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Mua căn 2PN, trả góp mỗi tháng</div>
<div class="text-2xl font-semibold">{k[0].pmt_t} tr</div>
</div>

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Tiền phải có sẵn ({k[0].down_pct}% giá căn)</div>
<div class="text-2xl font-semibold">{k[0].down_t} tỷ</div>
</div>

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Giá mua bằng</div>
<div class="text-2xl font-semibold">{k[0].price_years} năm thuê</div>
</div>

</div>

Mình so căn ở mức "1/4 rẻ nhất" cho cả hai bên: căn mua giá {k[0].price_t} tỷ, căn thuê {k[0].rent_t} triệu/tháng, đều là 2PN từ 50m² trở lên ở {inputs.city.label}. Phần mua giả định vay {k[0].ltv_t}% giá căn, trả đều trong {k[0].years} năm, lãi suất {k[0].rate_t}%/năm. Lãi suất bạn đổi được ở ô phía trên, cả bài sẽ tính lại theo.

## Tháng đầu tiên, riêng tiền lãi đã gấp {k[0].int_x} lần tiền thuê

<BarChart
    data={month}
    x=option
    y=v
    series=kind
    seriesOrder={['Tiền mất đi (thuê, lãi)', 'Tiền thành của mình (gốc)']}
    seriesColors={{'Tiền mất đi (thuê, lãi)': '#c8691f', 'Tiền thành của mình (gốc)': '#236aa4'}}
    swapXY=true
    sort=false
    labels=true
    stackTotalLabel=false
    yFmt="0.0"
    yAxisTitle="triệu đồng/tháng"
    title="Một tháng tiền nhà đi đâu"
    subtitle="Căn 2PN mức 1/4 rẻ nhất, tháng đầu tiên"
/>

Nhưng khoan, technically bạn không mất hết {k[0].pmt_t} triệu đó. Trong đó {k[0].princ1_t} triệu là tiền gốc, tức là bạn đang tự để dành vào chính căn nhà của mình. Phần thật sự mất đi là tiền lãi trả ngân hàng: {k[0].int1_t} triệu. Bên thuê, mất đi là cả {k[0].rent_t} triệu tiền nhà.

Vậy nên câu hỏi công bằng không phải "trả góp hay trả tiền thuê", mà là **"trả lãi hay trả tiền thuê"**.

{#if k[0].buyer_loses_more}

Và ở mức lãi {k[0].rate_t}%, tháng đầu tiên người mua mới là người "ném qua cửa sổ" nhiều hơn. Hơi trớ trêu nhỉ.

{:else}

Ở mức lãi {k[0].rate_t}%, tiền lãi tháng đầu đã thấp hơn tiền thuê, tức là mua đang "đỡ mất" hơn thuê ngay từ đầu.

{/if}

## Phải tới năm thứ {cross[0].year}, tiền lãi mỗi tháng mới thấp hơn tiền thuê

<LineChart
    data={amort}
    x=year
    y=interest
    xType=category
    lineColor="#c8691f"
    yFmt="0"
    xAxisTitle="Năm thứ"
    yAxisTitle="triệu đồng/tháng"
    title="Tiền lãi trung bình mỗi tháng, theo từng năm của khoản vay"
>
    <ReferenceLine y={k[0].rent_v} label="Tiền thuê: {k[0].rent_t} tr/tháng" hideValue=true />
    <ReferenceLine x={cross[0].year} label="Năm {cross[0].year}" hideValue=true />
</LineChart>

Tiền lãi giảm dần vì nợ gốc giảm dần. Nhưng nó giảm chậm hơn mình tưởng nhiều. Mấy năm đầu, phần lớn tiền trả góp chảy vào túi ngân hàng chứ chưa vào căn nhà.

Có một chỗ mình đang tính thiên về phía người thuê: đường tiền thuê ở đây đứng yên, trong khi ngoài đời chủ nhà sẽ tăng giá theo năm. Tiền thuê càng tăng thì điểm gặp nhau càng đến sớm. Ngược lại, mình cũng đang bỏ qua một chi phí của người mua: {k[0].down_t} tỷ tiền có sẵn, nếu không đổ vào nhà mà để gửi tiết kiệm thì cũng sinh lãi mỗi tháng. Hai thứ này kéo về hai phía, nên đừng coi năm thứ {cross[0].year} là một mốc chính xác. Nó chỉ để bạn thấy con đường này dài cỡ nào thôi.

## Ở {dist_head[0].lo_d}, giá mua bằng {dist_head[0].lo_y} năm tiền thuê, ở {dist_head[0].hi_d} là {dist_head[0].hi_y} năm

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
    subtitle="Căn mức 1/4 rẻ nhất của từng quận, so với mức chung {k[0].price_years} năm của thành phố"
>
    <ReferenceLine y={k[0].price_years_v} label="Mức chung: {k[0].price_years} năm" hideValue=true />
</BarChart>

Cách đọc biểu đồ này đơn giản lắm: nếu đem tiền thuê từng tháng gom lại, bao nhiêu năm thì đủ mua đứt căn đó. Số năm càng ít, mua càng "đỡ thiệt" so với thuê. Số năm càng nhiều thì đi thuê càng hời.

Ở mức chung của thành phố, tiền thuê một năm chỉ bằng khoảng {k[0].yield_t}% giá căn. Con số đó thấp hơn hẳn lãi suất vay {k[0].rate_t}%. Nói theo kiểu dân tài chính thì căn nhà "cho thuê" không đủ bù tiền vay để mua nó. Đó là lý do tại sao ở hầu hết các quận, nếu chỉ nhìn dòng tiền mỗi tháng, thuê rẻ hơn mua.

Chỉ tính quận có từ 30 tin bán và 30 tin thuê căn 2PN trở lên ({dist_head[0].n_d} quận).

---

Túm lại, thuê nhà có phải ném tiền qua cửa sổ không?

{#if k[0].buyer_loses_more}

Nếu chỉ tính tiền, thì ở thời điểm này, với mức lãi {k[0].rate_t}%, người mua mới là người ném nhiều hơn, ít nhất cho tới năm thứ {cross[0].year} của khoản vay. Có thể câu nói kia từng đúng ở một thời nào đó. Còn bây giờ thì nó cần được tính lại.

{:else}

Với mức lãi {k[0].rate_t}%, câu nói kia đúng: tiền thuê đang "mất" nhiều hơn tiền lãi ngay từ tháng đầu.

{/if}

Nhưng mình cũng không định kết bằng câu "đừng mua". Vì có những thứ không nằm trong bảng tính. Không phải nghe tin chủ nhà muốn lấy lại nhà đúng lúc mình bận nhất. Không phải đóng thùng chuyển nhà thêm lần nữa. Được khoan một cái lỗ lên tường mà không phải xin phép ai. Và cả cái lợi rất thật của tiền gốc: một khoản tiết kiệm bắt buộc, kiểu tiết kiệm mà ít ai trong chúng ta tự làm được nếu không có ngân hàng đứng sau nhắc mỗi tháng.

Mấy thứ đó đáng bao nhiêu tiền thì mỗi người một giá, mình không định giá hộ ai được. Mình chỉ mong lúc bạn quyết, bạn biết mình đang trả bao nhiêu cho chúng.

Nên thử thế này: chọn lại lãi suất ở đầu trang bằng đúng mức ngân hàng báo cho bạn **sau thời gian ưu đãi**, rồi đọc lại con số tiền lãi tháng đầu. Nếu bạn vẫn thấy nó đáng, gồng mua đi. Còn nếu chưa, cứ thuê tiếp, và đừng để ai làm bạn thấy có lỗi vì mỗi cuối tháng bấm chuyển khoản tiền nhà.

{/if}

---

**Cách tính.** Căn mua và căn thuê đều là căn chung cư 2PN từ 50m², lấy ở mức 1/4 rẻ nhất (phân vị 25) của từng thành phố, từng quận. Trả góp tính theo kiểu trả đều hằng tháng (gốc + lãi cố định), lãi suất giữ nguyên suốt khoản vay. Thực tế, khoản vay mua nhà thường có lãi ưu đãi trong một đến hai năm đầu rồi chuyển sang thả nổi. Báo chí tháng 10/2026 ghi nhận lãi thả nổi sau ưu đãi phổ biến khoảng 12-15%/năm, nên trang mặc định chọn 12%. Không tính phí công chứng, thuế, phí quản lý, tiền sửa nhà, cũng không tính giá nhà tăng hay giảm.

**Nguồn và hạn chế.** Giá rao bán và giá rao thuê căn hộ chung cư trên batdongsan.com.vn, kỳ {latest[0].label}. Đây là **giá rao, không phải giá giao dịch**. Căn đang cho thuê ở mức 1/4 rẻ nhất không chắc rộng bằng căn đang bán ở mức tương ứng: căn 2PN cho thuê có diện tích trung vị khoảng {k[0].rent_area}m², nhưng nhóm rẻ nhất có thể nhỏ hơn. Địa giới theo trước sáp nhập. Mã nguồn: [scrape-batdongsan-data](https://github.com/DataSpi/scrape-batdongsan-data) (pipeline) và [scrape-bds-rp-evidence](https://github.com/DataSpi/scrape-bds-rp-evidence) (trang này).
