# Setup Guide

## Prerequisites
- Python 3.8+
- Ollama installed and running

## Install Dependencies
```bash
pip install -r requirements.txt
```

## Configure Environment
Copy a sample env file:
```bash
cp .env.example .env
```

You can also use a local-only file:
```bash
cp .env.local.example .env.local
```

Add your OpenAI key if you plan to use the OpenAI submit feature:
```
OPENAI_API_KEY=sk-your-key
```

## Ollama Model
Recommended model for reliable JSON output:
```bash
ollama pull llama3.1:8b
```

Update `config.yaml` if needed:
```yaml
models:
  ollama:
    name: "llama3.1:8b"
```

## Run the App
```bash
python app.py
```

Open: http://127.0.0.1:7860
