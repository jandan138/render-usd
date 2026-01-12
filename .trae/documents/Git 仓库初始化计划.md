# Git 仓库初始化计划

我将把当前项目初始化为一个 Git 仓库，并添加适当的 `.gitignore` 文件以排除不需要的版本控制文件（如临时输出、环境目录等）。

## 1. 初始化 Git 仓库
*   在项目根目录 `/cpfs/shared/simulation/zhuzihou/dev/render-usd` 执行 `git init`。

## 2. 创建 .gitignore
*   创建一个 `.gitignore` 文件，包含以下忽略项：
    *   Python 缓存 (`__pycache__`, `*.pyc`)
    *   构建产物 (`build/`, `dist/`, `*.egg-info`)
    *   本地环境目录 (`miniconda/`, `venv/`, `.env`)
    *   IDE 配置 (`.vscode/`, `.idea/`)
    *   输出结果目录 (`output_*/`)
    *   临时文件 (`.DS_Store`)

## 3. 提交代码
*   添加所有文件到暂存区。
*   执行首次提交 (`Initial commit`)。

## 4. 验证
*   检查 `git status` 确保没有遗漏重要文件或包含不应提交的文件。
