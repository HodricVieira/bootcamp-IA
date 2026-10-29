from app.services.document_search import TextChunk


def generate_answer(question: str, chunks: list[TextChunk]) -> str:
    """Retorna uma mensagem explícita até que um provedor de IA seja configurado."""
    if not chunks:
        return "Não encontrei informações relevantes no documento para responder à pergunta."
    return (
        "A geração de respostas por IA ainda não foi configurada. "
        "Consulte os trechos encontrados nas fontes abaixo."
    )
