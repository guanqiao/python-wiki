"""
模型路由器测试
"""

import pytest

from pywiki.llm.model_router import (
    ModelTier,
    TaskType,
    ModelConfig,
    ModelRegistry,
    ModelRouter,
    TaskComplexity,
    ContextCompressor,
)


class TestModelTier:
    """ModelTier 枚举测试"""

    def test_tier_values(self):
        """测试等级值"""
        assert ModelTier.LITE.value == "lite"
        assert ModelTier.EFFICIENT.value == "efficient"
        assert ModelTier.PERFORMANCE.value == "performance"
        assert ModelTier.AUTO.value == "auto"

    def test_tier_is_string_enum(self):
        """测试等级是字符串枚举"""
        assert isinstance(ModelTier.LITE, str)


class TestTaskType:
    """TaskType 枚举测试"""

    def test_task_type_values(self):
        """测试任务类型值"""
        assert TaskType.CODE_COMPLETION.value == "code_completion"
        assert TaskType.DOC_GENERATION.value == "doc_generation"
        assert TaskType.CODE_REVIEW.value == "code_review"
        assert TaskType.ARCHITECTURE_ANALYSIS.value == "architecture_analysis"
        assert TaskType.QUEST_MODE.value == "quest_mode"


class TestModelConfig:
    """ModelConfig 数据类测试"""

    def test_create_model_config(self):
        """测试创建模型配置"""
        config = ModelConfig(
            name="gpt-4",
            tier=ModelTier.EFFICIENT,
            max_tokens=8192,
            cost_per_1k_tokens=0.03,
            avg_response_time_ms=1500,
            context_window=8192,
        )

        assert config.name == "gpt-4"
        assert config.tier == ModelTier.EFFICIENT
        assert config.max_tokens == 8192
        assert config.cost_per_1k_tokens == 0.03
        assert config.avg_response_time_ms == 1500
        assert config.context_window == 8192
        assert config.supports_streaming is True

    def test_create_model_config_with_streaming_disabled(self):
        """测试创建不支持流式的模型配置"""
        config = ModelConfig(
            name="custom-model",
            tier=ModelTier.LITE,
            max_tokens=4096,
            cost_per_1k_tokens=0.001,
            avg_response_time_ms=500,
            context_window=16385,
            supports_streaming=False,
        )

        assert config.supports_streaming is False


class TestTaskComplexity:
    """TaskComplexity 数据类测试"""

    def test_create_default_complexity(self):
        """测试创建默认复杂度"""
        complexity = TaskComplexity()

        assert complexity.code_size == 0
        assert complexity.file_count == 0
        assert complexity.dependency_depth == 0
        assert complexity.reasoning_required is False
        assert complexity.creativity_required is False

    def test_create_complexity_with_values(self):
        """测试创建带值的复杂度"""
        complexity = TaskComplexity(
            code_size=5000,
            file_count=50,
            dependency_depth=5,
            reasoning_required=True,
            creativity_required=True,
        )

        assert complexity.code_size == 5000
        assert complexity.file_count == 50
        assert complexity.dependency_depth == 5
        assert complexity.reasoning_required is True
        assert complexity.creativity_required is True


class TestModelRegistry:
    """ModelRegistry 测试"""

    def test_get_models_by_tier_lite(self):
        """测试获取 Lite 级别模型"""
        models = ModelRegistry.get_models_by_tier(ModelTier.LITE)

        assert len(models) >= 1
        for model in models:
            assert model.tier == ModelTier.LITE

    def test_get_models_by_tier_efficient(self):
        """测试获取 Efficient 级别模型"""
        models = ModelRegistry.get_models_by_tier(ModelTier.EFFICIENT)

        assert len(models) >= 1
        for model in models:
            assert model.tier == ModelTier.EFFICIENT

    def test_get_models_by_tier_performance(self):
        """测试获取 Performance 级别模型"""
        models = ModelRegistry.get_models_by_tier(ModelTier.PERFORMANCE)

        assert len(models) >= 1
        for model in models:
            assert model.tier == ModelTier.PERFORMANCE

    def test_get_model_exists(self):
        """测试获取存在的模型"""
        model = ModelRegistry.get_model("gpt-4")

        assert model is not None
        assert model.name == "gpt-4"
        assert model.tier == ModelTier.EFFICIENT

    def test_get_model_not_exists(self):
        """测试获取不存在的模型"""
        model = ModelRegistry.get_model("nonexistent-model")

        assert model is None

    def test_predefined_models_count(self):
        """测试预定义模型数量"""
        assert len(ModelRegistry.MODELS) >= 6


