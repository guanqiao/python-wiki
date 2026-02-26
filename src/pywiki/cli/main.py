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
    """增量更新 Wiki"""
    import asyncio
    from pywiki.sync.change_detector import ChangeDetector
    from pywiki.sync.incremental_updater import IncrementalUpdater
    from pywiki.wiki.manager import WikiManager

    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("正在检测变更...", total=None)

        wiki_manager = WikiManager(
            project=project,
            llm_config=settings.default_llm,
            wiki_config=settings.wiki,
        )

        change_detector = ChangeDetector(project.path)

        updater = IncrementalUpdater(
            wiki_manager=wiki_manager,
            change_detector=change_detector,
            progress_callback=lambda p, m: progress.update(task, description=m),
        )

        result = asyncio.run(updater.update())

        if result.success:
            console.print(f"[green]增量更新完成[/green]")
            console.print(f"  更新文件: {len(result.updated_files)}")
            if result.failed_files:
                console.print(f"  失败文件: {len(result.failed_files)}")
                for path, error in result.failed_files[:5]:
                    console.print(f"    - {path}: {error}")
            console.print(f"  耗时: {result.duration_seconds:.2f}秒")
        else:
            console.print(f"[red]增量更新失败: {result.error}[/red]")
            raise typer.Exit(1)


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
    top_k: int = typer.Option(10, "--top", "-k", help="返回结果数量"),
    mode: str = typer.Option("hybrid", "--mode", "-m", help="搜索模式 (semantic/keyword/hybrid)"),
):
    """搜索 Wiki 内容"""
    import asyncio
    from pywiki.search.engine import SearchEngine, SearchQuery, SearchMode
    from pywiki.knowledge.vector_store import VectorStore

    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("搜索中...", total=None)

        wiki_dir = project.path / ".python-wiki" / "repowiki"
        persist_dir = project.path / ".python-wiki" / "search_index"

        search_engine = SearchEngine(
            persist_dir=persist_dir,
            openai_api_key=settings.default_llm.api_key,
            openai_api_base=settings.default_llm.endpoint,
        )

        mode_enum = {
            "semantic": SearchMode.SEMANTIC,
            "keyword": SearchMode.KEYWORD,
            "hybrid": SearchMode.HYBRID,
        }.get(mode, SearchMode.HYBRID)

        search_query = SearchQuery(
            query=query,
            mode=mode_enum,
            top_k=top_k,
            project_name=project_name,
        )

        results = asyncio.run(search_engine.search(search_query))

        progress.update(task, completed=True)

    if not results:
        console.print("[yellow]未找到匹配结果[/yellow]")
        return

    console.print(f"\n[green]找到 {len(results)} 个结果:[/green]\n")

    for i, result in enumerate(results, 1):
        console.print(Panel(
            f"{result.content[:500]}{'...' if len(result.content) > 500 else ''}",
            title=f"[cyan]{i}. {result.source}[/cyan] (得分: {result.score:.3f})",
            subtitle=f"级别: {result.level.value}",
        ))


