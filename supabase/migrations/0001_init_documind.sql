-- DocuMind: documentos, trechos com embeddings e bucket privado de PDFs.
-- Rodar manualmente no SQL Editor do Supabase.

create extension if not exists vector with schema extensions;

create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    filename text not null,
    storage_path text not null,
    pages integer not null,
    characters integer not null,
    created_at timestamptz not null default now()
);

create table if not exists public.chunks (
    id bigserial primary key,
    document_id uuid not null references public.documents (id) on delete cascade,
    chunk_index integer not null,
    page integer not null,
    content text not null,
    embedding extensions.vector(768) not null
);

create index if not exists chunks_embedding_hnsw_idx
    on public.chunks using hnsw (embedding extensions.vector_cosine_ops);

create index if not exists chunks_document_id_idx on public.chunks (document_id);

-- RLS ligado e sem políticas: só a service role (backend) acessa.
alter table public.documents enable row level security;
alter table public.chunks enable row level security;

create or replace function public.match_chunks(
    query_embedding extensions.vector(768),
    doc_id uuid,
    match_count int default 5
)
returns table (
    id bigint,
    chunk_index integer,
    page integer,
    content text,
    similarity float
)
language sql
stable
set search_path = public, extensions
as $$
    select
        chunks.id,
        chunks.chunk_index,
        chunks.page,
        chunks.content,
        1 - (chunks.embedding <=> query_embedding) as similarity
    from chunks
    where chunks.document_id = doc_id
    order by chunks.embedding <=> query_embedding
    limit match_count;
$$;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('documents', 'documents', false, 10485760, array['application/pdf'])
on conflict (id) do nothing;
