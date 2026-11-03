import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// Mỗi chương trình = 1 file .md trong src/content/events (sửa được qua Pages CMS).
const events = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/events' }),
  schema: z.object({
    title: z.string(),
    subtitle: z.string().optional(),
    // done = đã diễn ra · ongoing = đang diễn ra · planned = dự kiến (chưa triển khai)
    status: z.enum(['done', 'ongoing', 'planned']).default('done'),
    type: z.enum(['Đêm thơ', 'Series', 'Workshop', 'Phim & Trình diễn', 'Chương trình quốc tế', 'Câu lạc bộ']),
    sortDate: z.coerce.date().optional(),
    dateLabel: z.string().optional(),
    venue: z.string().optional(),
    partners: z.array(z.string()).default([]),
    attendeesLabel: z.string().optional(),
    summary: z.string(),
    cover: z.string().optional(),
    youtube: z.string().optional(),
    instagramPosts: z.array(z.string()).default([]),
    needsConfirm: z.boolean().default(false),
  }),
});

export const collections = { events };
