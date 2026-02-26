"""
Python 解析器高级功能测试
测试 FastAPI、Pydantic、SQLAlchemy 支持
"""

from pathlib import Path

import pytest

from pywiki.parsers.python import PythonParser


class TestPythonFastAPI:
    """FastAPI 支持测试"""

    @pytest.fixture
    def parser(self):
        return PythonParser()

    def test_fastapi_route_detection(self, parser, tmp_path):
        """测试 FastAPI 路由检测"""
        code = '''
from fastapi import FastAPI

app = FastAPI()

@app.get("/items")
async def get_items():
    return {"items": []}

@app.post("/items")
async def create_item(item: dict):
    return item

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id}

@app.put("/items/{item_id}")
async def update_item(item_id: int, item: dict):
    return item

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    return {"deleted": item_id}
'''
        file_path = tmp_path / "api.py"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]

        # 检查是否识别了所有路由
        route_funcs = [f for f in module.functions if "FastAPI" in (f.docstring or "")]
        assert len(route_funcs) >= 5

    def test_fastapi_router_detection(self, parser, tmp_path):
        """测试 FastAPI Router 检测"""
        code = '''
from fastapi import APIRouter

router = APIRouter(prefix="/users")

@router.get("/")
async def list_users():
    return []

@router.get("/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}
'''
        file_path = tmp_path / "users.py"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        route_funcs = [f for f in result.modules[0].functions if "FastAPI" in (f.docstring or "")]
        assert len(route_funcs) >= 2


class TestPythonPydantic:
    """Pydantic 支持测试"""

    @pytest.fixture
    def parser(self):
        return PythonParser()

    def test_pydantic_model_detection(self, parser, tmp_path):
        """测试 Pydantic 模型检测"""
        code = '''
from pydantic import BaseModel, Field

class User(BaseModel):
    """User model"""
    id: int
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$")
    age: int = Field(..., ge=0, le=150)
    is_active: bool = True
'''
        file_path = tmp_path / "models.py"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.name == "User"
        assert "Pydantic Model" in (cls.docstring or "")
        assert "使用 Field 验证" in (cls.docstring or "")

    def test_pydantic_model_without_field(self, parser, tmp_path):
        """测试没有 Field 的 Pydantic 模型"""
        code = '''
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None
'''
        file_path = tmp_path / "models.py"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "Pydantic Model" in (cls.docstring or "")


class TestPythonSQLAlchemy:
    """SQLAlchemy 支持测试"""

    @pytest.fixture
    def parser(self):
        return PythonParser()

    def test_sqlalchemy_model_detection(self, parser, tmp_path):
        """测试 SQLAlchemy 模型检测"""
        code = '''
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
'''
        file_path = tmp_path / "models.py"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]

        # 找到 User 类（排除 Base 赋值）
        user_class = None
        for cls in module.classes:
            if cls.name == "User":
                user_class = cls
                break

        assert user_class is not None
        assert "SQLAlchemy Model" in (user_class.docstring or "")
        assert "自定义表名" in (user_class.docstring or "")

    def test_sqlalchemy_model_without_tablename(self, parser, tmp_path):
        """测试没有自定义表名的 SQLAlchemy 模型"""
        code = '''
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Item(Base):
    id = Column(Integer, primary_key=True)
    name = Column(String)
'''
        file_path = tmp_path / "models.py"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        item_class = [c for c in result.modules[0].classes if c.name == "Item"][0]
        assert "SQLAlchemy Model" in (item_class.docstring or "")


class TestPythonFrameworkEdgeCases:
    """框架支持边界情况测试"""

    @pytest.fixture
    def parser(self):
        return PythonParser()

    def test_mixed_frameworks(self, parser, tmp_path):
        """测试混合使用多个框架"""
        code = '''
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from fastapi import FastAPI

app = FastAPI()
Base = declarative_base()

class UserCreate(BaseModel):
    name: str
    email: str

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

@app.post("/users")
async def create_user(user: UserCreate):
    return user
'''
        file_path = tmp_path / "mixed.py"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        module = result.modules[0]

        # 检查 Pydantic 模型
        pydantic_classes = [c for c in module.classes if "Pydantic" in (c.docstring or "")]
        assert len(pydantic_classes) >= 1

        # 检查 SQLAlchemy 模型
        sqlalchemy_classes = [c for c in module.classes if "SQLAlchemy" in (c.docstring or "")]
        assert len(sqlalchemy_classes) >= 1

        # 检查 FastAPI 路由
        route_funcs = [f for f in module.functions if "FastAPI" in (f.docstring or "")]
        assert len(route_funcs) >= 1
