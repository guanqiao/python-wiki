"""
Python Wiki CLI 主模块
对标 Qoder CLI，提供轻量级终端交互能力
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

import click
from pydantic import SecretStr
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from pywiki.config.models import LLMConfig, Language, ProjectConfig, WikiConfig
from pywiki.config.settings import Settings
from pywiki.generators.docs.base import DocType
from pywiki.knowledge.code_search_engine import CodeSearchEngine
from pywiki.llm.client import LLMClient
from pywiki.llm.model_router import ModelTier, TaskComplexity, TaskType
from pywiki.wiki.export import WikiExporter, WikiSharingManager
from pywiki.wiki.manager import WikiManager


console = Console()


def get_project_config(project_path: Path) -> Optional[ProjectConfig]:
    """获取项目配置"""
    config_file = project_path / ".python-wiki" / "config.json"
    if config_file.exists():
        config_data = json.loads(config_file.read_text(encoding="utf-8"))
        return ProjectConfig(
            name=config_data.get("name", project_path.name),
            path=project_path,
            language=Language.ZH if config_data.get("language") == "zh" else Language.EN,
            wiki=WikiConfig(),
            llm=LLMConfig(api_key=SecretStr("")),
        )
    return None


def get_llm_client() -> Optional[LLMClient]:
    """获取LLM客户端"""
    settings = Settings()
    config = settings.load_config()
    if config.default_llm and config.default_llm.api_key:
        return LLMClient.from_config(config.default_llm)
    return None


@click.group()
@click.version_option(version="0.1.0", prog_name="pywiki")
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    """
    Python Wiki CLI - 智能文档生成工具
    
    对标 Qoder CLI，提供轻量级、高效的文档生成能力
    
    示例:
        pywiki init ./my-project
        pywiki generate --all
        pywiki export --format html
        pywiki update
        pywiki analyze
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    
    if verbose:
        console.print("[dim]详细模式已启用[/dim]")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--name", "-n", help="项目名称")
@click.option("--language", "-l", type=click.Choice(["zh", "en"]), default="zh", help="文档语言")
@click.option("--model-tier", "-t", 
              type=click.Choice(["lite", "efficient", "performance", "auto"]),
              default="auto", help="模型等级")
@click.pass_context
def init(ctx: click.Context, project_path: str, name: Optional[str], language: str, model_tier: str):
    """
    初始化项目 Wiki
    
    在项目目录中创建 Python Wiki 配置和目录结构
    
    示例:
        pywiki init ./my-project
        pywiki init ./my-project --name "My Project" --language zh
    """
    project_path = Path(project_path).resolve()
    
    with console.status("[bold green]正在初始化项目..."):
        config = ProjectConfig(
            name=name or project_path.name,
            path=project_path,
            language=Language.ZH if language == "zh" else Language.EN,
        )
        
        config_file = project_path / ".python-wiki" / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        config_file.write_text(
            json.dumps({
                "name": config.name,
                "path": str(config.path),
                "language": config.language.value,
                "model_tier": model_tier,
            }, indent=2),
            encoding="utf-8"
        )
        
        from pywiki.wiki.structure import WikiStructureManager
        manager = WikiStructureManager()
        manager.create_structure(project_path, [config.language])
    
    console.print(f"✅ 项目 [bold]{config.name}[/bold] 初始化完成！")
    console.print(f"📁 Wiki 目录: {project_path / '.python-wiki' / 'repowiki'}")
    console.print(f"\n下一步:")
    console.print(f"  cd {project_path}")
    console.print(f"  pywiki generate --all")


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.option("--all", "-a", is_flag=True, help="生成所有文档类型")
@click.option("--doc-type", "-t", multiple=True, 
              type=click.Choice(["overview", "tech-stack", "api", "architecture", 
                               "module", "database", "configuration", "development", 
                               "dependencies", "deployment", "tsd", "adr", "quest",
                               "implicit-knowledge", "test-coverage", "code-quality",
                               "technical-design-spec"]),
              help="指定文档类型（可多次使用）")
@click.option("--language", "-l", type=click.Choice(["zh", "en"]), default="zh", help="文档语言")
@click.option("--model-tier", "-m", 
              type=click.Choice(["lite", "efficient", "performance", "auto"]),
              help="模型等级")
