# 智慧管理中心 (Echo) 知识库

> 最后更新：2026-07-11

## 快速导航

### 项目文档
- [[PRD]] - 产品需求文档
- [[ARCHITECTURE]] - 架构设计
- [[ALIYUN_DEPLOY]] - 部署指南

### 开发指南
- [[guides/setup]] - 环境搭建
- [[guides/coding-standards]] - 编码规范
- [[guides/deployment]] - 部署流程

### 模块文档
- [[modules/auth]] - 认证模块
- [[modules/articles]] - 文章模块
- [[modules/kiwi-sales]] - 猕猴桃销售
- [[modules/overtime]] - 加班记录
- [[modules/expenses]] - 记账模块

### 决策记录
- [[decisions/001-use-flask]] - 选择 Flask 框架
- [[decisions/002-sqlite-choice]] - 选择 SQLite

### 问题追踪
- [[BUG_FIX_LESSONS]] - Bug 修复经验
- [[bugs/]] - Bug 记录

### 审计报告
- [[AUDIT_REPORT]] - 安全审计
- [[TOKEN_OPTIMIZATION]] - Token 优化
- [[TEST_OPTIMIZATION_MASTER]] - 测试优化

---

## 项目概览

| 属性 | 值 |
|------|-----|
| 项目名称 | 智慧管理中心 (Echo) |
| 版本 | v2.5.7 |
| 技术栈 | Flask + Vanilla JS + SQLite |
| 主要文件 | `app.py`, `static/index.html` |

## 常用命令

```bash
# 启动服务
python app.py

# 运行测试
python test_api.py

# 安装依赖
pip install -r requirements.txt
```
