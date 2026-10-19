---
title: Giá thuê chung cư
---

```sql periods
select p.period, p.label,
  'thue/chung-cu/' || p.period as link,
  m.period is not null as has_data,
  case when m.d0 = m.d1 then 'ngày ' || strftime(cast(m.d1 as date), '%d/%m/%Y')
    else strftime(cast(m.d0 as date), '%d/%m') || ' - ' || strftime(cast(m.d1 as date), '%d/%m/%Y') end as window_txt,
  replace(format('{:,}', cast(m.n_priced as bigint)), ',', '.') as n_txt
from bds_real.periods p
left join bds_real.rent_meta m using (period)
order by p.period desc
```

```sql trend
select p.label, k.period, k.city, k.avg_rent, k.avg_rent_m2
from bds_real.rent_city_kpi k
join bds_real.periods p using (period)
order by k.period, k.city
```

Tin cho thuê căn hộ chung cư ở HCM & HN trên batdongsan.com.vn. Bấm vào một kỳ để đọc bài phân tích chi tiết của kỳ đó.

## Các kỳ báo cáo

{#each periods as p}

{#if p.has_data}

- <a href={p.link} class="text-primary hover:underline"><b>{p.label}</b></a>: scrape {p.window_txt}, {p.n_txt} tin có giá.

{:else}

- <b>{p.label}</b>: kỳ này pipeline chưa cào tin cho thuê.

{/if}

{/each}

## Qua các kỳ

<LineChart
    data={trend}
    x=label
    y=avg_rent
    series=city
    sort=false
    markers=true
    yFmt="0.0"
    yAxisTitle="triệu đồng/tháng"
    title="Giá thuê trung bình theo kỳ"
/>

Số tin mỗi kỳ không bằng nhau, xem mục "So với kỳ trước" trong từng bài trước khi đọc xu hướng.