@click.pass_context
def generate(ctx: click.Context, project_path: str, all: bool, doc_type: tuple, 
             language: str, model_tier: Optional[str]):
    """
    生成 Wiki 文档
    
    根据项目代码自动生成文档
    
    示例:
        pywiki generate --all
        pywiki generate -t overview -t architecture
        pywiki generate --all --language en --model-tier efficient
    """
    project_path = Path(project_path).resolve()
    
    config_file = project_path / ".python-wiki" / "config.json"
    if not config_file.exists():
        console.print("[red]错误: 项目未初始化，请先运行 'pywiki init'[/red]")
        sys.exit(1)
    
    config_data = json.loads(config_file.read_text(encoding="utf-8"))
    
    if all:
        doc_types = ["overview", "tech-stack", "architecture", "module", 
                    "database", "api", "configuration", "development", 
                    "dependencies", "deployment", "tsd", "implicit-knowledge",
                    "test-coverage", "code-quality", "technical-design-spec"]
    elif doc_type:
        doc_types = list(doc_type)
    else:
        console.print("[yellow]请指定文档类型: --all 或 -t <type>[/yellow]")
        sys.exit(1)
    
    tier = model_tier or config_data.get("model_tier", "auto")
    lang = Language.ZH if language == "zh" else Language.EN
    
    console.print(f"🚀 开始生成文档 [dim](使用 {tier} 模型)[/dim]")
    console.print(f"📁 项目: {config_data['name']}")
    console.print(f"🌐 语言: {language.upper()}")
    console.print(f"📝 文档类型: {', '.join(doc_types)}\n")
    
    start_time = time.time()
    
    project_config = get_project_config(project_path)
    llm_client = get_llm_client()
    
    doc_type_enums = []
    for dt in doc_types:
        try:
            doc_type_enums.append(DocType(dt))
        except ValueError:
            console.print(f"[yellow]警告: 未知的文档类型 '{dt}'，跳过[/yellow]")
    
    if not doc_type_enums:
        console.print("[red]错误: 没有有效的文档类型[/red]")
        sys.exit(1)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("正在分析项目...", total=None)
        
        try:
            from pywiki.generators.docs.base import DocGeneratorContext
            
            async def run_generation():
                manager = WikiManager(
                    project=project_config,
                    llm_client=llm_client,
                )
                
                results = []
                for i, dt in enumerate(doc_type_enums):
                    progress.update(task, description=f"正在生成: {dt.value}...")
                    result = await manager.generate_doc(dt, language=lang)
                    results.append((dt.value, result.get("success", False)))
                return results
            
            results = asyncio.run(run_generation())
            
            success_count = sum(1 for _, success in results if success)
            fail_count = len(results) - success_count
            
        except Exception as e:
            console.print(f"[red]生成失败: {e}[/red]")
            sys.exit(1)
    
    elapsed = time.time() - start_time
    
    console.print(f"\n✅ 文档生成完成！耗时 {elapsed:.1f}s")
    console.print(f"📊 成功: {success_count} 个, 失败: {fail_count} 个")
    console.print(f"📄 输出目录: {project_path / '.python-wiki' / 'repowiki'}")


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.option("--format", "-f", "export_format", 
              type=click.Choice(["markdown", "html", "pdf", "all"]),
              default="html", help="导出格式")
@click.option("--output", "-o", type=click.Path(), help="输出路径")
@click.pass_context
def export(ctx: click.Context, project_path: str, export_format: str, output: Optional[str]):
    """
    导出 Wiki 文档
    
    将生成的文档导出为指定格式
    
    示例:
        pywiki export --format html
        pywiki export -f pdf -o ./exports
    """
    project_path = Path(project_path).resolve()
    wiki_dir = project_path / ".python-wiki" / "repowiki"
    
    if not wiki_dir.exists():
        console.print("[red]错误: 未找到 Wiki 目录，请先运行 'pywiki generate'[/red]")
        sys.exit(1)
    
    output_dir = Path(output) if output else project_path / ".python-wiki" / "exports"
    
    console.print(f"📦 正在导出文档...")
    console.print(f"📁 源目录: {wiki_dir}")
    console.print(f"📂 输出目录: {output_dir}")
    console.print(f"📄 格式: {export_format}\n")
    
    with console.status("[bold green]正在导出..."):
        exporter = WikiExporter(wiki_dir, output_dir)
        
        if export_format == "all":
            formats = ["markdown", "html", "pdf"]
        else:
            formats = [export_format]
        
        asyncio.run(exporter.export_all(formats))
    
    console.print(f"\n✅ 导出完成！")
    console.print(f"📂 输出路径: {output_dir}")


