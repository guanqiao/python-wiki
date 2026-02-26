"""
Python Wiki 统一异常类
提供清晰的异常层次结构
"""

from typing import Any, Optional


class PyWikiError(Exception):
    """Python Wiki 基础异常"""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


class ConfigurationError(PyWikiError):
    """配置错误"""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.config_key = config_key

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.config_key:
            result["config_key"] = self.config_key
        return result


class ProjectError(PyWikiError):
    """项目相关错误"""

    def __init__(
        self,
        message: str,
        project_name: Optional[str] = None,
        project_path: Optional[str] = None,
    ):
        super().__init__(message)
        self.project_name = project_name
        self.project_path = project_path

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.project_name:
            result["project_name"] = self.project_name
        if self.project_path:
            result["project_path"] = self.project_path
        return result


class ProjectNotFoundError(ProjectError):
    """项目不存在"""

    def __init__(self, project_name: str):
        super().__init__(
            f"项目 '{project_name}' 不存在",
            project_name=project_name,
        )


class ProjectAlreadyExistsError(ProjectError):
    """项目已存在"""

    def __init__(self, project_name: str):
        super().__init__(
            f"项目 '{project_name}' 已存在",
            project_name=project_name,
        )


class ParseError(PyWikiError):
    """代码解析错误"""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        language: Optional[str] = None,
    ):
        super().__init__(message)
        self.file_path = file_path
        self.line_number = line_number
        self.language = language

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.file_path:
            result["file_path"] = self.file_path
        if self.line_number:
            result["line_number"] = self.line_number
        if self.language:
            result["language"] = self.language
        return result


class UnsupportedLanguageError(ParseError):
    """不支持的语言"""

    def __init__(self, language: str, file_path: Optional[str] = None):
        super().__init__(
            f"不支持的语言: {language}",
            file_path=file_path,
            language=language,
        )


class LLMError(PyWikiError):
    """LLM 相关错误"""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.status_code = status_code

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.provider:
            result["provider"] = self.provider
        if self.model:
            result["model"] = self.model
        if self.status_code:
            result["status_code"] = self.status_code
        return result


class LLMConnectionError(LLMError):
    """LLM 连接错误"""

    def __init__(
        self,
        message: str = "无法连接到 LLM 服务",
        provider: Optional[str] = None,
    ):
        super().__init__(message, provider=provider)


class LLMRateLimitError(LLMError):
    """LLM 速率限制"""

    def __init__(
        self,
        message: str = "已达到 API 速率限制",
        provider: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message, provider=provider)
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.retry_after:
            result["retry_after"] = self.retry_after
        return result


class LLMAuthenticationError(LLMError):
    """LLM 认证错误"""

    def __init__(
        self,
        message: str = "API 认证失败",
        provider: Optional[str] = None,
    ):
        super().__init__(message, provider=provider)


class SearchError(PyWikiError):
    """搜索相关错误"""

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
    ):
        super().__init__(message)
        self.query = query

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.query:
            result["query"] = self.query
        return result


class IndexNotFoundError(SearchError):
    """索引不存在"""

    def __init__(self, project_name: str):
        super().__init__(f"项目 '{project_name}' 的搜索索引不存在")
        self.project_name = project_name


class WikiGenerationError(PyWikiError):
    """Wiki 生成错误"""

    def __init__(
        self,
        message: str,
        phase: Optional[str] = None,
        file_count: Optional[int] = None,
    ):
        super().__init__(message)
        self.phase = phase
        self.file_count = file_count

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.phase:
            result["phase"] = self.phase
        if self.file_count is not None:
            result["file_count"] = self.file_count
        return result


class ExportError(PyWikiError):
    """导出错误"""

    def __init__(
        self,
        message: str,
        format: Optional[str] = None,
        output_path: Optional[str] = None,
    ):
        super().__init__(message)
        self.format = format
        self.output_path = output_path

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.format:
            result["format"] = self.format
        if self.output_path:
            result["output_path"] = self.output_path
        return result


class GitError(PyWikiError):
    """Git 相关错误"""

    def __init__(
        self,
        message: str,
        git_command: Optional[str] = None,
    ):
        super().__init__(message)
        self.git_command = git_command

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.git_command:
            result["git_command"] = self.git_command
        return result


class NotAGitRepositoryError(GitError):
    """不是 Git 仓库"""

    def __init__(self, path: str):
        super().__init__(f"'{path}' 不是 Git 仓库")


class MemoryError(PyWikiError):
    """记忆系统错误"""

    def __init__(
        self,
        message: str,
        memory_type: Optional[str] = None,
    ):
        super().__init__(message)
        self.memory_type = memory_type


class VectorStoreError(PyWikiError):
    """向量存储错误"""

    def __init__(
        self,
        message: str,
        index_path: Optional[str] = None,
    ):
        super().__init__(message)
        self.index_path = index_path

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.index_path:
            result["index_path"] = self.index_path
        return result


class ValidationError(PyWikiError):
    """数据验证错误"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ):
        super().__init__(message)
        self.field = field
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.field:
            result["field"] = self.field
        if self.value is not None:
            result["value"] = str(self.value)
        return result
