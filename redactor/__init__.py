"""
Redactor Module for Ollama Guardrail

This module provides the core redaction functionality for detecting and
redacting sensitive information from text using LLM models.

Classes:
    SensitiveInformationRedactor: Main redactor class for processing text

Author: Harsh
"""

from .redactor import SensitiveInformationRedactor

__all__ = ['SensitiveInformationRedactor']

__version__ = "1.0.0"