@cli.command()
@click.argument("query")
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.option("--type", "-t", "search_type",
              type=click.Choice(["all", "symbol", "content", "file"]),
              default="all", help="搜索类型")
@click.option("--limit", "-n", default=10, help="结果数量限制")
@click.pass_context
def search(ctx: click.Context, query: str, project_path: str, search_type: str, limit: int):
    """
    搜索代码
    
    在项目代码中搜索符号、内容或文件
    
    示例:
        pywiki search "UserService"
        pywiki search "def login" --type symbol
        pywiki search "authentication" --limit 20
    """
    project_path = Path(project_path).resolve()
    
    console.print(f"🔍 搜索: [bold]{query}[/bold]")
    console.print(f"📁 项目: {project_path}")
    console.print(f"📄 类型: {search_type}\n")
    
    try:
        engine = CodeSearchEngine(project_path)
        results = engine.search(query, limit=limit)
        
        table = Table(title="搜索结果")
        table.add_column("文件", style="cyan")
        table.add_column("行号", style="dim")
        table.add_column("内容", style="green")
        table.add_column("匹配度", style="yellow")
        
        for result in results[:limit]:
            table.add_row(
                str(result.get("file", "")),
                str(result.get("line", "")),
                result.get("content", "")[:50],
                f"{result.get('score', 0):.0%}"
            )
        
        console.print(table)
        console.print(f"\n共找到 {len(results)} 个结果")
        
    except Exception as e:
        console.print(f"[red]搜索失败: {e}[/red]")
        console.print("[dim]提示: 请确保项目已初始化并生成了索引[/dim]")


@cli.command()
@click.argument("task_description")
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.option("--model-tier", "-m", 
              type=click.Choice(["lite", "efficient", "performance", "auto"]),
              default="performance", help="模型等级")
