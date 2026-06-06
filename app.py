"""
Ollama Guardrail - Sensitive Information Redaction Tool

A production-ready application for detecting and redacting sensitive information
from text using LLM models with optional OpenAI processing.

Features:
- 10 categories of sensitive information detection
- Configuration management via YAML
- Retry logic with exponential backoff
- Rate limiting for API calls
- Comprehensive error handling and logging
- Multi-tab Gradio interface

Author: Harsh
Repository: https://github.com/shrimpy8
"""

# Import necessary libraries and modules
from dotenv import load_dotenv, set_key, dotenv_values
import os
import gradio as gr
import logging
from logging.handlers import RotatingFileHandler
import traceback
from typing import List, Dict, Tuple

# Import utilities
from utils import (
    load_config,
    retry_api_call,
    safe_api_call,
    init_global_rate_limiter,
    rate_limited
)

# Import redactor module
from redactor import SensitiveInformationRedactor

# Load configuration
config = load_config()

# Configure logging with rotation
logging_config = config.get_logging_config()
root_logger = logging.getLogger()

# Clear any existing handlers to avoid duplicates
if root_logger.hasHandlers():
    root_logger.handlers.clear()

root_logger.setLevel(getattr(logging, logging_config['level']))

# Create formatters
formatter = logging.Formatter(logging_config['format'])

# Console handler
if logging_config['console']:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, logging_config['level']))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

# File handler with rotation
if logging_config['file_logging']:
    file_handler = RotatingFileHandler(
        logging_config['file'],
        maxBytes=logging_config['max_bytes'],
        backupCount=logging_config['backup_count']
    )
    file_handler.setLevel(getattr(logging, logging_config['level']))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

# App logger for this module
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    load_dotenv()
    logger.info("Environment variables loaded successfully")
except Exception as e:
    logger.error(f"Failed to load environment variables: {str(e)}")
    raise

# Get API key from environment and .env (if present)
env_path = os.path.join(os.getcwd(), ".env")
env_values = dotenv_values(env_path) if os.path.exists(env_path) else {}
openai_api_key = os.getenv("OPENAI_API_KEY", "")
openai_env_key = env_values.get("OPENAI_API_KEY", "")
if not openai_api_key:
    logger.warning("OpenAI API key not found in environment variables. Some functionality may be limited.")

# Initialize rate limiting if enabled
if config.is_rate_limiting_enabled():
    init_global_rate_limiter(
        max_requests_per_minute=config.get_max_requests_per_minute(),
        max_tokens_per_minute=config.get_max_tokens_per_minute()
    )
    logger.info("Rate limiting initialized")

# Get category configuration from config
CATEGORY_OPTIONS = config.get_category_options()
CATEGORY_MAP = config.get_category_map()

logger.info(f"Loaded {len(CATEGORY_OPTIONS)} redaction categories from configuration")


