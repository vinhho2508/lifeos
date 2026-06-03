AVAILABLE_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"],
        "default_model": "gpt-4o-mini",
    },
    "gemini": {
        "name": "Google Gemini",
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        "default_model": "gemini-2.5-flash",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "models": [
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-haiku-20240307",
        ],
        "default_model": "claude-sonnet-4-20250514",
    },
}
