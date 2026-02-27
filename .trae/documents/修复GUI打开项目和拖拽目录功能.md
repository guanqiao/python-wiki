## 修复计划

### 问题1：完善打开项目功能
修改 `main_window.py` 的 `_on_open_project()` 方法：
- 选择目录后，使用目录名作为默认项目名
- 创建 `ProjectConfig` 并添加到配置
- 设置为当前项目并刷新列表

### 问题2：实现拖拽目录功能
在 `MainWindow` 类中添加：
- `setAcceptDrops(True)` 启用拖拽
- `dragEnterEvent()` 接受文件/目录拖入
- `dropEvent()` 处理目录放下，调用打开项目逻辑