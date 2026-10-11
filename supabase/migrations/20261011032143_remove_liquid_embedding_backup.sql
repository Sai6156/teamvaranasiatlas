-- Remove only the discontinued secondary embedding feature.
drop function if exists public.search_chunks_liquid(uuid,text,extensions.vector,integer,text);
drop function if exists public.pending_liquid_chunks(integer,uuid);
drop function if exists public.missing_liquid_chunks(integer);
drop function if exists public.finish_liquid_index(jsonb);
drop table if exists public.free_embedding_status;
drop table if exists public.chunk_free_embeddings;
alter table public.chunks drop column if exists free_embedding_ready;
do $$ begin
 if exists(select 1 from public.chunks where embedding is null) then
  raise exception 'Original embedding coverage must be restored before enforcing the constraint';
 end if;
end $$;
alter table public.chunks alter column embedding set not null;
