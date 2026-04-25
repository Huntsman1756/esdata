SEED_CHANGES = [
    {
        "codigo": "CAMBIO-CNMV-001",
        "fuente": "cnmv",
        "impacto": "revisar reporting reservado",
        "estado": "nuevo",
        "obligaciones_afectadas": ["CNMV-IR-RESERVADA"],
        "accion_recomendada": "validar impacto y recalcular calendario de reporting",
        "prioridad": "alta",
        "fecha_detectado": "2026-04-25",
    }
]


def list_seed_changes() -> list[dict]:
    return [dict(item) for item in SEED_CHANGES]
