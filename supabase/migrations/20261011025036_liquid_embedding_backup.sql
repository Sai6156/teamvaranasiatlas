-- Separate vector spaces: OpenAI 1536 and Liquid 1024 are never compared.
alter table public.chunks alter column embedding drop not null;
alter table public.chunks add column free_embedding_ready boolean not null default false;
create table public.chunk_free_embeddings (
 chunk_id uuid not null references public.chunks(id) on delete cascade,
 organization_id uuid not null references public.organizations(id) on delete cascade,
 document_id uuid not null references public.documents(id) on delete cascade,
 segment integer not null check(segment>=0),
 model text not null check(model='liquid/lfm-2.5-embedding-350m:free'),
 embedding extensions.vector(1024) not null,
 primary key(chunk_id,segment)
);
create index chunk_free_embedding_idx on public.chunk_free_embeddings using hnsw(embedding extensions.vector_cosine_ops);
create index chunk_free_org_idx on public.chunk_free_embeddings(organization_id,document_id);
alter table public.chunk_free_embeddings enable row level security;
revoke all on public.chunk_free_embeddings from anon,authenticated;
grant select on public.chunk_free_embeddings to authenticated;
grant all on public.chunk_free_embeddings to service_role;
create policy free_embeddings_read on public.chunk_free_embeddings for select to authenticated using (
 public.is_member(organization_id) and exists(select 1 from public.chunks c join public.documents d on d.id=c.document_id where c.id=chunk_id and c.organization_id=chunk_free_embeddings.organization_id and c.document_id=chunk_free_embeddings.document_id and d.status='ready')
);

create function public.missing_liquid_chunks(batch_limit integer default 32)
returns table(id uuid,organization_id uuid,document_id uuid,content text)
language sql stable security invoker set search_path='' as $$
 select c.id,c.organization_id,c.document_id,c.content from public.chunks c join public.documents d on d.id=c.document_id
 where not c.free_embedding_ready and d.status='ready' order by c.id limit least(greatest(batch_limit,1),128);
$$;
revoke all on function public.missing_liquid_chunks(integer) from public,anon,authenticated;
grant execute on function public.missing_liquid_chunks(integer) to service_role;

create function public.finish_liquid_index(indexed_chunks jsonb) returns void
language sql security invoker set search_path='' as $$
 update public.chunks c set free_embedding_ready=true
 from jsonb_to_recordset(indexed_chunks) as entry(id uuid,segments integer)
 where c.id=entry.id and entry.segments>0 and entry.segments=(select count(*) from public.chunk_free_embeddings f where f.chunk_id=c.id and f.organization_id=c.organization_id and f.document_id=c.document_id and f.model='liquid/lfm-2.5-embedding-350m:free');
$$;
revoke all on function public.finish_liquid_index(jsonb) from public,anon,authenticated;
grant execute on function public.finish_liquid_index(jsonb) to service_role;

create function public.search_chunks_liquid(org uuid,lexical_query text,query_embedding extensions.vector(1024),result_limit integer default 24,folder text default null)
returns table(id uuid,document_id uuid,content text,location jsonb,document_name text,collection text,score double precision)
language sql stable security invoker set search_path='' as $$
 with query as (select case when lexical_query='' then null else to_tsquery('simple',lexical_query) end fts),
 eligible as not materialized (
 select c.*,d.name,d.collection from public.chunks c join public.documents d on d.id=c.document_id
 where c.organization_id=org and d.organization_id=org and d.status='ready' and public.is_member(org) and (folder is null or d.collection=folder)
 ), nearest as (
 select f.chunk_id id,f.embedding operator(extensions.<=>) query_embedding distance
 from public.chunk_free_embeddings f join eligible e on e.id=f.chunk_id
 where query_embedding is not null and e.free_embedding_ready and f.organization_id=org and f.document_id=e.document_id
 order by f.embedding operator(extensions.<=>) query_embedding limit 128
 ), semantic as (
 select id,row_number() over(order by distance) rank from (select id,min(distance) distance from nearest group by id) grouped order by distance limit 48
 ), lexical as (
 select e.id,row_number() over(order by ts_rank_cd(e.search_vector,q.fts,32) desc) rank from eligible e cross join query q where q.fts is not null and e.search_vector @@ q.fts order by ts_rank_cd(e.search_vector,q.fts,32) desc limit 48
 ), fused as (
 select coalesce(s.id,l.id) id,coalesce(1.0/(40+s.rank),0)+1.4*coalesce(1.0/(40+l.rank),0) score from semantic s full outer join lexical l on s.id=l.id
 ) select e.id,e.document_id,e.content,e.location,e.name,e.collection,f.score::double precision from fused f join eligible e on e.id=f.id order by f.score desc limit least(greatest(result_limit,1),40);
$$;
revoke all on function public.search_chunks_liquid(uuid,text,extensions.vector,integer,text) from public,anon;
grant execute on function public.search_chunks_liquid(uuid,text,extensions.vector,integer,text) to authenticated;

create or replace function public.search_chunks_v2(org uuid, lexical_query text, query_embedding extensions.vector(1536), result_limit integer default 24, folder text default null)
returns table(id uuid,document_id uuid,content text,location jsonb,document_name text,collection text,score double precision)
language sql stable security invoker set search_path='' as $$
 with query as (select case when lexical_query='' then null else to_tsquery('simple',lexical_query) end fts),
 eligible as not materialized (
 select c.*,d.name,d.collection from public.chunks c join public.documents d on d.id=c.document_id
 where c.organization_id=org and d.organization_id=org and d.status='ready' and public.is_member(org) and (folder is null or d.collection=folder)
 ), semantic as (
 select e.id,row_number() over(order by e.embedding operator(extensions.<=>) query_embedding) rank from eligible e where query_embedding is not null and e.embedding is not null order by e.embedding operator(extensions.<=>) query_embedding limit 48
 ), lexical as (
 select e.id,row_number() over(order by ts_rank_cd(e.search_vector,q.fts,32) desc) rank from eligible e cross join query q where q.fts is not null and e.search_vector @@ q.fts order by ts_rank_cd(e.search_vector,q.fts,32) desc limit 48
 ), fused as (
 select coalesce(s.id,l.id) id,coalesce(1.0/(40+s.rank),0)+1.4*coalesce(1.0/(40+l.rank),0) score from semantic s full outer join lexical l on s.id=l.id
 ) select e.id,e.document_id,e.content,e.location,e.name,e.collection,f.score::double precision from fused f join eligible e on e.id=f.id order by f.score desc limit least(greatest(result_limit,1),40);
$$;
revoke all on function public.search_chunks_v2(uuid,text,extensions.vector,integer,text) from public,anon;
grant execute on function public.search_chunks_v2(uuid,text,extensions.vector,integer,text) to authenticated;
