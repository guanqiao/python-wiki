"""
应用设置管理
"""

import json
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from pywiki.config.models import AppConfig, LLMConfig, ProjectConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PYWIKI_",
        env_nested_delimiter="__",
        case_sensitive=False
    )

    config_dir: Path = Path.home() / ".pywiki"
    config_file: Path = Path("config.json")
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._app_config: Optional[AppConfig] = None
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)

    @property
    def config_path(self) -> Path:
        return self.config_dir / self.config_file

    def load_config(self) -> AppConfig:
        if self._app_config is not None:
            return self._app_config

        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._app_config = AppConfig(**data)
        else:
            self._app_config = AppConfig()

        return self._app_config

    def save_config(self) -> None:
        if self._app_config is None:
            return

        json_str = self._app_config.model_dump_json(indent=2)
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(json_str)

    def get_project(self, name: str) -> Optional[ProjectConfig]:
        config = self.load_config()
        for project in config.projects:
            if project.name == name:
                return project
        return None

    def add_project(self, project: ProjectConfig) -> None:
        config = self.load_config()
        existing = self.get_project(project.name)
        if existing:
            config.projects.remove(existing)
        config.projects.append(project)
        self.save_config()

    def remove_project(self, name: str) -> bool:
        config = self.load_config()
        project = self.get_project(name)
        if project:
            config.projects.remove(project)
            self.save_config()
            return True
        return False

    def update_default_llm(self, llm_config: LLMConfig) -> None:
        config = self.load_config()
        config.default_llm = llm_config
        self.save_config()

    def set_last_project(self, name: str) -> None:
        config = self.load_config()
        config.last_project = name
        self.save_config()


settings = Settings()
