from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from enem_project.infra.data_quality import (
    assert_dashboard_data_checks,
    run_dashboard_data_checks,
)


def _setup_test_db(path: Path) -> None:
    conn = duckdb.connect(path.as_posix())
    try:
        # tb_notas: apenas para validar row_count > 0
        tb_notas = pd.DataFrame(
            {
                "ANO": [2019, 2019],
                "ID_INSCRICAO": ["2019A", "2019B"],
                "NOTA_CIENCIAS_NATUREZA": [500.0, 600.0],
                "NOTA_CIENCIAS_HUMANAS": [550.0, 650.0],
                "NOTA_LINGUAGENS_CODIGOS": [580.0, 680.0],
                "NOTA_MATEMATICA": [520.0, 720.0],
                "NOTA_REDACAO": [600.0, 700.0],
            }
        )
        conn.register("tb_notas_df", tb_notas)
        conn.execute(
            "CREATE TABLE tb_notas AS SELECT * FROM tb_notas_df",
        )

        # tb_notas_stats: valores dentro de [0, 1000]
        tb_notas_stats = pd.DataFrame(
            {
                "ANO": [2019],
                "NOTA_CIENCIAS_NATUREZA_count": [2],
                "NOTA_CIENCIAS_NATUREZA_mean": [550.0],
                "NOTA_CIENCIAS_NATUREZA_std": [50.0],
                "NOTA_CIENCIAS_NATUREZA_min": [500.0],
                "NOTA_CIENCIAS_NATUREZA_median": [550.0],
                "NOTA_CIENCIAS_NATUREZA_max": [600.0],
                "NOTA_CIENCIAS_HUMANAS_count": [2],
                "NOTA_CIENCIAS_HUMANAS_mean": [600.0],
                "NOTA_CIENCIAS_HUMANAS_std": [50.0],
                "NOTA_CIENCIAS_HUMANAS_min": [550.0],
                "NOTA_CIENCIAS_HUMANAS_median": [600.0],
                "NOTA_CIENCIAS_HUMANAS_max": [650.0],
                "NOTA_LINGUAGENS_CODIGOS_count": [2],
                "NOTA_LINGUAGENS_CODIGOS_mean": [630.0],
                "NOTA_LINGUAGENS_CODIGOS_std": [50.0],
                "NOTA_LINGUAGENS_CODIGOS_min": [580.0],
                "NOTA_LINGUAGENS_CODIGOS_median": [630.0],
                "NOTA_LINGUAGENS_CODIGOS_max": [680.0],
                "NOTA_MATEMATICA_count": [2],
                "NOTA_MATEMATICA_mean": [620.0],
                "NOTA_MATEMATICA_std": [100.0],
                "NOTA_MATEMATICA_min": [520.0],
                "NOTA_MATEMATICA_median": [620.0],
                "NOTA_MATEMATICA_max": [720.0],
                "NOTA_REDACAO_count": [2],
                "NOTA_REDACAO_mean": [650.0],
                "NOTA_REDACAO_std": [50.0],
                "NOTA_REDACAO_min": [600.0],
                "NOTA_REDACAO_median": [650.0],
                "NOTA_REDACAO_max": [700.0],
            }
        )
        conn.register("tb_notas_stats_df", tb_notas_stats)
        conn.execute(
            "CREATE TABLE tb_notas_stats AS SELECT * FROM tb_notas_stats_df",
        )

        # tb_notas_geo: também dentro de [0, 1000]
        tb_notas_geo = pd.DataFrame(
            {
                "ANO": [2019],
                "SG_UF_PROVA": ["SP"],
                "CO_MUNICIPIO_PROVA": ["3550308"],
                "NO_MUNICIPIO_PROVA": ["SAO PAULO"],
                "NOTA_CIENCIAS_NATUREZA_count": [2],
                "NOTA_CIENCIAS_NATUREZA_mean": [550.0],
                "NOTA_CIENCIAS_HUMANAS_count": [2],
                "NOTA_CIENCIAS_HUMANAS_mean": [600.0],
                "NOTA_LINGUAGENS_CODIGOS_count": [2],
                "NOTA_LINGUAGENS_CODIGOS_mean": [630.0],
                "NOTA_MATEMATICA_count": [2],
                "NOTA_MATEMATICA_mean": [620.0],
                "NOTA_REDACAO_count": [2],
                "NOTA_REDACAO_mean": [650.0],
            }
        )
        conn.register("tb_notas_geo_df", tb_notas_geo)
        conn.execute(
            "CREATE TABLE tb_notas_geo AS SELECT * FROM tb_notas_geo_df",
        )
    finally:
        conn.close()


