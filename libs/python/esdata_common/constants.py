"""Constantes compartidas entre API y workers."""

# Normas BOE conocidas y sus identificadores
DEFAULT_NORMAS = {
    "LIVA": "BOE-A-1992-28740",
    "LIRPF": "BOE-A-2006-20764",
    "LIS": "BOE-A-2014-12328",
    "LGT": "BOE-A-2003-23186",
    "ITPAJD": "BOE-A-1993-25359",
    "IRNR": "BOE-A-2004-4527",
    "IIEE": "BOE-A-1992-28741",
    "HL": "BOE-A-2004-4214",
    "DAC6": "BOE-A-2020-17265",
    "DAC6RD": "BOE-A-2021-5394",
    "DAC6EU": "BOE-A-2021-5394",
    "RIRPF": "BOE-A-2007-6820",
    "RIVA": "BOE-A-1992-28759",
    "RIS": "BOE-A-2014-12531",
    "RD1080": "BOE-A-2015-12843",
    "LIVA_IGIC": "BOE-A-2022-5689",
}

# Clasificacion de normas por tipo y ambito
NORMA_CLASSIFICATIONS = {
    "LIVA": {"tipo_documento": "ley", "ambito": "tributario"},
    "LIRPF": {"tipo_documento": "ley", "ambito": "tributario"},
    "LIS": {"tipo_documento": "ley", "ambito": "tributario"},
    "LGT": {"tipo_documento": "ley", "ambito": "tributario"},
    "ITPAJD": {"tipo_documento": "real_decreto_legislativo", "ambito": "tributario"},
    "IRNR": {"tipo_documento": "real_decreto_legislativo", "ambito": "tributario"},
    "IIEE": {"tipo_documento": "ley", "ambito": "tributario"},
    "HL": {"tipo_documento": "real_decreto_legislativo", "ambito": "tributario_local"},
    "DAC6": {"tipo_documento": "ley", "ambito": "tributario_internacional"},
    "DAC6RD": {"tipo_documento": "real_decreto", "ambito": "tributario_internacional"},
    "DAC6EU": {"tipo_documento": "directiva_ue", "ambito": "tributario_ue"},
    "RIRPF": {"tipo_documento": "real_decreto", "ambito": "tributario"},
    "RIVA": {"tipo_documento": "real_decreto", "ambito": "tributario"},
    "RIS": {"tipo_documento": "real_decreto", "ambito": "tributario"},
    "RD1080": {"tipo_documento": "real_decreto", "ambito": "tributario"},
    "LIVA_IGIC": {"tipo_documento": "ley", "ambito": "tributario_canarias"},
}

# Prefijos de fuentes conocidos para validacion
KNOWN_SOURCE_PREFIXES = frozenset({
    "LIVA", "LIRPF", "LIS", "LGT", "ITPAJD", "IRNR", "IIEE", "HL",
    "DAC6", "DAC6RD", "DAC6EU", "RIRPF", "RIVA", "RIS", "RD1080",
    "LIVA_IGIC", "SEPBLAC", "CNMV",
})

# Mapeo de alias de query a codigo DB
QUERY_TO_DB_CODE = {
    "IRNR": "IRNR", "LIRNR": "IRNR",
    "IRPF": "LIRPF", "LIRPF": "LIRPF", "RIRPF": "LIRPF",
    "IVA": "LIVA", "LIVA": "LIVA", "RIVA": "LIVA",
    "IS": "LIS", "LIS": "LIS", "RIS": "LIS",
    "LGT": "LGT",
    "ITPAJD": "ITPAJD", "ITP": "ITPAJD", "AJD": "ITPAJD",
    "IIEE": "IIEE",
    "DAC6": "DAC6", "DAC6RD": "DAC6RD", "DAC6EU": "DAC6EU",
}
