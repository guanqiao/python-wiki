## 实现计划

### 1. 修改 `DocGeneratorThread` 类 (main_window.py)
- 添加 `_is_paused` 标志和 `_pause_event` asyncio.Event
- 添加 `pause()` 方法：设置暂停标志，等待恢复
- 添加 `resume()` 方法：清除暂停标志，继续执行
- 增强 `cancel()` 方法：同时清除暂停状态
- 在生成循环中添加暂停检查点

### 2. 修改 `ProgressPanel` 类 (progress_panel.py)
- 将单个"取消"按钮改为"暂停"和"终止"两个按钮
- 添加 `pause_requested` 和 `resume_requested` 信号
- 添加暂停状态显示（按钮文字切换：暂停/继续）
- 添加 `_is_paused` 状态跟踪

### 3. 修改 `MainWindow` 类 (main_window.py)
- 连接暂停/恢复信号到线程控制
- 添加 `_on_pause_generation()` 方法
- 添加 `_on_resume_generation()` 方法
- 处理暂停/恢复状态变化

### 4. 按钮布局设计
```
[暂停/继续] [终止]
```
- 暂停按钮：点击后变为"继续"，再次点击恢复
- 终止按钮：红色，直接终止生成

### 5. 状态管理
- 正常状态：显示"暂停"和"终止"按钮
- 暂停状态：显示"继续"和"终止"按钮，进度条变为黄色
- 完成/错误状态：隐藏所有按钮