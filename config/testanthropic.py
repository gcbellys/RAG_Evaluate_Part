import os, anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")

# 强制走官方 API，而不是 kimi / moonshot
client = anthropic.Anthropic(
    api_key=api_key,
    base_url="https://api.anthropic.com"
)

resp = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=10,
    messages=[{"role": "user", "content": "ping"}],
)

print(resp)
