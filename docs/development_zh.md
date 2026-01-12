# 开发指南

[English](development.md)

## 贡献代码

欢迎贡献！请按照以下步骤操作：

1.  Fork 本仓库。
2.  创建一个特性分支 (`git checkout -b feature/AmazingFeature`)。
3.  提交您的更改 (`git commit -m 'Add some AmazingFeature'`)。
4.  推送到分支 (`git push origin feature/AmazingFeature`)。
5.  提交 Pull Request。

## 文档规范

为了保持高质量的文档，**任何代码更改都必须附带相应的文档更新**。

1.  **Docstrings**: 所有公共类和函数都必须有文档字符串（推荐 Google 风格）。
2.  **API 文档**: 如果您添加了新模块或函数，请更新 `docs/api/`。
3.  **可读性**: 使用清晰、简洁的语言。使用代码块作为示例。
4.  **链接**: 确保 `docs/api/*.md` 中的源代码链接有效。

### 示例文档字符串

```python
def my_function(param1: int, param2: str) -> bool:
    """
    Brief description of what the function does.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        bool: Description of the return value.
    """
    return True
```

## 测试

在提交 PR 之前，请运行本地测试以确保没有回归。

```bash
# 运行单文件渲染测试
python -m render_usd.cli single --usd_path <test_file.usd> --output_dir ./test_output
```