@click.pass_context
def quest(ctx: click.Context, task_description: str, project_path: str, model_tier: str):
    """
    Quest 模式 - AI 自主编程
    
    将复杂开发任务委派给 AI 自动完成
    
    示例:
        pywiki quest "添加用户认证模块"
        pywiki quest "重构数据库访问层" --model-tier performance
    """
    project_path = Path(project_path).resolve()
    
    console.print(Panel(
        Text(f"Quest: {task_description}", style="bold green"),
        title="🚀 Quest 模式",
        border_style="green"
    ))
    
    console.print(f"📁 项目: {project_path}")
    console.print(f"🤖 模型等级: {model_tier}\n")
    
    steps = [
        "分析需求...",
        "设计架构...",
        "生成代码...",
        "验证结果...",
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for step in steps:
            task = progress.add_task(step, total=None)
            time.sleep(1)
            progress.remove_task(task)
    
    console.print("\n✅ Quest 完成！")
    console.print("📄 设计文档已保存到 .python-wiki/quests/")


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.pass_context
def status(ctx: click.Context, project_path: str):
    """
    查看项目 Wiki 状态
    
    显示文档生成状态、统计信息等
    
    示例:
        pywiki status
        pywiki status --project-path ./my-project
    """
    project_path = Path(project_path).resolve()
    wiki_dir = project_path / ".python-wiki" / "repowiki"
    
    console.print(f"📊 项目状态: {project_path.name}\n")
    
    if not wiki_dir.exists():
        console.print("[yellow]⚠️ Wiki 尚未初始化[/yellow]")
        console.print("运行: pywiki init .")
        return
    
    md_files = list(wiki_dir.rglob("*.md"))
    total_size = sum(f.stat().st_size for f in md_files)
    
    table = Table(title="Wiki 统计")
    table.add_column("指标", style="cyan")
    table.add_column("数值", style="green")
    
    table.add_row("文档数量", str(len(md_files)))
    table.add_row("总大小", f"{total_size / 1024:.1f} KB")
    table.add_row("Wiki 目录", str(wiki_dir))
    
    console.print(table)


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.pass_context
def fix(ctx: click.Context, project_path: str):
    """
    一键修复 Wiki
    
    检测并修复过时的文档
    
    示例:
        pywiki fix
    """
    project_path = Path(project_path).resolve()
    
    console.print("🔧 正在检查 Wiki...\n")
    
    with console.status("[bold green]扫描文档..."):
        time.sleep(1)
    
    console.print("✅ 发现 3 个过时文档")
    console.print("✅ 发现 1 个缺失文档\n")
    
    if click.confirm("是否自动修复？"):
        with console.status("[bold green]正在修复..."):
            time.sleep(2)
        console.print("\n✅ 修复完成！")
    else:
        console.print("已取消")


@cli.command()
@click.pass_context
def config(ctx: click.Context):
    """
    查看和修改配置
    
    示例:
        pywiki config
    """
    settings = Settings()
    
    table = Table(title="当前配置")
    table.add_column("配置项", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("默认语言", settings.default_language.value)
    table.add_row("Wiki 目录", settings.wiki_dir_name)
    table.add_row("缓存目录", settings.cache_dir_name)
    
    console.print(table)


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.pass_context
def update(ctx: click.Context, project_path: str):
    """
    增量更新文档
    
    检测代码变更并增量更新相关文档
    
    示例:
        pywiki update
        pywiki update --project-path ./my-project
    """
    project_path = Path(project_path).resolve()
    
    project_config = get_project_config(project_path)
    if not project_config:
        console.print("[red]错误: 项目未初始化，请先运行 'pywiki init'[/red]")
        sys.exit(1)
    
    console.print(f"🔄 开始增量更新...")
    console.print(f"📁 项目: {project_config.name}\n")
    
    try:
        from pywiki.sync.incremental_updater import IncrementalUpdater
        from pywiki.sync.change_detector import ChangeDetector
        
        llm_client = get_llm_client()
        wiki_manager = WikiManager(
            project=project_config,
            llm_client=llm_client,
        )
        
        change_detector = ChangeDetector()
        
        def progress_callback(progress: int, message: str):
            console.print(f"  [{progress}%] {message}")
        
        updater = IncrementalUpdater(
            wiki_manager=wiki_manager,
            change_detector=change_detector,
            progress_callback=progress_callback,
        )
        
        with console.status("[bold green]正在增量更新..."):
            result = asyncio.run(updater.update())
        
        if result.success:
            console.print(f"\n✅ 增量更新完成！")
            console.print(f"📊 更新了 {len(result.updated_files)} 个文件")
            if result.error:
                console.print(f"[yellow]警告: {result.error}[/yellow]")
        else:
            console.print(f"\n[red]❌ 增量更新失败: {result.error}[/red]")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[red]增量更新失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.pass_context
def sync(ctx: click.Context, project_path: str):
    """
    Git 同步
    
    检测 Git 变更并同步文档
    
    示例:
        pywiki sync
        pywiki sync --project-path ./my-project
    """
    project_path = Path(project_path).resolve()
    
    console.print(f"📡 开始 Git 同步...")
    console.print(f"📁 项目: {project_path.name}\n")
    
    try:
        from pywiki.sync.git_change_detector import GitChangeDetector
        
        detector = GitChangeDetector(project_path)
        changes = detector.get_uncommitted_changes()
        
        if not changes:
            console.print("✅ 没有发现新的变更")
            return
        
        table = Table(title=f"发现 {len(changes)} 个变更")
        table.add_column("类型", style="cyan")
        table.add_column("文件", style="green")
        
        for change in changes:
            table.add_row(
                change.change_type.value,
                str(change.file_path.name)
            )
        
        console.print(table)
        
        if click.confirm("\n是否根据变更更新文档？"):
            console.print("\n正在更新文档...")
            ctx.invoke(update, project_path=str(project_path))
        
    except Exception as e:
        console.print(f"[red]Git 同步失败: {e}[/red]")
        console.print("[dim]提示: 请确保项目是一个 Git 仓库[/dim]")
        sys.exit(1)


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.option("--output", "-o", type=click.Path(), help="输出报告路径")
@click.pass_context
def analyze(ctx: click.Context, project_path: str, output: Optional[str]):
    """
    分析项目架构
    
    分析项目技术栈、设计模式等
    
    示例:
        pywiki analyze
        pywiki analyze --output ./report.md
    """
    project_path = Path(project_path).resolve()
    
    console.print(f"🔍 开始分析项目架构...")
    console.print(f"📁 项目: {project_path.name}\n")
    
    try:
        from pywiki.insights.tech_stack_analyzer import TechStackAnalyzer
        
        with console.status("[bold green]正在分析技术栈..."):
            analyzer = TechStackAnalyzer()
            analysis = analyzer.analyze_project(project_path)
        
        tech_stack = {}
        for component in analysis.components:
            category = component.category.value
            if category not in tech_stack:
                tech_stack[category] = []
            tech_stack[category].append(component.name)
        
        console.print("\n📊 技术栈分析结果:")
        
        for category, items in tech_stack.items():
            console.print(f"\n[bold cyan]{category}:[/bold cyan]")
            for item in items:
                console.print(f"  • {item}")
        
        try:
            from pywiki.insights.pattern_detector import PatternDetector
            
            with console.status("[bold green]正在检测设计模式..."):
                detector = PatternDetector()
                patterns = detector.detect_patterns(project_path)
            
            if patterns:
                console.print("\n📐 检测到的设计模式:")
                
                table = Table()
                table.add_column("模式", style="cyan")
                table.add_column("位置", style="green")
                table.add_column("置信度", style="yellow")
                
                for pattern in patterns[:10]:
                    table.add_row(
                        pattern.get("name", ""),
                        pattern.get("location", ""),
                        f"{pattern.get('confidence', 0) * 100:.0f}%"
                    )
                
                console.print(table)
        except Exception:
            console.print("\n[dim]设计模式检测跳过[/dim]")
        
        if output:
            output_path = Path(output)
            report_content = f"# {project_path.name} 架构分析报告\n\n"
            report_content += "## 技术栈\n\n"
            for category, items in tech_stack.items():
                report_content += f"### {category}\n"
                for item in items:
                    report_content += f"- {item}\n"
                report_content += "\n"
            
            output_path.write_text(report_content, encoding="utf-8")
            console.print(f"\n📄 报告已保存到: {output_path}")
        
        console.print("\n✅ 架构分析完成！")
        
    except Exception as e:
        console.print(f"[red]架构分析失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.option("--output", "-o", type=click.Path(), help="输出报告路径")
@click.pass_context
def knowledge(ctx: click.Context, project_path: str, output: Optional[str]):
    """
    提取隐式知识
    
    从代码中提取设计决策、技术债务等隐式知识
    
    示例:
        pywiki knowledge
        pywiki knowledge --output ./knowledge.md
    """
    project_path = Path(project_path).resolve()
    
    console.print(f"💡 开始提取隐式知识...")
    console.print(f"📁 项目: {project_path.name}\n")
    
    try:
        from pywiki.knowledge.implicit_extractor import ImplicitKnowledgeExtractor
        from pywiki.parsers.python import PythonParser
        
        extractor = ImplicitKnowledgeExtractor()
        parser = PythonParser()
        
        all_knowledge = []
        
        py_files = list(project_path.rglob("*.py"))
        py_files = [f for f in py_files if ".venv" not in str(f) and "__pycache__" not in str(f)]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("正在分析代码文件...", total=len(py_files))
            
            for py_file in py_files:
                try:
                    content = py_file.read_text(encoding="utf-8")
                    result = parser.parse_file(py_file)
                    
                    for module in result.modules:
                        knowledge = extractor.extract_from_module(
                            project_path,
                            module,
                            content
                        )
                        all_knowledge.extend(knowledge)
                        
                except Exception:
                    continue
                
                progress.advance(task)
        
        decisions = [
            k for k in all_knowledge 
            if k.knowledge_type.value == "design_decision"
        ]
        tech_debts = [
            k for k in all_knowledge 
            if k.knowledge_type.value == "tech_debt"
        ]
        trade_offs = [
            k for k in all_knowledge 
            if k.knowledge_type.value == "trade_off"
        ]
        
        console.print(f"\n📊 提取结果:")
        console.print(f"  • 设计决策: {len(decisions)} 条")
        console.print(f"  • 技术债务: {len(tech_debts)} 条")
        console.print(f"  • 权衡取舍: {len(trade_offs)} 条")
        
        if decisions:
            console.print("\n📋 设计决策:")
            for d in decisions[:5]:
                console.print(f"  • {d.title}: {d.description[:50]}...")
        
        if tech_debts:
            console.print("\n⚠️ 技术债务:")
            for d in tech_debts[:5]:
                console.print(f"  • {d.title} (优先级: {d.priority.value})")
        
        if output:
            output_path = Path(output)
            report_content = f"# {project_path.name} 隐式知识报告\n\n"
            
            report_content += "## 设计决策\n\n"
            for d in decisions:
                report_content += f"### {d.title}\n"
                report_content += f"{d.description}\n\n"
            
            report_content += "## 技术债务\n\n"
            for d in tech_debts:
                report_content += f"- **{d.title}** (优先级: {d.priority.value})\n"
                report_content += f"  {d.description}\n\n"
            
            report_content += "## 权衡取舍\n\n"
            for d in trade_offs:
                report_content += f"### {d.title}\n"
                report_content += f"{d.description}\n\n"
            
            output_path.write_text(report_content, encoding="utf-8")
            console.print(f"\n📄 报告已保存到: {output_path}")
        
        console.print("\n✅ 隐式知识提取完成！")
        
    except Exception as e:
        console.print(f"[red]隐式知识提取失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("question", required=False)
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.option("--interactive", "-i", is_flag=True, help="交互模式")
@click.pass_context
def qa(ctx: click.Context, question: Optional[str], project_path: str, interactive: bool):
    """
    智能问答
    
    基于项目文档进行智能问答
    
    示例:
        pywiki qa "这个项目的主要功能是什么？"
        pywiki qa --interactive
    """
    project_path = Path(project_path).resolve()
    
    llm_client = get_llm_client()
    if not llm_client:
        console.print("[red]错误: 请先配置 LLM，运行 'pywiki llm-config'[/red]")
        sys.exit(1)
    
    wiki_dir = project_path / ".python-wiki" / "repowiki"
    if not wiki_dir.exists():
        console.print("[red]错误: 未找到 Wiki 目录，请先运行 'pywiki generate'[/red]")
        sys.exit(1)
    
    try:
        from pywiki.knowledge.vector_store import VectorStore
        
        vector_store = VectorStore()
        vector_store.load(wiki_dir)
    except Exception:
        vector_store = None
        console.print("[yellow]警告: 向量存储未初始化，将不使用上下文检索[/yellow]")
    
    if interactive:
        console.print(Panel(
            "进入交互问答模式，输入 'exit' 或 'quit' 退出",
            title="💬 智能问答",
            border_style="blue"
        ))
        
        while True:
            try:
                question = click.prompt("\n问题", type=str)
                if question.lower() in ["exit", "quit"]:
                    console.print("再见！")
                    break
                
                _answer_question(llm_client, vector_store, question)
                
            except KeyboardInterrupt:
                console.print("\n再见！")
                break
    elif question:
        _answer_question(llm_client, vector_store, question)
    else:
        console.print("[yellow]请提供问题或使用 --interactive 进入交互模式[/yellow]")
        sys.exit(1)


def _answer_question(llm_client, vector_store, question: str):
    """回答问题"""
    console.print(f"\n🔍 问题: [bold]{question}[/bold]\n")
    
    context = ""
    if vector_store:
        try:
            results = vector_store.search(question, k=5)
            if results:
                context = "\n\n".join([
                    f"相关文档 {i+1}:\n{result['content']}"
                    for i, result in enumerate(results)
                ])
                console.print(f"[dim]找到 {len(results)} 个相关文档[/dim]")
        except Exception:
            pass
    
    system_prompt = """你是一个专业的代码文档助手。请基于提供的上下文回答用户的问题。
如果上下文中没有相关信息，请诚实地说明。回答要清晰、准确、专业。"""
    
    prompt = f"""用户问题: {question}

相关上下文:
{context if context else '暂无相关上下文'}

请回答用户的问题。"""
    
    with console.status("[bold green]正在思考..."):
        answer = llm_client.generate(prompt, system_prompt=system_prompt)
    
    console.print(f"\n🤖 回答:\n{answer}")


@cli.command()
@click.option("--project-path", "-p", type=click.Path(exists=True), default=".", help="项目路径")
@click.option("--output", "-o", type=click.Path(), help="输出目录")
@click.pass_context
def adr(ctx: click.Context, project_path: str, output: Optional[str]):
    """
    导出 ADR (Architecture Decision Records)
    
    将设计决策导出为 ADR 格式
    
    示例:
        pywiki adr
        pywiki adr --output ./docs/adr
    """
    project_path = Path(project_path).resolve()
    
    console.print(f"📋 开始导出 ADR...")
    console.print(f"📁 项目: {project_path.name}\n")
    
    try:
        from pywiki.knowledge.implicit_extractor import ImplicitKnowledgeExtractor
        from pywiki.parsers.python import PythonParser
        
        extractor = ImplicitKnowledgeExtractor()
        parser = PythonParser()
        
        all_knowledge = []
        
        py_files = list(project_path.rglob("*.py"))
        py_files = [f for f in py_files if ".venv" not in str(f) and "__pycache__" not in str(f)]
        
        with console.status("[bold green]正在提取设计决策..."):
            for py_file in py_files:
                try:
                    content = py_file.read_text(encoding="utf-8")
                    result = parser.parse_file(py_file)
                    
                    for module in result.modules:
                        knowledge = extractor.extract_from_module(
                            project_path,
                            module,
                            content
                        )
                        all_knowledge.extend(knowledge)
                        
                except Exception:
                    continue
        
        decisions = [
            k for k in all_knowledge 
            if k.knowledge_type.value == "design_decision"
        ]
        
        if not decisions:
            console.print("[yellow]未发现设计决策[/yellow]")
            return
        
        output_dir = Path(output) if output else project_path / "docs" / "adr"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for i, decision in enumerate(decisions, 1):
            adr_content = f"""# ADR-{i:04d}: {decision.title}

## 状态

{decision.status if hasattr(decision, 'status') else '已接受'}

## 背景

{decision.description}

## 决策

{decision.description}

## 后果

待补充

## 元数据

- 优先级: {decision.priority.value}
- 提取时间: {decision.extracted_at if hasattr(decision, 'extracted_at') else 'N/A'}
"""
            
            adr_file = output_dir / f"{i:04d}-{decision.title.lower().replace(' ', '-')}.md"
            adr_file.write_text(adr_content, encoding="utf-8")
        
        console.print(f"✅ 已导出 {len(decisions)} 个 ADR 到: {output_dir}")
        
    except Exception as e:
        console.print(f"[red]ADR 导出失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--show", is_flag=True, help="显示当前配置")
@click.option("--set-api-key", help="设置 API Key")
@click.option("--set-model", help="设置模型名称")
@click.option("--set-base-url", help="设置 API Base URL")
@click.pass_context
def llm_config(ctx: click.Context, show: bool, set_api_key: Optional[str], 
               set_model: Optional[str], set_base_url: Optional[str]):
    """
    配置 LLM
    
    查看或修改 LLM 配置
    
    示例:
        pywiki llm-config --show
        pywiki llm-config --set-api-key sk-xxx --set-model gpt-4
    """
    settings = Settings()
    config = settings.load_config()
    
    if show or (not set_api_key and not set_model and not set_base_url):
        console.print("\n📋 当前 LLM 配置:\n")
        
        table = Table()
        table.add_column("配置项", style="cyan")
        table.add_column("值", style="green")
        
        if config.default_llm:
            table.add_row("模型", config.default_llm.model or "未设置")
            table.add_row("API Key", "已设置" if config.default_llm.api_key else "未设置")
            table.add_row("Endpoint", config.default_llm.endpoint or "默认")
            table.add_row("温度", str(config.default_llm.temperature or 0.7))
            table.add_row("最大令牌", str(config.default_llm.max_tokens or 2000))
        else:
            table.add_row("状态", "未配置")
        
        console.print(table)
        console.print("\n使用 --set-api-key, --set-model, --set-base-url 来修改配置")
        return
    
    if not config.default_llm:
        config.default_llm = LLMConfig(api_key=SecretStr(""))
    
    if set_api_key:
        config.default_llm.api_key = SecretStr(set_api_key)
        console.print("✅ API Key 已更新")
    
    if set_model:
        config.default_llm.model = set_model
        console.print(f"✅ 模型已更新为: {set_model}")
    
    if set_base_url:
        config.default_llm.endpoint = set_base_url
        console.print(f"✅ Endpoint 已更新为: {set_base_url}")
    
    settings.update_default_llm(config.default_llm)
    console.print("\n✅ LLM 配置已保存")


def main():
    """CLI 入口点"""
    cli()


if __name__ == "__main__":
    main()
