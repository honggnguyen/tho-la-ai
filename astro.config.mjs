import { defineConfig } from 'astro/config';

// Địa chỉ web được đọc từ biến môi trường để dùng được cho cả 3 nơi host miễn phí:
//  - Cloudflare Pages:      SITE=https://tholaai.pages.dev                (không cần BASE)
//  - GitHub Pages (repo):   SITE=https://<user>.github.io  BASE=/<repo>
//  - GitHub Pages (user):   SITE=https://<user>.github.io                 (repo tên <user>.github.io)
export default defineConfig({
  site: process.env.SITE || 'https://tholaai.pages.dev',
  base: process.env.BASE || '/',
  trailingSlash: 'never',
});
