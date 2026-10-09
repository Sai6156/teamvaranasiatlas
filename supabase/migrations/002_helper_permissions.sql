-- Membership helpers are needed by authenticated RLS checks, never anonymous callers.
revoke all on function public.is_member(uuid), public.is_admin(uuid) from public, anon;
grant execute on function public.is_member(uuid), public.is_admin(uuid) to authenticated;
