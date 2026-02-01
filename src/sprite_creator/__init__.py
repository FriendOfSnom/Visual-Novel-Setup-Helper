"""
Gemini Sprite Creator (Tool 2)

AI-powered character sprite generator using Google Gemini vision models.
"""

# Lazy import to avoid pulling in heavy dependencies (rembg, etc.)
# when only using submodules like tester
def __getattr__(name):
    if name == "run_pipeline":
        from .pipeline import run_pipeline
        return run_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["run_pipeline"]
