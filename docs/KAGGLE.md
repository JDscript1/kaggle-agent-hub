# Kaggle quick start

Create a new Kaggle notebook, enable Internet if you need external APIs or the Gradio share tunnel, then use only two cells.

## Cell 1

```python
!git clone https://github.com/JDscript1/kaggle-agent-hub.git
```

## Cell 2

```python
%run /kaggle/working/kaggle-agent-hub/bootstrap.py
```

The bootstrap installs Python dependencies and starts the UI.

## Secrets

In Kaggle, add secrets with the exact names shown in the Providers panel, for example:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`
- `MOONSHOT_API_KEY`
- `OPENROUTER_API_KEY`

Do not put secret values in notebook cells that will be published.
