# demo-kb — 演示知识库

29 张人工策展的演示卡片（6 个 domain，含 supports/conflicts-with/involves 等关系），
用于开发调试与分发演示——开发仓不跟踪真实知识体（单向镜像纪律，见 AGENTS.md §七），
本目录是仓库内唯一的知识库样例。

## 用法

```bash
python -m nexogenesis serve --root demo-kb --port 8787
# 浏览器打开 http://localhost:8787
```

## 重新生成

```bash
python demo-kb/gen_demo_kb.py   # 注意：会重写本目录 01-Cards/（输出到脚本内 ROOT 变量指定处）
```
