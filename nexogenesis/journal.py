from datetime import datetime, timezone
from pathlib import Path

from nexogenesis.yaml_utils import atomic_write_file, merge_frontmatter, split_frontmatter


def append(root: Path, operation_id: str, action: str, targets: list[str], source: str, approved_by: str) -> None:
    journal_dir = root / "06-Journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    path = journal_dir / f"{month_key}.md"

    entry = f"- {now} | {operation_id} | {action} | targets={','.join(targets)} | source={source} | approved_by={approved_by}\n"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        body = body + entry
    else:
        meta = {"title": f"Journal {month_key}", "type": "journal"}
        body = entry
    atomic_write_file(path, merge_frontmatter(meta, body))
