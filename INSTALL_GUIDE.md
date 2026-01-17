# Installation Guide for Streamlit UI

## Quick Setup

### 1. Install Core Dependencies

```bash
pip install streamlit python-dotenv streamlit-mermaid
```

### 2. Or Update pyproject.toml

Add to your dependencies:

```toml
dependencies = [
    "crewai[tools]==1.8.1",
    "langchain-google-genai>=2.0.0",
    "streamlit>=1.28.0",
    "python-dotenv>=1.0.0",
    "streamlit-mermaid>=0.1.0"
]
```

Then run:
```bash
pip install -e .
```

### 3. Set Up Environment Variables

Create a `.env` file:

```bash
GOOGLE_API_KEY=your_google_api_key_here
SERPER_API_KEY=your_serper_api_key_here
MODEL=gemini-2.0-flash-exp
```

### 4. Run the App

```bash
streamlit run src/configurable_agents/app.py
```

## What You'll See

The app will open at `http://localhost:8501` with:

### Tab 1: 📊 Overview
- Flow summary metrics (steps, crews, agents, tasks)
- Flow description and details
- Current configuration

### Tab 2: 🎨 Flow Diagram ⭐ NEW!
- **Rendered visual flowchart** showing execution flow
- Crew detail diagrams (expand to see)
- Agent and task relationships

### Tab 3: 🚀 Execute
- Configure topic and LLM settings
- Run flow button
- Progress indicators

### Tab 4: 📊 Results
- Generated article
- Humanness score with gauge
- Download button
- Validation feedback

## Troubleshooting

### Diagrams showing as code instead of visuals?

Make sure `streamlit-mermaid` is installed:

```bash
pip install streamlit-mermaid
```

Then restart the Streamlit app.

### Import errors?

Make sure you're in the project directory and have installed in editable mode:

```bash
cd C:\Users\ghost\OneDrive\Desktop\Test\configurable-agents
pip install -e .
```

### API errors?

Check your `.env` file has valid:
- `GOOGLE_API_KEY` - Get from Google AI Studio
- `SERPER_API_KEY` - Get from serper.dev

## Features

✅ Visual flow diagrams with Mermaid
✅ Real-time flow configuration
✅ Multiple LLM model support
✅ Temperature and token control
✅ Article download
✅ Crew detail visualization

## Next Steps

- Customize agent goals and backstories (coming soon)
- Add/remove steps and crews (coming soon)
- Save/load custom configurations (coming soon)
