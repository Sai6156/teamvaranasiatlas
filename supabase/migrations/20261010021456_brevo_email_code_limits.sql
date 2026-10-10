-- No addresses, passwords, OTPs, or IPs are stored here: only keyed digests.
create table public.auth_email_limits (
 key text primary key check (length(key)=64),
 window_start timestamptz not null,
 last_sent timestamptz not null,
 sent_count integer not null
);
alter table public.auth_email_limits enable row level security;
revoke all on public.auth_email_limits from public,anon,authenticated;
grant all on public.auth_email_limits to service_role;
create index auth_email_limits_expiry on public.auth_email_limits(last_sent);

create function public.reserve_auth_email(recipient_key text, actor_key text)
returns boolean language plpgsql security invoker set search_path='' as $$
declare recipient public.auth_email_limits; actor public.auth_email_limits;
begin
 if length(recipient_key)<>64 or length(actor_key)<>64 or recipient_key=actor_key then
  raise exception 'Invalid rate limit key';
 end if;
 -- Consistent lock order prevents concurrent requests bypassing either limit.
 perform pg_advisory_xact_lock(hashtextextended(least(recipient_key,actor_key),42));
 perform pg_advisory_xact_lock(hashtextextended(greatest(recipient_key,actor_key),42));
 select * into recipient from public.auth_email_limits where key=recipient_key;
 select * into actor from public.auth_email_limits where key=actor_key;
 if recipient.key is not null and (recipient.last_sent>now()-interval '60 seconds' or
   (recipient.window_start>now()-interval '1 hour' and recipient.sent_count>=5)) then return false; end if;
 if actor.key is not null and actor.window_start>now()-interval '1 hour' and actor.sent_count>=30 then return false; end if;
 delete from public.auth_email_limits where last_sent<now()-interval '24 hours';
 insert into public.auth_email_limits(key,window_start,last_sent,sent_count)
 values(recipient_key,now(),now(),1),(actor_key,now(),now(),1)
 on conflict(key) do update set
  window_start=case when auth_email_limits.window_start<now()-interval '1 hour' then now() else auth_email_limits.window_start end,
  sent_count=case when auth_email_limits.window_start<now()-interval '1 hour' then 1 else auth_email_limits.sent_count+1 end,
  last_sent=now();
 return true;
end; $$;
revoke all on function public.reserve_auth_email(text,text) from public,anon,authenticated;
grant execute on function public.reserve_auth_email(text,text) to service_role;
