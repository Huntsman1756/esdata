"""Seed data para formularios W-8 del IRS.

Cubre los 4 formularios W-8 principales:
- W-8BEN: Foreign Individuals
- W-8BEN-E: Foreign Entities
- W-8EXP: Exempt Organizations
- W-8ECF: Exempt Withholding Certification
"""

FORMS = [
    {
        "codigo": "W-8BEN",
        "nombre": "Certificate of Foreign Status of Beneficial Owner for United States Tax Withholding",
        "descripcion": "Certificacion de condicion extranjera del beneficiario para retencion fiscal en EE.UU.",
        "tipo_sujeto": "persona_fisica",
        "finalidad": "Certificar condicion de no residente para aplicar tipo reducido de retencion bajo convenio DTA",
        "partes": {
            "Parte I": "Nombre del beneficiario (persona fisica), pais de citizenship, direccion permanente",
            "Parte II": "Numero de TIN extranjero (si aplica)",
            "Parte III": "Residencia fiscal, numero de TIN EE.UU. (ITIN o SSN)",
            "Parte IV": "Clasificacion del beneficiario (beneficial owner, agent, etc.)",
            "Parte V": "Articulo del convenio DTA aplicado y tipo de retencion reducido",
            "Parte VI": "Fecha, firma, nombre y cargo",
        },
        "validez_anios": 3,
        "obligacion_asociada": "Retencion sobre dividendos, intereses, royalties a no residentes",
        "texto_detalle": "Formulario obligatorio para personas fisicas extranjeras que obtienen ingresos de fuente estadounidense. Debe entregarse al withholding agent antes del primer pago sujeto a retencion.",
        "estado": "activo",
    },
    {
        "codigo": "W-8BEN-E",
        "nombre": "Certificate of Status of Beneficial Owner for United States Tax Withholding (Entities)",
        "descripcion": "Certificacion de estado del beneficiario para entidades extranjeras.",
        "tipo_sujeto": "persona_juridica",
        "finalidad": "Certificar condicion de entidad extranjera para retencion reducida y transparencia fiscal",
        "partes": {
            "Parte I": "Nombre de la entidad, pais de incorporacion/residencia, direccion",
            "Parte II": "Numero de GIIN (obligatorio para FFI/NFFE)",
            "Parte III": "Clasificacion (bank, financial institution, investment entity, etc.)",
            "Parte IV": "Control owners (personas fisicas que poseen >= 25%)",
            "Parte V": "Clasificacion bajo FATCA (FFI, NFFE exempt, reporting IFI, etc.)",
            "Parte VI": "Articulo DTA y tipo de retencion reducido",
            "Parte VII": "Fecha, firma, nombre y cargo del firmante autorizado",
        },
        "validez_anios": 3,
        "obligacion_asociada": "Retencion sobre pagos a entidades extranjeras + reporte FATCA",
        "texto_detalle": "Formulario obligatorio para entidades extranjeras. Requiere GIIN registrado en IRS para la mayoria de casos. Incluye seccion adicional para reportar control owners bajo FATCA.",
        "estado": "activo",
    },
    {
        "codigo": "W-8EXP",
        "nombre": "Certificate of Foreign Government or Other Foreign Organization for United States Tax Withholding",
        "descripcion": "Certificacion de gobierno extranjero o organizacion extranjera exenta.",
        "tipo_sujeto": "entidad_gubernamental",
        "finalidad": "Certificar condicion de entidad exenta o gobierno extranjero para exencion total de retencion",
        "partes": {
            "Parte I": "Nombre de la entidad, pais de residencia, direccion",
            "Parte II": "Estatus de exencion fiscal y fundamento legal",
            "Parte III": "Clasificacion (gobierno, banco central, organizacion internacional, etc.)",
            "Parte IV": "TIN extranjero y numero de TIN EE.UU. (si aplica)",
            "Parte V": "Firma de persona autorizada",
        },
        "validez_anios": 3,
        "obligacion_asociada": "Exencion de retencion para gobiernos y organizaciones internacionales",
        "texto_detalle": "Aplica a gobiernos extranjeros, bancos centrales, organizaciones internacionales, organizaciones sin fines de lucro exentas, fondos de pensiones y entidades qualificadas. La exencion puede ser total o parcial segun la naturaleza del ingreso.",
        "estado": "activo",
    },
    {
        "codigo": "W-8ECF",
        "nombre": "Exempt Withholding Certification",
        "descripcion": "Certificacion de retencion exenta para proveedores de fondos y intermediarios.",
        "tipo_sujeto": "entidad_gubernamental",
        "finalidad": "Certificar estatus de retencion exenta para pagos de intereses y dividendos",
        "partes": {
            "Parte I": "Nombre del certificado, tipo de entidad (broker, quasi-broker, etc.)",
            "Parte II": "Estatus de retencion exenta y fundamento (seccion IRC aplicable)",
            "Parte III": "Informacion del beneficiario y tipo de ingreso",
            "Parte IV": "Certificacion bajo penaltas de perjurio",
            "Parte V": "Fecha, firma y cargo del firmante",
        },
        "validez_anios": 3,
        "obligacion_asociada": "Retencion sobre pagos de intereses y dividendos a entidades qualificadas",
        "texto_detalle": "Formulario para brokers, intermediarios cualificados y otras entidades que reciben pagos sujetos a retencion pero que estan exentas bajo el Internal Revenue Code. Requiere renovacion cada 3 anos.",
        "estado": "activo",
    },
]


def seed_w8_forms():
    """Inserta formularios W-8 en irs_w8_form."""
    import json

    import os

    import psycopg

    DB_URL = os.getenv("DATABASE_URL", "postgresql://esdata:esdata_dev@localhost:5432/esdata")

    with psycopg.connect(DB_URL) as conn:
        cur = conn.cursor()
        for form in FORMS:
            cur.execute(
                """
                INSERT INTO irs_w8_form (
                    codigo, nombre, descripcion, tipo_sujeto, finalidad,
                    partes, validez_anios, obligacion_asociada, texto_detalle, estado
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s
                )
                ON CONFLICT (codigo) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    descripcion = EXCLUDED.descripcion,
                    tipo_sujeto = EXCLUDED.tipo_sujeto,
                    finalidad = EXCLUDED.finalidad,
                    partes = EXCLUDED.partes,
                    validez_anios = EXCLUDED.validez_anios,
                    obligacion_asociada = EXCLUDED.obligacion_asociada,
                    texto_detalle = EXCLUDED.texto_detalle,
                    estado = EXCLUDED.estado,
                    actualizado_en = now()
                """,
                (
                    form["codigo"],
                    form["nombre"],
                    form["descripcion"],
                    form["tipo_sujeto"],
                    form["finalidad"],
                    json.dumps(form["partes"]),
                    form["validez_anios"],
                    form["obligacion_asociada"],
                    form["texto_detalle"],
                    form["estado"],
                ),
            )
        conn.commit()

    print(f"Seeded {len(FORMS)} W-8 forms")


def main():
    seed_w8_forms()


if __name__ == "__main__":
    main()
