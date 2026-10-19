# CLAUDE.md

Convention và mục đích của repo. Không ghi trạng thái hay tiến độ ở đây.

## Dùng bản Evidence nào (quan trọng)

Repo dùng **Evidence legacy** (`@evidence-dev/evidence` 40.x, pin trong `package-lock.json`), **không phải Evidence Core/Studio** (CLI `evidence`, cú pháp Markdoc `{% table /%}`, cần `evidence login`). Lý do và đánh giá chi tiết: README.md. Tóm lại: chỉ legacy build ra site tĩnh để lên GitHub Pages.

- Cú pháp legacy: component kiểu Svelte (`<LineChart data={q} x=month y=price />`), query là khối ```` ```sql ten_query ```` viết bằng DuckDB SQL, input tham chiếu `${inputs.city.value}`. Docs: https://docs.evidence.dev (một phần docs nay mô tả Core, cẩn thận khi tra cứu).
- Lệnh: `npm run sources` (nạp dữ liệu), `npm run dev`, `npm run build` (ra `build/`). Không dùng CLI `evidence` đã cài trên máy; bản trong `node_modules` mới là bản đúng.
- Không nâng cấp `@evidence-dev/*` lên bản Core hoặc chạy `evidence migrate`/`login`/`publish`/`launch`/`link` nếu chưa hỏi.

## Repo này là gì

Prototype **báo cáo/dashboard tĩnh bằng Evidence** cho dự án phân tích thị trường BĐS Việt Nam. Repo anh em của `../scrape-batdongsan-data` (nơi scrape + dbt, tạo ra BigQuery `re_gold`). Repo này chỉ **đọc** `re_gold` và trình bày; không scrape, không viết dbt model, không ghi ngược vào BigQuery.

Đây là một trong các bản thử cùng một đặc tả đầu ra, để so sánh công cụ và chọn cái tốt nhất:

- `scrape-bds-rp-evidence` (repo này)
- `scrape-bds-rp-observable`, `scrape-bds-rp-astro` (nếu làm tiếp)

Đặt tên: `scrape-bds-rp-<framework>`; `rp` = report. Giữ nội dung/đặc tả giống nhau giữa các bản để so sánh công bằng.

## Đầu ra mong muốn

Một **site tĩnh** cho độc giả blog (series Substack của DataSpi/spyno), thay thế/bổ sung dashboard Looker Studio hiện tại. Người xem không cần quyền vào BigQuery và trang phải nhẹ, nhanh.

- **Host miễn phí**: đưa được lên GitHub Pages hoặc Firebase Hosting. Nếu Evidence không build ra static output host được như vậy, đó là kết quả quan trọng của bản thử này: ghi rõ vào README/docs của repo, đừng lách bằng server phải duy trì.
- **Cấu trúc trang**:
  - Đầu trang: 3-4 số lớn (VD giá/m² trung vị, số tin đang bán, thay đổi so với kỳ trước).
  - 4-6 biểu đồ, mỗi biểu đồ trả lời một câu hỏi. **Tiêu đề biểu đồ là kết luận** ("Giá Quận 2 tăng 8% trong 3 tháng"), không phải mô tả ("Giá theo quận").
  - Một bộ lọc chung ở đầu trang (thành phố, loại hình), không rải filter khắp nơi.
  - Cuối trang: nguồn dữ liệu, ngày cập nhật, hạn chế (giá là giá rao, không phải giá giao dịch).
- **Giao diện**: sạch, 1-2 màu nhấn còn lại xám, màu giữ ý nghĩa nhất quán, đủ khoảng trắng, đọc tốt trên điện thoại (phần lớn người mở link từ Substack bằng mobile).
- **Nhịp cập nhật**: build một lần mỗi tuần sau khi pipeline của repo kia chạy xong. Không cần realtime.
- **Tiếng Việt**: nội dung hiển thị cho người xem bằng tiếng Việt.

## Dữ liệu và ranh giới giữa hai repo

- **Site là public**: mọi thứ nằm trong bản build đều tải về được. Chỉ dùng **bảng đã aggregate** (theo quận/tháng/loại hình...), không bao giờ đưa dữ liệu từng tin đăng, số điện thoại, hay tên người đăng vào site.
- Aggregate nằm ở **dbt trong `../scrape-batdongsan-data`** (các bảng `mart_site_*` trong `re_gold`), không viết logic tính toán nặng bằng SQL trong trang Evidence. Trang chỉ `select` từ bảng đã chuẩn bị, để số liệu có một nguồn duy nhất và test được bằng dbt.
- Nguồn gốc: `re_gold.mart_real_estate` (và `mart_real_estate_rent`). Nhớ ngữ nghĩa từ repo kia: `fct_*`/`mart_*` chỉ giữ bản mới nhất, không có lịch sử; xu hướng theo thời gian phải đến từ snapshot/bảng aggregate theo kỳ.
- Cần cột/bảng mới thì thêm vào dbt ở repo kia, đừng bù bằng SQL phức tạp ở đây.

## Convention

- **Không commit credential.** Với nguồn BigQuery thật (plugin `@evidence-dev/bigquery`), thông tin xác thực đặt trong `sources/<ten>/connection.options.yaml` (đã gitignore qua `*.options.yaml`); chỉ `connection.yaml` (không chứa bí mật) được commit. Service account key dùng chung với repo kia: tham chiếu đường dẫn tuyệt đối tới file trong `../scrape-batdongsan-data`, không copy key vào repo này. Chỉ dùng quyền đọc (BigQuery Data Viewer + Job User là đủ).
- **Luồng dữ liệu**: `scripts/extract_data.py` (chạy local, cần key BigQuery) trích bảng **đã tổng hợp** ra `sources/bds_real/*.csv`; các CSV này được commit; Evidence build từ CSV (`npm run sources` + `npm run build`). Vì vậy key BigQuery chỉ cần trên máy local và **không bao giờ vào GitHub Actions/Secrets**: workflow `pages.yml` chỉ build từ CSV đã commit. Muốn đổi snapshot hay cập nhật số: chạy lại script rồi commit CSV mới.
- Script chỉ `SELECT`, đọc key qua biến môi trường `GOOGLE_APPLICATION_CREDENTIALS` (không copy key vào repo, không in nội dung key), và từ chối ghi file nếu có cột thuộc dạng định danh từng tin (title/link/product_id/số điện thoại...). Thêm bảng/cột mới vào script phải giữ nguyên các chốt chặn này.
- Mỗi snapshot phải chọn theo `date_scraped` (mart trộn nhiều đợt scrape và có tin không có ngày). Không so sánh số giữa hai snapshot mà không kiểm tra độ phủ mẫu (số tin, số quận) giống nhau; trang phải nói rõ khi mẫu khác nhau.
- Mọi con số trong văn bản trang web lấy từ truy vấn (in bằng `{query[0].cot}`), không gõ tay; chỉ các đoạn trích nguyên văn từ bài cũ là chuỗi cố định. Số đã định dạng sẵn thành chuỗi trong SQL (`printf`, `format`): component `<Value>` tự đoán kiểu theo tên cột (`*_pct` bị nhân 100) nên tránh dùng cho số đã chuẩn bị. Giọng văn và cấu trúc bài theo skill `real_estate_analyzer` của repo scrape-batdongsan-data.
- Mỗi thay đổi lớn một branch/PR riêng.
- Tích hợp vào pipeline tuần (nếu về sau chốt dùng): step build+deploy gọi từ `src/ops/run_weekly_pipeline.sh` của repo kia bằng đường dẫn tuyệt đối, **non-fatal** (dashboard lỗi không được làm sập scrape). Phần đó ghi ở CLAUDE.md của repo kia, không ghi ở đây.
- Tài liệu và comment viết tiếng Việt, tên file/biến tiếng Anh.
