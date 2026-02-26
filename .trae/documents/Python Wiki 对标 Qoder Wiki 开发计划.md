# Python Wiki 对标 Qoder Wiki 开发计划

## 总体路线图

**Phase 1 (P0) - 核心能力补齐** (39h)
- 自动化触发机制 (18h): FileWatcher + GitHooks + AutoSyncService
- 团队协作共享 (21h): KnowledgePackager + GitKnowledgeSync + TeamMemorySharing

**Phase 2 (P1) - 差异化功能** (55h)
- Quest 模式 (31h): SpecParser + TaskDecomposer + QuestEngine
- 智能问答增强 (24h): InlineChat + ContextEnricher增强 + CodeExplainer

**Phase 3 (P2) - 体验优化** (23h)
- 动态模型路由 (9h): ModelRouter
- 多语言扩展 (14h): Go/C# 解析器

**总计: 117小时**

## 关键差距对标

| 差距项 | Qoder | Python Wiki 现状 | 改进方案 |
|-------|-------|-----------------|---------|
| 自动化触发 | ✅ 自动 | ❌ 手动 | FileWatcher + GitHooks |
| 团队共享 | ✅ 支持 | ❌ 缺失 | GitKnowledgeSync |
| Quest 模式 | ✅ 支持 | ❌ 缺失 | QuestEngine |
| Inline Chat | ✅ 支持 | 🟡 基础QA | InlineChat组件 |
| 动态模型路由 | ✅ 支持 | ❌ 固定模型 | ModelRouter |

## 下一步行动

确认后将从 Phase 1.1 开始实施：
1. 添加 `watchdog` 依赖
2. 创建 `src/pywiki/sync/file_watcher.py`
3. 创建 `src/pywiki/sync/git_hooks.py`
4. 创建 `src/pywiki/sync/auto_sync_service.py`
5. 编写单元测试并集成到 CLI/GUI