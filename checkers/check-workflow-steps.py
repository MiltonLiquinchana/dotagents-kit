#!/usr/bin/env python3
"""Comprueba que cada paso de workflow que invoca una skill dice cómo se ejecuta.

Por cada bloque de workflow que contiene `**Skill**:` exige una línea `**Ejecución**:` con
`subagente` (y la remisión a la guía de ejecución de fases). Además comprueba que existe
`.agents/workflows/references/ejecutar-fase.md` en cada proyecto y que los orquestadores la citan.

Uso (desde dotagents-kit/):
  python3 -I checkers/check-workflow-steps.py [raiz]   (raiz por defecto: sources)
Sale con código 1 si encuentra algún problema.
"""
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "sources")
GUIDE = "workflows/references/ejecutar-fase.md"
ORCHESTRATORS = {"implement-feature.md", "implement-microservice-feature.md", "build-database-feature.md"}


def main():
    total = 0
    for project in sorted(p for p in root.iterdir() if (p / ".agents").is_dir()):
        errs = []
        agents = project / ".agents"
        if not (agents / GUIDE).exists():
            errs.append(f"falta .agents/{GUIDE}")
        for wf in sorted(agents.glob("workflows/**/*.md")):
            text = wf.read_text(encoding="utf-8")
            rel = wf.relative_to(project)
            if wf.name in ORCHESTRATORS and f".agents/{GUIDE}" not in text:
                errs.append(f"{rel}: el orquestador no cita .agents/{GUIDE}")
            # Un bloque por título de paso (##, ###) o viñeta de subpaso (- **Paso ...).
            for block in re.split(r"\n(?=#{2,4} |- \*\*Paso )", text):
                if "**Skill**" not in block:
                    continue
                title = block.strip().splitlines()[0][:70]
                m = re.search(r"\*\*Ejecuci[oó]n\*\*:\s*(.+)", block)
                if not m:
                    errs.append(f"{rel} | {title} | sin línea **Ejecución**")
                elif "subagente" not in m.group(1).lower():
                    errs.append(f"{rel} | {title} | **Ejecución** no indica subagente: {m.group(1)[:60]}")
        total += len(errs)
        print(f"##### {project.name}")
        for e in errs:
            print("  " + e)
        print()
    print(f"Total de problemas: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
