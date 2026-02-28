## 实现计划

### 1. 在 `WikiStorage` 类添加清空方法
**文件**: `src/pywiki/wiki/storage.py`

添加 `clear_all()` 方法：
- 删除语言目录下的所有文档
- 清空 `.history` 目录
- 重置 `.index.json` 索引文件

### 2. 在 `MainWindow` 添加清空按钮
**文件**: `src/pywiki/gui/main_window.py`

- 在工具栏添加 "🗑️ 清空Wiki" 按钮
- 添加 `_on_clear_wiki()` 方法处理清空逻辑
- 清空前弹出确认对话框
- 清空后刷新预览面板

### 3. 实现细节
- 清空按钮放在"增量更新"按钮旁边
- 点击后显示确认对话框，显示将要删除的目录路径
- 清空完成后显示成功提示并刷新UI