@app.command()
def sync(
    project_name: str = typer.Argument(..., help="项目名称"),
    commit_message: Optional[str] = typer.Option(None, "--message", "-m", help="提交消息"),
):
    """同步到 Git"""
    from pywiki.sync.git_change_detector import GitChangeDetector

    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    wiki_dir = project.path / ".python-wiki" / "repowiki"

    if not wiki_dir.exists():
        console.print(f"[red]错误: Wiki 目录不存在，请先生成文档[/red]")
        raise typer.Exit(1)

    try:
        git_detector = GitChangeDetector(project.path)

        if not git_detector.repo:
            console.print("[red]错误: 项目不是 Git 仓库[/red]")
            raise typer.Exit(1)

        changes = git_detector.get_uncommitted_changes(
            include_untracked=False,
            file_patterns=["*.md"],
        )

        wiki_changes = [c for c in changes if wiki_dir in c.file_path.parents]

        if not wiki_changes:
            console.print("[green]没有需要同步的变更[/green]")
            return

        console.print(f"发现 {len(wiki_changes)} 个文档变更")

        from git import Repo

        repo = Repo(project.path)
        wiki_rel_path = wiki_dir.relative_to(project.path)

        for change in wiki_changes:
            rel_path = change.file_path.relative_to(project.path)
            if change.change_type.value in ("added", "modified"):
                repo.index.add([str(rel_path)])
                console.print(f"  暂存: {rel_path}")

        if commit_message:
            repo.index.commit(commit_message)
            console.print(f"[green]已提交: {commit_message}[/green]")
        else:
            console.print("[yellow]文件已暂存，使用 --message 提交[/yellow]")

    except Exception as e:
        console.print(f"[red]同步失败: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def export(
    project_name: str = typer.Argument(..., help="项目名称"),
    output_format: str = typer.Option("markdown", "--format", "-f", help="输出格式,
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="输出目录"),
):
    """导出 Wiki 文档"""
    import asyncio
    from pywiki.wiki.export import WikiExporter

    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    wiki_dir = project.path / ".python-wiki" / "repowiki"

    if not wiki_dir.exists():
        console.print(f"[red]错误: Wiki 目录不存在，请先生成文档[/red]")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(f"导出为 {output_format}...", total=None)

        exporter = WikiExporter(wiki_dir=wiki_dir, output_dir=output_dir)

        try:
            if output_format == "markdown":
                result_path = asyncio.run(exporter.export_markdown())
            elif output_format == "html":
                result_path = asyncio.run(exporter.export_html(single_file=True))
            elif output_format == "pdf":
                result_path = asyncio.run(exporter.export_pdf())
            else:
                console.print(f"[red]不支持的格式: {output_format}[/red]")
                raise typer.Exit(1)

            progress.update(task, completed=True)
            console.print(f"[green]导出成功: {result_path}[/green]")

        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]导出失败: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def sync_auto(
    project_name: str = typer.Argument(..., help="项目名称"),
    action: str = typer.Argument("start", help="操作 (start/stop/status)"),
    mode: str = typer.Option("hybrid", "--mode", "-m", help="同步模式 (manual/auto/hybrid)"),
):
    """管理自动同步服务"""
    from pywiki.sync.auto_sync_service import AutoSyncService, SyncMode, SyncStatus

    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    sync_mode = {
        "manual": SyncMode.MANUAL,
        "auto": SyncMode.AUTO,
        "hybrid": SyncMode.HYBRID,
    }.get(mode, SyncMode.HYBRID)

    from pywiki.sync.auto_sync_service import SyncConfig

    config = SyncConfig(mode=sync_mode)

    def on_sync(events):
        console.print(f"[dim]检测到 {len(events)} 个文件变更[/dim]")

    def on_status_change(status: SyncStatus):
        status_colors = {
            SyncStatus.IDLE: "green",
            SyncStatus.SYNCING: "yellow",
            SyncStatus.ERROR: "red",
            SyncStatus.PAUSED: "blue",
        }
        console.print(f"[{status_colors.get(status, 'white')}]状态: {status.value}[/{status_colors.get(status, 'white')}]")

    service = AutoSyncService(
        project_path=project.path,
        config=config,
        on_sync=on_sync,
        on_status_change=on_status_change,
    )

    if action == "start":
        if service.start():
            console.print(Panel(
                f"[green]自动同步服务已启动[/green]\n\n"
                f"项目: {project_name}\n"
                f"模式: {mode}\n"
                f"路径: {project.path}",
                title="Python Wiki Auto Sync",
            ))

            import time
            try:
                while service.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]正在停止服务...[/yellow]")
                service.stop()
                console.print("[green]服务已停止[/green]")
        else:
            console.print("[red]启动失败[/red]")
            raise typer.Exit(1)

    elif action == "stop":
        service.stop()
        console.print("[green]自动同步服务已停止[/green]")

    elif action == "status":
        state = service.get_state()
        stats = service.get_statistics()

        table = Table(title="自动同步状态")
        table.add_column("属性", style="cyan")
        table.add_column("值", style="green")

        table.add_row("运行状态", "运行中" if stats["running"] else "已停止")
        table.add_row("同步模式", stats["mode"])
        table.add_row("当前状态", state["status"])
        table.add_row("上次同步", state["last_sync_time"] or "从未")
        table.add_row("待处理变更", str(state["pending_changes"]))
        table.add_row("总同步次数", str(state["total_syncs"]))
        table.add_row("文件监控", "启用" if stats["watcher_active"] else "禁用")
        table.add_row("Git Hooks", ", ".join(stats["hooks_installed"]) or "无")

        console.print(table)

    else:
        console.print(f"[red]未知操作: {action}[/red]")
        console.print("可用操作: start, stop, status")
        raise typer.Exit(1)


