# Thơ-là-ai? — website

Website tĩnh (Astro) cho dự án **Thơ-là-ai? (TLA)**. Số liệu thống kê lấy từ Excel, được **ẩn danh trước khi đưa lên web**.

## Cho người biên tập (không cần biết code)

1. Vào <https://app.pagescms.org> → đăng nhập bằng GitHub → chọn repo này.
2. **Chương trình**: thêm/sửa sự kiện bằng form (tên, trạng thái, ngày, địa điểm, nội dung, video YouTube).
3. **Thông tin chung & con số trang chủ**: sửa khẩu hiệu, email, link mạng xã hội, các con số lớn.
4. Ảnh: tải lên trong Pages CMS (thư mục `public/images`), mỗi ảnh nên < 500 KB.
5. Bấm **Save**: sau khoảng 1 phút web tự cập nhật.

> Video: đăng lên YouTube (chế độ *Không công khai/Unlisted*), chỉ dán **mã video** (đoạn sau `v=`) vào form.

## Cho người phát triển

Cần Node 20+ (máy hiện có Node 12: dùng `export PATH=$HOME/.local/node/bin:$PATH`).

```bash
npm install
npm run dev          # xem thử tại http://localhost:4321
npm run build        # build ra dist/
npm run stats        # tạo lại src/data/stats.json từ raw/*.xlsx (cần pandas, openpyxl)
npm run check:pii    # quét email/số điện thoại trước khi deploy
```

### Cập nhật số liệu thống kê
1. Đặt file Excel mới vào `raw/` (thư mục này **không** được đưa lên Git).
2. `npm run stats` → kiểm tra `src/data/stats.json` (chỉ có số tổng hợp, không tên/email/tiền).
3. Commit `stats.json`, web tự deploy.

Quy tắc ẩn danh nằm ở đầu `scripts/build_stats.py`: không xuất tiền, giới tính hay thông tin liên hệ; nhóm dưới 3 người được gộp vào "Khác".

### Deploy miễn phí (chọn một)
- **GitHub Pages**: đẩy repo lên GitHub → Settings → Pages → Source = *GitHub Actions*. Workflow ở `.github/workflows/deploy.yml`. Địa chỉ dạng `https://<user>.github.io/<repo>`.
- **Cloudflare Pages**: kết nối repo; build command `npm run build`, output `dist`, biến môi trường `NODE_VERSION=20` và `SITE=https://<tên>.pages.dev`.

## Cấu trúc
```
src/content/events/   mỗi chương trình = 1 file .md
src/data/             site.json (chỉnh qua CMS), stats.json (sinh tự động)
src/components/       biểu đồ SVG/HTML thuần (không cần JS)
src/pages/            trang chủ, chương trình, tác động, về TLA, liên hệ
scripts/              build_stats.py, check_pii.py
.pages.yml            cấu hình giao diện CMS
```
