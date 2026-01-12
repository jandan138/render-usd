# Miniconda 安装与环境配置计划

鉴于当前环境缺少 `conda`，我将在当前目录下本地安装 Miniconda，并配置项目所需的运行环境。

## 1. 下载与安装 Miniconda
*   检查系统架构（通常为 x86_64）。
*   从官方源下载 Miniconda3 安装脚本。
*   执行静默安装，将 Miniconda 安装到当前目录下的 `./miniconda` 文件夹中（避免权限问题）。

## 2. 配置环境
*   激活本地安装的 Conda。
*   使用项目根目录下的 `environment.yml` 创建名为 `render-usd` 的虚拟环境。
    *   **注意**: `isaacsim` 相关包的下载可能需要较长时间。
*   激活 `render-usd` 环境。

## 3. 安装项目依赖
*   在活跃环境中执行 `pip install -e .` 安装 `render-usd` 包。

## 4. 再次执行测试
*   运行之前的单文件渲染测试命令，验证环境是否就绪。

```bash
python -m render_usd.cli single \
    --usd_path /cpfs/shared/simulation/zhuzihou/dev/render-usd/examples/0a85b986de35ccfdec7c686d791fd747/0a85b986de35ccfdec7c686d791fd747.usd \
    --output_dir ./output_test
```
