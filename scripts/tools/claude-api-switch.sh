#!/usr/bin/env bash
set -euo pipefail

CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
PROFILES_FILE="$CLAUDE_DIR/api_profiles.json"
ROOT_CLAUDE_FILE="$HOME/.claude.json"
BACKUP_DIR="$CLAUDE_DIR/backups"

usage() {
  cat <<'EOF'
Usage:
  claude-api-switch.sh list
  claude-api-switch.sh current
  claude-api-switch.sh set-token <profile> <token>
  claude-api-switch.sh switch <profile>
  claude-api-switch.sh test [profile]

Profiles:
  kimi      -> https://api.kimi.com/coding/
  sssai_a   -> https://node-hk.sssaicode.com/api
  sssai_b   -> https://node-hk.sssaicode.com/api

Notes:
  - Profiles are stored at ~/.claude/api_profiles.json
  - switch will rewrite ~/.claude/settings.json and keep a backup in ~/.claude/backups/
  - test runs: timeout 30s claude --setting-sources user -p "reply with exactly OK"
EOF
}

ensure_dirs() {
  mkdir -p "$CLAUDE_DIR" "$BACKUP_DIR"
}

init_profiles_if_missing() {
  if [[ -f "$PROFILES_FILE" ]]; then
    return
  fi

  cat > "$PROFILES_FILE" <<'EOF'
{
  "profiles": {
    "kimi": {
      "base_url": "https://api.kimi.com/coding/",
      "token": "",
      "timeout_ms": 600000,
      "disable_nonessential_traffic": "1"
    },
    "sssai_a": {
      "base_url": "https://node-hk.sssaicode.com/api",
      "token": "",
      "timeout_ms": 600000,
      "disable_nonessential_traffic": "1"
    },
    "sssai_b": {
      "base_url": "https://node-hk.sssaicode.com/api",
      "token": "",
      "timeout_ms": 600000,
      "disable_nonessential_traffic": "1"
    }
  }
}
EOF
}

py() {
  python3 - "$@"
}

list_profiles() {
  py "$PROFILES_FILE" <<'PY'
import json, sys
from pathlib import Path
profiles_file = Path(sys.argv[1])
data = json.loads(profiles_file.read_text())
profiles = data.get("profiles", {})
for name, conf in profiles.items():
    token = conf.get("token", "")
    ready = "ready" if token else "missing_token"
    prefix = token[:13] + "***" if token else ""
    print(f"{name:8} base={conf.get('base_url','')} status={ready} {prefix}")
PY
}

show_current() {
  if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo "settings not found: $SETTINGS_FILE"
    return 1
  fi

  py "$SETTINGS_FILE" <<'PY'
import json, sys
from pathlib import Path
s = json.loads(Path(sys.argv[1]).read_text())
env = s.get("env", {})
base = env.get("ANTHROPIC_BASE_URL", "")
token = env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY") or ""
prefix = token[:13] + "***" if token else ""
print(f"base={base}")
print(f"token={prefix} len={len(token)}")
PY
}

set_token() {
  local profile="$1"
  local token="$2"
  py "$PROFILES_FILE" "$profile" "$token" <<'PY'
import json, sys
from pathlib import Path
profiles_file = Path(sys.argv[1])
profile = sys.argv[2]
token = sys.argv[3]
data = json.loads(profiles_file.read_text())
profiles = data.setdefault("profiles", {})
if profile not in profiles:
    raise SystemExit(f"unknown profile: {profile}")
profiles[profile]["token"] = token
profiles_file.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
print(f"token updated: {profile}")
PY
}

ensure_onboarding() {
  if [[ ! -f "$ROOT_CLAUDE_FILE" ]]; then
    echo '{"hasCompletedOnboarding": true}' > "$ROOT_CLAUDE_FILE"
    return
  fi

  py "$ROOT_CLAUDE_FILE" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
obj = json.loads(p.read_text())
obj["hasCompletedOnboarding"] = True
p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
print("onboarding flag ensured")
PY
}

switch_profile() {
  local profile="$1"

  local conf
  conf=$(py "$PROFILES_FILE" "$profile" <<'PY'
import json, sys
from pathlib import Path
profiles_file = Path(sys.argv[1])
profile = sys.argv[2]
data = json.loads(profiles_file.read_text())
profiles = data.get("profiles", {})
if profile not in profiles:
    raise SystemExit(f"unknown profile: {profile}")
conf = profiles[profile]
token = conf.get("token", "")
if not token:
    raise SystemExit(f"profile '{profile}' missing token; run set-token first")
print(conf.get("base_url", ""))
print(token)
print(conf.get("timeout_ms", 600000))
print(conf.get("disable_nonessential_traffic", "1"))
PY
)

  local base token timeout_ms disable_traffic
  base="$(echo "$conf" | sed -n '1p')"
  token="$(echo "$conf" | sed -n '2p')"
  timeout_ms="$(echo "$conf" | sed -n '3p')"
  disable_traffic="$(echo "$conf" | sed -n '4p')"

  if [[ -f "$SETTINGS_FILE" ]]; then
    cp "$SETTINGS_FILE" "$BACKUP_DIR/settings.json.bak.$(date +%Y%m%d%H%M%S)"
  fi

  py "$SETTINGS_FILE" "$token" "$base" "$timeout_ms" "$disable_traffic" <<'PY'
import json, sys
from pathlib import Path
settings_file = Path(sys.argv[1])
token, base, timeout_ms, disable_traffic = sys.argv[2:6]
obj = {
  "env": {
    "ANTHROPIC_AUTH_TOKEN": token,
    "ANTHROPIC_BASE_URL": base,
    "API_TIMEOUT_MS": int(timeout_ms),
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": str(disable_traffic)
  },
  "permissions": {
    "allow": [],
    "deny": []
  }
}
settings_file.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")
print(f"switched to base={base}")
PY

  ensure_onboarding
  echo "profile switched: $profile"
}

test_profile() {
  local profile="${1:-}"
  if [[ -n "$profile" ]]; then
    switch_profile "$profile"
  fi
  set +e
  timeout 30s claude --setting-sources user -p "reply with exactly OK" --output-format text
  local ec=$?
  set -e
  if [[ $ec -eq 0 ]]; then
    echo "test passed"
  else
    echo "test failed, exit=$ec"
    return $ec
  fi
}

main() {
  ensure_dirs
  init_profiles_if_missing

  local cmd="${1:-}"
  case "$cmd" in
    list)
      list_profiles
      ;;
    current)
      show_current
      ;;
    set-token)
      [[ $# -eq 3 ]] || { usage; exit 2; }
      set_token "$2" "$3"
      ;;
    switch)
      [[ $# -eq 2 ]] || { usage; exit 2; }
      switch_profile "$2"
      ;;
    test)
      if [[ $# -eq 2 ]]; then
        test_profile "$2"
      elif [[ $# -eq 1 ]]; then
        test_profile
      else
        usage
        exit 2
      fi
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo "unknown command: $cmd"
      usage
      exit 2
      ;;
  esac
}

main "$@"