@app.command()
def hooks_install(
    project_name: str = typer.Argument(..., help="项目名称"),
    force: bool = typer.Option(False, "--force", "-f", help="强制覆盖现有 hooks"),
):
    """安装 Git hooks"""
    from pywiki.sync.git_hooks import GitHooksManager, HookType

    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    manager = GitHooksManager(repo_path=project.path)

    if not manager.is_git_repo():
        console.print("[red]错误: 项目不是 Git 仓库[/red]")
        raise typer.Exit(1)

    results = manager.install_hooks(force=force)

    table = Table(title="Git Hooks 安装结果")
    table.add_column("Hook 类型", style="cyan")
    table.add_column("状态", style="green")

    for hook_type, success in results.items():
        status = "[green]已安装[/green]" if success else "[yellow]已跳过[/yellow]"
        table.add_row(hook_type.value, status)

    console.print(table)

    installed = manager.get_installed_hooks()
    console.print(f"\n当前已安装的 hooks: {[h.value for h in installed]}")


@app.command()
def hooks_uninstall(
    project_name: str = typer.Argument(..., help="项目名称"),
):
    """卸载 Git hooks"""
    from pywiki.sync.git_hooks import GitHooksManager

    settings = Settings()

    project = settings.get_project(project_name)
    if not project:
        console.print(f"[red]错误: 项目 '{project_name}' 不存在[/red]")
        raise typer.Exit(1)

    manager = GitHooksManager(repo_path=project.path)

    if not manager.is_git_repo():
        console.print("[red]错误: 项目不是 Git 仓库[/red]")
        raise typer.Exit(1)

    results = manager.uninstall_hooks()

    removed_count = sum(1 for success in results.values() if success)
    console.print(f"[green]已卸载 {removed_count} 个 hooks[/green]")


@app.command()
def hook_trigger(
    hook_type: str = typer.Argument(..., help="Hook 类型 (post-commit/post-merge/post-checkout)"),
    args: list[str] = typer.Argument(None, help="Hook 参数"),
):
    """内部命令: 由 Git hooks 调用触发同步"""
    from pathlib import Path
    from pywiki.sync.git_hooks import GitHooksManager, HookType

    repo_path = Path.cwd()

    try:
        hook_enum = HookType(hook_type)
    except ValueError:
        console.print(f"[red]未知的 hook 类型: {hook_type}[/red]")
        raise typer.Exit(1)

    manager = GitHooksManager(repo_path=repo_path)

    context = {}
    if args:
        if hook_enum == HookType.POST_COMMIT and args:
            context["commit_hash"] = args[0]
        elif hook_enum == HookType.POST_CHECKOUT and len(args) >= 2:
            context["from_branch"] = args[0]
            context["to_branch"] = args[1]

    result = manager.trigger_hook(hook_enum, context)

    if result.success:
        console.print(f"[dim]{result.output}[/dim]")
    else:
        console.print(f"[red]Hook 执行失败: {result.error}[/red]")


