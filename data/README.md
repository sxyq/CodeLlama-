# data/README.md

本目录仅存放训练数据的说明与规范路径。

| 文件 | 用途 | Git |
|---|---|---|
| `Fine-Tuning.json` | Assembly + Pseudocode → C/C++ 原始对话数据（1455 条） | **禁止同步到 GitHub** |

LOCAL 路径：`data/Fine-Tuning.json`  
REMOTE 路径：`$HOME/codellama-lora/data/Fine-Tuning.json`

SHA256（两侧一致）：

`28bab944c2db29d492fb362f9e728ac8f2d4d24deb1737af80049df7e3a1c7b6`

规则：

- 远程 `Fine-Tuning.json` 为只读原始数据，不得原地修改。
- 如需 `train.json` / `validation.json` / `test.json`，必须新建文件。
- GitHub 不同步数据本体、`.venv`、`LLaMA-Factory` 完整仓库、model、checkpoint、大型 logs、credential。
