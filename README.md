# TicketFlow AI
College demo helpdesk: ML ticket classification, priority rules, duplicate detection, knowledge-base search, optional Generative AI chat and ticket solution suggestions.

## Run (Windows VS Code)
1. Extract ZIP, open folder in VS Code Terminal.
2. `python -m venv .venv`
3. `.venv\\Scripts\\activate`
4. `pip install -r requirements.txt`
5. `python app.py`
6. Visit http://127.0.0.1:5000

## Enable real Generative AI
Set an API key for an OpenAI-compatible Chat Completions service in your terminal before running the app:
```powershell
$env:OPENAI_API_KEY="your-key"
$env:OPENAI_MODEL="gpt-4o-mini"
python app.py
```
Optionally set `OPENAI_BASE_URL` for a compatible provider. Keep the key private; API usage may cost money. If no key is present, assistant uses local KB search and clearly operates in fallback mode (not generative AI).

## Demo
Dashboard → Load demo tickets. Then try `/assistant` or submit a ticket. Tests: `python tests.py`.

## Modules
`app.py` Flask routes + SQLite · `ml_engine.py` TF-IDF/Logistic Regression, KB retrieval, duplicate similarity · `ai_assistant.py` optional API + fallback · templates/static interface.

Prototype caveats: small training examples, rule-based priority, no authentication, AI is advisory only, and it does not perform remote device actions. Use test data only.