class TestModelRouter:
    """ModelRouter 测试"""

    @pytest.fixture
    def router(self):
        """创建路由器实例"""
        return ModelRouter()

    def test_router_initialization(self, router: ModelRouter):
        """测试路由器初始化"""
        assert router.default_tier == ModelTier.AUTO
        assert router.usage_stats == {}

    def test_router_with_custom_default_tier(self):
        """测试自定义默认等级"""
        router = ModelRouter(default_tier=ModelTier.PERFORMANCE)

        assert router.default_tier == ModelTier.PERFORMANCE

    def test_select_model_code_completion(self, router: ModelRouter):
        """测试代码补全任务模型选择"""
        model = router.select_model(TaskType.CODE_COMPLETION)

        assert model is not None
        assert model in ModelRegistry.MODELS

    def test_select_model_doc_generation(self, router: ModelRouter):
        """测试文档生成任务模型选择"""
        model = router.select_model(TaskType.DOC_GENERATION)

        assert model is not None

    def test_select_model_architecture_analysis(self, router: ModelRouter):
        """测试架构分析任务模型选择"""
        model = router.select_model(TaskType.ARCHITECTURE_ANALYSIS)

        assert model is not None

    def test_select_model_with_specific_tier(self, router: ModelRouter):
        """测试指定等级模型选择"""
        model = router.select_model(
            TaskType.CODE_COMPLETION,
            tier=ModelTier.PERFORMANCE,
        )

        selected_model = ModelRegistry.get_model(model)
        assert selected_model is not None
        assert selected_model.tier == ModelTier.PERFORMANCE

    def test_select_model_with_preferred_provider(self, router: ModelRouter):
        """测试优先提供商模型选择"""
        model = router.select_model(
            TaskType.DOC_GENERATION,
            preferred_provider="openai",
        )

        assert "gpt" in model.lower() or model in ModelRegistry.MODELS

    def test_select_model_with_complexity_small(self, router: ModelRouter):
        """测试小复杂度任务模型选择"""
        complexity = TaskComplexity(
            code_size=50,
            file_count=2,
        )

        model = router.select_model(
            TaskType.CODE_COMPLETION,
            complexity=complexity,
        )

        assert model is not None

    def test_select_model_with_complexity_large(self, router: ModelRouter):
        """测试大复杂度任务模型选择"""
        complexity = TaskComplexity(
            code_size=15000,
            file_count=150,
            dependency_depth=5,
            reasoning_required=True,
        )

        model = router.select_model(
            TaskType.CODE_COMPLETION,
            complexity=complexity,
        )

        assert model is not None

    def test_select_model_records_usage(self, router: ModelRouter):
        """测试模型选择记录使用统计"""
        router.select_model(TaskType.CODE_COMPLETION)

        assert len(router.usage_stats) > 0

    def test_get_usage_stats(self, router: ModelRouter):
        """测试获取使用统计"""
        router.select_model(TaskType.CODE_COMPLETION)
        router.select_model(TaskType.DOC_GENERATION)
        router.select_model(TaskType.CODE_COMPLETION)

        stats = router.get_usage_stats()

        assert len(stats) > 0

    def test_estimate_cost(self, router: ModelRouter):
        """测试成本估算"""
        cost = router.estimate_cost("gpt-4", 1000, 500)

        assert cost > 0
        assert isinstance(cost, float)

    def test_estimate_cost_unknown_model(self, router: ModelRouter):
        """测试未知模型成本估算"""
        cost = router.estimate_cost("unknown-model", 1000, 500)

        assert cost == 0.0

    def test_get_model_info_exists(self, router: ModelRouter):
        """测试获取存在的模型信息"""
        info = router.get_model_info("gpt-4")

        assert info is not None
        assert info["name"] == "gpt-4"
        assert "tier" in info
        assert "max_tokens" in info
        assert "cost_per_1k_tokens" in info

    def test_get_model_info_not_exists(self, router: ModelRouter):
        """测试获取不存在的模型信息"""
        info = router.get_model_info("nonexistent-model")

        assert info is None


class TestModelRouterTierDetermination:
    """ModelRouter 等级确定测试"""

    @pytest.fixture
    def router(self):
        return ModelRouter()

    def test_determine_tier_with_specific_tier(self, router: ModelRouter):
        """测试指定等级时确定等级"""
        tier = router._determine_tier(
            TaskType.CODE_COMPLETION,
            None,
            ModelTier.PERFORMANCE,
        )

        assert tier == ModelTier.PERFORMANCE

    def test_determine_tier_auto_uses_task_mapping(self, router: ModelRouter):
        """测试 AUTO 等级使用任务映射"""
        tier = router._determine_tier(
            TaskType.CODE_COMPLETION,
            None,
            None,
        )

        assert tier == ModelTier.LITE

    def test_determine_tier_with_complexity_adjusts(self, router: ModelRouter):
        """测试复杂度调整等级"""
        complexity = TaskComplexity(
            code_size=15000,
            file_count=150,
            reasoning_required=True,
        )

        tier = router._determine_tier(
            TaskType.CODE_COMPLETION,
            complexity,
            None,
        )

        assert tier in [ModelTier.EFFICIENT, ModelTier.PERFORMANCE]


