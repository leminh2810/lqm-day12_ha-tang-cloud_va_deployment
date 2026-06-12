"""Mock LLM used by the final lab project.

This keeps the project runnable without a real OpenAI or Anthropic API key.
"""
import random
import time


MOCK_RESPONSES = {
    "default": [
        "This is a mock AI agent response. In production this would call a real LLM.",
        "The agent is running correctly. Ask another question to continue.",
        "Your question was received and processed by the deployed agent.",
    ],
    "docker": [
        "Docker packages an application with its runtime and dependencies so it can run consistently anywhere."
    ],
    "deploy": [
        "Deployment is the process of moving code from a local machine to a server or cloud platform."
    ],
    "health": [
        "The agent is healthy and ready to serve requests."
    ],
}


def ask(question: str, delay: float = 0.1) -> str:
    time.sleep(delay + random.uniform(0, 0.05))
    question_lower = question.lower()
    for keyword, responses in MOCK_RESPONSES.items():
        if keyword in question_lower:
            return random.choice(responses)
    return random.choice(MOCK_RESPONSES["default"])


def ask_stream(question: str):
    response = ask(question)
    for word in response.split():
        time.sleep(0.05)
        yield word + " "
