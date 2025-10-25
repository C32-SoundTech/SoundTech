import os

import warnings
warnings.filterwarnings("ignore", module="jieba")
warnings.filterwarnings("ignore", module="pydantic")

import jieba
jieba.setLogLevel(jieba.logging.INFO)

# Disable ChromaDB/PostHog telemetry early to avoid posthog.capture signature mismatch
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Hard-disable PostHog capture to avoid signature mismatch regardless of library version
try:
    import posthog  # noqa: F401
    posthog.disabled = True
    def _posthog_noop_capture(*args, **kwargs):
        return None
    posthog.capture = _posthog_noop_capture
    # Guard client instance method in case code calls Client.capture directly
    try:
        import posthog.client as posthog_client  # type: ignore
        def _client_noop_capture(self, event, **kwargs):
            return None
        posthog_client.Client.capture = _client_noop_capture
    except Exception:
        pass
except Exception:
    pass