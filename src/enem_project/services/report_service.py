import io
import logging
from datetime import datetime
import pandas as pd
import jinja2
from weasyprint import HTML

logger = logging.getLogger(__name__)


class ReportService:
    """
    Serviço profissional de geração de relatórios (Excel e PDF).
    Foca em formatação empresarial, layout limpo e sanitização de dados.
    """

    @staticmethod
    def _sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
        """
        Higieniza o DataFrame para remover artefatos de CSV/DB, quebras de linha
        indesejadas e caracteres de controle que quebram a renderização.
        Garante que a sanitização ocorra em todas as colunas string-like.
        """
        df = df.copy()

        for col in df.columns:
            # Tenta converter para string se ainda não for, para aplicar str methods
            if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
                df[col] = df[col].astype(str).replace(r"[\n\r\t]+", " ", regex=True)
                df[col] = df[col].str.replace(r"^["']+|"['"]+$", "", regex=True)
                df[col] = df[col].str.strip()
                # Tenta converter strings numéricas limpas de volta para números
                df[col] = pd.to_numeric(df[col], errors="ignore")
            # Para colunas já numéricas (após primeira tentativa ou originais), garante formatação padrão
            elif pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].fillna(0) # Preenche NaN com 0
                
                # Se for float, tenta converter para int se for "inteiro seguro"
                if pd.api.types.is_float_dtype(df[col]):
                    # Verifica se todos os valores são inteiros (ex: 3048.0)
                    # Usar uma tolerância pequena ou comparação direta
                    try:
                        if (df[col] % 1 == 0).all():
                            df[col] = df[col].astype(int)
                        else:
                            df[col] = df[col].round(1)
                    except Exception:
                        pass # Mantém como float se falhar a verificação

        return df

    @staticmethod
    def generate_excel(df: pd.DataFrame) -> bytes:
        """
        Gera um arquivo Excel (.xlsx) altamente formatado em memória.
        Aplica sanitização prévia e formatação condicional de colunas.
        """
        # 1. Sanitização Defensiva
        df = ReportService._sanitize_df(df)

        output = io.BytesIO()

        # Engine xlsxwriter permite formatação avançada
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Dados ENEM")

            workbook = writer.book
            worksheet = writer.sheets["Dados ENEM"]

            # Definição de Estilos Profissionais
            header_format = workbook.add_format(
                {
                    "bold": True,
                    "text_wrap": True,
                    "valign": "top",
                    "fg_color": "#1F4E78",  # Azul Corporativo
                    "font_color": "#FFFFFF",
                    "border": 1,
                    "align": "center",
                }
            )

            # Formato para texto (alinhado à esquerda, borda)
            string_format = workbook.add_format(
                {"border": 1, "valign": "vcenter", "text_wrap": False, "align": "left"}
            )

            # Formato para números (alinhado à direita, 1 casa decimal, borda)
            number_format = workbook.add_format(
                {"num_format": "#,##0.0", "border": 1, "valign": "vcenter", "align": "right"}
            )
            
            # Formato para números inteiros
            int_format = workbook.add_format(
                {"num_format": "#,##0", "border": 1, "valign": "vcenter", "align": "right"}
            )

            # Aplica formatação nas colunas
            for col_num, col_name in enumerate(df.columns.values):
                # Escreve o cabeçalho novamente para garantir o estilo
                worksheet.write(0, col_num, col_name, header_format)

                # Lógica de largura de coluna (Autofit com limites)
                max_len_data = 0
                if not df.empty:
                    # Amostra das primeiras 100 linhas para performance
                    sample = df[col_name].head(100).astype(str)
                    if not sample.empty: # Garante que a amostra não esteja vazia
                        max_len_data = sample.map(len).max()
                
                max_len_header = len(str(col_name))
                # Largura ideal: max(header, data) + padding
                column_width = min(max(max_len_data, max_len_header) + 3, 50)

                # Aplica o formato correto baseado no tipo de dado
                if pd.api.types.is_integer_dtype(df[col_name]):
                    worksheet.set_column(col_num, col_num, column_width, int_format)
                elif pd.api.types.is_numeric_dtype(df[col_name]):
                    worksheet.set_column(col_num, col_num, column_width, number_format)
                else:
                    worksheet.set_column(col_num, col_num, column_width, string_format)

        return output.getvalue()

    @staticmethod
    def generate_pdf(
        df: pd.DataFrame,
        title: str = "Relatório de Dados ENEM",
        filter_summary: str = "Filtros: N/A",
    ) -> bytes:
        """
        Gera um PDF vetorial profissional usando HTML/CSS (WeasyPrint).
        Aplica sanitização e CSS defensivo para evitar quebras de layout.
        """
        try:
            # 1. Sanitização Defensiva
            df = ReportService._sanitize_df(df)

            limit_pdf = 2000
            truncated = False
            original_count = len(df)

            if original_count > limit_pdf:
                df = df.head(limit_pdf)
                truncated = True
                logger.warning(
                    f"PDF truncado: {original_count} linhas reduzidas para {limit_pdf} para evitar OOM."
                )

            # Formatação de valores para o HTML (para não ficar 123.45678)
            formatters = {}
            for col in df.columns:
                # Lógica específica para colunas de contagem (Inscritos, Provas Aplicadas)
                # Garante que sejam exibidos como inteiros mesmo se forem floats no DF
                col_lower = str(col).lower()
                if "inscritos" in col_lower or "provas" in col_lower or "qtd" in col_lower:
                     formatters[col] = lambda x: f"{int(x)}" if pd.notna(x) else ""
                
                elif pd.api.types.is_float_dtype(df[col]):
                    # Arredonda floats (médias) para 1 casa decimal
                    formatters[col] = lambda x: f"{x:.1f}".replace('.', ',') if pd.notna(x) else ""
                
                elif pd.api.types.is_integer_dtype(df[col]):
                    formatters[col] = lambda x: f"{int(x)}" if pd.notna(x) else ""


            html_table = df.to_html(
                index=False,
                border=0,
                classes=[],
                formatters=formatters,
                escape=True # Importante para segurança
            )

            # Template HTML Profissional
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    @page {
                        size: A4 landscape;
                        margin: 0.4cm; /* Margem ainda mais reduzida */
                        @bottom-right {
                            content: "Página " counter(page) " de " counter(pages);
                            font-size: 6.5pt;
                            font-family: sans-serif;
                            color: #666;
                        }
                        @bottom-left {
                            content: "Gerado em {{ date }} - ENEM Data Robotics";
                            font-size: 6.5pt;
                            font-family: sans-serif;
                            color: #666;
                        }
                    }
                    body {
                        font-family: 'Helvetica', 'Arial', sans-serif;
                        font-size: 9pt; /* Fonte base aumentada */
                        color: #333;
                        line-height: 1.2;
                    }
                    h1 {
                        color: #1F4E78;
                        border-bottom: 2px solid #1F4E78;
                        padding-bottom: 5px;
                        margin-bottom: 8px;
                        font-size: 12pt;
                        margin-top: 0;
                    }
                    .filter-summary {
                        font-size: 9pt;
                        color: #555;
                        margin-bottom: 10px;
                        font-style: italic;
                    }
                    .warning {
                        background-color: #fff3cd;
                        color: #856404;
                        padding: 5px;
                        border: 1px solid #ffeeba;
                        margin-bottom: 8px;
                        border-radius: 3px;
                        font-size: 8pt;
                    }
                    
                    /* Tabela Compacta e Profissional */
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        font-size: 7.5pt; /* Fonte de dados aumentada */
                        page-break-inside: auto;
                        table-layout: fixed; /* Força layout fixo para controle de largura */
                        word-break: break-all; /* Quebra qualquer palavra para caber */
                    }
                    
                    thead {
                        display: table-header-group;
                        border-bottom: 2px solid #1F4E78;
                    }
                    
                    tr {
                        page-break-inside: avoid;
                        page-break-after: auto;
                    }
                    
                    th {
                        background-color: #1F4E78;
                        color: white;
                        font-weight: bold;
                        text-align: center;
                        padding: 3px 2px; /* Padding reduzido */
                        border: 1px solid #ccc;
                        vertical-align: middle;
                        white-space: normal; /* Permite quebra no cabeçalho */
                        font-size: 8pt; /* Fonte do cabeçalho aumentada */
                    }
                    
                    td {
                        border: 1px solid #ccc;
                        padding: 2px; /* Padding reduzido */
                        vertical-align: middle;
                        word-wrap: break-word;
                        overflow-wrap: break-word;
                        text-align: center; /* Centralização solicitada para padronização */
                    }
                    
                    /* Tentativa de ajuste de largura de coluna - baseado no seu snippet */
                    /* Assume ordem de colunas: Ano, Estado, CO_MUNICIPIO_PROVA, Município, Total Inscritos, NOTA_... */
                    col:nth-child(1) { width: 5%; }  /* Ano */
                    col:nth-child(2) { width: 5%; }  /* Estado */
                    col:nth-child(3) { width: 10%; } /* CO_MUNICIPIO_PROVA */
                    col:nth-child(4) { width: 20%; } /* Município */
                    col:nth-child(5) { width: 10%; } /* Total Inscritos */
                    /* As demais 10 colunas (5 counts, 5 means) dividem os 50% restantes, ~5% cada */

                    tr:nth-child(even) {
                        background-color: #f7f7f7; /* Cor mais suave */
                    }
                </style>
            </head>
            <body>
                <h1>{{ title }}</h1>
                <p class="filter-summary">{{ filter_summary }}</p>
                
                {% if truncated %}
                <div class="warning">
                    <strong>Aviso:</strong> Exibindo apenas as primeiras {{ limit }} linhas. Use Excel para dados completos.
                </div>
                {% endif %} 
                
                {{ table_html }}
            </body>
            </html>
            """

            template = jinja2.Template(html_template)
            
            context = {
                "title": title,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "filter_summary": filter_summary,
                "table_html": html_table,
                "truncated": truncated,
                "limit": limit_pdf,
            }

            rendered_html = template.render(context)
            pdf_file = HTML(string=rendered_html).write_pdf()
            return pdf_file

        except Exception as e:
            logger.error(f"Erro crítico ao gerar PDF: {e}", exc_info=True)
            raise e