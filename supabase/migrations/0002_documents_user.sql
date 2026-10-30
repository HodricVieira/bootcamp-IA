-- Associa cada documento ao usuário autenticado do Supabase Auth.
alter table public.documents
    add column if not exists user_id uuid references auth.users (id) on delete cascade;

create index if not exists documents_user_id_idx on public.documents (user_id);

alter table public.documents enable row level security;
alter table public.chunks enable row level security;

drop policy if exists "Users can access their documents" on public.documents;
create policy "Users can access their documents"
    on public.documents for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "Users can access their document chunks" on public.chunks;
create policy "Users can access their document chunks"
    on public.chunks for all
    using (
        exists (
            select 1 from public.documents
            where documents.id = chunks.document_id
              and documents.user_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1 from public.documents
            where documents.id = chunks.document_id
              and documents.user_id = auth.uid()
        )
    );
