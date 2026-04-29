# Data Policy

## Objetivo

Definir una politica minima de datos para operar `esdata` sin acumular informacion sensible innecesaria.

## Principios

- guardar solo lo necesario para operar y depurar
- no registrar secretos
- minimizar la retencion de informacion potencialmente sensible

## Que no guardar por defecto

- tokens o claves de autenticacion
- cabeceras `X-API-Key`
- prompts completos del usuario si contienen informacion sensible
- bodies completos de peticiones operativas si no son imprescindibles

## Que si se puede guardar

- timestamp
- endpoint llamado
- codigo de respuesta
- duracion
- identificadores tecnicos no sensibles

## Retencion recomendada

- logs operativos: 7 a 30 dias segun necesidad real
- datos sensibles: no conservar salvo necesidad puntual y controlada

## Regla practica

Si una consulta o body podria contener PII, datos fiscales sensibles o informacion corporativa delicada, no dejarlo persistido completo en logs por defecto.
