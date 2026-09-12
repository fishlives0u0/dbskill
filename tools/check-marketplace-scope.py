#!/usr/bin/env python3
"""校验 Claude Code marketplace、全量入口与本仓库本地扩展的暴露范围。"""

import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT_DIR / ".claude-plugin" / "marketplace.json"
BUNDLE_MANIFEST_PATH = ROOT_DIR / ".claude-plugin" / "plugin.json"
LOCAL_REGISTRY_PATH = ROOT_DIR / ".dbs-local" / "custom-skills.json"


def published_skill_dirs() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--", "skills/*/SKILL.md"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        paths = [Path(line) for line in result.stdout.splitlines() if line]
    else:
        paths = list((ROOT_DIR / "skills").glob("*/SKILL.md"))

    return sorted(
        path.parent.name for path in paths if "beta" not in path.parent.name
    )


def load_local_skills() -> list[dict]:
    if not LOCAL_REGISTRY_PATH.is_file():
        return []
    data = json.loads(LOCAL_REGISTRY_PATH.read_text(encoding="utf-8"))
    return data.get("skills", [])


def main() -> None:
    marketplace = json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))
    plugins = marketplace.get("plugins", [])
    plugin_names = [plugin.get("name") for plugin in plugins]
    local_skills = load_local_skills()
    local_names = [skill.get("name") for skill in local_skills]
    all_names = plugin_names + local_names
    expected_paths = [f"./skills/{name}" for name in plugin_names]
    expected_paths.extend(skill.get("source", f"./skills/{skill.get('name')}") for skill in local_skills)
    bundle_manifest = json.loads(BUNDLE_MANIFEST_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []

    if len(plugin_names) != len(set(plugin_names)):
        errors.append("marketplace 存在重复插件名")
    if len(local_names) != len(set(local_names)):
        errors.append("本地扩展注册表存在重复 Skill 名")
    collisions = sorted(set(plugin_names) & set(local_names))
    if collisions:
        errors.append(f"本地扩展与官方 Skill 重名：{collisions!r}")

    for plugin in plugins:
        name = plugin.get("name", "<未命名>")
        expected_source = "./" if name == "dbs" else f"./skills/{name}"
        if plugin.get("source") != expected_source:
            errors.append(
                f"插件 {name} 的 source 为 {plugin.get('source')!r}，"
                f"应为 {expected_source!r}"
            )
        if plugin.get("strict") is not True:
            errors.append(f"插件 {name} 应使用 strict: true 隔离组件")
        if "skills" in plugin:
            errors.append(f"插件 {name} 不应在 marketplace 中重复声明 skills")

    for skill in local_skills:
        name = skill.get("name", "")
        source = skill.get("source", "")
        if not name or not source:
            errors.append(f"本地扩展登记缺少 name/source：{skill!r}")
            continue
        skill_file = ROOT_DIR / source.removeprefix("./") / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"本地扩展 {name} 引用了不存在的 {source}/SKILL.md")

    if bundle_manifest.get("name") != "dbs":
        errors.append("根级 plugin.json 的 name 应为 'dbs'")
    if "version" in bundle_manifest:
        errors.append("根级 plugin.json 不应固定 version，应沿用 marketplace 发布版本")
    bundle_paths = bundle_manifest.get("skills")
    if bundle_paths != expected_paths:
        errors.append(
            f"dbs 全量入口的 skills 为 {bundle_paths!r}，应为 {expected_paths!r}"
        )
    if any("beta" in path for path in bundle_paths or []):
        errors.append(f"dbs 全量入口暴露了本地 beta Skill：{bundle_paths!r}")
    for path in bundle_paths or []:
        skill_file = ROOT_DIR / path.removeprefix("./") / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"dbs 全量入口引用了不存在的 {path}/SKILL.md")

    extra_skill_dirs = sorted(set(published_skill_dirs()) - set(all_names))
    if extra_skill_dirs:
        errors.append(
            "Git 已跟踪但未登记到 marketplace 或本地扩展注册表的公开 Skill："
            f"{extra_skill_dirs!r}"
        )

    if errors:
        print("Marketplace 暴露范围校验失败：", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        sys.exit(1)

    print(
        "Marketplace 暴露范围校验通过："
        f"{len(plugin_names)} 个官方公开入口 + {len(local_names)} 个本地扩展；"
        f"dbs 全量入口共加载 {len(expected_paths)} 个 Skill 路径"
    )


if __name__ == "__main__":
    main()
