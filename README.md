# Render USD

A modular rendering pipeline for USD assets using NVIDIA Isaac Sim.

## 📖 Documentation

Full documentation is available in the [docs/](docs/) directory.

*   **[Getting Started](docs/getting_started.md)**: Installation and setup.
*   **[Usage Guide](docs/usage.md)**: How to run rendering tasks.
*   **[API Reference](docs/api/core.md)**: Detailed code documentation.
*   **[Architecture](docs/architecture.md)**: System design overview.

## Quick Start

```bash
# Install package
pip install -e .

# Render a single file
python -m render_usd.cli single --usd_path /path/to/asset.usd --output_dir ./output
```
