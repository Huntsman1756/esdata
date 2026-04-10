# Estructura del monorepo

esdata/
├── .github/
│   └── workflows/
│       ├── ci.yml              # tests + lint en cada PR
│       └── deploy.yml          # deploy a Railway en merge a main
│
├── apps/
│   ├── api/                    # FastAPI principal
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── legislacion.py
│   │   │   ├── materias.py
│   │   │   ├── doctrina.py
│   │   │   └── status.py
│   │   ├── models/             # modelos SQLAlchemy
│   │   ├── schemas/            # modelos Pydantic
│   │   ├── services/
│   │   │   ├── search.py       # lógica full-text + confianza
│   │   │   └── confianza.py    # política de niveles 1-3
│   │   ├── mcp_server.py       # fastapi-mcp montado en /mcp
│   │   ├── alembic/            # migraciones
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   └── workers/                # workers de ingesta
│       ├── boe.py              # worker BOE legislación
│       ├── doctrina_dgt.py     # worker consultas DGT
│       ├── doctrina_teac.py    # worker resoluciones TEAC
│       ├── requirements.txt
│       └── Dockerfile
│
├── libs/
│   └── common/                 # código compartido API + workers
│       ├── db.py               # conexión PostgreSQL compartida
│       ├── models.py           # modelos SQLAlchemy (única fuente de verdad)
│       └── sync_log.py         # helpers para sync_log
│
├── infra/
│   ├── sql/
│   │   └── init.sql            # schema completo (DDL)
│   └── cloudflare/
│       └── worker.js           # Cloudflare Worker (gateway)
│
├── railway.toml                # configuración Railway
├── docker-compose.yml          # entorno local
└── .env.example                # variables de entorno documentadas
