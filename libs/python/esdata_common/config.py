"""Carga de variables de entorno y configuracion."""

import os
from pathlib import Path


def load(env_file: str | None = None) -> None:
    """Cargar variables de entorno desde archivo .env si existe.

    Args:
        env_file: Ruta al archivo .env. Si None, busca .env en la raiz del proyecto.
    """
    if env_file:
        env_path = Path(env_file)
    else:
        # Buscar .env en la raiz del proyecto (subiendo desde este archivo)
        env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"

    if env_path.exists():
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)


def get_database_url(default: str = "postgresql+psycopg://user:password@localhost:5432/esdata") -> str:
    """Obtener DATABASE_URL desde entorno con valor por defecto."""
    return os.getenv("DATABASE_URL", default)


def get_bool_env(name: str, default: bool = False) -> bool:
    """Leer variable booleana de entorno.

    Valores aceptados para True: '1', 'true', 'yes', 'on'
    Valores aceptados para False: '0', 'false', 'no', 'off'
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def get_int_env(name: str, default: int = 0) -> int:
    """Leer variable entera de entorno."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def get_str_env(name: str, default: str = "") -> str:
    """Leer variable string de entorno."""
    return os.getenv(name, default)


def get_list_env(name: str, separator: str = ",") -> list[str]:
    """Leer variable lista de entorno (valores separados por coma)."""
    raw = os.getenv(name)
    if not raw:
        return []
    return [item.strip() for item in raw.split(separator) if item.strip()]
