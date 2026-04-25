# Secrets

## Objetivo

Definir una pauta minima para gestion de secretos en despliegues privados de `esdata`.

## Secretos criticos

- `DATABASE_URL`
- `POSTGRES_PASSWORD`
- `MCP_API_KEY`
- cualquier token futuro dedicado a `ChatGPT Business` o `Actions`

## Reglas

- nunca guardar secretos reales en git
- nunca poner secretos en `.env.example`
- nunca loggear secretos o cabeceras de auth
- no reutilizar la misma key para `MCP` personal y `Actions` corporativas

## Separacion recomendada

- una key para `MCP` personal
- una key distinta para integraciones corporativas
- secretos distintos por entorno si existe mas de uno

## Almacenamiento

### Fase de prueba

- `.env` real solo en el servidor
- permisos restringidos al usuario operador

### Fase corporativa

- secret manager o vault del entorno
- rotacion documentada
- ownership claro de cada secreto

## Rotacion minima

Al rotar un secreto:

1. actualizar el valor en el entorno
2. recrear el servicio afectado
3. validar `health`
4. validar el cliente que depende de ese secreto
5. retirar el secreto anterior
