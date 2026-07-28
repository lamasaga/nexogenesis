import shutil
from pathlib import Path

import click

from nexogenesis.schemas import BUFFER_ROLES


@click.command()
@click.option("--root", default=".", help="项目根目录")
def init_cmd(root: str):
    root_path = Path(root).resolve()
    dirs = [
        "00-Inbox",
        "01-Cards/_meta",
        "02-Profile",
        "03-Archive",
        "04-OutBox",
        "04-OutBox/discussions",
        *[f"05-Buffer/{role}" for role in sorted(BUFFER_ROLES)],
        "06-Journal",
        "schemes/default",
        "tests/fixtures",
        ".nexogenesis/tmp",
    ]
    for d in dirs:
        (root_path / d).mkdir(parents=True, exist_ok=True)

    scheme_src = Path(__file__).parent.parent.parent / "schemes" / "default"
    scheme_dst = root_path / "schemes" / "default"
    for fname in [
        "scheme.md",
        "ontology-template.md",
        "profile-template.md",
        "migration.md",
        "body-structure-template.md",
        "discussion-template.md",
        "attention.yaml",
    ]:
        src = scheme_src / fname
        dst = scheme_dst / fname
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)

    git_dir = root_path / ".git"
    if git_dir.exists():
        hook_src = root_path / "hooks" / "pre-commit"
        hook_dst = git_dir / "hooks" / "pre-commit"
        if hook_src.exists():
            shutil.copy(hook_src, hook_dst)
            hook_dst.chmod(0o755)
            click.echo("Installed git pre-commit hook.")

    ontology = root_path / "01-Cards" / "_meta" / "ontology.md"
    if not ontology.exists():
        template = scheme_dst / "ontology-template.md"
        if template.exists():
            shutil.copy(template, ontology)

    body_structure = root_path / "01-Cards" / "_meta" / "body-structure.md"
    if not body_structure.exists():
        # 优先 scheme 模板，其次包内 schemes/default
        for candidate in (
            scheme_dst / "body-structure-template.md",
            scheme_src / "body-structure-template.md",
        ):
            if candidate.exists():
                shutil.copy(candidate, body_structure)
                break

    click.echo(f"Initialized Nexogenesis project at {root_path}")
