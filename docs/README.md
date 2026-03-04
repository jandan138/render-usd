# Documentation Index

Welcome to the **Render USD** project documentation. This library provides a comprehensive toolkit for rendering USD (Universal Scene Description) assets using NVIDIA Isaac Sim.

[中文版](README_zh.md)

## 📚 Contents

### 1. [Getting Started](guides/getting_started.md)
*   [Prerequisites](guides/getting_started.md#prerequisites)
*   [Installation](guides/getting_started.md#installation)
*   [Setting up Environment](guides/getting_started.md#setting-up-environment)

### 2. [Architecture Overview](design/architecture.md)
*   [System Design](design/architecture.md#system-design)
*   [Core Modules](design/architecture.md#core-modules)
*   [Directory Structure](design/architecture.md#directory-structure)

### 3. [Usage Guide](guides/usage.md)
*   [Command Line Interface (CLI)](guides/usage.md#command-line-interface)
*   [Single File Rendering](guides/usage.md#single-file-rendering)
*   [Batch Rendering](guides/usage.md#batch-rendering)
*   [DLC Job Submission](dlc/README.md)

### 3.5. [DLC Pipeline Documentation](dlc/README.md)
*   [DLC Changelog](dlc/changelog.md) - History of all DLC-related changes
*   [DLC Crash Fix Summary](dlc-crash-fix-summary.md) - Segmentation fault fix documentation
*   [Crash Investigation](dlc/crash-investigation/) - Detailed analysis of crash issues
    *   [Fix Implementation](dlc/crash-investigation/fix-implementation.md)
    *   [Renderer Analysis](dlc/crash-investigation/renderer-analysis.md)
    *   [Resource Analysis](dlc/crash-investigation/resource-analysis.md)
    *   [Parameter Comparison](dlc/crash-investigation/parameter-comparison.md)
    *   [Isaac Sim Research](dlc/crash-investigation/isaac-sim-crash-research.md)
    *   [USD File Analysis](dlc/crash-investigation/usd-file-analysis.md)
*   [Agent Team Playbook](agent-team-playbook.md) - Guidelines for agent-based development

### 4. API Reference
*   **[Core Modules](api/core.md)**: High-level rendering logic, camera management, and scene setup.
*   **[Utilities](api/utils.md)**: Helper functions for USD manipulation, image processing, and more.
*   **[Configuration](api/config.md)**: Global settings and environment variables.

### 5. [Development Guide](guides/development.md)
*   [Contributing](guides/development.md#contributing)
*   [Documentation Guidelines](guides/development.md#documentation-guidelines)
*   [Testing](guides/development.md#testing)

---

## Quick Links
*   [Source Code](../src/render_usd/)
*   [Examples](../examples/)
