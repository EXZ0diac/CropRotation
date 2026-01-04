# Flowchart for `main.py`

This file shows the high level flow of `main.py` (Telegram bot + model loading + optional Flask webhook). Render the diagram block using a Mermaid previewer (VS Code Mermaid plugin) or an online Mermaid renderer.

```mermaid
flowchart TD
  Start([Start])
  Start --> LoadEnv["Load .env and env vars"]
  LoadEnv --> LoadArtifacts["Load scaler, encoder, model (Keras/TFLite) via _load_artifacts()"]
  LoadArtifacts --> InitFlask["Init Flask app (webhook endpoint)"]
  LoadArtifacts --> InitBot["Init Telegram Application and handlers"]
  InitBot --> RegisterHandlers["Register command handlers (/start, /canPlant, /setSoilValue, /status, etc.)"]
  RegisterHandlers --> PrepareState["Load user data (user_soil, user_plants) from JSON files"]
  PrepareState --> DecideMode{USE_WEBHOOK?}
  DecideMode -->|yes| SetupWebhook["Set webhook URL (ngrok or provided), start Flask server to receive updates"]
  DecideMode -->|no| DeleteWebhook["Attempt deleteWebhook() to avoid conflicts"]
  DeleteWebhook --> StartPolling["Start long-polling bot.run_polling()"]
  SetupWebhook --> StartFlask["Start Flask app / webhook listener"]
  StartPolling --> Run["Bot running (polling)"]
  StartFlask --> Run["Bot running (webhook)"]
  Run --> Idle([Idle — handlers respond to messages])
  Idle --> Stop([Stop/Shutdown])
```

Notes:
- Handlers call helper functions: `predict_crop()`, `suitability_check()`, and file I/O helpers `load_user_*` and `save_user_*`.
- The file also contains CLI/control logic to choose webhook vs polling and to try fallback dashboard endpoints when handling `/status`.
