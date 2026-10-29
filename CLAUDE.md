# DocuMind — contexto do projeto

MVP do Bootcamp IA First. É um chatbot que recebe **um PDF por sessão** e responde perguntas usando **somente** o conteúdo desse PDF, mostrando o trecho e a página que fundamentam cada resposta. Quando o documento não tem base para responder, o sistema devolve sempre a mesma mensagem fixa:

> Não encontrei informações sobre isso no documento enviado.

## Stack

- `backend/`: FastAPI, Python 3.12, PyMuPDF, SDK `google-genai`, Supabase (pgvector + Storage).
- `frontend/`: HTML + CSS + JS puro (`index.html`, `app.js`, `styles.css`), servido pelo FastAPI via `StaticFiles` em `/`. **Não migrar para React/Vite.**
- Modelos: `gemini-3.6-flash` para respostas e `gemini-embedding-001` (768 dimensões) para embeddings, configuráveis por `.env`.

## Onde fica cada etapa do RAG (`backend/app/services/`)

| Etapa | Arquivo |
| --- | --- |
| Extrair texto por página | `pdf_reader.py` |
| Dividir em trechos | `document_search.py` (`split_into_chunks`) |
| Embeddings | `embeddings.py` |
| Guardar e buscar por similaridade | `document_store.py` (memória ou Supabase) |
| Montar prompt + gerar com Gemini | `ai_service.py` |

As rotas ficam em `app/api/routes/documents.py`.

## Regras

- Branch `feat/documind-mvp`. Um commit por etapa, mensagens em português. **Não fazer push nem merge sem pedir.**
- Configuração em `app/core/config.py` com prefixo `DOCUMIND_`. Nunca escrever chaves no código. Atualizar `backend/.env.example` sempre que surgir uma variável nova.
- Rodar `pytest` dentro de `backend/` ao fim de cada etapa e só concluir com tudo verde.
- Testes usam fakes (embedder e answerer falsos) e store em memória, sem rede. Testes que chamam o Gemini real usam `@pytest.mark.integration` e são pulados sem `DOCUMIND_GEMINI_API_KEY`.
- Não executar nada no Supabase pelo código ou CLI: o SQL fica em `supabase/migrations/` e é rodado manualmente no painel.
- Usar só PDFs públicos ou fictícios. Não registrar em log o conteúdo do documento nem a pergunta completa.
- No front, usar sempre `textContent`, nunca `innerHTML` com dados da API.

## Contrato da API

- `GET /health`
- `POST /documents/upload`: multipart, campo `file`, devolve 201 com `document_id`, `filename`, `pages`, `characters`, `status`.
- `POST /documents/{id}/ask`: body `{"question": "..."}`, devolve o JSON abaixo.

```json
{"document_id": "...", "question": "...", "found": true,
 "answer": "O prazo é 15 de fevereiro [1].",
 "sources": [{"ref": 1, "page": 1, "text": "...", "score": 0.82}]}
```

  Quando `found` for `false`, `answer` é a mensagem fixa e `sources` vem vazio.
- `DELETE /documents/{id}`: devolve 204.

Erros:

| Código | Situação |
| --- | --- |
| 400 | Arquivo vazio ou inválido |
| 413 | Acima de 10 MB ou de 100 páginas |
| 415 | Arquivo não é PDF |
| 404 | Documento inexistente |
| 502 | Falha no Gemini, com a mensagem "O serviço de IA não respondeu. Tente de novo." |
