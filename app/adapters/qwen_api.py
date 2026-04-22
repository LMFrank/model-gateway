from app.adapters.openai_compatible import OpenAICompatibleAdapter

# Backward-compatible alias. New code should import OpenAICompatibleAdapter.
QwenApiAdapter = OpenAICompatibleAdapter

__all__ = ["QwenApiAdapter"]