def test_run_dashboard_data_checks_pass(tmp_path: Path) -> None:
    db_path = tmp_path / "enem_test.duckdb"
    _setup_test_db(db_path)
    conn = duckdb.connect(db_path.as_posix())
    try:
        checks = run_dashboard_data_checks(conn)
        assert checks, "Esperava ao menos um check executado"
        assert all(c.passed for c in checks), "Todos os checks devem passar"
    finally:
        conn.close()


def test_assert_dashboard_data_checks_detects_out_of_range(tmp_path: Path) -> None:
    db_path = tmp_path / "enem_test_fail.duckdb"
    conn = duckdb.connect(db_path.as_posix())
    try:
        # Cria tabelas mínimas com um valor inválido (> 1000) em NOTA_MATEMATICA_mean.
        conn.execute(
            """
            CREATE TABLE tb_notas (
                ANO INTEGER,
                ID_INSCRICAO VARCHAR,
                NOTA_CIENCIAS_NATUREZA DOUBLE,
                NOTA_CIENCIAS_HUMANAS DOUBLE,
                NOTA_LINGUAGENS_CODIGOS DOUBLE,
                NOTA_MATEMATICA DOUBLE,
                NOTA_REDACAO DOUBLE
            );
            INSERT INTO tb_notas VALUES
                (2019, '2019A', 500, 550, 580, 520, 600);

            CREATE TABLE tb_notas_stats AS
            SELECT
                2019 AS ANO,
                1 AS NOTA_CIENCIAS_NATUREZA_count,
                500.0 AS NOTA_CIENCIAS_NATUREZA_mean,
                0.0 AS NOTA_CIENCIAS_NATUREZA_std,
                500.0 AS NOTA_CIENCIAS_NATUREZA_min,
                500.0 AS NOTA_CIENCIAS_NATUREZA_median,
                500.0 AS NOTA_CIENCIAS_NATUREZA_max,
                1 AS NOTA_CIENCIAS_HUMANAS_count,
                550.0 AS NOTA_CIENCIAS_HUMANAS_mean,
                0.0 AS NOTA_CIENCIAS_HUMANAS_std,
                550.0 AS NOTA_CIENCIAS_HUMANAS_min,
                550.0 AS NOTA_CIENCIAS_HUMANAS_median,
                550.0 AS NOTA_CIENCIAS_HUMANAS_max,
                1 AS NOTA_LINGUAGENS_CODIGOS_count,
                580.0 AS NOTA_LINGUAGENS_CODIGOS_mean,
                0.0 AS NOTA_LINGUAGENS_CODIGOS_std,
                580.0 AS NOTA_LINGUAGENS_CODIGOS_min,
                580.0 AS NOTA_LINGUAGENS_CODIGOS_median,
                580.0 AS NOTA_LINGUAGENS_CODIGOS_max,
                1 AS NOTA_MATEMATICA_count,
                1200.0 AS NOTA_MATEMATICA_mean, -- fora do intervalo
                0.0 AS NOTA_MATEMATICA_std,
                520.0 AS NOTA_MATEMATICA_min,
                520.0 AS NOTA_MATEMATICA_median,
                520.0 AS NOTA_MATEMATICA_max,
                1 AS NOTA_REDACAO_count,
                650.0 AS NOTA_REDACAO_mean,
                0.0 AS NOTA_REDACAO_std,
                650.0 AS NOTA_REDACAO_min,
                650.0 AS NOTA_REDACAO_median,
                650.0 AS NOTA_REDACAO_max;

            CREATE TABLE tb_notas_geo AS
            SELECT
                2019 AS ANO,
                'SP' AS SG_UF_PROVA,
                '3550308' AS CO_MUNICIPIO_PROVA,
                'SAO PAULO' AS NO_MUNICIPIO_PROVA,
                1 AS NOTA_CIENCIAS_NATUREZA_count,
                500.0 AS NOTA_CIENCIAS_NATUREZA_mean,
                1 AS NOTA_CIENCIAS_HUMANAS_count,
                550.0 AS NOTA_CIENCIAS_HUMANAS_mean,
                1 AS NOTA_LINGUAGENS_CODIGOS_count,
                580.0 AS NOTA_LINGUAGENS_CODIGOS_mean,
                1 AS NOTA_MATEMATICA_count,
                520.0 AS NOTA_MATEMATICA_mean,
                1 AS NOTA_REDACAO_count,
                650.0 AS NOTA_REDACAO_mean;
            """
        )

        try:
            assert_dashboard_data_checks(conn)
        except RuntimeError as exc:
            # Espera falha por nota fora do intervalo
            assert "tb_notas_stats.notas_in_range" in str(exc)
        else:  # pragma: no cover - proteção
            raise AssertionError("Era esperado RuntimeError devido a notas fora do intervalo.")
    finally:
        conn.close()
