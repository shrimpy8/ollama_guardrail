# Import necessary libraries and modules
from dotenv import load_dotenv  # Load environment variables from .env file
import os  # Get environment variable values
from langchain_ollama.llms import OllamaLLM  # Ollama LLM model
from langchain_openai import ChatOpenAI  # OpenAI model
import gradio as gr  # Gradio interface for building web app
import json  # Parse JSON data
import prompt  # Prompt template library
import logging  # For logging errors and debug information
import traceback  # For detailed exception tracing
from typing import List, Dict, Tuple, Union, Optional  # Type hints

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    load_dotenv()
    logger.info("Environment variables loaded successfully")
except Exception as e:
    logger.error(f"Failed to load environment variables: {str(e)}")
    raise

# Set up OpenAI model with API key and model name
openai_api_key = os.getenv("OPENAI_API_KEY", "")  # Get OpenAI API key from environment variable
if not openai_api_key:
    logger.warning("OpenAI API key not found in environment variables. Some functionality may be limited.")

# Define category options and mappings
# Maps category names to their respective redaction placeholders
CATEGORY_OPTIONS = [
    "Email Addresses",
    "Phone Numbers",
    "Social Security Numbers",
    "Credit Card Numbers",
    "Dates of Birth",
    "Addresses",
    "Passwords",
    "Confidential Business Information",
    "Medical Information",
    "Other Sensitive Information"
]

CATEGORY_MAP = {
    "Email Addresses": "[EMAIL-1]",
    "Phone Numbers": "[PHONE-NUM-1]",
    "Social Security Numbers": "[SSN-1]",
    "Credit Card Numbers": "[CREDIT-CARD-NUM-1]",
    "Dates of Birth": "[DOB-1]",
    "Addresses": "[ADDRESS-1]",
    "Passwords": "[PASSWORD-1]",
    "Confidential Business Information": "[CBI-1]",
    "Medical Information": "[MEDICAL-1]",
    "Other Sensitive Information": "[OTHER]"
}

