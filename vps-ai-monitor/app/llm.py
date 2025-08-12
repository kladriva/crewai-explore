import os
from crewai import LLM

def build_llm():
    if os.getenv("OPENAI_API_KEY"):
        return LLM(model="gpt-4o-mini") 
    
    #base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    #return LLM(model="ollama/llama3", base_url=base)
