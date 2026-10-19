---
title: Thị trường nhà ở HCM & HN
---

```sql cc
with lp as (select max(period) as period from bds_real.cc_meta)
select p.label, 'mua/chung-cu/' || p.period as link,
  printf('%.1f', max(case when k.city = 'Hồ Chí Minh' then k.avg_price_1m2 end)) as hcm,
  printf('%.1f', max(case when k.city = 'Hà Nội' then k.avg_price_1m2 end)) as hn,
  replace(format('{:,}', cast(sum(k.n) as bigint)), ',', '.') as n_txt
from bds_real.cc_city_kpi k
join lp using (period)
join bds_real.periods p using (period)
group by 1, 2
```

```sql nd
with lp as (select max(period) as period from bds_real.nd_meta)
select p.label, 'mua/nha-dat/' || p.period as link,
  printf('%.1f', max(case when k.city = 'Hồ Chí Minh' and k.type = 'nhà riêng' then k.avg_price_1m2 end)) as hcm,
  printf('%.1f', max(case when k.city = 'Hà Nội' and k.type = 'nhà riêng' then k.avg_price_1m2 end)) as hn,
  replace(format('{:,}', cast(sum(k.n) as bigint)), ',', '.') as n_txt
from bds_real.nd_type_kpi k
join lp using (period)
join bds_real.periods p using (period)
group by 1, 2
```

```sql rent
with lp as (select max(period) as period from bds_real.rent_meta)
select p.label, 'thue/chung-cu/' || p.period as link,
  printf('%.1f', max(case when k.city = 'Hồ Chí Minh' then k.avg_rent end)) as hcm,
  printf('%.1f', max(case when k.city = 'Hà Nội' then k.avg_rent end)) as hn,
  replace(format('{:,}', cast(sum(k.n) as bigint)), ',', '.') as n_txt
from bds_real.rent_city_kpi k
join lp using (period)
join bds_real.periods p using (period)
group by 1, 2
```

```sql latest
select label from bds_real.periods order by period desc limit 1
```

Giá nhà rao bán và cho thuê ở HCM & HN, cào từ batdongsan.com.vn và cập nhật theo kỳ. Đây là phần số liệu đi kèm series [phân tích BĐS trên Substack](https://spyno.substack.com) của mình. Mỗi mục bên dưới có danh sách các kỳ báo cáo, bấm vào một kỳ để đọc bài phân tích chi tiết. Từ kỳ thứ hai trở đi, mỗi bài có thêm mục so sánh với kỳ trước.

# Giá mua

<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 my-4">

<a href="/mua/chung-cu" class="block rounded-lg border border-base-300 p-4 hover:bg-base-200 no-underline">
<div class="text-lg font-semibold">Chung cư</div>
<div class="text-sm text-base-content-muted">Giá/m² trung bình, kỳ {cc[0].label}</div>
<div class="mt-2">HCM <b>{cc[0].hcm}</b> · HN <b>{cc[0].hn}</b> tr/m²</div>
<div class="text-sm text-base-content-muted mt-1">{cc[0].n_txt} tin có giá</div>
</a>

<a href="/mua/nha-dat" class="block rounded-lg border border-base-300 p-4 hover:bg-base-200 no-underline">
<div class="text-lg font-semibold">Nhà đất</div>
<div class="text-sm text-base-content-muted">Nhà riêng, giá/m² trung bình, kỳ {nd[0].label}</div>
<div class="mt-2">HCM <b>{nd[0].hcm}</b> · HN <b>{nd[0].hn}</b> tr/m²</div>
<div class="text-sm text-base-content-muted mt-1">{nd[0].n_txt} tin có giá, 4 loại hình</div>
</a>

</div>

# Giá thuê

<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 my-4">

<a href="/thue/chung-cu" class="block rounded-lg border border-base-300 p-4 hover:bg-base-200 no-underline">
<div class="text-lg font-semibold">Chung cư</div>
<div class="text-sm text-base-content-muted">Giá thuê trung bình, kỳ {rent[0].label}</div>
<div class="mt-2">HCM <b>{rent[0].hcm}</b> · HN <b>{rent[0].hn}</b> tr/tháng</div>
<div class="text-sm text-base-content-muted mt-1">{rent[0].n_txt} tin</div>
</a>

<a href="/thue/nha-dat" class="block rounded-lg border border-dashed border-base-300 p-4 hover:bg-base-200 no-underline">
<div class="text-lg font-semibold">Nhà đất</div>
<div class="text-sm text-base-content-muted">Nhà riêng, nhà mặt phố, phòng trọ...</div>
<div class="mt-2"><b>Sắp có</b></div>
<div class="text-sm text-base-content-muted mt-1">Pipeline chưa cào loại hình này</div>
</a>

</div>

{#if nd[0].label !== latest[0].label}

> Kỳ {latest[0].label} pipeline chưa cào nhà đất rao bán, nên thẻ nhà đất đang hiện kỳ {nd[0].label}.

{/if}

---

**Nguồn:** batdongsan.com.vn. **Hạn chế:** đây là giá rao, không phải giá giao dịch; tin rao có thể trùng hoặc không còn hiệu lực; địa giới theo trước sáp nhập. Mã nguồn: [scrape-batdongsan-data](https://github.com/DataSpi/scrape-batdongsan-data) (pipeline) và [scrape-bds-rp-evidence](https://github.com/DataSpi/scrape-bds-rp-evidence) (trang này).
