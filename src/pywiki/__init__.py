"""
Python Wiki - AI-powered Wiki documentation generator
对标 Qoder Wiki 的 Python 实现
"""

__version__ = "0.1.0"
__author__ = "Python Wiki Team"

from pywiki.config.settings import Settings
from pywiki.config.models import LLMConfig, WikiConfig

__all__ = [
    "Settings",
    "LLMConfig", 
    "WikiConfig",
    "__version__",
]
