from pathlib import Path
import sys

import click

from nexogenesis.commands.validate import run_validate
from nexogenesis.indexing import check_index_staleness
from nexogenesis.schemas import BUFFER_ROLES
from nexogenesis.store import Store
from nexogenesis.models import CardType, RelationType


def _python_env_hints() -> list[str]:
    hints: list[str] = []
    exe = Path(sys.executable).resolve()
    exe_s = str(exe).lower()
    if "windowsapps" in exe_s or "microsoft\\windowsapps" in exe_s:
        hints.append(
            f"当前 Python 疑似 Windows Store 占位符：{exe}；"
            "请改用项目 .venv\\Scripts\\python.exe 或正式安装的 python.exe"
        )
    venv = Path(sys.prefix)
    if "venv" not in str(venv).lower() and ".venv" not in str(venv).lower():
        hints.append(
            "建议在项目虚拟环境中运行：.venv\\Scripts\\python.exe -m nexogenesis …"
        )
    hints.append("Windows 若中文乱码，可设置环境变量 PYTHONUTF8=1")
    return hints


def _graph_sparsity_warnings(root_path: Path) -> list[str]:
    cards_dir = root_path / "01-Cards"
    if not cards_dir.exists():
        return []
    store = Store(cards_dir).load()
    instances = [
        c for c in store.cards.values() if c.type != CardType.DOMAIN
    ]
    if len(instances) < 5:
        return []
    hollow = sum(1 for c in instances if not c.relations)
    ratio = hollow / len(instances)
    warnings: list[str] = []
    if ratio >= 0.4:
        warnings.append(
            f"图谱偏稀：{hollow}/{len(instances)} 张非 domain 卡无 outgoing relations "
            f"（{ratio:.0%}）。建议 construct --lens articulate|distinguish 优先补边；"
            "conflict 须 involves 双方，勿只挂 domain。"
        )
    conflicts = [c for c in store.cards.values() if c.type == CardType.CONFLICT]
    missing_involves = [
        c.id
        for c in conflicts
        if not any(r.type == RelationType.INVOLVES for r in c.relations)
    ]
    if missing_involves:
        show = ", ".join(f"`{x}`" for x in missing_involves[:6])
        extra = len(missing_involves) - min(6, len(missing_involves))
        msg = f"conflict 缺 involves：{show}"
        if extra > 0:
            msg += f" …等共 {len(missing_involves)} 张"
        warnings.append(msg + "。对立双方应落到 claim/model。")
    return warnings


@click.command()
@click.option("--root", default=".", help="项目根目录")
def doctor_cmd(root: str):
    root_path = Path(root).resolve()
    issues: list[str] = []

    for hint in _python_env_hints():
        click.echo(f"HINT: {hint}")

    for d in ["00-Inbox", "01-Cards", "02-Profile", "05-Buffer", "06-Journal"]:
        if not (root_path / d).exists():
            issues.append(f"缺少目录: {d}")

    for role in sorted(BUFFER_ROLES):
        role_dir = root_path / "05-Buffer" / role
        if not role_dir.exists():
            issues.append(f"缺少 Buffer role 目录: 05-Buffer/{role}")

    meta = root_path / "01-Cards" / "_meta"
    for name in ("ontology.md", "body-structure.md"):
        if not (meta / name).exists():
            issues.append(f"缺少契约文件: 01-Cards/_meta/{name}")

    hook = root_path / ".git" / "hooks" / "pre-commit"
    if (root_path / ".git").exists() and not hook.exists():
        issues.append("已有 .git 但未安装 pre-commit hook（可重新运行 init）")

    errors, warnings = run_validate(root_path)
    for e in errors:
        issues.append(e)
    for w in warnings:
        click.echo(f"WARNING: {w}")

    stale_issues, stale_warnings = check_index_staleness(root_path)
    for w in stale_warnings:
        click.echo(f"WARNING: {w}")
    issues.extend(stale_issues)

    for w in _graph_sparsity_warnings(root_path):
        click.echo(f"WARNING: {w}")

    if issues:
        for i in issues:
            click.echo(f"ISSUE: {i}")
        raise click.ClickException("Doctor found issues.")
    click.echo("Doctor: OK")
