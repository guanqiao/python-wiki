"""
CLI 主入口
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from pywiki.config.settings import Settings
from pywiki.config.models import ProjectConfig, WikiConfig, LLMConfig
from pywiki.wiki.manager import WikiManager, GenerationStatus
from pywiki.llm.client import LLMClient

app = typer.Typer(
    name="pywiki",
    help="AI-powered Wiki documentation generator - 对标 Qoder Wiki",
    add_completion=False,
)
console = Console()


@app.command()
def init(
    project_path: Path = typer.Argument(..., help="项目路径"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="项目名称"),
    language: str = typer.Option("zh", "--language", "-l", help="文档语言 (zh/en)"),
):
    """初始化 Wiki 项目"""
    settings = Settings()

    project_name = name or project_path.name

    project_config = ProjectConfig(
        name=project_name,
        path=project_path,
        wiki=WikiConfig(language=language),
        llm=LLMConfig(api_key=""),
    )

    settings.add_project(project_config)

    console.print(Panel(
        f"[green]项目初始化成功![/green]\n\n"
        f"项目名称: {project_name}\n"
        f"项目路径: {project_path}\n"
        f"文档语言: {language}",
        title="Python Wiki",
    ))


@app.command()
def generate(
    project_name: str = typer.Argument(..., help="项目名称"),
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="配置文件路径"),
):
    """生成 Wiki 文档"""
    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    config = settings.load_config()
    if not config.default_llm:
        console.print("[red]错误: 请先配置 LLM (使用 'pywiki config-llm' 命令)[/red]")
        raise typer.Exit(1)

    llm_client = LLMClient.from_config(config.default_llm)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("生成 Wiki...", total=100)

        def update_progress(p):
            progress.update(task, completed=p.processed_files / max(p.total_files, 1) * 100)

        manager = WikiManager(project, llm_client, update_progress)

        async def run():
            success = await manager.generate_full()
            return success

        success = asyncio.run(run())

    if success:
        console.print(f"[green]Wiki 生成成功![/green]")
        console.print(f"输出目录: {project.path / project.wiki.output_dir}")
    else:
        console.print("[red]Wiki 生成失败[/red]")
        raise typer.Exit(1)


@app.command()
def update(
    project_name: str = typer.Argument(..., help="项目名称"),
):
    """增量更新 Wiki 文档"""
    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    console.print("[yellow]增量更新功能开发中...[/yellow]")


@app.command()
def list_projects():
    """列出所有项目"""
    settings = Settings()
    config = settings.load_config()

    if not config.projects:
        console.print("[yellow]暂无项目[/yellow]")
        return

    table = Table(title="项目列表")
    table.add_column("名称", style="cyan")
    table.add_column("路径", style="green")
    table.add_column("语言", style="magenta")

    for project in config.projects:
        table.add_row(
            project.name,
            str(project.path),
            project.wiki.language,
        )

    console.print(table)


@app.command()
def config_llm(
    provider: str = typer.Option("openai", "--provider", "-p", help="LLM 提供商"),
    endpoint: str = typer.Option("https://api.openai.com/v1", "--endpoint", "-e", help="API endpoint"),
    api_key: str = typer.Option(..., "--api-key", "-k", help="API Key"),
    model: str = typer.Option("gpt-4", "--model", "-m", help="模型名称"),
    ca_cert: Optional[Path] = typer.Option(None, "--ca-cert", help="CA 证书路径"),
):
    """配置 LLM"""
    settings = Settings()

    llm_config = LLMConfig(
        provider=provider,
        endpoint=endpoint,
        api_key=api_key,
        model=model,
        ca_cert=ca_cert,
    )

    settings.update_default_llm(llm_config)

    console.print(Panel(
        f"[green]LLM 配置已保存[/green]\n\n"
        f"Provider: {provider}\n"
        f"Endpoint: {endpoint}\n"
        f"Model: {model}",
        title="Python Wiki",
    ))


@app.command()
def search(
    project_name: str = typer.Argument(..., help="项目名称"),
    query: str = typer.Argument(..., help="搜索查询"),
):
    """搜索 Wiki 内容"""
    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    console.print("[yellow]搜索功能开发中...[/yellow]")


@app.command()
def sync(
    project_name: str = typer.Argument(..., help="项目名称"),
):
    """同步到 Git"""
    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    console.print("[yellow]Git 同步功能开发中...[/yellow]")


@app.command()
def export(
    project_name: str = typer.Argument(..., help="项目名称"),
    output_format: str = typer.Option("markdown", "--format", "-f", help="输出格式 (markdown/html/pdf)"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录"),
):
    """导出 Wiki 文档"""
    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    console.print(f"[yellow]导出功能开发中... 格式: {output_format}[/yellow]")


if __name__ == "__main__":
    app()
