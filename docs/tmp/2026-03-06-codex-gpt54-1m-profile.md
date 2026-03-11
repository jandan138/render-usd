Problem

Enable an experimental `gpt-5.4` 1M-context profile for the local Codex CLI,
make it the default for future Codex launches, and globally enable the
experimental `multi_agent` feature by default. Then raise the default command
execution permissions so most commands run without approval, while especially
high-risk destructive command prefixes are blocked globally.

Investigation

Checked the local Codex config and model cache on 2026-03-06, and verified the
official Codex config reference.
Confirmed that:

- `/root/.codex/config.toml` is the user's global Codex CLI config file.
- The top-level `profile` key controls the default profile applied at startup.
- The `codex features enable <name>` command persists feature flags in
  `~/.codex/config.toml` as `features.<name> = true`.
- `approval_policy = "never"` removes approval prompts for normal command
  execution.
- `sandbox_mode = "danger-full-access"` removes sandbox restrictions and gives
  Codex broad local execution permissions.
- The current execpolicy mechanism uses prefix-based command rules.
- The active default model is `gpt-5.4`.
- The default Codex-exposed context window for `gpt-5.4` is `272000`.
- The 1M context option is experimental and must be enabled explicitly with
  `model_context_window` and `model_auto_compact_token_limit`.
- The experimental multi-agent feature is named `multi_agent`.

Solution

Appended a new profile to `/root/.codex/config.toml`:

- `[profiles.gpt54_1m]`
- `model = "gpt-5.4"`
- `model_reasoning_effort = "xhigh"`
- `model_verbosity = "high"`
- `model_context_window = 1000000`
- `model_auto_compact_token_limit = 900000`

Then set the top-level default startup profile:

- `profile = "gpt54_1m"`

Enabled the experimental global feature flag:

- `[features]`
- `multi_agent = true`

Raised the global execution permissions:

- `approval_policy = "never"`
- `sandbox_mode = "danger-full-access"`

Added global destructive-command guardrails in `/root/.codex/rules/default.rules`:

- `rm`
- `mv`
- `rmdir`
- `unlink`
- `git clean`
- `git reset --hard`
- `git checkout --`
- `git push --force`
- `git push -f`
- `git push --force-with-lease`

This makes future `codex` launches use the 1M configuration by default,
without requiring `--profile gpt54_1m`, and the multi-agent feature is enabled
for new Codex sessions by default. Most commands now run without approval, and
the listed destructive prefixes are blocked globally.

Results

Execution command:

```bash
cat <<'EOF' >> /root/.codex/config.toml

[profiles.gpt54_1m]
model = "gpt-5.4"
model_reasoning_effort = "xhigh"
model_verbosity = "high"
model_context_window = 1000000
model_auto_compact_token_limit = 900000
EOF
```

Observed result:

- The profile block was added successfully.
- The global config now defaults to `gpt54_1m` at startup.
- The global feature state now reports `multi_agent experimental true`.
- The global config now uses `approval_policy = "never"` and
  `sandbox_mode = "danger-full-access"`.
- Execpolicy checks confirm that `rm`, `mv`, `git clean`, and force-push forms
  beginning with `git push --force` or `git push -f` are blocked.
- A backup copy of the previous config was written to `/tmp/`.

Risk note:

- `model_auto_compact_token_limit = 900000` is a conservative inferred value,
  not an OpenAI-published recommendation.
- Prefix-based execpolicy rules do not catch `git push origin main --force`
  because `--force` is not at the command prefix. Catching every force-push
  shape would require a broader rule such as blocking all `git push`.
