-- ============================================================================
-- ADMIN ALLOWLIST — who is allowed into the admin panel
-- Money Master — Financial Simulation Game
--
-- WHY a separate table (not an is_admin column on users):
--   public.users has a "FOR ALL USING (auth.uid() = id)" policy, which lets a
--   logged-in user UPDATE their OWN row. If admin were a flag there, any student
--   could set themselves admin from the browser. This table has RLS ON and NO
--   policies, so the anon/authenticated clients can neither read nor write it.
--   Only the Flask backend (service_role key) can — which is exactly who checks it.
--
-- HOW TO APPLY:  Supabase -> SQL Editor -> paste -> Run. Safe to re-run.
-- ============================================================================

create table if not exists public.admins (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.admins enable row level security;
-- (intentionally no policies -> clients are fully denied; backend bypasses RLS)

-- ── GRANT ADMIN ────────────────────────────────────────────────────────────
-- 1) Create the admin's login first: Authentication -> Users -> Add user
--    (email + password, tick Auto Confirm User).
-- 2) Then make them an admin by email:
--
--    insert into public.admins (user_id)
--    select id from auth.users where email = 'admin@yourcollege.edu'
--    on conflict (user_id) do nothing;
--
-- To revoke:  delete from public.admins where user_id =
--    (select id from auth.users where email = 'admin@yourcollege.edu');
--
-- To list current admins:
--    select u.email from public.admins a join auth.users u on u.id = a.user_id;
