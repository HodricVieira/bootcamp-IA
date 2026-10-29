# DocuMind

MVP de uma API REST para extrair texto pesquisável de PDFs e recuperar trechos relevantes
por palavras-chave. A API foi construída com FastAPI e PyMuPDF.

## Pré-requisitos e instalação

É necessário Python 3.12 ou superior. Crie e ative um ambiente virtual:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Execute o servidor com `uvicorn app.main:app --reload`. A documentação Swagger fica em
`http://127.0.0.1:8000/docs`. A página inicial fica em `http://127.0.0.1:8000/`.

Na página inicial, envie um PDF pesquisável de até 10 MB, escreva uma pergunta e selecione
**Consultar documento**. O documento é enviado uma vez; depois, é possível fazer outras
perguntas sobre ele sem reenviar o arquivo. A API mantém os documentos em memória enquanto
o servidor estiver em execução.

## Endpoints

- `GET /health`: verifica o funcionamento.
- `POST /documents/upload`: recebe o campo multipart `file` e processa um PDF de até 10 MB.
- `GET /documents/{document_id}`: retorna somente os metadados.
- `POST /documents/{document_id}/ask`: recebe `{"question": "..."}` e retorna fontes encontradas.
- `DELETE /documents/{document_id}`: remove o documento da memória.

Exemplo:

```bash
curl -F "file=@regulamento.pdf" http://127.0.0.1:8000/documents/upload
curl -X POST http://127.0.0.1:8000/documents/ID/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Qual é o prazo?"}'
```

Quando houver contexto, a resposta contém `document_id`, `question`, `answer` e `sources`
(com página e texto). A resposta informa explicitamente que a geração por IA não foi
configurada; os trechos recuperados continuam disponíveis para integração futura.

## Arquitetura e limitações

O texto é extraído página a página por PyMuPDF. Páginas sem texto são ignoradas na busca,
mas não alteram a numeração. Os trechos são divididos sem separar palavras e a busca
normaliza maiúsculas e acentos para comparar palavras-chave.

O armazenamento é somente em memória: reiniciar o processo perde os documentos. O MVP não
faz OCR, autenticação, banco de dados ou RAG/embeddings. Por isso, deve ser usado localmente
ou em demonstrações, sem exposição pública de documentos privados. A interface de IA está
desacoplada em `app/services/ai_service.py` e pode receber um provedor configurado por
variável de ambiente em uma evolução posterior.

## Testes

```bash
pytest
```

Os testes geram PDFs em memória, não fazem chamadas a APIs pagas e cobrem upload, extração,
busca, perguntas, metadados, erros e remoção.
