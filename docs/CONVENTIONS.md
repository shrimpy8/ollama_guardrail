# Documentation Conventions

This project uses short, practical docstrings for public functions/classes and key helpers.

## Docstring Standard (short form)
Use Google-style blocks when the function is non-trivial or has side effects.

Template:
"""
One-line summary.

Args:
    name (type): Purpose.

Returns:
    type: What is returned.

Raises:
    ExceptionType: When it happens (optional).
"""

Guidelines:
- Keep it short. Prefer clarity over completeness.
- Document side effects (logging, I/O, rate limiting) when relevant.
- For tiny helpers, a single-line docstring is acceptable.
- Do not repeat obvious information already in the function name.
