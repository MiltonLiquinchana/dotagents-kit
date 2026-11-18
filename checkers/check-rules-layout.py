#!/usr/bin/env python3
"""Valida la organización de reglas en sources/*/.

Comprueba, por proyecto:
  A. AGENTS.md existe, pesa menos de 16 KiB, ordena leer .agents/rules/project.md y no contiene
     números de paso ni detalles internos de orquestación.
  B. Existe .agents/rules/project.md.
  C. Cada .agents/rules/*.md tiene frontmatter con un `trigger` válido para Antigravity
     (`description` obligatorio en model_decision, `globs` obligatorio en glob).
  D. Las reglas no nombran skills, workflows, pasos, rutas, orquestador ni subagentes.
  E. Cada regla compartida (todas menos project.md) tiene 2 o más consumidores
     (skills, workflows o AGENTS.md que la citan por ruta completa).
  F. Las referencias a reglas usan la ruta completa `.agents/rules/<archivo>.md` y apuntan a un archivo
     que existe. Una referencia sin ruta (`rules.md`, `rules/x.md`) cuenta como error.
  G. Los archivos que una skill cita como `references/<archivo>` existen dentro de esa skill.

Uso (desde dotagents-kit/):
  python3 -I checkers/check-rules-layout.py [raiz]   (raiz por defecto: sources)
Sale con código 1 si encuentra algún problema.
"""
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "sources")
AGENTS_MAX_BYTES = 16 * 1024
VALID_TRIGGERS = {"always_on", "model_decision", "glob", "manual"}

# Nombres de reglas que existieron antes de reorganizarlas: si se citan sin ruta, son referencias rotas en potencia.
KNOWN_RULE_NAMES = {
    "rules", "architecture-rules", "sonarqube-compliance", "performance-budget", "agent-browser",
    "sql-quality-gate", "tgrep", "graphify", "codebase-memory", "knowledge-base", "project", "global",
}

FORBIDDEN_CI = [
    r"\bpaso\s+[0-9C]", r"\bC[0-9]+(\.[0-9]+)?\b", r"\bworkflows?\b", r"\borquestador(es)?\b",
    r"\bsubagentes?\b", r"full-route|correction-route",
    r"implement-feature|implement-microservice-feature|build-database-feature",
]
FORBIDDEN_CS = [r"Ruta Completa", r"Ruta de Corrección"]
AGENTS_FORBIDDEN = [r"\bpaso\s+[0-9C]", r"\bC[0-9]+(\.[0-9]+)?\b", r"\bsubagentes?\b"]

FULL_REF = re.compile(r"\.agents/rules/([\w.-]+\.md)")
BARE_REF = re.compile(r"(?<![\w./-])(?:rules/)?(" + "|".join(sorted(KNOWN_RULE_NAMES)) + r")\.md\b")


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    data = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    return data


def consumer_files(agents_dir, project_dir):
    files = list(agents_dir.glob("skills/**/*.md"))
    files += list(agents_dir.glob("workflows/**/*.md"))
    agents_md = project_dir / "AGENTS.md"
    if agents_md.exists():
        files.append(agents_md)
    return files


