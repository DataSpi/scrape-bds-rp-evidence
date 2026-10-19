---
title: Giá mua nhà đất
---

```sql periods
select p.period, p.label,
  'mua/nha-dat/' || p.period as link,
  m.period is not null as has_data,
  case when m.d0 = m.d1 then 'ngày ' || strftime(cast(m.d1 as date), '%d/%m/%Y')
    else strftime(cast(m.d0 as date), '%d/%m') || ' - ' || strftime(cast(m.d1 as date), '%d/%m/%Y') end as window_txt,
  replace(format('{:,}', cast(m.n_priced as bigint)), ',', '.') as n_txt
from bds_real.periods p
left join bds_real.nd_meta m using (period)
order by p.period desc
```

Tin rao bán nhà riêng, nhà mặt phố, biệt thự liền kề và shophouse ở HCM & HN trên batdongsan.com.vn. Bấm vào một kỳ để đọc bài phân tích chi tiết của kỳ đó.

## Các kỳ báo cáo

{#each periods as p}

{#if p.has_data}

- <a href={p.link} class="text-primary hover:underline"><b>{p.label}</b></a>: scrape {p.window_txt}, {p.n_txt} tin có giá.

{:else}

- <b>{p.label}</b>: kỳ này pipeline chưa cào nhà đất.

{/if}

{/each}
