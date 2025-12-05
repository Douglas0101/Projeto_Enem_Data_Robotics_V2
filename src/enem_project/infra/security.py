import hashlib
import logging
import pandas as pd

logger = logging.getLogger("security")

class SecurityEngine:
    """
    Motor de segurança para aplicação de políticas de proteção de dados (LGPD),
    assinatura digital e validação de integridade.
    """

    @staticmethod
    def apply_dynamic_masking(df: pd.DataFrame, role: str = "user") -> pd.DataFrame:
        """
        Aplica máscara dinâmica de dados (DDM) em colunas sensíveis baseada na role do usuário.
        Em conformidade com LGPD, anonimiza dados pessoais para usuários sem privilégio administrativo.

        Args:
            df (pd.DataFrame): DataFrame contendo os dados a serem processados.
            role (str): Papel do usuário ('admin', 'user', 'analyst').

        Returns:
            pd.DataFrame: DataFrame com colunas sensíveis mascaradas se necessário.
        """
        if role == "admin":
            return df

        # Trabalha em uma cópia para não afetar o objeto original se for usado em outro lugar
        masked_df = df.copy()

        for col in masked_df.columns:
            col_upper = col.upper()
            # Lógica heurística ou explicita para identificar PII
            if col_upper in ["NU_INSCRICAO", "CPF", "NOME_CANDIDATO", "EMAIL"]:
                # Aplica máscara
                masked_df[col] = masked_df[col].apply(lambda x: SecurityEngine._mask_value(str(x), "partial"))
            
        return masked_df

    @staticmethod
    def _mask_value(value: str, method: str) -> str:
        """
        Função auxiliar para mascarar um único valor.
        """
        if not value or value.lower() == "nan" or value.lower() == "none":
            return ""
        
        if len(value) <= 4:
            return "*" * len(value)

        if method == "partial":
            # Mostra os primeiros 2 e últimos 2 caracteres
            return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
        elif method == "hash":
             return hashlib.sha256(value.encode()).hexdigest()[:16]
        else:
            return "*" * len(value)

    @staticmethod
    def verify_export_signature(file_hash: str) -> bool:
        """
        Stub para validação de não-repúdio.
        Verifica se o hash do arquivo exportado corresponde a um registro auditado válido.
        
        Args:
            file_hash (str): Hash SHA-256 do arquivo gerado.

        Returns:
            bool: True se a assinatura for válida/reconhecida, False caso contrário.
        """
        # TODO: Implementar verificação contra tabela de auditoria de exports (tb_audit_exports)
        # Por enquanto, simula uma validação bem-sucedida para hashes não nulos
        if not file_hash:
            return False
            
        logger.info(f"Verificando assinatura digital do arquivo: {file_hash}")
        return True
