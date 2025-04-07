# Sensitive Information Redaction Tool

A privacy-focused application that automatically identifies and redacts sensitive information from text before processing it with AI models. This tool helps protect personally identifiable information (PII) and other sensitive data when working with AI systems.

## Features

- **Automated Detection & Redaction**: Identifies and redacts multiple categories of sensitive information
- **Customizable Categories**: Choose which types of sensitive information to detect and redact
- **OpenAI Integration**: Process redacted text with OpenAI's models
- **User-Friendly Interface**: Simple web interface built with Gradio
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

## Categories of Sensitive Information

The tool can detect and redact the following types of sensitive information:

- Email Addresses
- Phone Numbers
- Social Security Numbers
- Credit Card Numbers
- Dates of Birth
- Addresses
- Passwords
- Confidential Business Information
- Medical Information
- Other Sensitive Information

## Requirements

- Python 3.8+
- Ollama (running locally)
- OpenAI API key (optional, for the OpenAI processing feature)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/ollama_guardrail.git
   cd ollama_guardrail
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root directory and add your OpenAI API key (optional):
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

## Usage

1. Start the application:
   ```
   python app.py
   ```

2. Open the web interface in your browser (the URL will be displayed in the terminal)

3. Use the Redaction Tool:
   - Enter the text you want to analyze in the input box
   - Select the categories of sensitive information you want to detect
   - Click "Redact Information" to process the text
   - Review the redacted text and JSON output
   - Click "Submit to OpenAI" to process the redacted text with OpenAI

4. Configure OpenAI (optional):
   - Go to the "OpenAI Config" tab
   - Enter your OpenAI API key
   - Click "Update API Key" to save the key

## How It Works

1. **Text Input**: The user enters text that may contain sensitive information
2. **Category Selection**: The user selects which types of sensitive information to detect
3. **Detection & Redaction**: The Ollama LLM model identifies and redacts sensitive information
4. **Output**: The tool provides:
   - A JSON response with details about the detected information
   - The redacted text with placeholders for sensitive information
5. **OpenAI Processing** (optional): The redacted text can be processed by OpenAI

## Project Structure

- `app.py`: Main application file
- `prompt.py`: Prompt template for the Ollama LLM model
- `requirements.txt`: Required Python packages
- `.env`: Environment variables (OpenAI API key)

## Dependencies

- `gradio==5.23.3`: Web interface framework
- `python-dotenv==1.1.0`: Environment variable management
- `langchain-ollama==0.3.1`: Ollama LLM integration
- `langchain-openai==0.3.12`: OpenAI integration

## Troubleshooting

- **JSON Parsing Errors**: If you see JSON parsing errors, the model may have returned invalid JSON
- **OpenAI Processing Failures**: If OpenAI processing fails, check your API key in the OpenAI Config tab
- **Ollama Connection Issues**: Make sure Ollama is running locally
- **Logging**: Check the application logs in `app.log` for detailed error information

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Your License Here]

## Credits

- Built with [LangChain](https://www.langchain.com/)
- Interface created with [Gradio](https://www.gradio.app/)
- Uses [Ollama](https://ollama.ai/) for local LLM processing