def build_gradio_interface():
    """
    Build and configure the Gradio web interface for the application.

    Creates a multi-tab interface with:
    - Redaction Tool tab for detecting and redacting sensitive information
    - OpenAI Config tab for managing API keys
    - Help & About tab for documentation

    Returns:
        gr.Blocks: Configured Gradio interface ready to launch

    Raises:
        Exception: If UI creation fails (logged and re-raised)
    """
    # Create redactor instance with OpenAI API key
    redactor = SensitiveInformationRedactor(openai_api_key=openai_api_key)

    # Get UI configuration
    ui_config = config.get_input_text_config()
    output_config = config.get_output_text_config()

    logger.info("Building Gradio interface")

    # Build Gradio interface
    # Map config theme name to a concrete Gradio theme instance.
    theme_name = config.get_ui_theme().lower()
    theme = None
    if theme_name == "soft":
        theme = gr.themes.Soft()
    elif theme_name == "monochrome":
        theme = gr.themes.Monochrome()
    elif theme_name == "default":
        theme = gr.themes.Default()

    with gr.Blocks(
        title=config.get_ui_title(),
        theme=theme,
        css="""
        #action-row .gr-button, #openai-row .gr-button {
            max-width: 220px;
            width: 220px;
        }
        """
    ) as demo:
        # Main redaction tab
        with gr.Tab("Redaction Tool"):
            gr.Markdown(f"# {config.get_ui_title()}")
            gr.Markdown(f"*{config.get_ui_description()}*")
            openai_key_status = "Set" if openai_api_key else "Not set"
            gr.Markdown(
                f"**Ollama Model**: {config.get_ollama_model_name()} | "
                f"**OpenAI Model**: {config.get_openai_model_name()} ({openai_key_status}) | "
                f"**Log Level**: {config.get_logging_config()['level']}"
            )
            gr.Markdown(
                "**How to use:** 1) Enter text and select categories. "
                "2) Click **Redact Information**. 3) Review JSON + redacted text. "
                "4) If your OpenAI key is set, click **Submit to OpenAI** to process the redacted text."
            )

            # Input area
            with gr.Row():
                with gr.Column(scale=3):
                    input_text = gr.Textbox(
                        label="Input Text",
                        placeholder=ui_config.get('placeholder', 'Enter text to analyze...'),
                        lines=ui_config.get('lines', 10)
                    )
                    error_msg = gr.Markdown(value="", visible=False)
                with gr.Column(scale=1):
                    all_toggle = gr.Checkbox(
                        label="All categories",
                        value=config.get_category_selection_default_all()
                    )
                    gr.Markdown("---")
                    category_selection = gr.CheckboxGroup(
                        CATEGORY_OPTIONS,
                        label="Select Categories to Detect and Redact",
                        value=CATEGORY_OPTIONS if config.get_category_selection_default_all() else []
                    )
                    category_action = gr.State(value="")

            # Redaction button
            with gr.Row(elem_id="action-row"):
                with gr.Column(scale=0, min_width=220):
                    redact_button = gr.Button("Redact Information", variant="primary", elem_id="redact-btn")

            # Output area
            with gr.Row():
                with gr.Column():
                    with gr.Accordion("Detailed JSON Output", open=False):
                        redacted_output = gr.JSON(label="Detailed JSON Output")
                with gr.Column():
                    redacted_text_display = gr.Textbox(
                        label="Redacted Text",
                        placeholder="Redacted text will appear here...",
                        lines=output_config.get('lines', 10)
                    )

            # OpenAI submission area (hidden when no API key is configured)
            openai_enabled = bool(openai_api_key)
            with gr.Row(elem_id="openai-row"):
                with gr.Column(scale=0, min_width=220):
                    submit_button = gr.Button("Submit to OpenAI", visible=openai_enabled, elem_id="openai-btn")
            openai_response = gr.Textbox(
                label="OpenAI Response",
                placeholder="Response from OpenAI will appear here...",
                lines=output_config.get('lines', 10),
                visible=openai_enabled
            )
            status_msg = gr.Textbox(label="Status", visible=True)

            def apply_all_toggle(all_selected: bool, action: str):
                """Select or clear all categories based on the toggle."""
                if action == "sync":
                    return gr.update(), ""
                return (CATEGORY_OPTIONS if all_selected else []), ""

            def sync_all_toggle(selected: List[str], action: str):
                """Keep the All toggle in sync with manual selections."""
                if action == "sync":
                    return gr.update(), ""
                return (len(selected) == len(CATEGORY_OPTIONS)), "sync"

            all_toggle.change(
                fn=apply_all_toggle,
                inputs=[all_toggle, category_action],
                outputs=[category_selection, category_action]
            )

            category_selection.change(
                fn=sync_all_toggle,
                inputs=[category_selection, category_action],
                outputs=[all_toggle, category_action]
            )

            # Define functions for button click events
            def on_redact_click(text: str, categories: List[str]) -> Tuple[Dict, str, str]:
                """Handler for redact button clicks."""
                try:
                    if not text:
                        return {"error": "No text provided"}, "", gr.update(value="Please enter some text to redact.", visible=True), gr.update(value="**Error:** Please enter some text to redact.", visible=True)
                    text = text.strip()
                    if not text:
                        return {"error": "No text provided"}, "", gr.update(value="Please enter some text to redact.", visible=True), gr.update(value="**Error:** Please enter some text to redact.", visible=True)
                    if not categories:
                        return {"error": "No categories selected"}, "", gr.update(value="Please select at least one category.", visible=True), gr.update(value="**Error:** Please select at least one category.", visible=True)

                    soft_limit = ui_config.get('soft_limit', 2500)
                    hard_limit = ui_config.get('hard_limit', 5000)
                    if len(text) > hard_limit:
                        return {"error": "Input too long"}, "", gr.update(value="Please limit input to 5,000 characters.", visible=True), gr.update(value="**Error:** Please limit input to 5,000 characters.", visible=True)
                    if len(text) > soft_limit:
                        status_warning = f"Warning: input exceeds {soft_limit} characters; processing may be slower."
                    else:
                        status_warning = ""

                    result, redacted = redactor.identify_sensitive_information(
                        text, categories, category_map=CATEGORY_MAP
                    )
                    detected_count = len(result.get('detected_sensitive_data', []))
                    status = f"Processed text and found {detected_count} sensitive items."
                    if status_warning:
                        status = f"{status} {status_warning}"

                    return result, redacted, status, gr.update(value="", visible=False)

                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"Error in redaction process: {str(e)}\n{tb}")

                    if config.should_sanitize_error_messages():
                        return {"error": "An error occurred"}, "", "An error occurred during redaction.", gr.update(value="**Error:** An error occurred during redaction.", visible=True)
                    else:
                        return {"error": str(e)}, "", f"An error occurred: {str(e)}", gr.update(value=f"**Error:** {str(e)}", visible=True)

            def on_openai_submit(redacted_text: str) -> Tuple[str, str]:
                """Handler for OpenAI submit button clicks."""
                try:
                    if not redacted_text:
                        return "No text to process.", "Please redact some text first."

                    result = redactor.submit_to_openai(redacted_text)
                    return result, "Processed with OpenAI."

                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"Error in OpenAI submission: {str(e)}\n{tb}")

                    if config.should_sanitize_error_messages():
                        return "An error occurred.", "Error during OpenAI processing."
                    else:
                        return f"An error occurred: {str(e)}", f"Error: {str(e)}"

            # Connect button click events to handlers
            redact_button.click(
                fn=on_redact_click,
                inputs=[input_text, category_selection],
                outputs=[redacted_output, redacted_text_display, status_msg, error_msg]
            )

            submit_button.click(
                fn=on_openai_submit,
                inputs=[redacted_text_display],
                outputs=[openai_response, status_msg]
            )

        # OpenAI Configuration Tab
        with gr.Tab("OpenAI Config"):
            gr.Markdown("## OpenAI API Configuration")
            gr.Markdown("Configure your OpenAI API key for processing redacted text.")

            api_key_input = gr.Textbox(
                label="OpenAI API Key",
                placeholder="API key is not set" if not openai_api_key else "Enter your OpenAI API key here...",
                type="password",
                value=""
            )
            persist_key = gr.Checkbox(
                label="Save key to .env",
                value=bool(openai_env_key)
            )
            key_source = "Loaded from .env" if openai_env_key else "Not set"
            openai_status = gr.Markdown(f"**Key status**: {key_source}")
            update_button = gr.Button("Update API Key")
            update_status = gr.Textbox(
                label="Status",
                placeholder="Update status will appear here..."
            )

            def update_api_key(new_api_key: str, save_key: bool):
                """Handler for API key update button clicks."""
                try:
                    # Optionally write to .env file
                    if save_key:
                        try:
                            set_key(env_path, "OPENAI_API_KEY", new_api_key)
                            logger.info(".env file updated with OpenAI API key")
                        except Exception as e:
                            logger.error(f"Failed to write to .env file: {str(e)}")
                            return f"Failed to update .env file: {str(e)}", gr.update(), gr.update(), gr.update()

                    # Update environment variable
                    if new_api_key:
                        os.environ["OPENAI_API_KEY"] = new_api_key
                    else:
                        os.environ.pop("OPENAI_API_KEY", None)

                    # Update the redactor's OpenAI model
                    if new_api_key:
                        if not redactor.update_openai_api_key(new_api_key):
                            return "API Key saved but failed to update model. Check logs for details.", gr.update(), gr.update(), gr.update()
                        key_msg = "Saved to .env" if save_key else "Session only"
                        return f"API Key updated successfully. ({key_msg})", gr.update(visible=True), gr.update(visible=True), gr.update(value=f"**Key status**: {key_msg}")
                    else:
                        redactor.openai_model = None
                        key_msg = "Cleared"
                        return "API Key cleared successfully.", gr.update(visible=False), gr.update(visible=False), gr.update(value=f"**Key status**: {key_msg}")

                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"Error updating API key: {str(e)}\n{tb}")

                    if config.should_sanitize_error_messages():
                        return "An error occurred while updating the API key.", gr.update(), gr.update(), gr.update()
                    else:
                        return f"An error occurred: {str(e)}", gr.update(), gr.update(), gr.update()

            update_button.click(
                fn=update_api_key,
                inputs=[api_key_input, persist_key],
                outputs=[update_status, submit_button, openai_response, openai_status]
            )

        # Help & About tab
        with gr.Tab("Help & About"):
            gr.Markdown(f"""
            # {config.get_ui_title()}

            {config.get_ui_description()}

            ## Features

            - **{len(CATEGORY_OPTIONS)} Redaction Categories**: Email, phone, SSN, credit cards, addresses, and more
            - **Production-Ready**: Comprehensive error handling, retry logic, rate limiting
            - **Configuration Management**: Customize via config.yaml without code changes
            - **OpenAI Integration**: Optional processing of redacted text with OpenAI

            ## How to Use

            ### 1. Redaction Tool Tab

            - **Enter Text**: Paste or type the text you want to analyze in the input box
            - **Select Categories**: Choose which types of sensitive information to detect
            - **Click "Redact Information"**: Process the text to identify and redact sensitive data
            - **Review Output**:
              - **JSON Output**: Detailed information about detected sensitive data
              - **Redacted Text**: Your original text with sensitive information replaced by placeholders
            - **Submit to OpenAI** (optional): Process the redacted text with OpenAI

            ### 2. OpenAI Config Tab

            - Enter your OpenAI API key
            - Click "Update API Key" to save the key
            - The key is stored in your local .env file

            ## Redaction Categories

            {chr(10).join([f"- **{cat}**" for cat in CATEGORY_OPTIONS])}

            ## Troubleshooting

            - **JSON Parsing Errors**: The model may have returned invalid JSON. Try again or simplify your input.
            - **OpenAI Processing Fails**: Check your API key in the OpenAI Config tab
            - **Rate Limiting**: If you see delays, rate limiting is protecting your API quota
            - **Other Issues**: Check the application logs in `{logging_config['file']}`

            ## Configuration

            All settings can be customized in `config.yaml`:
            - Model names and parameters
            - Retry logic settings
            - Rate limiting thresholds
            - Logging configuration
            - UI customization
            - Feature flags

            ## Security & Privacy

            - All processing happens locally with your Ollama installation
            - OpenAI processing is optional and requires explicit API key configuration
            - Sensitive data logging is disabled by default
            - Error messages are sanitized to prevent information leakage
            - Rate limiting prevents API quota exhaustion

            ## Version & Info

            - **Ollama Model**: {config.get_ollama_model_name()}
            - **OpenAI Model**: {config.get_openai_model_name()}
            - **Prompt Version**: {config.get_prompt_version()}
            - **Rate Limiting**: {'Enabled' if config.is_rate_limiting_enabled() else 'Disabled'}
            - **Log File**: {logging_config['file']}
            - **Configuration**: config.yaml
            """)

    logger.info("Gradio interface built successfully")
    return demo


