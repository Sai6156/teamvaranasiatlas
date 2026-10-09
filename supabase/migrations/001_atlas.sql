-- Atlas: organization isolation, private storage, hybrid search, durable jobs.
create extension if not exists vector with schema extensions;
create extension if not exists pgcrypto with schema extensions;

create table public.organizations (
 id uuid primary key default gen_random_uuid(), name text not null check(length(name) between 2 and 100),
 created_by uuid not null references auth.users(id), created_at timestamptz not null default now()
);
create table public.memberships (
 organization_id uuid not null references public.organizations(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 role text not null check(role in ('admin','employee')), display_name text not null default '',
 email text not null, created_at timestamptz not null default now(), primary key(organization_id,user_id)
);
create index memberships_user_idx on public.memberships(user_id);
create function public.is_member(org uuid) returns boolean language sql stable security definer set search_path = '' as $$
 select exists(select 1 from public.memberships where organization_id=org and user_id=auth.uid());
$$;
create function public.is_admin(org uuid) returns boolean language sql stable security definer set search_path = '' as $$
 select exists(select 1 from public.memberships where organization_id=org and user_id=auth.uid() and role='admin');
$$;

create table public.documents (
 id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.organizations(id) on delete cascade,
 uploaded_by uuid not null references auth.users(id), name text not null, mime_type text not null,
 size_bytes bigint not null check(size_bytes between 1 and 26214400), content_hash text not null,
 storage_path text not null unique, collection text not null default 'General',
 status text not null default 'uploaded' check(status in ('uploaded','queued','extracting','chunking','embedding','ready','failed','deleted')),
 error_message text, chunk_count integer not null default 0, extraction_note text,
 created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create index documents_org_status_idx on public.documents(organization_id,status);
create unique index documents_hash_idx on public.documents(organization_id,content_hash) where status <> 'deleted';
create table public.chunks (
 id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.organizations(id) on delete cascade,
 document_id uuid not null references public.documents(id) on delete cascade, ordinal integer not null,
 content text not null, location jsonb not null default '{}', embedding extensions.vector(1536) not null,
 embedding_model text not null, search_vector tsvector generated always as (to_tsvector('simple',content)) stored,
 unique(document_id,ordinal)
);
create index chunks_embedding_idx on public.chunks using hnsw (embedding extensions.vector_cosine_ops);
create index chunks_search_idx on public.chunks using gin(search_vector);
create index chunks_org_idx on public.chunks(organization_id);
create table public.ingestion_jobs (
 id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.organizations(id) on delete cascade,
 document_id uuid not null references public.documents(id) on delete cascade,
 kind text not null default 'ingest' check(kind in ('ingest','delete')),
 status text not null default 'queued' check(status in ('queued','running','done','failed')),
 attempts integer not null default 0, lease_until timestamptz, available_at timestamptz not null default now(),
 last_error text, created_at timestamptz not null default now()
);
create index jobs_claim_idx on public.ingestion_jobs(status,available_at);
create table public.conversations (
 id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.organizations(id) on delete cascade,
 user_id uuid not null references auth.users(id), title text not null default 'New conversation', created_at timestamptz not null default now()
);
create table public.messages (
 id uuid primary key default gen_random_uuid(), conversation_id uuid not null references public.conversations(id) on delete cascade,
 organization_id uuid not null references public.organizations(id) on delete cascade,
 role text not null check(role in ('user','assistant')), content text not null,
 citations jsonb not null default '[]', model text, created_at timestamptz not null default now()
);
create table public.invitations (
 id uuid primary key default gen_random_uuid(), organization_id uuid not null references public.organizations(id) on delete cascade,
 email text not null, role text not null check(role in ('admin','employee')), token_hash text not null unique,
 invited_by uuid not null references auth.users(id), expires_at timestamptz not null default now()+interval '7 days',
 accepted_at timestamptz, created_at timestamptz not null default now()
);
create table public.audit_events (
 id bigint generated always as identity primary key, organization_id uuid not null references public.organizations(id) on delete cascade,
 user_id uuid references auth.users(id), action text not null, details jsonb not null default '{}', created_at timestamptz not null default now()
);
create table public.usage_events (
 id bigint generated always as identity primary key, organization_id uuid not null references public.organizations(id) on delete cascade,
 user_id uuid references auth.users(id), kind text not null, model text, total_tokens integer, duration_ms integer,
 created_at timestamptz not null default now()
);

alter table public.organizations enable row level security;
alter table public.memberships enable row level security;
alter table public.documents enable row level security;
alter table public.chunks enable row level security;
alter table public.ingestion_jobs enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.invitations enable row level security;
alter table public.audit_events enable row level security;
alter table public.usage_events enable row level security;
create policy org_read on public.organizations for select to authenticated using(public.is_member(id));
create policy member_read on public.memberships for select to authenticated using(public.is_member(organization_id));
create policy docs_read on public.documents for select to authenticated using(public.is_member(organization_id) and status <> 'deleted');
create policy chunks_read on public.chunks for select to authenticated using(public.is_member(organization_id) and exists(select 1 from public.documents d where d.id=document_id and d.organization_id=chunks.organization_id and d.status='ready'));
create policy conv_read on public.conversations for select to authenticated using(user_id=auth.uid() and public.is_member(organization_id));
create policy conv_insert on public.conversations for insert to authenticated with check(user_id=auth.uid() and public.is_member(organization_id));
create policy conv_delete on public.conversations for delete to authenticated using(user_id=auth.uid() and public.is_member(organization_id));
create policy msg_read on public.messages for select to authenticated using(public.is_member(organization_id) and exists(select 1 from public.conversations c where c.id=conversation_id and c.organization_id=messages.organization_id and c.user_id=auth.uid()));
create policy msg_insert on public.messages for insert to authenticated with check(public.is_member(organization_id) and exists(select 1 from public.conversations c where c.id=conversation_id and c.organization_id=messages.organization_id and c.user_id=auth.uid()));
create policy invite_read on public.invitations for select to authenticated using(public.is_admin(organization_id));
create policy audit_read on public.audit_events for select to authenticated using(public.is_admin(organization_id));
create policy usage_read on public.usage_events for select to authenticated using(public.is_admin(organization_id));

create function public.create_organization(workspace_name text, full_name text default '') returns uuid language plpgsql security definer set search_path='' as $$
declare result uuid; user_email text;
begin
 if auth.uid() is null then raise exception 'Authentication required'; end if;
 select email into user_email from auth.users where id=auth.uid() and email_confirmed_at is not null;
 if user_email is null then raise exception 'Confirm your email before creating a workspace'; end if;
 if (select count(*) from public.memberships where user_id=auth.uid() and role='admin') >= 5 then raise exception 'Workspace limit reached'; end if;
 insert into public.organizations(name,created_by) values(trim(workspace_name),auth.uid()) returning id into result;
 insert into public.memberships(organization_id,user_id,role,email,display_name) values(result,auth.uid(),'admin',user_email,left(full_name,100));
 insert into public.audit_events(organization_id,user_id,action) values(result,auth.uid(),'workspace.created');
 return result;
end; $$;

create function public.register_document(org uuid, doc_id uuid, filename text, mime text, bytes bigint, hash text, folder text default 'General') returns uuid language plpgsql security definer set search_path='' as $$
begin
 if not public.is_admin(org) then raise exception 'Only workspace admins can upload'; end if;
 perform pg_advisory_xact_lock(hashtextextended(org::text,0));
 if (select count(*) from public.documents where organization_id=org and status<>'deleted') >= 200 then raise exception 'Document limit reached'; end if;
 if (select coalesce(sum(size_bytes),0) from public.documents where organization_id=org and status<>'deleted')+bytes > 524288000 then raise exception 'Workspace storage limit reached'; end if;
 insert into public.documents(id,organization_id,uploaded_by,name,mime_type,size_bytes,content_hash,storage_path,collection)
 values(doc_id,org,auth.uid(),left(filename,250),mime,bytes,hash,org::text||'/'||doc_id::text||'/original',left(folder,80));
 insert into public.audit_events(organization_id,user_id,action,details) values(org,auth.uid(),'document.registered',jsonb_build_object('document_id',doc_id));
 return doc_id;
end; $$;

create function public.enqueue_document(doc uuid) returns void language plpgsql security definer set search_path='' as $$
declare org uuid;
begin
 select organization_id into org from public.documents where id=doc for update;
 if not public.is_admin(org) then raise exception 'Only workspace admins can queue'; end if;
 if not exists(select 1 from public.documents where id=doc and status in ('uploaded','failed')) then raise exception 'Document cannot be queued'; end if;
 update public.documents set status='queued',error_message=null,updated_at=now() where id=doc;
 insert into public.ingestion_jobs(organization_id,document_id) values(org,doc);
end; $$;

create function public.delete_document(doc uuid) returns void language plpgsql security definer set search_path='' as $$
declare org uuid;
begin
 select organization_id into org from public.documents where id=doc for update;
 if not public.is_admin(org) then raise exception 'Only workspace admins can delete'; end if;
 update public.documents set status='deleted',updated_at=now() where id=doc;
 delete from public.chunks where document_id=doc;
 insert into public.ingestion_jobs(organization_id,document_id,kind) values(org,doc,'delete');
 insert into public.audit_events(organization_id,user_id,action,details) values(org,auth.uid(),'document.deleted',jsonb_build_object('document_id',doc));
end; $$;

create function public.create_invitation(org uuid, invite_email text, invite_role text, secret_hash text) returns uuid language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
 if not public.is_admin(org) then raise exception 'Only workspace admins can invite'; end if;
 if invite_role not in ('admin','employee') or length(secret_hash)<>64 then raise exception 'Invalid invitation'; end if;
 insert into public.invitations(organization_id,email,role,token_hash,invited_by) values(org,lower(trim(invite_email)),invite_role,secret_hash,auth.uid()) returning id into result;
 return result;
end; $$;
create function public.accept_invitation(secret_hash text, full_name text default '') returns uuid language plpgsql security definer set search_path='' as $$
declare invitation public.invitations; user_email text;
begin
 select email into user_email from auth.users where id=auth.uid() and email_confirmed_at is not null;
 if user_email is null then raise exception 'Verified email required'; end if;
 select * into invitation from public.invitations where token_hash=secret_hash and accepted_at is null and expires_at>now() for update;
 if invitation.id is null or lower(user_email)<>invitation.email then raise exception 'Invitation is expired or belongs to another email'; end if;
 insert into public.memberships(organization_id,user_id,role,email,display_name) values(invitation.organization_id,auth.uid(),invitation.role,user_email,left(full_name,100)) on conflict do nothing;
 update public.invitations set accepted_at=now() where id=invitation.id;
 insert into public.audit_events(organization_id,user_id,action) values(invitation.organization_id,auth.uid(),'member.joined');
 return invitation.organization_id;
end; $$;

create function public.reserve_question(org uuid) returns void language plpgsql security definer set search_path='' as $$
begin
 if not public.is_member(org) then raise exception 'Workspace access denied'; end if;
 perform pg_advisory_xact_lock(hashtextextended(org::text,1));
 if (select count(*) from public.usage_events where organization_id=org and kind='question' and created_at>date_trunc('day',now()))>=200 then raise exception 'Daily workspace question limit reached'; end if;
 if (select count(*) from public.usage_events where user_id=auth.uid() and kind='question' and created_at>now()-interval '1 minute')>=10 then raise exception 'Please wait before asking another question'; end if;
 insert into public.usage_events(organization_id,user_id,kind) values(org,auth.uid(),'question');
end; $$;

create function public.hybrid_search(org uuid, query_text text, query_embedding extensions.vector(1536), result_limit integer default 8, folder text default null)
returns table(id uuid,document_id uuid,content text,location jsonb,document_name text,collection text,score double precision)
language sql stable security invoker set search_path='' as $$
 with eligible as (
 select c.*,d.name,d.collection from public.chunks c join public.documents d on d.id=c.document_id
 where c.organization_id=org and d.organization_id=org and d.status='ready' and public.is_member(org) and (folder is null or d.collection=folder)
 ), semantic as (
 select id,row_number() over(order by embedding operator(extensions.<=>) query_embedding) rank from eligible where query_embedding is not null order by embedding operator(extensions.<=>) query_embedding limit 24
 ), lexical as (
 select id,row_number() over(order by ts_rank_cd(search_vector,websearch_to_tsquery('simple',query_text)) desc) rank
 from eligible where search_vector @@ websearch_to_tsquery('simple',query_text) order by ts_rank_cd(search_vector,websearch_to_tsquery('simple',query_text)) desc limit 24
 ), fused as (
 select coalesce(s.id,l.id) id,coalesce(1.0/(60+s.rank),0)+coalesce(1.0/(60+l.rank),0) score from semantic s full outer join lexical l on s.id=l.id
 ) select e.id,e.document_id,e.content,e.location,e.name,e.collection,f.score::double precision from fused f join eligible e on e.id=f.id order by f.score desc limit least(greatest(result_limit,1),20);
$$;

create function public.claim_job() returns setof public.ingestion_jobs language plpgsql security definer set search_path='' as $$
begin
 return query with candidate as (
 select id from public.ingestion_jobs where attempts<3 and ((status='queued' and available_at<=now()) or (status='running' and lease_until<now())) order by created_at for update skip locked limit 1
 ) update public.ingestion_jobs j set status='running',attempts=j.attempts+1,lease_until=now()+interval '10 minutes' from candidate where j.id=candidate.id returning j.*;
end; $$;
create function public.publish_document(doc uuid, job uuid, expected_attempt integer, note text default null) returns boolean language plpgsql security definer set search_path='' as $$
declare current_doc public.documents;
begin
 select * into current_doc from public.documents where id=doc for update;
 if current_doc.status='deleted' or not exists(select 1 from public.ingestion_jobs where id=job and document_id=doc and status='running' and attempts=expected_attempt and lease_until>now()) then return false; end if;
 update public.documents set status='ready',chunk_count=(select count(*) from public.chunks where document_id=doc),extraction_note=note,error_message=null,updated_at=now() where id=doc;
 update public.ingestion_jobs set status='done',lease_until=null where id=job;
 return true;
end; $$;

revoke all on function public.claim_job() from public,anon,authenticated;
revoke all on function public.publish_document(uuid,uuid,integer,text) from public,anon,authenticated;
grant execute on function public.claim_job() to service_role;
grant execute on function public.publish_document(uuid,uuid,integer,text) to service_role;
revoke all on function public.create_organization(text,text), public.register_document(uuid,uuid,text,text,bigint,text,text), public.enqueue_document(uuid), public.delete_document(uuid), public.create_invitation(uuid,text,text,text), public.accept_invitation(text,text), public.reserve_question(uuid), public.hybrid_search(uuid,text,extensions.vector,integer,text) from public,anon;
grant execute on function public.create_organization(text,text), public.register_document(uuid,uuid,text,text,bigint,text,text), public.enqueue_document(uuid), public.delete_document(uuid), public.create_invitation(uuid,text,text,text), public.accept_invitation(text,text), public.reserve_question(uuid), public.hybrid_search(uuid,text,extensions.vector,integer,text) to authenticated;

insert into storage.buckets(id,name,public,file_size_limit) values('company-documents','company-documents',false,26214400) on conflict(id) do nothing;
create policy atlas_storage_read on storage.objects for select to authenticated using(bucket_id='company-documents' and exists(select 1 from public.documents d where d.storage_path=storage.objects.name and d.status<>'deleted' and public.is_member(d.organization_id)));
create policy atlas_storage_upload on storage.objects for insert to authenticated with check(bucket_id='company-documents' and exists(select 1 from public.documents d where d.storage_path=storage.objects.name and d.status='uploaded' and d.uploaded_by=auth.uid() and public.is_admin(d.organization_id)));
