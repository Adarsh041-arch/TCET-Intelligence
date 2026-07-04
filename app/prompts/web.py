WEB_SEARCH_SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Answer the user's question accurately "
    "using the provided web search results as context. You are allowed to answer "
    "questions beyond TCET using this web context. Do not restrict yourself to TCET."
)

WEB_SEARCH_DECISION_PROMPT = (
    "Task: Decide if answering the user's query requires current real-time information, news, local weather, sports scores, or specific factual details that might be missing from your static knowledge.\n"
    "Examples:\n"
    '- "latest news about Apple" -> YES\n'
    '- "price of BTC today" -> YES\n'
    '- "who is the prime minister of India" -> YES\n'
    '- "how to write a binary search in python" -> NO\n'
    '- "what is the capital of France" -> NO\n'
    '- "tell me a story" -> NO\n\n'
    'User Query: "{query}"\n\n'
    "Require web search? (YES/NO):"
)
