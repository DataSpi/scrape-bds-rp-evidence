---
title: Căn nhà đầu tiên?
---

```sql latest
select e.period, p.label
from bds_real.cc_entry e join bds_real.periods p using (period)
order by e.period desc limit 1
```

```sql prev
select e.period, p.label
from bds_real.cc_entry e join bds_real.periods p using (period)
where e.period < (select period from ${latest})
order by e.period desc limit 1
```

```sql seg
select segment, n, n_district,
  printf('%.2f', p10_ty) as p10, printf('%.2f', p25_ty) as p25, printf('%.2f', p50_ty) as p50,
  cast(area_entry as int) as area_entry,
  replace(format('{:,}', cast(n as bigint)), ',', '.') as n_txt
from bds_real.cc_entry
where period = (select period from ${latest}) and city = '${inputs.city.value}'
order by segment desc
```

```sql gap
select printf('%.2f', max(case when segment = '2PN' then p25_ty end) - max(case when segment = '1PN' then p25_ty end)) as save_ty,
  max(case when segment = '2PN' then area_entry end) - max(case when segment = '1PN' then area_entry end) as lose_m2
from bds_real.cc_entry
where period = (select period from ${latest}) and city = '${inputs.city.value}'
```

```sql hist
-- tô các cột nằm dưới trung vị (p50) của chính thành phố đang chọn
with c as (
  select p50_ty from bds_real.cc_entry
  where period = (select period from ${latest}) and city = '${inputs.city.value}' and segment = '2PN'
)
select case when h.bin_lo >= 8 then '8+' else printf('%.1f', h.bin_lo) end as bin,
  h.bin_lo, round(100.0 * h.n / sum(h.n) over (), 1) as pct,
  case when h.bin_lo < c.p50_ty then 'Nửa rẻ hơn' else 'Nửa đắt hơn' end as grp
from bds_real.cc_entry_hist h, c
where h.period = (select period from ${latest}) and h.city = '${inputs.city.value}' and h.segment = '2PN'
order by h.bin_lo
```

```sql dist
with c as (
  select p25_ty as city_p25 from bds_real.cc_entry
  where period = (select period from ${latest}) and city = '${inputs.city.value}' and segment = '2PN'
)
select d.district, d.p25_ty, d.p50_ty, d.n,
  case when d.p25_ty <= c.city_p25 then 'Bằng hoặc thấp hơn mức chung' else 'Cao hơn mức chung' end as grp
from bds_real.cc_entry_district d, c
where d.period = (select period from ${latest}) and d.city = '${inputs.city.value}' and d.segment = '2PN'
order by d.p25_ty
```

```sql dist_head
with d as (select * from ${dist}),
c as (
  select p25_ty from bds_real.cc_entry
  where period = (select period from ${latest}) and city = '${inputs.city.value}' and segment = '2PN'
)
select
  (select string_agg(district, ', ' order by p25_ty) from (select * from d order by p25_ty limit 3)) as top3,
  (select printf('%.2f', min(p25_ty)) from d) as min_p25,
  (select count(*) from d) as n_d,
  (select count(*) from d where p25_ty <= (select p25_ty from c)) as n_under
```

```sql trend
with e as (
  select p.label, e.* from bds_real.cc_entry e join bds_real.periods p using (period)
  where e.city = '${inputs.city.value}' and e.segment = '2PN'
)
select label, period, 1 as k, '10% căn rẻ nhất' as name, p10_ty as v from e
union all select label, period, 2, '25% căn rẻ nhất', p25_ty from e
union all select label, period, 3, 'P50 – Trung vị', p50_ty from e
order by period, k
```

```sql cmp
with c as (select * from bds_real.cc_entry where period = (select period from ${latest}) and city = '${inputs.city.value}' and segment = '2PN'),
p as (select * from bds_real.cc_entry where period = (select period from ${prev}) and city = '${inputs.city.value}' and segment = '2PN')
select
  printf('%+.1f%%', 100.0 * (c.p25_ty / p.p25_ty - 1)) as p25_chg,
  printf('%+.0f%%', 100.0 * (c.n * 1.0 / p.n - 1)) as n_chg,
  abs(c.n * 1.0 / p.n - 1) > 0.2 as sample_shift,
  p.n_district as nd_p, c.n_district as nd_c
from c, p
```

<Dropdown name=city title="Thành phố" defaultValue="Hồ Chí Minh">
    <DropdownOption value="Hồ Chí Minh" valueLabel="TP.HCM" />
    <DropdownOption value="Hà Nội" valueLabel="Hà Nội" />
</Dropdown>

Nếu bạn cũng đang ở tuổi 2x, mỗi tháng cố để dành một ít và thỉnh thoảng lại mở app ngân hàng ra nhẩm "còn bao lâu nữa", thì trang này viết cho bạn.

