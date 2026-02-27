## 计划：检查依赖、安装并运行 GUI

### 步骤 1: 检查 Poetry 是否安装
检查系统中是否已安装 Poetry，如果没有则需要安装。

### 步骤 2: 安装项目依赖
使用 Poetry 安装所有依赖：
```bash
cd d:\opensource\github\python-wiki
poetry install
```

### 步骤 3: 运行 GUI 应用
使用 Poetry 运行 GUI：
```bash
poetry run python -m pywiki.main
```
或者通过配置的脚本入口：
```bash
poetry run pywiki-gui
```

### 可能的依赖问题
- 如果 Poetry 未安装，需要先安装 Poetry
- PyQt6 在 Windows 上可能需要额外的系统依赖
- tree-sitter 相关包可能需要编译工具

请确认此计划后，我将开始执行。