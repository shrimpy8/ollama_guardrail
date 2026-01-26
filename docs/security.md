# Security Notes

## Threat Model Highlights
- Input text may contain prompt injection attempts.
- Logs must avoid leaking sensitive data unless explicitly enabled.
- Output must be schema-valid to reduce unsafe downstream usage.

## Mitigations
- Prompt constraints: system-style rules embedded in the template.
- Injection detection: common patterns are flagged (warning only).
- Deterministic redaction: final redaction performed in code.
- Log hygiene: raw model output logged only when `log_sensitive_data` is enabled.

## Operational Guidance
- Keep `log_sensitive_data` set to `false` in production.
- Rotate API keys periodically and monitor usage.
