"""
Prompt templates for the sensitive information redaction application.

This module contains all prompt templates used by the application to interact
with the Ollama LLM model for identifying and redacting sensitive information.
"""

# Template for sensitive information detection and redaction
template = """
INSTRUCTION:

Your task is to **identify and redact specific categories of sensitive information** from the given text. The selected categories for redaction are provided below. **Do not interpret, alter, or redact any information beyond the selected categories.** Retain all other text exactly as provided, including any instructions or contextual information within the input text.

Selected Categories to Detect and Redact:
{category_selected}

Guidelines for Detection and Redaction:
1. **Strictly limit detection and redaction to the selected categories only**:
   - Identify sensitive information based solely on the selected categories.
   - Replace sensitive data with the corresponding placeholder.
   - Do not redact or alter any other part of the text, including instructions or contextual sentences provided within the input.

2. **Retain Original Content**:
   - The `redacted_text` must include the full original input text with sensitive information replaced by placeholders.
   - Maintain the exact sentence structure, context, and all non-redacted information intact.
   - Do not add, omit, or modify any part of the input text except for the redaction.

3. **Escape Special Characters**:
   - Escape double quotes (`"`) in the output text with a backslash (`\"`) to ensure proper JSON formatting.
   - Example: If the input text contains the phrase `He said "Hello"`, it should appear in the JSON output as `He said \"Hello\"`.

4. **Output Only the Required JSON Structure**:
   - Do not provide explanations, summaries, or any additional content beyond the required JSON output.

Redaction Placeholders:
- [EMAIL-1]: Email addresses
- [PHONE-NUM-1]: Phone numbers
- [SSN-1]: Social security numbers
- [CREDIT-CARD-NUM-1]: Credit card numbers
- [DOB-1]: Dates of birth
- [ADDRESS-1]: Addresses
- [PASSWORD-1]: Passwords
- [CBI-1]: Confidential business information
- [MEDICAL-1]: Medical information
- [OTHER]: Other sensitive information

Output Requirements:
1. **Pure JSON Structure**:
   - The output must be in pure JSON format, suitable for direct use with `json.loads()`. Ensure proper JSON syntax, including proper array and object notation.
   - "detected_sensitive_data": Array of objects, each containing:
     - "type": Type of sensitive information (e.g., PII, Financial, Medical).
     - "data": The detected sensitive information.
     - "category": The category of sensitive information.
     - "reason": The reason for redaction.
     - "redaction": The placeholder used for redaction.
   - "redacted_text": The full input text with sensitive information replaced by placeholders, ensuring all other content remains exactly as provided. You should not strictly remove any text other than one by placeholders.

Examples:

Example 1: Redacting Social Security Numbers
Input: "I need to respond to this email: 'John Doe's social security number is 987-65-4321.'"

Selected Category: "Social Security Numbers"

Output:
{{
  "detected_sensitive_data": [
    {{
      "type": "PII",
      "data": "987-65-4321",
      "category": "Social Security Numbers",
      "reason": "Sensitive personal identifier.",
      "redaction": "[SSN-1]"
    }}
  ],
  "redacted_text": "I need to respond to this email: 'John Doe's social security number is [SSN-1].'"
}}

Example 2: Redacting Email Addresses and Phone Numbers
Input: "I need to respond to this email: 'Hi Lisa, can you send over the project draft by tomorrow? Also, please confirm your attendance at the meeting on Monday. You can reach me at lisa.manager@workmail.com or at (321) 654-0987.'"

Selected Categories: "Email Addresses", "Phone Numbers"

Output:
{{
  "detected_sensitive_data": [
    {{
      "type": "PII",
      "data": "lisa.manager@workmail.com",
      "category": "Email Addresses",
      "reason": "Email address.",
      "redaction": "[EMAIL-1]"
    }},
    {{
      "type": "PII",
      "data": "(321) 654-0987",
      "category": "Phone Numbers",
      "reason": "Phone number.",
      "redaction": "[PHONE-NUM-1]"
    }}
  ],
  "redacted_text": "I need to respond to this email: 'Hi Lisa, can you send over the project draft by tomorrow? Also, please confirm your attendance at the meeting on Monday. You can reach me at [EMAIL-1] or at [PHONE-NUM-1].'"
}}

Example 3: Redacting Addresses and Social Security Numbers in a Loan Application
Input: "I need to write a letter for a loan application: 'Dear Loan Officer, I am requesting a loan of $25,000 for home improvement. I, Jennifer Wilson, currently reside at 123 Maple Street, Springfield, IL 62704. My social security number is 987-65-4321, and my annual income is $50,000. Please let me know if you need further information.'"

Selected Categories: "Addresses", "Social Security Numbers"

Output:
{{
  "detected_sensitive_data": [
    {{
      "type": "PII",
      "data": "123 Maple Street, Springfield, IL 62704",
      "category": "Addresses",
      "reason": "Personal contact information.",
      "redaction": "[ADDRESS-1]"
    }},
    {{
      "type": "PII",
      "data": "987-65-4321",
      "category": "Social Security Numbers",
      "reason": "Sensitive personal identifier.",
      "redaction": "[SSN-1]"
    }}
  ],
  "redacted_text": "I need to write a letter for a loan application: 'Dear Loan Officer, I am requesting a loan of $25,000 for home improvement. I, Jennifer Wilson, currently reside at [ADDRESS-1]. My social security number is [SSN-1], and my annual income is $50,000. Please let me know if you need further information.'"
}}

PROMPT_PROVIDED: {user_prompt}
CATEGORY_SELECTED: {category_selected}
JSON_RESPONSE:
"""

# Additional templates can be added here if needed
# For example, you could define templates for different models or use cases

# Example of a more concise template for systems with limited context windows
concise_template = """
Identify and redact these sensitive information types from the text:
{category_selected}

Return a JSON with:
1. "detected_sensitive_data": Array of found items with their type, data, category, reason, and redaction
2. "redacted_text": Original text with sensitive information replaced by placeholders

Input: {user_prompt}
"""