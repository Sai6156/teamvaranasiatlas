alter table public.documents add column if not exists total_pages integer not null default 0;
alter table public.documents add column if not exists processed_pages integer not null default 0;
alter table public.documents add column if not exists index_total_chunks integer not null default 0;
alter table public.documents add column if not exists index_completed_chunks integer not null default 0;
alter table public.documents add column if not exists indexing_version text not null default 'v1';
alter table public.conversations add column if not exists updated_at timestamptz not null default now();
update public.conversations c set updated_at=coalesce((select max(m.created_at) from public.messages m where m.conversation_id=c.id),c.created_at);
create index if not exists conversations_owner_activity_idx on public.conversations(organization_id,user_id,updated_at desc);
create schema if not exists private;
create or replace function private.touch_conversation() returns trigger language plpgsql security definer set search_path='' as $$
begin
 update public.conversations set updated_at=new.created_at where id=new.conversation_id and organization_id=new.organization_id;
 return new;
end; $$;
revoke all on function private.touch_conversation() from public,anon,authenticated;
create trigger message_activity after insert on public.messages for each row execute function private.touch_conversation();

create or replace function public.search_chunks_v2(org uuid, lexical_query text, query_embedding extensions.vector(1536), result_limit integer default 24, folder text default null)
returns table(id uuid,document_id uuid,content text,location jsonb,document_name text,collection text,score double precision)
language sql stable security invoker set search_path='' as $$
 with query as (select case when lexical_query='' then null else to_tsquery('simple',lexical_query) end fts),
 eligible as not materialized (
 select c.*,d.name,d.collection from public.chunks c join public.documents d on d.id=c.document_id
 where c.organization_id=org and d.organization_id=org and d.status='ready' and public.is_member(org) and (folder is null or d.collection=folder)
 ), semantic as (
 select e.id,row_number() over(order by e.embedding operator(extensions.<=>) query_embedding) rank from eligible e where query_embedding is not null order by e.embedding operator(extensions.<=>) query_embedding limit 48
 ), lexical as (
 select e.id,row_number() over(order by ts_rank_cd(e.search_vector,q.fts,32) desc) rank from eligible e cross join query q where q.fts is not null and e.search_vector @@ q.fts order by ts_rank_cd(e.search_vector,q.fts,32) desc limit 48
 ), fused as (
 select coalesce(s.id,l.id) id,coalesce(1.0/(40+s.rank),0)+1.4*coalesce(1.0/(40+l.rank),0) score from semantic s full outer join lexical l on s.id=l.id
 ) select e.id,e.document_id,e.content,e.location,e.name,e.collection,f.score::double precision from fused f join eligible e on e.id=f.id order by f.score desc limit least(greatest(result_limit,1),40);
$$;
revoke all on function public.search_chunks_v2(uuid,text,extensions.vector,integer,text) from public,anon;
grant execute on function public.search_chunks_v2(uuid,text,extensions.vector,integer,text) to authenticated;

create or replace function public.request_reindex(doc uuid) returns void language plpgsql security definer set search_path='' as $$
declare org uuid;
begin
 select organization_id into org from public.documents where id=doc and status<>'deleted' for update;
 if not public.is_admin(org) then raise exception 'Only workspace admins can reindex'; end if;
 if exists(select 1 from public.ingestion_jobs where document_id=doc and status in ('queued','running')) then raise exception 'Document is already processing'; end if;
 update public.documents set status='queued',error_message=null,processed_pages=0,index_completed_chunks=0,updated_at=now() where id=doc;
 insert into public.ingestion_jobs(organization_id,document_id) values(org,doc);
end; $$;
revoke all on function public.request_reindex(uuid) from public,anon;
grant execute on function public.request_reindex(uuid) to authenticated;