class SensitiveInformationRedactor:
    """
    A class to handle the redaction of sensitive information using LLM models.
    """
    
    def __init__(self, ollama_model_name: str = "llama3.2:latest", openai_model_name: str = "gpt-3.5-turbo"):
        """
        Initialize the redactor with specified LLM models.
        
        Args:
            ollama_model_name (str): Name of the Ollama model to use for detection and redaction.
            openai_model_name (str): Name of the OpenAI model to use for processing redacted text.
        """
        try:
            self.ollama_model = OllamaLLM(model=ollama_model_name)
            logger.info(f"Initialized Ollama model: {ollama_model_name}")
            
            # Initialize OpenAI model if API key is available
            if openai_api_key:
                self.openai_model = ChatOpenAI(model=openai_model_name, api_key=openai_api_key)
                logger.info(f"Initialized OpenAI model: {openai_model_name}")
            else:
                self.openai_model = None
                logger.warning("OpenAI model not initialized due to missing API key")
        except Exception as e:
            logger.error(f"Error initializing models: {str(e)}")
            raise
    
    def identify_sensitive_information(self, text: str, categories: List[str]) -> Tuple[Dict, str]:
        """
        Process input text to identify and redact sensitive information.
        
        Args:
            text (str): Input text to analyze for sensitive information.
            categories (list): List of category names to detect and redact.
            
        Returns:
            tuple: JSON output from Ollama model and extracted redacted text.
        """
        if not text:
            logger.warning("Empty text provided for sensitive information detection")
            return {"error": "No text provided"}, ""
            
        if not categories:
            logger.warning("No categories selected for redaction")
            return {"error": "No categories selected"}, text
        
        try:
            # Get formatting for selected categories
            selected_formats = [CATEGORY_MAP[cat] for cat in categories if cat in CATEGORY_MAP]
            categories_str = "\n".join(selected_formats)
            
            # Format the prompt template with user text and selected categories
            formatted_prompt = prompt.template.format(
                category_selected=categories_str, 
                user_prompt=text
            )
            
            # Call the Ollama model
            output = self.ollama_model.invoke(formatted_prompt)
            logger.debug(f"Raw Ollama output: {output}")
            
            try:
                # Parse JSON output from the model
                parsed_output = json.loads(output)
                redacted_text = parsed_output.get("redacted_text", "")
                logger.info(f"Successfully parsed model output, detected {len(parsed_output.get('detected_sensitive_data', []))} sensitive items")
                return parsed_output, redacted_text
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse model output as JSON: {str(e)}\nOutput: {output}")
                return {
                    "error": "Failed to parse output as JSON. The model may not have produced valid JSON format.",
                    "raw_output": output
                }, ""
                
        except Exception as e:
            logger.error(f"Error in sensitive information detection: {str(e)}")
            return {"error": f"An error occurred: {str(e)}"}, ""
    
    def submit_to_openai(self, redacted_text: str) -> str:
        """
        Submit redacted text to OpenAI for processing.
        
        Args:
            redacted_text (str): Redacted text to submit to OpenAI.
            
        Returns:
            str: Response from OpenAI model or error message.
        """
        if not redacted_text:
            logger.warning("Empty text provided for OpenAI processing")
            return "No text provided for processing."
            
        if not self.openai_model:
            logger.error("OpenAI model not available - missing API key")
            return "OpenAI processing is not available. Please add an API key in the OpenAI Config tab."
            
        try:
            # Prepare the instruction with redacted text
            instruction = "The following text has been redacted for sensitive information. Please process the text as it is provided as a PROMPT:\n"
            final_prompt = instruction + redacted_text
            
            # Call the OpenAI model
            response = self.openai_model.invoke(final_prompt)
            
            # Extract content from response
            if hasattr(response, 'content'):
                logger.info("Successfully received response from OpenAI")
                return response.content
            else:
                logger.warning("No content in OpenAI response")
                return "No response content available."
                
        except Exception as e:
            logger.error(f"Error in OpenAI processing: {str(e)}")
            return f"An error occurred while processing with OpenAI: {str(e)}"

