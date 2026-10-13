AVAILABLE_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-5.2"],
        "default_model": "gpt-5.4-nano",
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