@app.command("generate-docs")
def generate_docs(
    project_name: str = typer.Argument(..., help="项目名称"),
    doc_types: Optional[str] = typer.Option(
        None, 
        "--types", "-t", 
        help="文档类型，逗号分隔 (overview,tech-stack,api,architecture,module,dependencies,configuration,development,database,tsd)"
    ),
    language: str = typer.Option("zh", "--language", "-l", help="文档语言 (zh/en)"),
):
    """生成项目文档（对标 Qoder Wiki）
    
    支持生成的文档类型：
    - overview: 项目概述
    - tech-stack: 技术栈文档
    - api: API 文档
    - architecture: 架构文档
    - module: 模块文档
    - dependencies: 依赖文档
    - configuration: 配置文档
    - development: 开发指南
    - database: 数据库文档
    - tsd: 技术设计文档
    """
    from pywiki.generators.docs.base import DocType
    from pywiki.config.models import Language

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

    selected_types: list[DocType] = []
    if doc_types:
        type_map = {
            "overview": DocType.OVERVIEW,
            "tech-stack": DocType.TECH_STACK,
            "api": DocType.API,
            "architecture": DocType.ARCHITECTURE,
            "module": DocType.MODULE,
            "dependencies": DocType.DEPENDENCIES,
            "configuration": DocType.CONFIGURATION,
            "development": DocType.DEVELOPMENT,
            "database": DocType.DATABASE,
            "tsd": DocType.TSD,
        }
        for t in doc_types.split(","):
            t = t.strip().lower()
            if t in type_map:
                selected_types.append(type_map[t])
    else:
        selected_types = list(DocType)

    lang = Language.ZH if language == "zh" else Language.EN

    console.print(Panel(
        f"[cyan]开始生成文档[/cyan]\n\n"
        f"项目: {project_name}\n"
        f"文档类型: {len(selected_types)} 种\n"
        f"语言: {language}",
        title="Python Wiki 文档生成",
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("生成文档...", total=len(selected_types))

        def update_progress(p):
            if p.get("completed_docs"):
                progress.update(task, completed=len(p["completed_docs"]))

        manager = WikiManager(project, llm_client, update_progress)

        async def run():
            return await manager.generate_docs(
                doc_types=selected_types,
                language=lang,
                progress_callback=update_progress,
            )

        result = asyncio.run(run())

    if result["success"]:
        console.print(f"\n[green]✓ 文档生成成功![/green]")
        console.print(f"  生成文件: {len(result['generated_files'])} 个")
        console.print(f"  耗时: {result['duration_seconds']:.2f} 秒")
        
        if result["generated_files"]:
            console.print("\n[cyan]生成的文件:[/cyan]")
            for file_path in result["generated_files"][:10]:
                console.print(f"  - {file_path}")
            if len(result["generated_files"]) > 10:
                console.print(f"  ... 还有 {len(result['generated_files']) - 10} 个文件")
        
        if result["failed_docs"]:
            console.print(f"\n[yellow]失败的文档: {result['failed_docs']}[/yellow]")
    else:
        console.print(f"[red]✗ 文档生成失败: {result['message']}[/red]")
        raise typer.Exit(1)


@app.command("list-doc-types")
def list_doc_types():
    """列出支持的文档类型"""
    from pywiki.wiki.manager import WikiManager
    from pywiki.config.models import ProjectConfig, WikiConfig, LLMConfig
    from pathlib import Path

    dummy_project = ProjectConfig(
        name="dummy",
        path=Path("."),
        llm=LLMConfig(api_key=""),
    )
    manager = WikiManager(dummy_project, None)
    doc_types = manager.get_supported_doc_types()

    table = Table(title="支持的文档类型")
    table.add_column("类型", style="cyan")
    table.add_column("描述", style="green")

    for dt in doc_types:
        table.add_row(dt["type"], dt["description"])

    console.print(table)


if __name__ == "__main__":
    app()
