-- Shared public sources; private organizations and personal chats stay isolated.
alter table public.organizations
 add column is_demo boolean not null default false,
 add column demo_ready boolean not null default false,
 add column demo_slug text,
 add column demo_region text check (demo_region in ('India', 'Global'));
create unique index organizations_demo_slug_idx on public.organizations(demo_slug) where is_demo;
alter table public.organizations add constraint demo_metadata_check
 check ((not is_demo and not demo_ready and demo_slug is null and demo_region is null)
 or (is_demo and demo_slug is not null and demo_region is not null));

create or replace function public.is_member(org uuid) returns boolean
language sql stable security definer set search_path = '' as $$
 select auth.uid() is not null and (
   exists(select 1 from public.memberships where organization_id=org and user_id=auth.uid())
   or (exists(select 1 from auth.users where id=auth.uid() and email_confirmed_at is not null)
       and exists(select 1 from public.organizations where id=org and is_demo and demo_ready))
 );
$$;
revoke all on function public.is_member(uuid) from public, anon;
grant execute on function public.is_member(uuid) to authenticated, service_role;

-- Shared source visibility must not reveal another person's membership details.
alter policy member_read on public.memberships using (
 exists(select 1 from public.organizations o where o.id=organization_id and not o.is_demo)
 and public.is_member(organization_id)
);

create function public.publish_demo_library(org uuid) returns void
language plpgsql security definer set search_path = '' as $$
begin
 if not exists(select 1 from public.organizations where id=org and is_demo) then
   raise exception 'Not a demo workspace';
 end if;
 if (select count(*) from public.documents where organization_id=org and status='ready') <> 3
 or exists(select 1 from public.documents d where d.organization_id=org and
   (d.status<>'ready' or d.chunk_count<1 or d.chunk_count<>(select count(*) from public.chunks c where c.document_id=d.id))) then
   raise exception 'Demo must have three completely indexed documents';
 end if;
 update public.organizations set demo_ready=true where id=org;
end; $$;
revoke all on function public.publish_demo_library(uuid) from public, anon, authenticated;
grant execute on function public.publish_demo_library(uuid) to service_role;
