# Claude API 切换工具说明

## Problem

需要在同一台机器上频繁切换 Claude CLI 的多个 API 配置（目前是 1 个 Kimi + 2 个 SSSAI），避免每次手工改 `~/.claude/settings.json`。

## Investigation

之前实际使用过的方式有三种：

1. 临时环境变量方式（仅当前 shell 会话生效）
   - `export ANTHROPIC_BASE_URL=...`
   - `export ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN=...`
2. 用户级配置文件方式（长期生效）
   - `~/.claude/settings.json` 中写入 `env`
3. 初始化文件方式（跳过 onboarding）
   - `~/.claude.json` 中确保 `hasCompletedOnboarding: true`

痛点：手改配置容易遗漏字段，且多 key 轮换不方便。

## Solution

新增脚本：`scripts/tools/claude-api-switch.sh`

功能：

- `list`：列出 profile 和是否已配置 token
- `current`：查看当前生效的 base/token 前缀
- `set-token <profile> <token>`：写入某个 profile 的 token
- `switch <profile>`：切换并重写 `~/.claude/settings.json`
- `test [profile]`：切换后做 30 秒连通性测试

内置 profile：

- `kimi`（`https://api.kimi.com/coding/`）
- `sssai_a`（`https://node-hk.sssaicode.com/api`）
- `sssai_b`（`https://node-hk.sssaicode.com/api`）

profile 存储文件：`~/.claude/api_profiles.json`

## Results

### 1) 初始化 profile

```bash
bash scripts/tools/claude-api-switch.sh list
```

### 2) 设置三个 token（示例）

```bash
bash scripts/tools/claude-api-switch.sh set-token kimi <KIMI_TOKEN>
bash scripts/tools/claude-api-switch.sh set-token sssai_a <SSSAI_TOKEN_A>
bash scripts/tools/claude-api-switch.sh set-token sssai_b <SSSAI_TOKEN_B>
```

### 3) 切换到某个 API

```bash
bash scripts/tools/claude-api-switch.sh switch kimi
```

### 4) 切换并测试

```bash
bash scripts/tools/claude-api-switch.sh test sssai_b
```

### 5) 查看当前配置

```bash
bash scripts/tools/claude-api-switch.sh current
```

说明：`switch` 会自动备份旧配置到 `~/.claude/backups/`。
