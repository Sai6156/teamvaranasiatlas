create or replace function public.claim_job() returns setof public.ingestion_jobs language plpgsql security definer set search_path='' as $$
begin
 with expired as (
  update public.ingestion_jobs set status='failed',lease_until=null,last_error='The worker was interrupted repeatedly. Please retry this document.'
  where status='running' and lease_until<now() and attempts>=3 returning document_id
 ) update public.documents set status='failed',error_message='The worker was interrupted repeatedly. Please retry this document.'
 where id in (select document_id from expired) and status not in ('ready','deleted');
 return query with candidate as (
 select id from public.ingestion_jobs where attempts<3 and ((status='queued' and available_at<=now()) or (status='running' and lease_until<now())) order by created_at for update skip locked limit 1
 ) update public.ingestion_jobs j set status='running',attempts=j.attempts+1,lease_until=now()+interval '10 minutes' from candidate where j.id=candidate.id returning j.*;
end; $$;
