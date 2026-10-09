create function public.manage_member(org uuid, target uuid, new_role text default null) returns void language plpgsql security definer set search_path='' as $$
declare old_role text;
begin
 if not public.is_admin(org) then raise exception 'Only workspace admins can manage access'; end if;
 perform pg_advisory_xact_lock(hashtextextended(org::text,2));
 select role into old_role from public.memberships where organization_id=org and user_id=target for update;
 if old_role is null then raise exception 'Member not found'; end if;
 if new_role is not null and new_role not in ('admin','employee') then raise exception 'Invalid role'; end if;
 if old_role='admin' and (new_role is null or new_role='employee') and (select count(*) from public.memberships where organization_id=org and role='admin')<=1 then raise exception 'Keep at least one admin in the workspace'; end if;
 if new_role is null then delete from public.memberships where organization_id=org and user_id=target;
 else update public.memberships set role=new_role where organization_id=org and user_id=target; end if;
 insert into public.audit_events(organization_id,user_id,action,details) values(org,auth.uid(),'member.access_changed',jsonb_build_object('target',target,'role',new_role));
end; $$;
revoke all on function public.manage_member(uuid,uuid,text) from public,anon;
grant execute on function public.manage_member(uuid,uuid,text) to authenticated;