def check_project(project_dir):
    errs = []
    agents_dir = project_dir / ".agents"
    rules_dir = agents_dir / "rules"
    rule_files = sorted(rules_dir.glob("*.md")) if rules_dir.exists() else []
    skill_names = {p.parent.name for p in agents_dir.glob("skills/*/SKILL.md")}

    # A. AGENTS.md
    agents_md = project_dir / "AGENTS.md"
    if not agents_md.exists():
        errs.append("A: falta AGENTS.md")
    else:
        text = agents_md.read_text(encoding="utf-8")
        size = len(text.encode("utf-8"))
        if size > AGENTS_MAX_BYTES:
            errs.append(f"A: AGENTS.md pesa {size} bytes (máximo {AGENTS_MAX_BYTES})")
        if ".agents/rules/project.md" not in text:
            errs.append("A: AGENTS.md no ordena leer `.agents/rules/project.md`")
        pat = re.compile("|".join(AGENTS_FORBIDDEN), re.I)
        for i, line in enumerate(text.splitlines(), 1):
            m = pat.search(line)
            if m:
                errs.append(f"A: AGENTS.md L{i} [{m.group(0)}] {line.strip()[:120]}")

    # B. project.md
    if not (rules_dir / "project.md").exists():
        errs.append("B: falta .agents/rules/project.md")

    # C y D. Cada regla
    names_pat = [rf"(?<![\w-]){re.escape(n)}(?![\w-])" for n in skill_names]
    pat_ci = re.compile("|".join(FORBIDDEN_CI + names_pat), re.I)
    pat_cs = re.compile("|".join(FORBIDDEN_CS))
    for rf in rule_files:
        text = rf.read_text(encoding="utf-8")
        fm = frontmatter(text)
        if fm is None:
            errs.append(f"C: {rf.name}: sin frontmatter (Antigravity la descarta)")
        else:
            trig = fm.get("trigger")
            if trig not in VALID_TRIGGERS:
                errs.append(f"C: {rf.name}: trigger inválido o ausente ({trig!r})")
            if trig == "model_decision" and not fm.get("description"):
                errs.append(f"C: {rf.name}: model_decision sin description")
            if trig == "glob" and not (fm.get("globs") or fm.get("glob")):
                errs.append(f"C: {rf.name}: glob sin globs")
        for i, line in enumerate(text.splitlines(), 1):
            m = pat_ci.search(line) or pat_cs.search(line)
            if m:
                errs.append(f"D: {rf.name} L{i} [{m.group(0)}] {line.strip()[:120]}")

    # E. Consumidores de cada regla compartida
    files = consumer_files(agents_dir, project_dir)
    for rf in rule_files:
        if rf.name == "project.md":
            continue
        users = set()
        for f in files:
            if f".agents/rules/{rf.name}" in f.read_text(encoding="utf-8"):
                users.add(str(f.relative_to(project_dir)))
        if len(users) < 2:
            errs.append(f"E: {rf.name}: {len(users)} consumidor(es) {sorted(users)}; con menos de 2 debe mudarse a su consumidor")

    # F. Referencias a reglas (ruta completa y existencia)
    existing = {rf.name for rf in rule_files}
    for f in files + rule_files:
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(project_dir)
        for name in FULL_REF.findall(text):
            if name not in existing:
                errs.append(f"F: {rel}: cita `.agents/rules/{name}`, que no existe")
        stripped = FULL_REF.sub("", text)
        for i, line in enumerate(stripped.splitlines(), 1):
            for m in BARE_REF.finditer(line):
                errs.append(f"F: {rel} L{i}: referencia sin ruta completa `{m.group(0)}`")

    # G. references/ citadas por cada skill
    for skill_md in agents_dir.glob("skills/*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8")
        for ref in set(re.findall(r"(?<![\w/])references/([\w./-]+\.md)", text)):
            if not (skill_md.parent / "references" / ref).exists():
                errs.append(f"G: {skill_md.relative_to(project_dir)}: cita references/{ref}, que no existe")

    # Informativo: peso de lo que se carga siempre en Antigravity
    always = sum(len(rf.read_bytes()) for rf in rule_files
                 if (frontmatter(rf.read_text(encoding="utf-8")) or {}).get("trigger") == "always_on")
    if agents_md.exists():
        always += len(agents_md.read_bytes())
    return errs, always


def main():
    total = 0
    for project_dir in sorted(p for p in root.iterdir() if (p / ".agents").is_dir()):
        errs, always = check_project(project_dir)
        total += len(errs)
        print(f"##### {project_dir.name}  (AGENTS.md + reglas always_on: {always} bytes)")
        for e in errs:
            print("  " + e)
        print()
    print(f"Total de problemas: {total}")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