class TestModelRouterComplexityAdjustment:
    """ModelRouter 复杂度调整测试"""

    @pytest.fixture
    def router(self):
        return ModelRouter()

    def test_adjust_tier_small_complexity(self, router: ModelRouter):
        """测试小复杂度调整"""
        complexity = TaskComplexity(code_size=50, file_count=2)

        tier = router._adjust_tier_by_complexity(ModelTier.LITE, complexity)

        assert tier == ModelTier.LITE

    def test_adjust_tier_medium_complexity(self, router: ModelRouter):
        """测试中等复杂度调整"""
        complexity = TaskComplexity(code_size=500, file_count=10)

        tier = router._adjust_tier_by_complexity(ModelTier.LITE, complexity)

        assert tier in [ModelTier.LITE, ModelTier.EFFICIENT]

    def test_adjust_tier_large_complexity(self, router: ModelRouter):
        """测试大复杂度调整"""
        complexity = TaskComplexity(
            code_size=15000,
            file_count=150,
            dependency_depth=5,
            reasoning_required=True,
        )

        tier = router._adjust_tier_by_complexity(ModelTier.EFFICIENT, complexity)

        assert tier == ModelTier.PERFORMANCE

    def test_adjust_tier_with_creativity(self, router: ModelRouter):
        """测试创造性需求调整"""
        complexity = TaskComplexity(creativity_required=True)

        tier = router._adjust_tier_by_complexity(ModelTier.LITE, complexity)

        assert tier in [ModelTier.LITE, ModelTier.EFFICIENT]


class TestContextCompressor:
    """ContextCompressor 测试"""

    @pytest.fixture
    def compressor(self):
        return ContextCompressor(max_tokens=100)

    def test_compress_short_context(self, compressor: ContextCompressor):
        """测试压缩短上下文"""
        context = "Hello, world!"

        result = compressor.compress(context)

        assert result == context

    def test_compress_long_context_smart(self, compressor: ContextCompressor):
        """测试智能压缩长上下文"""
        context = "def hello():\n" * 1000

        result = compressor.compress(context, strategy="smart")

        assert len(result) < len(context)

    def test_compress_remove_comments(self, compressor: ContextCompressor):
        """测试移除注释压缩"""
        context = '''
def hello():
    # This is a comment
    print("Hello")
    """This is a docstring"""
'''

        result = compressor.compress(context, strategy="remove_comments")

        assert "#" not in result or "This is a comment" not in result

    def test_compress_summarize(self, compressor: ContextCompressor):
        """测试摘要压缩"""
        context = '''
"""Module docstring"""
def function_one():
    pass

def function_two():
    pass

class MyClass:
    def method(self):
        pass
'''

        result = compressor.compress(context, strategy="summarize")

        assert "def " in result or "class " in result

    def test_compress_truncate(self, compressor: ContextCompressor):
        """测试截断压缩"""
        context = "x" * 10000

        result = compressor.compress(context, strategy="truncate")

        assert len(result) < len(context)

    def test_smart_compress_preserves_imports(self, compressor: ContextCompressor):
        """测试智能压缩保留导入语句"""
        context = "import os\nimport sys\n" + "x = 1\n" * 1000

        result = compressor._smart_compress(context)

        assert "import os" in result
        assert "import sys" in result

    def test_smart_compress_preserves_definitions(self, compressor: ContextCompressor):
        """测试智能压缩保留定义"""
        context = "def my_function():\n    pass\n\nclass MyClass:\n    pass\n" + "x = 1\n" * 1000

        result = compressor._smart_compress(context)

        assert "def my_function" in result
        assert "class MyClass" in result

    def test_remove_comments_single_line(self, compressor: ContextCompressor):
        """测试移除单行注释"""
        context = "x = 1  # comment\ny = 2"

        result = compressor._remove_comments(context)

        assert "# comment" not in result
        assert "x = 1" in result

    def test_summarize_extracts_structure(self, compressor: ContextCompressor):
        """测试摘要提取结构"""
        context = '''
"""Module for testing"""
import os

def function_a():
    """Function A"""
    pass

def function_b():
    pass

class TestClass:
    def method(self):
        pass
'''

        result = compressor._summarize(context)

        assert "def function_a" in result
        assert "class TestClass" in result

    def test_truncate_preserves_head_and_tail(self, compressor: ContextCompressor):
        """测试截断保留头尾"""
        context = "START\n" + "MIDDLE\n" * 1000 + "END"

        result = compressor._truncate(context)

        assert "START" in result
        assert "END" in result
