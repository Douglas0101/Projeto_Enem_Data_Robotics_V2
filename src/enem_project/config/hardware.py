from __future__ import annotations

from dataclasses import dataclass
import os

try:
    import psutil  # type: ignore
except ImportError:  # pragma: no cover
    psutil = None


@dataclass(frozen=True)
class HardwareProfile:
    """
    Perfil de hardware para tunar paralelismo e uso de memória.

    Os valores padrão aqui foram pensados para:

    - CPU: 4 threads lógicas
    - RAM: ~20 GB
    """

    n_logical_cores: int
    n_workers_cpu: int
    n_workers_io: int
    ram_gb_total: float
    ram_gb_available: float
    max_ram_gb_for_pipelines: float
    csv_chunk_rows: int
    streaming_threshold_gb: float

    def requires_streaming(self, file_size_gb: float) -> bool:
        """
        Determina se um arquivo CSV deve ser processado em modo streaming,
        comparando o tamanho estimado com o limite seguro para manter tudo
        em memória.
        """
        return file_size_gb >= self.streaming_threshold_gb


def _detect_ram_gb() -> float:
    if psutil is not None:
        try:
            return psutil.virtual_memory().total / (1024**3)
        except Exception:
            pass  # nosec B110
    # fallback se psutil não estiver instalado
    return 20.0


def _detect_available_ram_gb(total: float) -> float:
    if psutil is not None:
        try:
            return psutil.virtual_memory().available / (1024**3)
        except Exception:
            pass  # nosec B110
    return total * 0.8


def _env_float(var_name: str) -> float | None:
    raw = os.getenv(var_name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _resolve_max_ram_pipeline(ram_gb: float) -> float:
    env_override = _env_float("ENEM_MAX_RAM_GB")
    if env_override is not None:
        return min(env_override, ram_gb * 0.9)
    return min(12.0, ram_gb * 0.6)


def _calculate_chunk_rows(max_ram_pipeline: float) -> int:
    env_override = os.getenv("ENEM_CSV_CHUNK_ROWS")
    if env_override:
        try:
            value = int(env_override)
            if value > 0:
                return value
        except ValueError:
            pass

    bytes_budget = max_ram_pipeline * (1024**3) * 0.25
    estimated_row_bytes = int(os.getenv("ENEM_ESTIMATED_ROW_BYTES", "450"))
    chunk_rows = int(bytes_budget / max(estimated_row_bytes, 200))
    chunk_rows = max(150_000, min(chunk_rows, 1_500_000))
    return chunk_rows


def _resolve_streaming_threshold(
    ram_total: float,
    ram_available: float,
    max_ram_pipeline: float,
) -> float:
    env_override = _env_float("ENEM_STREAMING_THRESHOLD_GB")
    if env_override is not None and env_override > 0:
        return env_override

    base = min(
        max_ram_pipeline * 0.45,
        ram_total * 0.35,
        ram_available * 0.55,
    )
    return max(1.5, base)


def build_profile_for_local() -> HardwareProfile:
    n_logical = os.cpu_count() or 4

    # Para CPU-bound (transformações pesadas, ML),
    # usamos no máx ~ n_cores - 1, mas nunca mais que 3
    n_workers_cpu = max(1, min(3, n_logical - 1))

    # Para I/O-bound (ler vários arquivos pequenos ao mesmo tempo),
    # podemos ter um pouco mais de workers
    n_workers_io = max(1, min(4, n_logical * 2))

    ram_gb = _detect_ram_gb()
    ram_available = _detect_available_ram_gb(ram_gb)
    max_ram_pipelines = _resolve_max_ram_pipeline(ram_gb)
    csv_chunk_rows = _calculate_chunk_rows(max_ram_pipelines)
    streaming_threshold = _resolve_streaming_threshold(
        ram_total=ram_gb,
        ram_available=ram_available,
        max_ram_pipeline=max_ram_pipelines,
    )

    return HardwareProfile(
        n_logical_cores=n_logical,
        n_workers_cpu=n_workers_cpu,
        n_workers_io=n_workers_io,
        ram_gb_total=ram_gb,
        ram_gb_available=ram_available,
        max_ram_gb_for_pipelines=max_ram_pipelines,
        csv_chunk_rows=csv_chunk_rows,
        streaming_threshold_gb=streaming_threshold,
    )


PROFILE = build_profile_for_local()
