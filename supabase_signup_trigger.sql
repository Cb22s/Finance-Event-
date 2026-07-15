-- ############################################################################
-- ##  NOT REQUIRED FOR A FRESH INSTALL (F-02).                               ##
-- ##  The handle_new_user() function and on_auth_user_created trigger are    ##
-- ##  now created by supabase.sql. A fresh install runs ONLY supabase.sql.   ##
-- ##  Retained only to retrofit an older live project. Idempotent if re-run. ##
-- ############################################################################

-- ============================================================================
-- SIGNUP TRIGGER — auto-create a public.users row when someone signs up
-- Money Master — Financial Simulation Game
--
-- WHY THIS IS REQUIRED (and why a fresh deploy breaks without it):
--   public.player_state.user_id  ->  REFERENCES public.users(id)
--   Nothing in the Flask backend inserts into public.users. On the OLD project
--   this row was created by a trigger set up by hand in the dashboard, which is
--   NOT captured in supabase.sql. On a fresh project that trigger doesn't exist,
--   so the very first /allocate call fails with a foreign-key violation because
--   there is no matching public.users row for the authenticated user.
--
--   This file recreates that trigger. Run it ONCE, AFTER supabase.sql.
--   Safe to run more than once (idempotent).
--
-- HOW TO APPLY:
--   Supabase Dashboard -> SQL Editor -> paste this file -> Run.
-- ============================================================================

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.users (id, email, name)
  values (
    new.id,
    new.email,
    coalesce(
      new.raw_user_meta_data->>'name',
      new.raw_user_meta_data->>'full_name',
      split_part(new.email, '@', 1)
    )
  )
  on conflict (id) do nothing;   -- never clobber an existing profile
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ── Backfill: create profiles for any auth users that already exist ─────────
-- (harmless on a truly fresh project; useful if you created test users first)
insert into public.users (id, email, name)
select u.id, u.email,
       coalesce(u.raw_user_meta_data->>'name',
                u.raw_user_meta_data->>'full_name',
                split_part(u.email, '@', 1))
from auth.users u
on conflict (id) do nothing;
