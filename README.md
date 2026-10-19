# scrape-bds-rp-evidence

Prototype báo cáo tĩnh bằng [Evidence](https://github.com/evidence-dev/evidence) (bản **legacy**) cho dự án phân tích thị trường BĐS Việt Nam. Repo anh em của `scrape-batdongsan-data`. Mục đích và đầu ra mong muốn: xem [CLAUDE.md](CLAUDE.md).

Trang demo (dữ liệu giả): https://dataspi.github.io/scrape-bds-rp-evidence/

## Chạy local

```bash
npm ci
npm run sources   # nạp CSV trong sources/ vào DuckDB
npm run dev       # xem trước, hot reload
npm run build     # ra thư mục build/ (site tĩnh)
```

Dữ liệu demo sinh bằng `python3 scripts/gen_dummy_data.py` (seed cố định).

## Kết quả đánh giá Evidence cho mục tiêu "site tĩnh, host miễn phí"

- **Evidence Core** (bản mới, CLI `evidence`, template hiện tại của `evidence-dev/template`): SQL chạy phía server, `evidence serve` là server Node cần connector trực tiếp tới warehouse, **không có lệnh build ra site tĩnh**. Không đưa lên GitHub Pages được; self-host chỉ qua Docker (Vercel/Render/Fly/Railway) kèm Basic Auth.
- **Evidence legacy** (`@evidence-dev/evidence` 40.x, nhánh `legacy` của template): build ra site tĩnh (`@sveltejs/adapter-static`), SQL chạy trong trình duyệt bằng DuckDB WASM. Đây là bản repo này dùng. Đã đóng băng: template chuyển sang Core từ 2026-08-20, bản npm cuối là 40.1.8.
- **Cái giá của legacy**: bản build nặng khoảng 86 MB (chủ yếu 2 file DuckDB WASM, trình duyệt tải một file khoảng 30+ MB ở lần xem đầu); chrome giao diện (sidebar, nhãn tháng trên trục) mặc định tiếng Anh; không còn phát triển tính năng mới.
