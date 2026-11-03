/** Nối đường dẫn nội bộ với `base` (cần khi host ở github.io/<repo>). */
export const u = (path: string): string => {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return `${base}${path.startsWith('/') ? path : '/' + path}`;
};
