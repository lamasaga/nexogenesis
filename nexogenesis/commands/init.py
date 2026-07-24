import shutil
from pathlib import Path

import click


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
        "05-Buffer/claim",
        "05-Buffer/model",
        "05-Buffer/method",
        "05-Buffer/conflict",
        "05-Buffer/note",
        "06-Journal",
        "schemes/default",
        "tests/fixtures",
        ".nexogenesis/tmp",
    ]
    for d in dirs:
        (root_path / d).mkdir(parents=True, exist_ok=True)

    scheme_src = Path(__file__).parent.parent.parent / "schemes" / "default"
    scheme_dst = root_path / "schemes" / "default"
    for fname in ["scheme.md", "ontology-template.md", "profile-template.md", "migration.md"]:
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

    click.echo(f"Initialized Nexogenesis project at {root_path}")
