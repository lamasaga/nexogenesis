from pathlib import Path

import click


@click.command(name="serve")
@click.option("--root", default=".", help="知识库根目录")
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8787, type=int)
def serve_cmd(root: str, host: str, port: int) -> None:
    """启动 Web 应用（FastAPI + 前端构建产物）。"""
    import uvicorn

    from nexogenesis.runtime.api import create_app

    app = create_app(Path(root))
    uvicorn.run(app, host=host, port=port)
