#!/usr/bin/env python3
"""Apply fishlives0u0 local DBS skills on top of the mirrored upstream repository."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".dbs-local" / "custom-skills.json"
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = ROOT / ".claude-plugin" / "plugin.json"
SNAPSHOT = ROOT / "skills" / "dbs" / "references" / "official-skill-names.txt"
VERSION = ROOT / "VERSION"


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    custom = registry.get("skills", [])
    version = VERSION.read_text(encoding="utf-8").strip()

    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    plugins = marketplace.setdefault("plugins", [])
    by_name = {item.get("name"): item for item in plugins}

    for skill in custom:
        name = skill["name"]
        skill_file = ROOT / skill["source"].removeprefix("./") / "SKILL.md"
        if not skill_file.is_file():
            raise SystemExit(f"Local skill is missing: {skill_file}")

        local_entry = {
            "name": name,
            "description": skill["description"],
            "source": skill["source"],
            "strict": True,
            "version": version,
            "category": skill.get("category", "content-creation"),
            "keywords": skill.get("keywords", []),
        }

        existing = by_name.get(name)
        if existing is None:
            plugins.append(local_entry)
        else:
            # Local registry is the source of truth for explicitly registered custom skills.
            existing.clear()
            existing.update(local_entry)

    marketplace["plugins"] = plugins
    MARKETPLACE.write_text(
        json.dumps(marketplace, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))
    paths = plugin.setdefault("skills", [])
    for skill in custom:
        path = skill["source"]
        if path not in paths:
            paths.append(path)
    plugin["skills"] = paths
    PLUGIN.write_text(
        json.dumps(plugin, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Keep the fallback candidate snapshot aware of local skills as well.
    if SNAPSHOT.is_file():
        lines = SNAPSHOT.read_text(encoding="utf-8").splitlines()
        existing_names = {line.strip() for line in lines if line.strip() and not line.startswith("#")}
        changed = False
        for skill in custom:
            if skill["name"] not in existing_names:
                lines.append(skill["name"])
                changed = True
        if changed:
            SNAPSHOT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Applied {len(custom)} local DBS extension(s) on upstream v{version}.")


if __name__ == "__main__":
    main()
