"""
配置模型定义
"""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, SecretStr


class LLMProvider(str, Enum):
    OPENAI = "openai"
    AZURE = "azure"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class Language(str, Enum):
    ZH = "zh"
    EN = "en"


class LLMConfig(BaseModel):
    provider: LLMProvider = Field(default=LLMProvider.OPENAI, description="LLM 提供商")
    endpoint: str = Field(
        default="https://api.openai.com/v1",
        description="API endpoint URL"
    )
    api_key: SecretStr = Field(..., description="API Key")
    model: str = Field(default="gpt-4", description="模型名称")
    ca_cert: Optional[Path] = Field(default=None, description="CA 证书路径")
    timeout: int = Field(default=60, description="请求超时时间(秒)")
    max_retries: int = Field(default=3, description="最大重试次数")
    temperature: float = Field(default=0.7, description="生成温度")
    max_tokens: int = Field(default=4096, description="最大 token 数")

    class Config:
        use_enum_values = True


class WikiConfig(BaseModel):
    language: Language = Field(default=Language.ZH, description="文档语言")
    output_dir: Path = Field(default=Path(".python-wiki/repowiki"), description="输出目录")
    template_dir: Optional[Path] = Field(default=None, description="模板目录")
    max_files: int = Field(default=6000, description="最大文件数")
    exclude_patterns: list[str] = Field(
        default=["*.pyc", "__pycache__", ".git", "node_modules", "venv", ".venv"],
        description="排除模式"
    )
    include_private: bool = Field(default=False, description="是否包含私有成员")
    generate_diagrams: bool = Field(default=True, description="是否生成图表")
    diagram_types: list[str] = Field(
        default=["architecture", "flowchart", "sequence", "class", "state", "er", "component", "db_schema"],
        description="要生成的图表类型"
    )

    class Config:
        use_enum_values = True


class ProjectConfig(BaseModel):
    name: str = Field(..., description="项目名称")
    path: Path = Field(..., description="项目路径")
    description: Optional[str] = Field(default=None, description="项目描述")
    wiki: WikiConfig = Field(default_factory=WikiConfig)
    llm: LLMConfig = Field(..., description="LLM 配置")


class AppConfig(BaseModel):
    projects: list[ProjectConfig] = Field(default_factory=list, description="项目列表")
    default_llm: Optional[LLMConfig] = Field(default=None, description="默认 LLM 配置")
    last_project: Optional[str] = Field(default=None, description="上次打开的项目")
