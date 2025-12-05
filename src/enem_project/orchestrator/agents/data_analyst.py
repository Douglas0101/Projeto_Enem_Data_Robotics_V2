from __future__ import annotations

import google.generativeai as genai
import duckdb
import textwrap

from ...config.settings import settings
from ...infra.db import get_duckdb_conn, register_parquet_views
from ...infra.logging import logger

# Configuração Global do Gemini
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


def get_database_context() -> str:
    """
    Recupera o esquema (DDL) das tabelas de dashboard para informar o LLM
    sobre a estrutura do banco de dados.
    """
    conn = get_duckdb_conn(read_only=True)
    try:
        # Registra as views para garantir que existam na sessão
        register_parquet_views(conn)

        tables_of_interest = [
            "gold_tb_notas_stats",
            "gold_tb_notas_geo",
            "gold_tb_notas_geo_uf",
            "gold_tb_notas_histogram",
        ]

        schema_text = "ESQUEMA DO BANCO DE DADOS (DuckDB):\n\n"

        for table in tables_of_interest:
            try:
                # Pega o DDL da view/tabela
                # No DuckDB, 'DESCRIBE table' retorna colunas e tipos.
                df = conn.sql(f"DESCRIBE {table}").df()

                schema_text += f"TABELA: {table}\n"
                schema_text += "COLUNAS:\n"
                for _, row in df.iterrows():
                    schema_text += f"  - {row['column_name']} ({row['column_type']})\n"
                schema_text += "\n"
            except Exception:
                logger.warning(
                    f"Tabela {table} não encontrada ou vazia durante introspecção."
                )
                continue

        return schema_text
    finally:
        conn.close()


def execute_sql_query(query: str) -> str:
    """
    Executa uma consulta SQL no banco de dados DuckDB (modo somente leitura).
    Retorna o resultado formatado como Markdown ou mensagem de erro.
    """
    logger.info(f"🤖 Agente executando SQL: {query}")

    # Sanity Check Básico
    forbidden_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE"]
    if any(k in query.upper() for k in forbidden_keywords):
        return "ERRO: Consultas de modificação (DROP, DELETE, etc.) não são permitidas por segurança."

    conn = get_duckdb_conn(read_only=True)
    try:
        register_parquet_views(conn)

        # Executa e converte para DataFrame
        df = conn.sql(query).df()

        if df.empty:
            return "A consulta retornou 0 resultados."

        # Limita o tamanho da resposta para não estourar tokens
        if len(df) > 20:
            preview = df.head(20).to_markdown(index=False)
            return f"Retornando os primeiros 20 resultados de {len(df)} encontrados:\n\n{preview}"

        return df.to_markdown(index=False)

    except duckdb.Error as e:
        return f"ERRO SQL: {str(e)}"
    except Exception as e:
        return f"ERRO DESCONHECIDO: {str(e)}"
    finally:
        conn.close()


class DataAnalystAgent:
    def __init__(self):
        self.model_name = settings.GEMINI_MODEL_NAME
        self.schema_context = get_database_context()

        # Definição das Ferramentas (Tools)
        self.tools = [execute_sql_query]

        # Configuração do Modelo com Tools
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            tools=self.tools,
            system_instruction=self._get_system_prompt(),
        )

        self.chat = self.model.start_chat(enable_automatic_function_calling=True)

    def _get_system_prompt(self) -> str:
        return textwrap.dedent(f"""
            Você é o Assistente de Dados 'Data Robotics', um especialista em análise de dados educacionais do ENEM.
            Sua missão é responder perguntas dos usuários consultando o banco de dados SQL real.

            CONTEXTO DO BANCO DE DADOS:
            {self.schema_context}

            DIRETRIZES:
            1. Use SEMPRE a ferramenta 'execute_sql_query' para buscar dados. Não invente números.
            2. Ao gerar SQL, use sintaxe DuckDB. As tabelas estão disponíveis como views (ex: gold_tb_notas_stats).
            3. Prefira consultas agregadas (AVG, COUNT, GROUP BY) a menos que o usuário peça dados brutos.
            4. Se a resposta da ferramenta for uma tabela Markdown, apresente-a ao usuário e faça uma breve análise (1 parágrafo) sobre os destaques.
            5. Se o usuário perguntar algo fora do contexto do ENEM ou dos dados disponíveis, explique educadamente que só tem acesso a esses dados.
            6. Seja conciso e profissional. Use formatação Markdown (negrito, listas) para facilitar a leitura.
            
            EXEMPLOS DE QUERIES:
            - Média por ano: "SELECT ANO, AVG(NOTA_MATEMATICA_mean) FROM gold_tb_notas_stats GROUP BY ANO ORDER BY ANO"
            - Melhor estado em 2023: "SELECT SG_UF_PROVA, NOTA_MATEMATICA_mean FROM gold_tb_notas_geo_uf WHERE ANO=2023 ORDER BY NOTA_MATEMATICA_mean DESC LIMIT 5"
        """)

    def send_message(self, user_message: str) -> str:
        """
        Envia uma mensagem para o agente e retorna a resposta textual final.
        """
        try:
            response = self.chat.send_message(user_message)
            return response.text
        except Exception as e:
            logger.error(f"Erro no chat do agente: {e}")
            return "Desculpe, encontrei um erro ao processar sua solicitação. Verifique se a chave de API está configurada corretamente."
