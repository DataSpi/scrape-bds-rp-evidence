---
title: Giá mua chung cư
---

```sql periods
select p.period, p.label,
  'mua/chung-cu/' || p.period as link,
  case when m.d0 = m.d1 then 'ngày ' || strftime(cast(m.d1 as date), '%d/%m/%Y')
    else strftime(cast(m.d0 as date), '%d/%m') || ' - ' || strftime(cast(m.d1 as date), '%d/%m/%Y') end as window_txt,
  replace(format('{:,}', cast(m.n_priced as bigint)), ',', '.') as n_txt
from bds_real.periods p
join bds_real.cc_meta m using (period)
order by p.period desc
```

```sql trend
select p.label, k.period, k.city, k.avg_price_1m2,
  round(100.0 * k.n_lt3 / k.n, 1) as pct_lt3
from bds_real.cc_city_kpi k
join bds_real.periods p using (period)
order by k.period, k.city
```

Tin rao bán căn hộ chung cư ở HCM & HN trên batdongsan.com.vn. Mỗi kỳ là một ảnh chụp toàn bộ tin trong đợt scrape của kỳ đó. Bấm vào một kỳ để đọc bài phân tích chi tiết của kỳ đó.

## Các kỳ báo cáo

{#each periods as p}

- <a href={p.link} class="text-primary hover:underline"><b>{p.label}</b></a>: scrape {p.window_txt}, {p.n_txt} tin có giá.

{/each}

## Qua các kỳ

<LineChart
    data={trend}
    x=label
    y=avg_price_1m2
    series=city
    sort=false
    markers=true
    yFmt="0.0"
    yAxisTitle="triệu đồng/m²"
    title="Giá/m² trung bình theo kỳ"
/>

<LineChart
    data={trend}
    x=label
    y=pct_lt3
    series=city
    sort=false
    markers=true
    yFmt="0.0"
    yAxisTitle="% số tin"
    title="Tỷ lệ tin dưới 3 tỷ theo kỳ"
/>

Số tin mỗi kỳ không bằng nhau, xem mục "So với kỳ trước" trong từng bài trước khi đọc xu hướng.
