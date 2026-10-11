-- Consistent lock order and idempotency for concurrent worker/PC backfills.
create or replace function public.finish_liquid_index(indexed_chunks jsonb) returns void
language plpgsql security invoker set search_path='' as $$
declare item record;
begin
 for item in select e.id,e.segments from jsonb_to_recordset(indexed_chunks) as e(id uuid,segments integer) order by e.id loop
  update public.chunks c set free_embedding_ready=true
  where c.id=item.id and not c.free_embedding_ready and item.segments>0 and item.segments=(select count(*) from public.chunk_free_embeddings f where f.chunk_id=c.id and f.organization_id=c.organization_id and f.document_id=c.document_id and f.model='liquid/lfm-2.5-embedding-350m:free');
 end loop;
end; $$;
revoke all on function public.finish_liquid_index(jsonb) from public,anon,authenticated;
grant execute on function public.finish_liquid_index(jsonb) to service_role;
