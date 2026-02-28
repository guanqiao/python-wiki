## 问题分析

通过分析已生成的文档 `D:\opensource\ruoyi-vue-pro-master-jdk17\.python-wiki\repowiki\zh\03-Modules\index.md`（1.3MB），发现以下问题：

### 当前问题

1. **模块列表过于琐碎**：3509个模块被平铺列出，每个模块只包含1个类，导致文档巨大且难以阅读
2. **缺乏层次结构**：仅按首字母分组（cn, com, org等），没有按业务功能或架构层次聚合
3. **信息重复冗余**：每个模块都显示"1个类"、"0方法"等重复统计
4. **缺乏高阶抽象**：没有展示模块间的关系、职责边界、业务领域划分

### 改进方案

#### 1. 多级分组聚合（核心改进）
- **按业务领域分组**：识别模块的业务领域（如 tenant、dict、excel、quartz 等）
- **按架构分层分组**：presentation、business、data、infrastructure
- **按功能模块分组**：core、config、util、validation 等

#### 2. 抽象层次提升
- **包级别摘要**：为每个子包生成摘要描述，而非列出每个类
- **职责归纳**：自动归纳一组相关类的共同职责
- **依赖关系聚合**：展示包间的依赖关系而非类间依赖

#### 3. 智能过滤与折叠
- **隐藏内部实现细节**：过滤掉仅包含1个类且无实质内容的琐碎模块
- **提供折叠视图**：默认展示聚合视图，允许展开查看详情
- **重要性排序**：按模块复杂度、依赖度排序

#### 4. 可视化增强
- **包结构树形图**：展示模块的层级关系
- **领域边界图**：展示业务领域划分
- **依赖热力图**：展示模块间耦合度

### 具体修改计划

#### 阶段1：改进模块分组逻辑
**文件**: `src/pywiki/generators/docs/module_generator.py`
- 修改 `_generate_index_content` 方法
- 实现多级分组：先按业务领域，再按架构分层
- 添加包摘要生成功能

#### 阶段2：添加抽象摘要生成
**文件**: `src/pywiki/generators/docs/module_generator.py`
- 新增 `_generate_package_summary` 方法
- 基于类名、文档字符串归纳包职责
- 统计包内关键指标（类数量、公共API数量等）

#### 阶段3：优化模板展示
**文件**: `src/pywiki/generators/docs/templates/module.md.j2`
- 修改模块列表展示方式
- 添加折叠/展开支持
- 优化统计信息展示

#### 阶段4：增强包分析器
**文件**: `src/pywiki/analysis/package_analyzer.py`
- 添加业务领域检测功能
- 改进架构分层检测
- 添加包职责推断

### 预期效果

改进后的文档结构示例：
```markdown
# 模块文档

## 概述
- 模块总数：3509
- 业务领域：12个（租户、字典、Excel、定时任务...）

## 业务领域

### 租户管理 (tenant)
**职责**: 多租户数据隔离、租户上下文管理
**包含模块**: 15个包，120个类
**核心类**: TenantContext、TenantMQInterceptor...

#### 核心模块 (core)
- **职责**: 租户上下文和拦截器
- **类数量**: 8
- **主要功能**: MQ消息拦截、Redis隔离

#### MQ集成 (mq)
- **Kafka支持**: TenantKafkaInterceptor...
- **RabbitMQ支持**: TenantRabbitMQInitializer...

### 字典管理 (dict)
...
```

相比当前的平铺列表，新结构将信息密度提升10倍以上，更易于理解系统架构。