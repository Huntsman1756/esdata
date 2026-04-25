# esdata_common: utilidades compartidas entre API y workers

## Estructura

```
esdata_common/
|-- __init__.py
|-- config.py          # Carga de variables de entorno y configuracion
|-- db.py              # Engine SQLAlchemy, session factory, db_session()
|-- logging.py         # Configuracion de logging unificada
|-- http.py            # Cliente HTTP reutilizable con retries
|-- constants.py       # Constantes compartidas (nombres de normas, etc.)
```

## Uso

### API

```python
# apps/api/requirements.txt debe incluir:
# -e ../../libs/python/esdata_common

from esdata_common import config, db, logging

config.load()
logger = logging.configure(__name__)
with db.db_session() as session:
    ...
```

### Workers

```python
from esdata_common import config, db, logging

config.load()
logger = logging.configure(__name__)
with db.db_session() as session:
    ...
```

## Migracion

Para migrar un modulo existente:

1. Reemplazar `os.getenv("DATABASE_URL", ...)` por `config.get_database_url()`
2. Reemplazar `db_session()` propio por `esdata_common.db.db_session()`
3. Reemplazar `logging.basicConfig(...)` por `logging.configure(__name__)`
4. Agregar `libs/python/esdata_common` a requirements.txt como editable

## Notas

- No mover logica de negocio aqui
- Solo utilidades transversales entre API y workers
- Mantener dependencias minimas (solo sqlalchemy, os, logging stdlib)
