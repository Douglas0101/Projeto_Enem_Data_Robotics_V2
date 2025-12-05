from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..orchestrator.agents.data_analyst import DataAnalystAgent
from ..infra.logging import logger

router = APIRouter(prefix="/v1/chat", tags=["chat"])

# Instância global do agente (Singleton simples para este contexto local)
# Em produção, usaríamos sessões persistentes.
_agent_instance: Optional[DataAnalystAgent] = None

def get_agent() -> DataAnalystAgent:
    global _agent_instance
    if _agent_instance is None:
        try:
            _agent_instance = DataAnalystAgent()
        except Exception as e:
            logger.error(f"Falha ao inicializar agente de IA: {e}")
            raise HTTPException(status_code=503, detail="Serviço de IA indisponível (verifique API KEY)")
    return _agent_instance


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Envia uma mensagem para o Assistente de Dados e recebe a resposta.
    O agente tem acesso autônomo ao banco de dados DuckDB para responder perguntas factuais.
    """
    agent = get_agent()
    
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    logger.info(f"💬 Chat recebido: {request.message}")
    
    try:
        # Processamento síncrono (o Gemini SDK é síncrono por padrão, mas rápido o suficiente para demo)
        # Se demorar muito, considerar rodar em threadpool.
        response_text = agent.send_message(request.message)
        return ChatResponse(response=response_text)
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no processamento da IA")
