# Vernacular FD Advisor (UI + Terminal Edition)

Localhost-ready FD advisor with both terminal and web UI for regional language contexts.

## Features

- Python CLI for user interaction
- Streamlit web UI for proper browser-based experience
- MySQL-backed FD offers + dialect jargon dictionary
- Free-text reason based FD suggestion (no fixed goal restriction)
- Simple return estimate (principal, interest, maturity amount)
- Fine-tuned model integration hook (LLaMA/Mistral local path via `LOCAL_MODEL_PATH`)
- Safe fallback explanation when model is unavailable

## Tech Stack

- Python 3.10+
- MySQL 8+
- `mysql-connector-python`, `python-dotenv`
- Optional: HuggingFace `transformers` + `torch` for local model inference

## Setup

1. Create virtual environment and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment:

```bash
cp .env.example .env
```

Update `.env` values with your local MySQL credentials.

3. Create DB schema and seed data:

```bash
mysql -u root -p < schema.sql
mysql -u root -p vernacular_fd < seed.sql
```

4. Run app (Terminal):

```bash
python main.py
```

5. Run app (Web UI):

```bash
streamlit run web_app.py
```

Then open the localhost URL shown in terminal (usually `http://localhost:8501`).

## Integrating Fine-Tuned Model

If you have a fine-tuned LoRA merged model directory locally:

1. Put model directory path in `.env`:

```env
LOCAL_MODEL_PATH=/absolute/path/to/your/fine_tuned_model
```

2. Re-run app. It will use local generation pipeline from `app/llm.py`.

If not set, app uses deterministic fallback explanation text.

## Training Note (Unsloth)

- `train.py` Unsloth LoRA training script hai.
- Ye mostly **Linux + NVIDIA CUDA GPU** environment ke liye suitable hai.
- macOS par training run karne ki jagah Linux GPU machine use karke model train karo, then final model folder ko is project me laake `.env` me `LOCAL_MODEL_PATH` set karo.

## Speech-to-Speech Mode (Google STT + gTTS)

Speech-enabled terminal assistant run karne ke liye:

```bash
python speech_fd_app.py
```

Is mode me:
- app sawal bolega
- user voice se jawab dega
- unclear input par app repeat/confirm karega
- reason free text hai (Wedding/Education jaise fixed options compulsory nahi)
- user kisi language me bole, system input ko English structured info me normalize karke process karega
- final jawab preferred language me bolkar sunayega

## Ollama Extraction Pipeline

Speech pipeline now supports:
- multi-language speech intake
- Ollama JSON extraction (`amount_inr`, `tenor_months`, `reason`, `confirmation`)
- response translation back to preferred language

Set these env vars in `.env`:

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3
OLLAMA_API_KEY=
```
## Existing DB Migration (important)

Agar aapne purana schema pehle se banaya hua hai, to ye migration ek baar run karo:

```bash
mysql -u root -p vernacular_fd < migrate_user_history.sql
```


Dependencies:
- `SpeechRecognition`
- `gTTS`
- `pyaudio` (mic capture ke liye)

If `pyaudio` install issue on macOS:

```bash
brew install portaudio
python -m pip install pyaudio
```

## Suggested Next Upgrade (Speech)

You mentioned:
- Speech-to-Text: Google Speech Recognition
- Text-to-Speech: Google TTS / gTTS

This code supports terminal + web UI right now. You can further add:
- `speech_recognition` module for input mode
- `gTTS` + `playsound` for spoken response mode

## Project Structure

```text
.
├── app
│   ├── advisor.py
│   ├── config.py
│   ├── db.py
│   └── llm.py
├── main.py
├── web_app.py
├── schema.sql
├── seed.sql
├── .env.example
└── requirements.txt
```