def build_gradio_interface():
    """
    Build and configure the Gradio web interface for the application.
    
    Returns:
        gr.Blocks: Configured Gradio interface.
    """
    # Create redactor instance
    redactor = SensitiveInformationRedactor()
    
    # Build Gradio interface
    with gr.Blocks(title="Sensitive Information Redaction Tool") as demo:
        with gr.Tab("Redaction Tool"):
            # Input area
            with gr.Row():
                with gr.Column(scale=3):
                    input_text = gr.Textbox(
                        label="Input Text", 
                        placeholder="Enter text to analyze for sensitive information...",
                        lines=10
                    )
                with gr.Column(scale=1):
                    category_selection = gr.CheckboxGroup(
                        CATEGORY_OPTIONS, 
                        label="Select Categories to Detect and Redact"
                    )
                    
            # Redaction button
            redact_button = gr.Button("Redact Information", variant="primary")
            
            # Output area
            with gr.Row():
                with gr.Column():
                    redacted_output = gr.JSON(label="Detailed JSON Output")
                with gr.Column():
                    redacted_text_display = gr.Textbox(
                        label="Redacted Text", 
                        placeholder="Redacted text will appear here...",
                        lines=10
                    )
            
            # OpenAI submission area
            submit_button = gr.Button("Submit to OpenAI")
            openai_response = gr.Textbox(
                label="OpenAI Response", 
                placeholder="Response from OpenAI will appear here...",
                lines=10
            )
            status_msg = gr.Textbox(label="Status", visible=True)

            # Define functions for button click events
            def on_redact_click(text, categories):
                """Handler for redact button clicks"""
                try:
                    if not text:
                        return {"error": "No text provided"}, "", "Please enter some text to redact."
                    if not categories:
                        return {"error": "No categories selected"}, text, "Please select at least one category."
                        
                    result, redacted = redactor.identify_sensitive_information(text, categories)
                    status = f"Processed text and found {len(result.get('detected_sensitive_data', []))} sensitive items."
                    return result, redacted, status
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"Error in redaction process: {str(e)}\n{tb}")
                    return {"error": str(e)}, "", f"An error occurred: {str(e)}"

            def on_openai_submit(redacted_text):
                """Handler for OpenAI submit button clicks"""
                try:
                    if not redacted_text:
                        return "No text to process.", "Please redact some text first."
                        
                    result = redactor.submit_to_openai(redacted_text)
                    return result, "Processed with OpenAI."
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"Error in OpenAI submission: {str(e)}\n{tb}")
                    return f"An error occurred: {str(e)}", f"Error: {str(e)}"

            # Connect button click events to handlers
            redact_button.click(
                fn=on_redact_click, 
                inputs=[input_text, category_selection], 
                outputs=[redacted_output, redacted_text_display, status_msg]
            )
            
            submit_button.click(
                fn=on_openai_submit, 
                inputs=[redacted_text_display], 
                outputs=[openai_response, status_msg]
            )

        # OpenAI Configuration Tab
        with gr.Tab("OpenAI Config"):
            api_key_input = gr.Textbox(
                label="OpenAI API Key", 
                placeholder="Enter your OpenAI API key here...", 
                type="password", 
                value=openai_api_key
            )
            update_button = gr.Button("Update API Key")
            update_status = gr.Textbox(label="Status", placeholder="Update status will appear here...")

            def update_api_key(new_api_key):
                """Handler for API key update button clicks"""
                try:
                    # Validate key is not empty
                    if not new_api_key:
                        return "API Key cannot be empty."
                        
                    # Write to .env file
                    try:
                        with open(".env", "w") as f:
                            f.write(f"OPENAI_API_KEY={new_api_key}\n")
                    except Exception as e:
                        logger.error(f"Failed to write to .env file: {str(e)}")
                        return f"Failed to update .env file: {str(e)}"
                        
                    # Update environment variable
                    os.environ["OPENAI_API_KEY"] = new_api_key
                    
                    # Update the redactor's OpenAI model
                    try:
                        redactor.openai_model = ChatOpenAI(model="gpt-3.5-turbo", api_key=new_api_key)
                        logger.info("OpenAI model updated with new API key")
                    except Exception as e:
                        logger.error(f"Failed to update OpenAI model: {str(e)}")
                        return f"API Key saved but failed to update model: {str(e)}"
                        
                    return "API Key updated successfully."
                except Exception as e:
                    tb = traceback.format_exc()
                    logger.error(f"Error updating API key: {str(e)}\n{tb}")
                    return f"An error occurred: {str(e)}"

            update_button.click(fn=update_api_key, inputs=api_key_input, outputs=update_status)
            
        # Add instructions and about tab
        with gr.Tab("Help & About"):
            gr.Markdown("""
            # Sensitive Information Redaction Tool
            
            This tool helps you identify and redact sensitive information from text before processing it with AI models.
            
            ## How to use:
            
            1. In the **Redaction Tool** tab:
               - Enter the text you want to analyze in the input box
               - Select the categories of sensitive information you want to detect
               - Click "Redact Information" to process the text
               - Review the redacted text and JSON output
               - Click "Submit to OpenAI" to process the redacted text
               
            2. In the **OpenAI Config** tab:
               - Enter your OpenAI API key
               - Click "Update API Key" to save the key
               
            ## Troubleshooting:
            
            - If you see JSON parsing errors, the model may have returned invalid JSON
            - If OpenAI processing fails, check your API key in the OpenAI Config tab
            - For other issues, check the application logs
            """)

    return demo

def main():
    """
    Main entry point for the application.
    """
    try:
        # Build and launch Gradio interface
        demo = build_gradio_interface()
        logger.info("Gradio interface built successfully")
        
        # Launch the web app
        demo.launch(share=True)
        logger.info("Gradio app launched")
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        print(f"CRITICAL ERROR: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main()