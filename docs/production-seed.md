# Production Seed Plan

ShowFZU production seed data is copied from the current local SQLite demo database, but production media is uploaded to Supabase Storage. Production rows must not reference `frontend/public/demo-posts` or `local-demo/` paths.

## Batch Identity

- Batch ID: `showfzu-prod-seed-v1`
- Storage prefix: `seed-batches/showfzu-prod-seed-v1/`
- Seed user marker: `users.avatar_storage_path` starts with `seed-batches/showfzu-prod-seed-v1/users/`

This avoids schema changes while still giving the seed script a reliable cleanup marker. `avatar_storage_path` is not exposed by public API serializers.

## Commands

From the repository root:

```powershell
npm run seed:production:plan
npm run seed:production
npm run seed:production:cleanup
```

The production commands read credentials from ignored local env files, preferring:

1. `backend/.env.production.local`
2. `backend/.env.render.local`
3. `backend/.env`

Required variables:

- `SHOWFZU_DATABASE_URL`
- `SHOWFZU_SUPABASE_URL`
- `SHOWFZU_SUPABASE_SERVICE_KEY`
- `SHOWFZU_STORAGE_POSTS_BUCKET`
- `SHOWFZU_PUBLIC_BASE_URL`

Do not commit these values.

## Current Source Inventory

The current local SQLite source contains:

- 6 demo author accounts
- 30 demo posts
- 46 media rows
- 44 images
- 2 videos
- About 60 MB total media
- No source video currently exceeds the 50 MB per-file limit

Because the current source videos are already below 50 MB, no additional compression is required before production seeding. If a future source video exceeds 50 MB, the script compresses it into `backend/.production-seed-cache/` using H.264/AAC with a target below 50 MB before upload.

## Safety Rules

- The script seeds only the authors of the local demo posts. Extra local test accounts with no demo posts are excluded.
- The script cleans the existing `showfzu-prod-seed-v1` batch before inserting, so it can be rerun.
- Cleanup deletes seeded posts, seeded users, associated comments, likes, favorites, media records, and Storage objects under the seed prefix.
- If target users or posts conflict with non-seed data, the script aborts rather than overwriting production content.
- If upload or insert fails mid-run, uploaded objects from that attempt are removed before the error is raised.
