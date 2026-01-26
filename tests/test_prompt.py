"""
Unit tests for prompt template loading.
"""

import os
from prompt import get_template, DEFAULT_TEMPLATE


def test_get_template_from_file(tmp_path):
    template_path = tmp_path / "template.txt"
    template_path.write_text("Hello {user_prompt}")

    template = get_template(str(template_path))

    assert "Hello {user_prompt}" in template


def test_get_template_fallback():
    template = get_template("/nonexistent/prompt.txt")

    assert template == DEFAULT_TEMPLATE
