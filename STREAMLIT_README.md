# Streamlit UI for Configurable Agents

Simple web interface to configure and run your agent workflows.

## Quick Start

### 1. Install Dependencies

First, add streamlit to your dependencies:

```bash
pip install streamlit python-dotenv
```

Or update your `pyproject.toml`:
```toml
dependencies = [
    "crewai[tools]==1.8.1",
    "langchain-google-genai>=2.0.0",
    "streamlit>=1.28.0",
    "python-dotenv>=1.0.0"
]
```

### 2. Set Up Environment Variables

Make sure your `.env` file contains:
```
GOOGLE_API_KEY=your_google_api_key_here
SERPER_API_KEY=your_serper_api_key_here
MODEL=gemini-2.0-flash-exp
```

### 3. Run the App

From your project root directory:

```bash
streamlit run src/configurable_agents/app.py
```

The app will open in your browser at `http://localhost:8501`

## Features

### 🎯 Simple Configuration
- **Topic Input**: Enter any topic you want to research and write about
- **LLM Temperature**: Adjust creativity vs focus (0.0 = focused, 1.0 = creative)
- **Model Selection**: Choose from available Google Gemini models
- **Advanced Settings**: Fine-tune crew-specific temperatures and token limits

### 🚀 One-Click Execution
- Pre-loaded with the article generation flow
- Progress indicators during execution
- Clear success/error messaging

### 📊 Rich Results Display
- **Humanness Score**: Visual gauge showing AI writing detection score
- **Generated Article**: Full article with download option
- **Validation Feedback**: Detailed analysis of writing quality
- **YAML Config Viewer**: Inspect the full configuration being used

## UI Layout

```
┌─────────────────────────────────────────┐
│  Sidebar: Configuration                 │
├─────────────────────────────────────────┤
│  • Topic Input                          │
│  • LLM Temperature Slider               │
│  • Model Selection                      │
│  • Advanced Settings (collapsible)      │
│  • View YAML Config Button              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│  Main Area: Execution & Results         │
├─────────────────────────────────────────┤
│  • Current config summary               │
│  • Run Flow button                      │
│  • Progress indicators                  │
│  • Results:                             │
│    - Humanness Score (with gauge)       │
│    - Generated Article                  │
│    - Download button                    │
│    - Validation Feedback                │
└─────────────────────────────────────────┘
```

## How It Works

1. **Load Config**: The app loads `article_generation_flow.yaml` as the default configuration
2. **User Input**: You configure the topic and LLM parameters via the UI
3. **Config Merge**: Your inputs are merged into the base configuration
4. **Flow Execution**: The `run_flow()` function kicks off the agent workflow
5. **Results Display**: Structured output (ArticleValidationOutput) is displayed with nice formatting

## Customization

### Using Different Flow Configs

To use a different flow configuration, modify the `load_default_config()` function in `app.py`:

```python
@st.cache_data
def load_default_config():
    config_path = Path(__file__).parent / "your_custom_flow.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
```

### Adding More Input Fields

To expose more configuration options, add them to the sidebar:

```python
# Example: Add a max word count input
max_words = st.sidebar.number_input(
    "Max Article Words",
    min_value=100,
    max_value=2000,
    value=600,
    help="Maximum words for the article"
)
```

## Tips

- **First Run**: The first execution might take 2-5 minutes as agents research and write
- **Temperature Settings**: 
  - Research crew: 0.3-0.5 for factual accuracy
  - Writer crew: 0.7-0.9 for creative writing
- **Model Selection**: 
  - `gemini-2.0-flash-exp`: Fastest, good balance
  - `gemini-1.5-pro`: Most capable, slower
- **Download**: Click the download button to save articles as `.txt` files

## Troubleshooting

### App won't start
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify your `.env` file contains valid API keys

### Flow execution fails
- Check console output for detailed error messages
- Verify your GOOGLE_API_KEY is valid
- Ensure SERPER_API_KEY is set if using web search

### Results not displaying
- Check that your flow config outputs to `state.custom_var.final_output`
- Verify the output task has an `output_model` defined

## Next Steps

Want to extend this UI? Consider adding:
- [ ] Config file upload/download
- [ ] Real-time execution logs viewer
- [ ] Multiple flow configs selector
- [ ] Save/load favorite configurations
- [ ] Export results to PDF/Markdown
- [ ] Execution history viewer

---

Built with ❤️ using CrewAI Flows & Streamlit
