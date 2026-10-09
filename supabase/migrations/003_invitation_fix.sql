create or replace function public.create_invitation(org uuid, invite_email text, invite_role text, secret_hash text) returns uuid language plpgsql security definer set search_path='' as $$
declare result uuid;
begin
 if not public.is_admin(org) then raise exception 'Only workspace admins can invite'; end if;
 if invite_role not in ('admin','employee') or length(secret_hash)<>64 then raise exception 'Invalid invitation'; end if;
 insert into public.invitations(organization_id,email,role,token_hash,invited_by) values(org,lower(trim(invite_email)),invite_role,secret_hash,auth.uid()) returning id into result;
 return result;
end; $$;
