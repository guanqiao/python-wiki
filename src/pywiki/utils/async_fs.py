"""
异步文件系统操作
"""

import aiofiles
from pathlib import Path
from typing import Optional, Union
import asyncio


class AsyncFileSystem:
    """异步文件系统操作"""

    @staticmethod
    async def read_file(file_path: Path, encoding: str = "utf-8") -> str:
        """异步读取文件"""
        async with aiofiles.open(file_path, "r", encoding=encoding) as f:
            return await f.read()

    @staticmethod
    async def write_file(
        file_path: Path,
        content: str,
        encoding: str = "utf-8"
    ) -> None:
        """异步写入文件"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(file_path, "w", encoding=encoding) as f:
            await f.write(content)

    @staticmethod
    async def read_bytes(file_path: Path) -> bytes:
        """异步读取二进制文件"""
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()

    @staticmethod
    async def write_bytes(file_path: Path, content: bytes) -> None:
        """异步写入二进制文件"""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

    @staticmethod
    async def exists(file_path: Path) -> bool:
        """检查文件是否存在"""
        return file_path.exists()

    @staticmethod
    async def delete(file_path: Path) -> bool:
        """删除文件"""
        try:
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                import shutil
                shutil.rmtree(file_path)
            return True
        except Exception:
            return False

    @staticmethod
    async def list_files(
        directory: Path,
        pattern: str = "*",
        recursive: bool = False
    ) -> list[Path]:
        """列出文件"""
        if recursive:
            return list(directory.rglob(pattern))
        return list(directory.glob(pattern))

    @staticmethod
    async def copy_file(source: Path, destination: Path) -> None:
        """复制文件"""
        import shutil
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    @staticmethod
    async def move_file(source: Path, destination: Path) -> None:
        """移动文件"""
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)

    @staticmethod
    async def ensure_dir(directory: Path) -> None:
        """确保目录存在"""
        directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    async def get_file_size(file_path: Path) -> int:
        """获取文件大小"""
        return file_path.stat().st_size

    @staticmethod
    async def get_file_mtime(file_path: Path) -> float:
        """获取文件修改时间"""
        return file_path.stat().st_mtime
