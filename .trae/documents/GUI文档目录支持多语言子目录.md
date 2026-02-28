## 实现计划

修改 `src/pywiki/gui/panels/preview_panel.py` 文件：

### 1. 修改 `_load_document_list` 方法
- 检测 wiki 目录下是否存在语言子目录（`zh/`、`en/` 等）
- 如果存在多语言目录：
  - 创建语言节点作为顶级节点（如 "🌐 中文 (zh)"、"🌐 English (en)"）
  - 每个语言节点下显示该语言的文档树结构
- 如果不存在多语言目录：
  - 保持原有行为，直接显示文档树

### 2. 添加语言显示名称映射
- 添加辅助方法将语言代码转换为友好的显示名称
- `zh` → "中文", `en` → "English"

### 3. 目录树结构示例
```
📁 文档根目录
├── 🌐 中文 (zh)
│   ├── 📁 01-Overview
│   │   └── 📄 README.md
│   └── 📁 02-Architecture
│       └── 📄 README.md
└── 🌐 English (en)
    ├── 📁 01-Overview
    │   └── 📄 README.md
    └── 📁 02-Architecture
        └── 📄 README.md
```