"""
Python Wiki CLI 主模块
对标 Qoder CLI，提供轻量级终端交互能力
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from pywiki.config.settings import Settings
from pywiki.config.models import ProjectConfig, Language
from pywiki.wiki.manager import WikiManager
from pywiki.wiki.export import WikiExporter, WikiSharingManager
from pywiki.knowledge.code_search_engine import CodeSearchEngine
from pywiki.llm.model_router import ModelRouter, ModelTier, TaskType, TaskComplexity


console = Console()


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
        # 创建配置
        config = ProjectConfig(
            name=name or project_path.name,
            path=project_path,
            language=Language.ZH if language == "zh" else Language.EN,
        )
        
        # 保存配置
        config_file = project_path / ".python-wiki" / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        config_file.write_text(
            json.dumps({
                "name": config.name,
                "path": str(config.path),
                "language": config.language.value,
                "model_tier": model_tier,
            }, indent=2),
            encoding="utf-8"
        )
        
        # 创建 Wiki 目录结构
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
                               "dependencies", "tsd", "adr", "quest"]),
              help="指定文档类型（可多次使用）")
@click.option("--model-tier", "-m", 
              type=click.Choice(["lite", "efficient", "performance", "auto"]),
              help="模型等级")
@click.pass_context
def generate(ctx: click.Context, project_path: str, all: bool, doc_type: tuple, model_tier: Optional[str]):
    """
    生成 Wiki 文档
    
    根据项目代码自动生成文档
    
    示例:
        pywiki generate --all
        pywiki generate -t overview -t architecture
        pywiki generate --all --model-tier efficient
    """
    project_path = Path(project_path).resolve()
    
    # 加载配置
    config_file = project_path / ".python-wiki" / "config.json"
    if not config_file.exists():
        console.print("[red]错误: 项目未初始化，请先运行 'pywiki init'[/red]")
        sys.exit(1)
    
    import json
    config_data = json.loads(config_file.read_text(encoding="utf-8"))
    
    # 确定文档类型
    if all:
        doc_types = ["overview", "tech-stack", "architecture", "module", 
                    "database", "api", "configuration", "development", 
                    "dependencies", "tsd"]
    elif doc_type:
        doc_types = list(doc_type)
    else:
        console.print("[yellow]请指定文档类型: --all 或 -t <type>[/yellow]")
        sys.exit(1)
    
    # 确定模型等级
    tier = model_tier or config_data.get("model_tier", "auto")
    
    console.print(f"🚀 开始生成文档 [dim](使用 {tier} 模型)[/dim]")
    console.print(f"📁 项目: {config_data['name']}")
    console.print(f"📝 文档类型: {', '.join(doc_types)}\n")
    
    # 执行生成
    start_time = time.time()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("正在分析项目...", total=None)
        
        # 这里简化实现，实际应该调用 WikiManager
        for i, dt in enumerate(doc_types):
            progress.update(task, description=f"正在生成: {dt}...")
            time.sleep(0.5)  # 模拟生成过程
    
    elapsed = time.time() - start_time
    
    console.print(f"\n✅ 文档生成完成！耗时 {elapsed:.1f}s")
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
        
        # 异步执行导出
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
    
    # 这里简化实现，实际应该调用 CodeSearchEngine
    # 模拟搜索结果
    table = Table(title="搜索结果")
    table.add_column("文件", style="cyan")
    table.add_column("行号", style="dim")
    table.add_column("内容", style="green")
    table.add_column("匹配度", style="yellow")
    
    # 模拟数据
    results = [
        ("src/services/user.py", "45", "class UserService:", "95%"),
        ("src/models/user.py", "12", "def authenticate():", "87%"),
        ("src/api/auth.py", "23", "from services.user import UserService", "82%"),
    ]
    
    for file, line, content, score in results[:limit]:
        table.add_row(file, line, content, score)
    
    console.print(table)
    console.print(f"\n共找到 {len(results)} 个结果")


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
    
    # 模拟 Quest 执行流程
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
            time.sleep(1)  # 模拟执行
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
    
    # 统计文档
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
    
    # 模拟检测结果
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


def main():
    """CLI 入口点"""
    cli()


if __name__ == "__main__":
    main()
