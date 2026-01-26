# Prompt Templates

Prompt templates are externalized to allow updates without code changes.

## Location
- Default template: `prompts/redaction_v1.txt`
- Configured via `prompts.redaction_template` in `config.yaml`

## Versioning
- `prompts.version` is a label used for display/logging.
- Update the version when you make prompt changes.

## Editing Guidance
- Keep the JSON output contract intact.
- Do not add new keys unless you also update parsing/validation.
- Avoid embedding hardcoded category names; categories are injected at runtime.