Thông thường, khi đọc tin bds bạn sẽ chỉ bắt được con số giá trung bình. Mà số TB thì tính ra vô thưởng vô phạt, nó tính vào đó cả những căn penhouse, căn hộ view sông quận trung tâm giá trên trời, những căn mà cá là nếu có tiền mua thì bạn đã chẳng đọc bài này. Mình viết bài này mong giúp các bạn trả lời một câu hỏi rất đơn giản: **Không có tiền mà vẫn muốn mua được nhà thì tìm ở đâu?**

Vậy nên ở đây mình chỉ nhìn vào phần đáy của thị trường, gồm những căn chung cư đủ rộng để sống chứ không chỉ để ngủ. Studio và căn siêu nhỏ không tính. Số liệu là giá rao trên batdongsan.com.vn kỳ {latest[0].label}.

{#if seg.length > 0}

<div class="grid grid-cols-2 sm:grid-cols-4 gap-3 my-6">

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">1/4 căn 2PN rao dưới</div>
<div class="text-2xl font-semibold text-primary">{seg[0].p25} tỷ</div>
</div>

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">1/10 căn 2PN rao dưới</div>
<div class="text-2xl font-semibold">{seg[0].p10} tỷ</div>
</div>

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">1/4 căn 1PN rao dưới</div>
<div class="text-2xl font-semibold">{seg[1].p25} tỷ</div>
</div>

<div class="rounded-lg border border-base-300 p-3">
<div class="text-xs text-base-content-muted">Căn 2PN giá đầu vào rộng khoảng</div>
<div class="text-2xl font-semibold">{seg[0].area_entry} m²</div>
</div>

</div>

**Ở {inputs.city.label}, một căn 2PN "sống được" bắt đầu từ khoảng {seg[0].p25} tỷ.** Cứ 4 căn 2PN từ 50m² trở lên thì có 1 căn rao dưới mức đó.

Có thể bạn sẽ hỏi: sao không lấy luôn căn rẻ nhất cho nhanh? Ban đầu mình cũng định làm thế. Nhưng lúc lọc số, mình thấy đáy của một trang rao tin là chỗ khá kì cục. Ở đó có tin mồi rao giá thấp chỉ để có người gọi tới, có tin gõ nhầm một số 0, có căn chưa có sổ, có nhà ở xã hội mà không phải ai cũng đủ điều kiện mua. Xuống tới nhóm 10% rẻ nhất, dưới {seg[0].p10} tỷ, mấy căn như vậy đã bắt đầu lẫn vào. Mức 1/4 thì khác. Ở đó vẫn còn hàng thật, và đủ nhiều để bạn có căn mà đi xem, mà mặc cả.

## Một nửa số căn 2PN rao dưới {seg[0].p50} tỷ

<BarChart
    data={hist}
    x=bin
    y=pct
    series=grp
    seriesOrder={['Nửa rẻ hơn', 'Nửa đắt hơn']}
    seriesColors={{'Nửa rẻ hơn': '#236aa4', 'Nửa đắt hơn': '#c4c4c4'}}
    sort=false
    yFmt="0.0"
    xAxisTitle="Giá rao từ (tỷ đồng)"
    yAxisTitle="% số căn 2PN"
    title="Tỷ trọng căn 2PN (từ 50m²) theo khoảng giá"
/>

Cột xanh là nửa rẻ hơn của thị trường, các căn rao dưới {seg[0].p50} tỷ. Mỗi cột rộng 0,5 tỷ, nhãn là mốc đầu (cột "3.0" là từ 3 đến dưới 3,5 tỷ). Cột "8+" gộp mọi căn từ 8 tỷ trở lên.

## Căn 2PN rẻ nhất tập trung ở {dist_head[0].top3}

<BarChart
    data={dist}
    x=district
    y=p25_ty
    series=grp
    seriesOrder={['Bằng hoặc thấp hơn mức chung', 'Cao hơn mức chung']}
    seriesColors={{'Bằng hoặc thấp hơn mức chung': '#236aa4', 'Cao hơn mức chung': '#c4c4c4'}}
    swapXY=true
    sort=false
    labels=true
    stackTotalLabel=false
    yFmt="0.00"
    yAxisTitle="tỷ đồng"
    title="Phân vị 25 (P25) – Giá rao 2PN"
    subtitle="25% rẻ nhất"
/>

**{dist_head[0].n_under}/{dist_head[0].n_d} quận (cột xanh) có giá đầu vào bằng hoặc thấp hơn mức chung của thành phố ({seg[0].p25} tỷ).**

Nhìn biểu đồ này mình hay nghĩ tới chuyện đi làm mỗi sáng. Quận càng ở trên càng rẻ, nhưng thường cũng là quận bạn phải dậy sớm hơn, kẹt xe lâu hơn mới tới chỗ làm. Mỗi ngày thêm 30 phút ngồi trên xe có đáng để bớt được một tỷ không? Câu này mỗi người một đáp án, và thành thật mà nói, số liệu không trả lời thay bạn được.

Chỉ tính quận có từ 30 tin 2PN trở lên. Quận ít tin hơn thì vài căn lẻ là đủ kéo con số lệch hẳn.

## Lùi xuống 1PN tiết kiệm được khoảng {gap[0].save_ty} tỷ, nhưng mất khoảng {gap[0].lose_m2} m²

<DataTable data={seg} rows=all>
    <Column id=segment title="Loại căn" />
    <Column id=p10 title="10% rẻ nhất dưới (tỷ)" align=right />
    <Column id=p25 title="25% rẻ nhất dưới (tỷ)" align=right />
    <Column id=p50 title="Trung vị (tỷ)" align=right />
    <Column id=area_entry title="Diện tích nhóm rẻ (m²)" align=right />
    <Column id=n_txt title="Số tin" align=right />
</DataTable>

"Diện tích nhóm rẻ" là diện tích trung vị của 25% căn rẻ nhất, tức là với số tiền đầu vào, căn bạn mua được thường rộng chừng đó.

Bớt một phòng ngủ là cách nhanh nhất để mục tiêu bớt xa. Mình không nghĩ đó là lựa chọn sai, nhất là khi bạn đang ở một mình hoặc mới về chung nhà với ai đó. Có điều nên nghĩ trước một chút: nếu vài năm nữa nhà có thêm người, căn 1PN gần như chắc chắn phải bán đi để đổi căn lớn hơn. Lại thêm một lần phí giao dịch, thêm một lần đi tìm nhà. Rẻ hôm nay, có khi lại là đắt về sau.

{/if}

{#if prev.length > 0 && cmp.length > 0}

## So với {prev[0].label}: giá đầu vào căn 2PN {cmp[0].p25_chg}

<LineChart
    data={trend}
    x=label
    y=v
    series=name
    sort=false
    markers=true
    yFmt="0.00"
    yAxisTitle="tỷ đồng"
    title="Giá căn 2PN qua các kỳ"
/>

Con số trên là thay đổi của mức 1/4. Số tin 2PN thay đổi {cmp[0].n_chg}, số quận có tin là {cmp[0].nd_p} kỳ trước và {cmp[0].nd_c} kỳ này.

{#if cmp[0].sample_shift}

> **Khoan vội mừng (hoặc vội lo).** Số tin giữa hai kỳ chênh hơn 20%. Mình là người cào bộ số này nên mình biết: mẫu đổi nhiều như vậy thì giá đổi có thể chỉ vì kỳ này cào được thêm (hoặc mất) vài dự án, vài quận, chứ chưa chắc thị trường đã đổi. Hai kỳ là quá ít để nói giá đang lên hay xuống. Cho mình thêm vài kỳ nữa nhé.

{/if}

{/if}

{#if seg.length > 0}

---

Túm lại, nếu chỉ nhớ một thứ từ trang này thì nhớ giúp mình con số này: **{seg[0].p25} tỷ cho căn 2PN, {seg[1].p25} tỷ cho căn 1PN** ở {inputs.city.label}.

Nó không phải để làm bạn nản. Nó là cái mốc. Mốc để biết mình đang đứng cách căn nhà đầu tiên bao xa, và mốc để so khi một ngày nào đó bạn thật sự đi xem nhà. Gặp căn nào rao thấp hơn hẳn mức đó thì cứ hỏi cho ra lý do trước, rồi hãy mừng.

Đường còn dài. Nhưng biết mình đang đi tới đâu thì đi đỡ mệt hơn nhiều.

{/if}

---

**Cách đọc số.** "Sống được" ở đây là căn chung cư 1PN từ 35m² hoặc 2PN từ 50m². Tin không ghi số phòng ngủ hoặc diện tích sẽ bị loại. "1/4 căn rao dưới X" là phân vị 25 (P25) của giá rao. Dùng phân vị thay cho giá thấp nhất vì giá thấp nhất gần như luôn là tin lỗi hoặc tin mồi.

**Nguồn và hạn chế.** Tin rao bán căn hộ chung cư trên batdongsan.com.vn còn hiệu lực trong các đợt cào của kỳ {latest[0].label}. Đây là **giá rao, không phải giá giao dịch**: giá chốt thường thấp hơn, và tin có thể trùng hoặc đã bán. Không tách được nhà ở xã hội, căn chưa có sổ hay căn bán kèm hợp đồng thuê. Địa giới theo trước sáp nhập. Mã nguồn: [scrape-batdongsan-data](https://github.com/DataSpi/scrape-batdongsan-data) (pipeline) và [scrape-bds-rp-evidence](https://github.com/DataSpi/scrape-bds-rp-evidence) (trang này).
