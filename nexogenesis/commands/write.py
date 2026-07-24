import os
import tempfile
from pathlib import Path

import click

from nexogenesis import journal
from nexogenesis.commands.index import generate_indexes
from nexogenesis.commands.validate import run_validate
from nexogenesis.operations import BatchOperation, card_meta_from_write
from nexogenesis.yaml_utils import atomic_write_file, merge_frontmatter


def _append_profile_question(profile_path: Path, item: dict) -> None:
    lines = []
    if profile_path.exists():
        lines = profile_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["# 问题清单", "", "| 问题 | 提出时间 | 状态 |", "|---|---|---|"]
    lines.append(f"| {item['question']} | {item.get('added_at', '')} | active |")
    atomic_write_file(profile_path, "\n".join(lines) + "\n")


@click.command()
@click.option("--batch", required=True, type=click.Path(exists=True), help="batch YAML 文件")
@click.option("--root", default=".", help="项目根目录")
def write_cmd(batch: str, root: str):
    root_path = Path(root).resolve()
    cards_dir = root_path / "01-Cards"
    profile_path = root_path / "02-Profile" / "问题清单.md"
    batch_op = BatchOperation.from_file(Path(batch))

    card_writes = [w for w in batch_op.writes if w.get("target", "card") == "card"]
    profile_writes = [w for w in batch_op.writes if w.get("target") == "profile_question"]

    backup_files: list[tuple[Path, Path | None]] = []
    try:
        for item in card_writes:
            final_path = cards_dir / f"{item['id']}.md"
            meta = card_meta_from_write(item)
            content = merge_frontmatter(meta, item.get("body", ""))
            tmp = Path(tempfile.mktemp(dir=cards_dir, prefix=".tmp-", suffix=".md"))
            tmp.write_text(content, encoding="utf-8")
            backup = None
            if final_path.exists():
                backup = Path(tempfile.mktemp(dir=cards_dir, prefix=".bak-", suffix=".md"))
                backup.write_text(final_path.read_text(encoding="utf-8"), encoding="utf-8")
            os.replace(tmp, final_path)
            backup_files.append((final_path, backup))

        for pw in profile_writes:
            _append_profile_question(profile_path, pw)

        errors, warnings = run_validate(root_path)
        if errors:
            raise RuntimeError("; ".join(errors))

        journal.append(
            root_path,
            batch_op.operation_id,
            "write",
            [w["id"] for w in card_writes],
            batch_op.source,
            batch_op.approved_by,
        )
        generate_indexes(root_path)

    except Exception:
        for final_path, backup in backup_files:
            if backup and backup.exists():
                os.replace(backup, final_path)
            elif backup is None and final_path.exists():
                os.unlink(final_path)
        raise click.ClickException("Write failed and was rolled back.")
    finally:
        for _, backup in backup_files:
            if backup and backup.exists():
                os.unlink(backup)

    click.echo(f"Wrote {len(card_writes)} card(s), {len(profile_writes)} question(s).")
