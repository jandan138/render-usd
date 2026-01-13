# Development Guide

[中文版](development_zh.md)

## Contributing

We welcome contributions! Please follow these steps:

1.  Fork the repository.
2.  Create a feature branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

## Documentation Guidelines

To maintain high-quality documentation, **any code change must be accompanied by a corresponding documentation update**.

1.  **Docstrings**: All public classes and functions must have docstrings (Google Style recommended).
2.  **API Docs**: If you add a new module or function, update `docs/api/`.
3.  **Readability**: Use clear, concise English. Use code blocks for examples.
4.  **Links**: Ensure links to source code in `docs/api/*.md` are valid.

### Example Docstring

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

## Testing

Before submitting a PR, run the local tests to ensure no regressions.

```bash
# Run single file render test
python -m render_usd.cli single --usd_path <test_file.usd> --output_dir ./test_output
```
