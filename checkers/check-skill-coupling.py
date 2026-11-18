#!/usr/bin/env python3
"""Detecta acoplamiento en las skills de sources/*/.agents/skills.

Una skill está limpia cuando:
  1. No nombra otras skills, workflows, pasos, rutas ni al orquestador.
  2. Tiene las secciones '## Entrada' y '## Salida'.
  3. Su sección '## Salida' escribe en OUT_DIR.

Uso:
  python3 -I checkers/check-skill-coupling.py [raiz]   (raiz por defecto: sources)
Sale con código 1 si encuentra algún problema.
"""
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "sources")

# Términos prohibidos en una skill (no dependen de mayúsculas).
FORBIDDEN_CI = [
    r"\bpaso\s+[0-9C]",            # "Paso 6", "Paso C3"
    r"\bC[0-9]+(\.[0-9]+)?\b",      # "C3", "C3.5"
    r"\bworkflows?\b",
    r"\borquestador(es)?\b",        # no atrapa "página orquestadora" (concepto React)
    r"\bsubagentes?\b",
    r"full-route|correction-route",
    r"implement-feature|implement-microservice-feature|build-database-feature",
]
# Términos prohibidos sensibles a mayúsculas (evita falsos positivos como "ruta completa del archivo").
FORBIDDEN_CS = [r"Ruta Completa", r"Ruta de Corrección"]


def skill_names():
    return {p.parent.name for p in root.glob("*/.agents/skills/*/SKILL.md")}


def section(text, title):
    m = re.search(rf"^## {title}\b.*?(?=^## |\Z)", text, re.M | re.S)
    return m.group(0) if m else None


def main():
    names = skill_names()
    problems = 0
    for f in sorted(root.glob("*/.agents/skills/**/*.md")):
        skill = f.relative_to(root).parts[3]
        others = [n for n in names if n != skill]
        pat_ci = re.compile("|".join(FORBIDDEN_CI + [rf"(?<![\w-]){re.escape(n)}(?![\w-])" for n in others]), re.I)
        pat_cs = re.compile("|".join(FORBIDDEN_CS))
        text = f.read_text(encoding="utf-8")
        hits = []
        for i, line in enumerate(text.splitlines(), 1):
            m = pat_ci.search(line) or pat_cs.search(line)
            if m:
                hits.append(f"  L{i}: [{m.group(0)}] {line.strip()[:160]}")
        if f.name == "SKILL.md":
            if section(text, "Entrada") is None:
                hits.append("  falta la sección '## Entrada'")
            out = section(text, "Salida")
            if out is None:
                hits.append("  falta la sección '## Salida'")
            elif "OUT_DIR" not in out:
                hits.append("  la sección '## Salida' no escribe en OUT_DIR")
        if hits:
            problems += len(hits)
            print(f"### {f} ({len(hits)})")
            print("\n".join(hits))
    print(f"\nTotal de problemas: {problems}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
