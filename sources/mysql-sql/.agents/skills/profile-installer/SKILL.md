---
name: profile-installer
description: Materializa el esquema mínimo de perfiles y su contrato desde plantillas aprobadas, adaptando la nomenclatura del proyecto.
---
<!-- si-archivo integraciones.gestion_usuarios=organizaciones|aplicacion -->

# Instalación de gestión de usuarios

## Entrada

`OUT_DIR`, plan aprobado y elección de modelo de `.agents/stack.yaml`. Si falta una decisión, devuelve `estado: bloqueado`.
<!-- si integraciones.gestion_usuarios=organizaciones -->
Recibe tabla nueva o tabla existente con nombre, PK, columna Clerk y columna de nombre aprobados.
<!-- fin -->

## Responsabilidad

Aplica `.agents/rules/architecture-rules.md` y `.agents/rules/project.md`. Materializa los assets con `python3 -B -E .agents/scripts/render-perfiles.py --output OUT_DIR/sql`.
<!-- si integraciones.gestion_usuarios=organizaciones -->
Para tabla existente añade las cuatro opciones de identificadores documentadas por `--help`; no crea ni modifica esa tabla.
<!-- fin -->
 Revisa que no quedan marcadores. Los nombres físicos salen exclusivamente de la nomenclatura local y del contrato aprobado; los alias de resultados son el contrato de API.

Los estados son PENDIENTE=1, INVITADO_A_CLERK=2, ACTIVO=3 e INACTIVO=4. Las semillas se instalan una vez, sin reemplazar datos existentes. No hay tablas de contraseñas ni roles. No ejecuta SQL en bases reales, no usa MCP para escribir ni lee otro proyecto. No escribe notebooks. El contrato se guarda junto al SQL y registra nombres, parámetros y resultados de cada procedimiento; completa su tabla a partir del SQL materializado, no de suposiciones.

## Salida

`OUT_DIR/profiles-report.md` con frontmatter `artefacto: profiles-report.md`, `skill: profile-installer`, `estado: ok|fallo|bloqueado`, archivos materializados, nombres finales, comandos y salidas literales. Un error o marcador pendiente es fallo; no declares ejecutadas pruebas que no corriste.
