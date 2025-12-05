import pandas as pd
from pathlib import Path

from enem_project.config import paths as paths_module
from enem_project.data import metadata as metadata_module
from enem_project.orchestrator.base import Orchestrator
from enem_project.orchestrator.context import OrchestratorContext
from enem_project.orchestrator.security import SecurityManager
from enem_project.orchestrator.agents.parquet_quality import (
    GoldParquetAuditAgent,
    SilverParquetQualityAgent,
)
from enem_project.orchestrator.workflows.audit_workflow import (
    run_quality_audit_for_years,
)


def _setup_tmp_paths(tmp_path: Path, monkeypatch) -> tuple[Path, Path]:
    silver_root = tmp_path / "data" / "01_silver"
    gold_root = tmp_path / "data" / "02_gold"
    silver_root.mkdir(parents=True)
    gold_root.mkdir(parents=True)

    monkeypatch.setattr(paths_module, "silver_dir", lambda: silver_root)
    monkeypatch.setattr(paths_module, "gold_dir", lambda: gold_root)
    monkeypatch.setattr(metadata_module, "gold_dir", lambda: gold_root)

    return silver_root, gold_root


def test_silver_parquet_quality_agent_detects_extra_columns(
    tmp_path: Path, monkeypatch
):
    silver_root, _ = _setup_tmp_paths(tmp_path, monkeypatch)
    df = pd.DataFrame(
        {
            "ID_INSCRICAO": [1, 2],
            "ANO": [2016, 2016],
            "COL_EXTRA": ["x", "y"],
        }
    )
    df.to_parquet(silver_root / "microdados_enem_2016.parquet", index=False)

    metadata_df = pd.DataFrame(
        {
            "ano": [2016, 2016],
            "nome_original": ["ID_INSCRICAO", "ANO_ORIG"],
            "nome_padrao": ["ID_INSCRICAO", "ANO"],
            "descricao": ["", ""],
            "tipo_padrao": ["string", "int"],
            "dominio_valores": [None, None],
        }
    )

    agent = SilverParquetQualityAgent(year=2016, metadata=metadata_df)
    orchestrator = Orchestrator([agent], SecurityManager(policies={}))
    ctx = OrchestratorContext(run_id="test-silver", params={}, data={}, logs=[])

    ctx = orchestrator.run(ctx)
    handle = ctx.get_data("audit_silver_2016")
    summary = handle.payload

    assert summary["row_count"].iloc[0] == 2
    assert summary["column_count"].iloc[0] == 3
    assert summary["missing_expected_columns"].iloc[0] is None
    assert "COL_EXTRA" in summary["columns_not_in_metadata"].iloc[0]


def test_gold_parquet_audit_agent_reads_all_files(tmp_path: Path, monkeypatch):
    _, gold_root = _setup_tmp_paths(tmp_path, monkeypatch)

    other_df = pd.DataFrame({"foo": [1, 2, 3]})

    metadata_module.save_metadata(
        pd.DataFrame(
            {
                "ano": [2016],
                "nome_original": ["VAL"],
                "nome_padrao": ["VAL"],
                "descricao": [""],
                "tipo_padrao": ["int"],
                "dominio_valores": [None],
            }
        )
    )
    other_df.to_parquet(gold_root / "qa_summary.parquet", index=False)

    metadata_df = metadata_module.load_metadata()
    agent = GoldParquetAuditAgent(metadata_df)
    orchestrator = Orchestrator([agent], SecurityManager(policies={}))
    ctx = OrchestratorContext(run_id="test-gold", params={}, data={}, logs=[])
    ctx = orchestrator.run(ctx)

    summary = ctx.get_data("audit_gold").payload
    assert len(summary) == 2
    assert {"qa_summary.parquet", metadata_module.METADATA_FILE_NAME}.issubset(
        set(Path(p).name for p in summary["parquet_path"])
    )


def test_run_quality_audit_for_years_creates_report(tmp_path: Path, monkeypatch):
    silver_root, gold_root = _setup_tmp_paths(tmp_path, monkeypatch)

    df_2016 = pd.DataFrame(
        {
            "ID_INSCRICAO": [1],
            "ANO": [2016],
            "NOTA_CN": [500.0],
        }
    )
    df_2017 = pd.DataFrame(
        {
            "ID_INSCRICAO": [2],
            "ANO": [2017],
            "NOTA_CN": [510.0],
        }
    )
    df_2016.to_parquet(silver_root / "microdados_enem_2016.parquet", index=False)
    df_2017.to_parquet(silver_root / "microdados_enem_2017.parquet", index=False)

    metadata_records = []
    for year in (2016, 2017):
        metadata_records.extend(
            [
                {
                    "ano": year,
                    "nome_original": "ID_INSCRICAO",
                    "nome_padrao": "ID_INSCRICAO",
                    "descricao": "",
                    "tipo_padrao": "string",
                    "dominio_valores": None,
                },
                {
                    "ano": year,
                    "nome_original": "ANO",
                    "nome_padrao": "ANO",
                    "descricao": "",
                    "tipo_padrao": "int",
                    "dominio_valores": None,
                },
                {
                    "ano": year,
                    "nome_original": "NOTA_CN",
                    "nome_padrao": "NOTA_CN",
                    "descricao": "",
                    "tipo_padrao": "float",
                    "dominio_valores": None,
                },
            ]
        )

    metadata_module.save_metadata(pd.DataFrame.from_records(metadata_records))

    result = run_quality_audit_for_years([2016, 2017])

    report_path = Path(result["report_path"])
    assert report_path.exists()
    silver_summary = result["silver"]
    assert len(silver_summary) == 2
    assert set(silver_summary["ano"]) == {2016, 2017}

    gold_summary = result["gold"]
    assert metadata_module.METADATA_FILE_NAME in set(
        Path(p).name for p in gold_summary["parquet_path"]
    )
