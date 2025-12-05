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
    Foca em formatação empresarial e layout limpo.
    """

    @staticmethod
    def generate_excel(df: pd.DataFrame) -> bytes:
        """
        Gera um arquivo Excel (.xlsx) altamente formatado em memória.
        """
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
                }
            )

            string_format = workbook.add_format({"border": 1})
            number_format = workbook.add_format({"num_format": "0.0", "border": 1})

            # Aplica formatação nas colunas
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

                # Aplica formatação condicional baseada no tipo da coluna
                cell_format = string_format
                if pd.api.types.is_numeric_dtype(df[value]):
                    cell_format = number_format

                # Ajuste de largura (Auto-fit aproximado)
                column_len = (
                    max(df[value].astype(str).map(len).max(), len(str(value))) + 2
                )
                worksheet.set_column(
                    col_num, col_num, min(column_len, 50), cell_format
                )  # Max 50 chars width + format

        return output.getvalue()

        return output.getvalue()

    @staticmethod
    def generate_pdf(
        df: pd.DataFrame,
        title: str = "Relatório de Dados ENEM",
        filter_summary: str = "Filtros: N/A",
    ) -> bytes:
        """
        Gera um PDF vetorial profissional usando HTML/CSS (WeasyPrint).
        """
        try:
            limit_pdf = 2000
            truncated = False
            original_count = len(df)

            if original_count > limit_pdf:
                df = df.head(limit_pdf)
                truncated = True
                logger.warning(
                    f"PDF truncado: {original_count} linhas reduzidas para {limit_pdf} para evitar OOM."
                )

            # Template HTML Minimalista e Elegante
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    @page {
                        size: A4 landscape;
                        margin: 1cm;
                        @bottom-right {
                            content: "Página " counter(page) " de " counter(pages);
                            font-size: 9pt;
                            font-family: sans-serif;
                            color: #666;
                        }
                        @bottom-left {
                            content: "Gerado em {{ date }} - ENEM Data Robotics";
                            font-size: 9pt;
                            font-family: sans-serif;
                            color: #666;
                        }
                    }
                    body {
                        font-family: 'Helvetica', 'Arial', sans-serif;
                        font-size: 10pt;
                        color: #333;
                    }
                    h1 {
                        color: #1F4E78;
                        border-bottom: 2px solid #1F4E78;
                        padding-bottom: 10px;
                        margin-bottom: 20px;
                    }
                    .filter-summary {
                        font-size: 10pt;
                        color: #555;
                        margin-bottom: 15px;
                    }
                    .warning {
                        background-color: #fff3cd;
                        color: #856404;
                        padding: 10px;
                        border: 1px solid #ffeeba;
                        margin-bottom: 15px;
                        border-radius: 4px;
                        font-size: 9pt;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 10px;
                    }
                    th {
                        background-color: #1F4E78;
                        color: white;
                        font-weight: bold;
                        text-align: left;
                        padding: 8px;
                        font-size: 9pt;
                    }
                    td {
                        border-bottom: 1px solid #ddd;
                        padding: 6px 8px;
                        font-size: 9pt;
                    }
                    tr:nth-child(even) {
                        background-color: #f2f2f2;
                    }
                    .footer {
                        margin-top: 20px;
                        font-size: 8pt;
                        text-align: center;
                        color: #777;
                    }
                </style>
            </head>
            <body>
                <h1>{{ title }}</h1>
                <p class="filter-summary">{{ filter_summary }}</p>
                
                {% if truncated %}
                <div class="warning">
                    <strong>Aviso:</strong> Este relatório PDF contém apenas as primeiras {{ limit }} linhas. 
                    Para o conjunto de dados completo, utilize a exportação em Excel.
                </div>
                {% endif %}
                
                {{ table_html }}
                
                <div class="footer">
                    Relatório gerado automaticamente pela plataforma ENEM Data Robotics.
                </div>
            </body>
            </html>
            """

            # Renderiza o HTML com os dados
            template = jinja2.Template(html_template)

            # Converte DataFrame para HTML limpo (sem classes default do pandas)
            table_html = df.to_html(
                index=False, border=0, classes=[], float_format="%.1f"
            )

            # Prepara o contexto
            context = {
                "title": title,
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "filter_summary": filter_summary,
                "table_html": table_html,
                "truncated": truncated,
                "limit": limit_pdf,
                "total_rows": original_count,
            }

            rendered_html = template.render(context)

            # Gera o PDF
            pdf_file = HTML(string=rendered_html).write_pdf()
            return pdf_file

        except Exception as e:
            logger.error(f"Erro crítico ao gerar PDF: {e}", exc_info=True)
            raise e
