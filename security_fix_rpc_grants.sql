-- ############################################################################
-- ##  INCREMENTAL PATCH — NOT part of a fresh install (F-02).                ##
-- ##  supabase.sql already REVOKEs public EXECUTE on process_month_atomically.##
-- ##  Use ONLY to retrofit an older live project. Idempotent.                ##
-- ############################################################################

-- ============================================================================
-- SECURITY FIX — Revoke public execute on the atomic month-processing RPC
-- Money Master — Financial Simulation Game (QA-001)
--
-- HOW TO APPLY:
--   Supabase Dashboard -> SQL Editor -> paste this file -> Run.
--   Safe to run more than once (idempotent — REVOKE/GRANT are not additive).
--
-- PROBLEM:
--   public.process_month_atomically is SECURITY DEFINER and mutates every
--   player's financial state + advances the game month. It was never
--   REVOKEd from PUBLIC, so Postgres' default EXECUTE grant stood, and
--   Supabase's PostgREST layer exposed it at /rest/v1/rpc/process_month_atomically
--   to the anon and authenticated roles. The function performs no internal
--   admin check — it only validates month sequencing and idempotency — so
--   anyone holding the public anon key (intentionally embedded in
--   frontend/js/config.js) could call it directly and bypass the Flask
--   backend's admin_required gate entirely: rewrite any player's cash,
--   stocks, loans, net worth, score, or advance the month.
--
-- FIX:
--   Revoke EXECUTE from PUBLIC/anon/authenticated; grant only to
--   service_role, which is what the Flask backend actually connects as.
--   No behavior change for the legitimate path — the backend already uses
--   the service_role key for every RPC call.
-- ============================================================================

REVOKE EXECUTE ON FUNCTION public.process_month_atomically(json, json, json, json, integer) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.process_month_atomically(json, json, json, json, integer) FROM anon;
REVOKE EXECUTE ON FUNCTION public.process_month_atomically(json, json, json, json, integer) FROM authenticated;
GRANT EXECUTE ON FUNCTION public.process_month_atomically(json, json, json, json, integer) TO service_role;

-- ============================================================================
-- VERIFY (optional): only postgres/service_role should show EXECUTE.
-- ============================================================================
SELECT grantee, privilege_type
FROM information_schema.routine_privileges
WHERE routine_name = 'process_month_atomically';
