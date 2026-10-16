-- Run once in the SQL Editor of the project configured in index.html.
-- This table contains no application or user data.
begin;

create table if not exists public.etravel_keepalive (
  id smallint primary key check (id = 1)
);

insert into public.etravel_keepalive (id) values (1)
on conflict (id) do nothing;

alter table public.etravel_keepalive enable row level security;

revoke all on table public.etravel_keepalive from public, anon, authenticated;
grant select (id) on table public.etravel_keepalive to anon;

drop policy if exists "Anonymous keepalive read" on public.etravel_keepalive;
create policy "Anonymous keepalive read"
on public.etravel_keepalive for select to anon using (true);

notify pgrst, 'reload schema';
commit;