def main():
    """
    Main entry point for the application.

    Initializes the application, builds the Gradio interface, and launches the web server.
    Handles all startup errors gracefully with comprehensive logging.

    Raises:
        Exception: Critical errors that prevent application startup
    """
    try:
        logger.info("=" * 60)
        logger.info("Starting Ollama Guardrail Application")
        logger.info(f"Ollama Model: {config.get_ollama_model_name()}")
        logger.info(f"OpenAI Model: {config.get_openai_model_name()}")
        logger.info(f"Prompt Version: {config.get_prompt_version()}")
        logger.info(f"Rate Limiting: {'Enabled' if config.is_rate_limiting_enabled() else 'Disabled'}")
        logger.info(f"Logging Level: {config.get_logging_config()['level']}")
        logger.info(f"Categories: {len(CATEGORY_OPTIONS)}")
        logger.info("=" * 60)

        # Build and launch Gradio interface
        demo = build_gradio_interface()
        logger.info("Gradio interface built successfully")

        # Get server configuration
        server_config = config.get_server_config()

        # Launch the web app
        demo.launch(
            server_name=server_config.get('host', '127.0.0.1'),
            server_port=server_config.get('port', 7860),
            share=config.get_ui_share()
        )
        logger.info("Gradio app launched")

    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}", exc_info=True)
        print(f"\n{'='*60}")
        print(f"CRITICAL ERROR: {str(e)}")
        print(f"{'='*60}")
        print("Please check app.log for details")
        print("\nTroubleshooting:")
        print("1. Ensure Ollama is installed and running: ollama serve")
        print("2. Verify the model is available: ollama list")
        print(f"3. Pull the model if needed: ollama pull {config.get_ollama_model_name()}")
        print("4. Check config.yaml for correct settings")
        print("5. Verify all dependencies are installed: pip install -r requirements.txt")
        print(f"{'='*60}\n")
        traceback.print_exc()


if __name__ == "__main__":
    main()
