"""Server-side usage limits and safe provider errors for the public demo."""
from collections import deque
from threading import Lock
from time import monotonic


class UsageLimit(ValueError):
    pass


class RateBudget:
    def __init__(self, clock=monotonic):
        self.clock = clock
        self.calls = deque()
        self.lock = Lock()

    def take(self):
        with self.lock:
            now = self.clock()
            while self.calls and now - self.calls[0] >= 60:
                self.calls.popleft()
            if len(self.calls) >= 5:
                raise UsageLimit("Please wait a minute. This demo allows five questions per minute.")
            self.calls.append(now)


def trim_history(history):
    return [{"role": item["role"], "content": item["content"][:1000]}
            for item in history[-6:] if item["role"] in {"user", "assistant"}]


def safe_error(exc):
    if isinstance(exc, UsageLimit):
        return str(exc)
    if getattr(exc, "status_code", None) == 429 or type(exc).__name__ == "RateLimitError":
        return "The shared AI quota is busy or exhausted. Please try again later."
    if isinstance(exc, TimeoutError) or "Timeout" in type(exc).__name__:
        return "The request took too long. Please try a shorter question."
    if getattr(exc, "status_code", None) in {401, 403}:
        return "The AI service is unavailable. Please try again later."
    return "The request could not be completed. Please try again later."
