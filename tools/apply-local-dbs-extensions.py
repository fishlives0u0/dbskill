#!/usr/bin/env python3
"""Apply fishlives0u0 local DBS skills on top of the mirrored upstream repository."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".dbs-local" / "custom-skills.json"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
SNAPSHOT = ROOT / "skills" / "dbs" / "references" / "official-skill-names.txt"
VERSION = ROOT / "VERSION"


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    custom = registry.get("skills", [])
    version = VERSION.read_text(encoding="utf-8").strip()

    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    paths = plugin.setdefault("skills", [])

    for skill in custom:
        name = skill["name"]
        source = skill["source"]
        skill_file = ROOT / source.removeprefix("./") / "SKILL.md"
        if not skill_file.is_file():
            raise SystemExit(f"Local skill is missing: {skill_file}")
        if source not in paths:
            paths.append(source)

    plugin["description"] = (
        "dontbesilent 商业工具箱完整入口。包含官方正式 Skill、系统更新入口与本仓库本地扩展 Skill。"
    )
    plugin["skills"] = paths
    PLUGIN.write_text(
        json.dumps(plugin, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if SNAPSHOT.is_file():
        lines = SNAPSHOT.read_text(encoding="utf-8").splitlines()
        existing_names = {
            line.strip()
            for line in lines
            if line.strip() and not line.lstrip().startswith("#")
        }
        for skill in custom:
            if skill["name"] not in existing_names:
                lines.append(skill["name"])
        SNAPSHOT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Applied {len(custom)} local DBS extension(s) on upstream v{version}.")


if __name__ == "__main__":
    main()
