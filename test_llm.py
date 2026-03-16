import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

OPENROUTER_API_KEY = "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"

llm = ChatOpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    model="nvidia/nemotron-3-nano-30b-a3b:free", # This automatically grabs whatever free model is currently active!
    max_tokens=2048,
    temperature=0.3
)

print("Sending request to OpenRouter...")
messages = [
    HumanMessage(content="Write a Python script to perform lemmatization and tokenization on a sentence.")
]

response = llm.invoke(messages)

print("\n--- RESPONSE ---")
print(response.content)