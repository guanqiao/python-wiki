
"""
个人偏好记忆
"""
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class PersonalPreferences:
    """个人偏好配置"""
    code_style: str = "pep8"
    naming_convention: str = "snake_case"
    language: str = "zh"
    theme: str = "light"
    auto_save: bool = True
    custom_settings: dict[str, Any] = field(default_factory=dict)


class PersonalMemory:
    """个人偏好记忆管理器"""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._preferences: Optional[PersonalPreferences] = None
        self._load_preferences()

    def _get_preferences_path(self) -> Path:
        return self.storage_path / "personal_preferences.json"

    def _load_preferences(self) -> None:
        pref_path = self._get_preferences_path()
        if pref_path.exists():
            try:
                with open(pref_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._preferences = PersonalPreferences(**data)
            except Exception:
                self._preferences = PersonalPreferences()
        else:
            self._preferences = PersonalPreferences()

    def _save_preferences(self) -> None:
        if self._preferences:
            pref_path = self._get_preferences_path()
            with open(pref_path, "w", encoding="utf-8") as f:
                json.dump(asdict(self._preferences), f, ensure_ascii=False, indent=2)

    def get_preferences(self) -> PersonalPreferences:
        """获取个人偏好"""
        if self._preferences is None:
            self._load_preferences()
        return self._preferences

    def update_preferences(self, **kwargs: Any) -> None:
        """更新个人偏好"""
        if self._preferences is None:
            self._load_preferences()
        
        for key, value in kwargs.items():
            if hasattr(self._preferences, key):
                setattr(self._preferences, key, value)
        
        self._save_preferences()

    def set_custom_setting(self, key: str, value: Any) -> None:
        """设置自定义设置"""
        if self._preferences is None:
            self._load_preferences()
        
        self._preferences.custom_settings[key] = value
        self._save_preferences()

    def get_custom_setting(self, key: str, default: Any = None) -> Any:
        """获取自定义设置"""
        if self._preferences is None:
            self._load_preferences()
        
        return self._preferences.custom_settings.get(key, default)

    def reset_preferences(self) -> None:
        """重置为默认偏好"""
        self._preferences = PersonalPreferences()
        self._save_preferences()
