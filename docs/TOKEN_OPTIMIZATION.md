# Claude Code Token 优化指南

> 本文件约定 Claude Code 会话中的 token 消耗优化策略。每一条都会直接影响会话成本。
> 测试相关的专项优化见 `docs/TEST_TOKEN_OPTIMIZATION.md`。

---

## 一、CLAUDE.md 瘦身原则

CLAUDE.md 注入到**每一轮对话的 system prompt**，是最该省 tokens 的地方。

### ✅ 保留内容（不可逆约束）
- 端口、编码、路径等硬约束（违反则故障）
- 业务特定规则（违反则数据错误）
- 代码中无法直观推断的反模式
- 搜索入口关键字

### ❌ 删除内容（重复计费）
- 项目描述、概述段 → 压缩成一行
- 通用技术知识（JWT/SQLite/Flask 用法）→ 代码里有
- 架构描述 → 移到 ARCHITECTURE.md
- 设计文档引用 → 删（不走 CLAUDE.md）
- 显而易见的内容（上传路径、默认分类等）→ 代码里有
- 一次性历史记录（如"v2.2.0 修复了 XX"）→ 删

### 精简示例

```markdown
❌ 浪费版（70 行，~1800 token）
"智慧管理中心" (Echo) — a single-user Flask web app combining personal 
knowledge base, kiwi-sales order management, overtime tracking, 
and expense accounting. Version v2.2.1, MIT license.
......（大段描述）

✅ 节约版（20 行，~500 token）
# Echo — 单用户 Flask + 原生JS SPA，SQLite
## 命令
python app.py              # :5001
## 关键约束（违反则故障）
- 端口 5001（非 5000）
- SQLite 占位符 ?（非 %s）
......（只留约束）
```

**你的 CLAUDE.md 当前每轮消耗约 500 token，目标 ≤ 800 token。**

---

## 二、settings.json 配置规范

### 全局 settings.json（~/.claude/settings.json）

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "...",
    "ANTHROPIC_BASE_URL": "https://api.longcat.chat/anthropic",
    "ANTHROPIC_DEFAULT_FABLE_MODEL": "LongCat-2.0",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "LongCat-2.0",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "LongCat-2.0",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "LongCat-2.0",
    "ANTHROPIC_MODEL": "LongCat-Flash-Chat",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "6000"
  },
  "instructions": "默认中文回复，代码注释用中文。输出简洁：先结论后细节。不要重复显而易见的内容。",
  "includeCoAuthoredBy": false,
  "model": "sonnet",
  "theme": "light"
}
```

### 配置原则

| 字段 | 规范 |
|------|------|
| `instructions` | 放跨项目通用偏好（语言、输出格式），≤ 2 行，替代在各项目 CLAUDE.md 重复 |
| `env` | 只保留必要的代理/认证配置，删除冗余的 `_MODEL_NAME`（与 `_MODEL` 重复） |
| `includeCoAuthoredBy` | `false` — 避免每段输出附加 co-authored 元数据 |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | 按需要限制，防止单轮输出膨胀 |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | `"1"` — 禁止非必要网络流量 |

### 项目级 .claude/settings.local.json

- 只放**项目相关**的权限白名单
- 定期清理历史一次性命令（诊断、扫描等）
- 当前保留 5 条：python -c / test_api.py / echo / node -e / node --check

---

## 三、提示词工程规范

### 核心原则
**写给"执行者"而非"阅读者"** — 一句话能说清的，绝不写一段。

### ❌ 浪费 vs ✅ 节约 对比

| 场景 | ❌ 浪费写法 | ✅ 节约写法 |
|------|-----------|-----------|
| 修 bug | "我发现文章详情页打开的时候有一个问题..."（+200 token） | "修复文章详情页标题点击无响应 bug。检查 static/index.html 事件绑定。"（+30 token） |
| 查数据 | "能不能帮我查一下数据库里现在有多少条..." | `SELECT COUNT(*) FROM expenses; SELECT * FROM expenses LIMIT 5;` |
| 查代码 | "看看我们的认证逻辑哪里有问题" | "检查 app.py generate_token() 的 JWT 签名" |
| 新增功能 | "我想要一个导出功能，用户点击按钮后能..." | "新增 /api/kiwi-sales/export 路由，GBK 编码 CSV。" |

### 具体技巧

1. **用祈使句，砍掉礼貌用语和背景故事**
   ```
   ❌ "麻烦你帮我看一下这个登录逻辑为什么总是失败..."
   ✅ "诊断 POST /api/auth/login 返回 401 的原因。app.py:auth_login()"
   ```

2. **给出路径/行号，避免让 Claude 搜索**
   ```
   ❌ "看看认证逻辑哪里有问题"
   ✅ "检查 app.py generate_token() 的 JWT 签名，当前报错 'Invalid token'"
   ```

3. **指定精确输出格式，避免长篇解释**
   ```
   ❌ "帮我总结一下"
   ✅ "用 3 条 bullet 总结根因，不要解释过程"
   ✅ "只输出修改后的函数，不要解释"
   ```

4. **用结构化模板约束回答**
   ```
   回答格式：
   ## 结论
   ## 修改文件
   ## 风险
   其他一律不写
   ```

---

## 四、工具与代理调度策略

### 按任务分级选工具

| 任务复杂度 | 正确工具 | 例子 |
|-----------|---------|------|
| 查一个值/一行代码 | **直接给位置** | "读 app.py:88" |
| 搜一个关键字 | **Grep** | "grep login_required" |
| 找一类文件 | **Glob** | "有哪些 .py 文件" |
| 理解跨 3+ 文件的流程 | **Agent @Explore** | "梳理认证流程" |
| 多文件改动 | **Agent** | "重构 X 模块" |

### 常见浪费场景

| 坑 | 浪费方式 | 省法 |
|----|---------|------|
| 全文件 Read | Read 整个 app.py（1532 行） | Grep 定位行号再 Read 指定范围 |
| 多重 Agent 展开 | 5 个 Agent 各读同一文件 | 1 个 Explore 读完 SendMessage 转交 |
| 搜完再搜 | Claude Grep 找不到换关键词再搜 | 直接告诉 `-n` 参数和文件路径 |
| 大 diff 分析 | "review 整个分支" 全量 load | 先 `git diff --stat` 锁定文件再评 |

### 黄金原则
- **永远不要**让 Claude 读取你已经知道内容的文件
- 你明确知道位置 → 直接给 `file:line`
- 不确定在哪 → 说"用 Grep 搜关键词 X"
- 跨文件重构 → 用 Agent 的 `@Explore` 模式做只读扫描

---

## 五、模型选择策略

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 语法级小改动（修 typo、加日志） | Haiku 4.5 | 速度最快，成本最低 |
| 常规功能开发 | Sonnet | 性价比最佳 |
| 复杂架构/多文件重构 | Opus | 避免多次返工反而省 token |
| Code Review / 安全检查 | Sonnet 足够 | 不需要最高推理 |

### 关键原则
> **用例复杂度匹配模型等级，既不过度也不低估。**

---

## 六、工作流瘦身

### 1. 避免大型 workflow 展开子任务
```
❌ "帮我加个导出按钮" → 启动 5 个 worktree 子代理
✅ 让主 Agent 直接改 3 行代码
```

### 2. 合理使用 Plan Mode
```
❌ "改个按钮颜色" → 先 plan 5 分钟 → 再执行
✅ Plan Mode 只用于多方案权衡、重大重构、不确定影响范围时
```

### 3. 控制 message 累积（关键！）

| 命令 | 作用 | 何时用 |
|------|------|--------|
| `/compact` | 压缩对话历史为摘要 | 每完成一个大功能后、context 过长时 |
| `/clear` | 清空历史 | 切换话题时 |
| `/cost` | 查看当前用量 | 定期监控 |
| `/model` | 切换模型 | 任务类型变化时 |

**最佳实践流程：**
```
开始会话
  → 完成功能 A → /compact 压缩
  → 完成功能 B → /compact 压缩
  → 切换到新话题 → /clear 清空
  → 每 10 分钟看一次 /cost，了解消耗分布
```

### 4. 任务分割：用新会话隔离无关工作
```
❌ 一个会话里既做前端美化又做后端重构又做数据库迁移
✅ 一个会话做一个明确任务，做完 /compact 或开新会话
```

---

## 七、具体可操作 Tricks

### Trick 1：打断（Esc）——立即止损
当你看到 Claude 开始长篇大论、读大量不相关文件、或者走向错误方向时：
```
按 Esc 立即打断
用更精确的指令重新引导
```
成本：已消耗的 token 不可挽回，但避免后续 10 轮浪费。

### Trick 2：复用已有结果，禁止重复读取
```
❌ "帮我看看 app.py"（第 3 次了）→ Claude 重新 Read 整个文件
✅ "参考之前读的 app.py 第 450 行代码，修改其中的判断逻辑"
```

### Trick 3：偏好声明放在 settings.json，不是每轮重复
```
❌ 每轮都说："回复请用中文，输出简洁"
✅ 在全局 settings.json 的 instructions 里写一次
```

### Trick 4：用注释而非外部文档
```
❌ 把设计思路写在对话里
✅ 在代码注释里写设计思路（代码被 Read 时自然看到）
```

### Trick 5：精确行号 + 路径，不给搜索空间
```
❌ "看看认证模块"（Claude 要搜索整个项目）
✅ "检查 app.py:120 generate_token 和 app.py:135 login_required"
```

---

## 八、总结：Token 优化检查清单

| # | 检查项 | 节省量级 |
|---|--------|---------|
| 1 | CLAUDE.md 精简到 30 行以内 | 高 |
| 2 | 每次 prompt 砍掉礼貌/背景，只留指令 | 中 |
| 3 | 给出文件:行号，避免自由搜索 | 高 |
| 4 | Grep/Glob 优先于全文件 Read | 高 |
| 5 | 每完成功能就 /compact | 极高 |
| 6 | 切换话题用 /clear | 高 |
| 7 | 用 /cost 监控，发现异常立即调整 | 中 |
| 8 | 简单任务用 haiku，复杂用 sonnet/opus | 高 |
| 9 | 不在会话里混合无关任务 | 高 |
| 10 | 错误方向立即 Esc 打断 | 中 |

### 最终对比

| 指标 | 优化前会话 | 优化后会话 |
|------|-----------|-----------|
| 每轮 context | ~8000 token (CLAUDE.md + 历史) | ~3000 token |
| 典型任务轮数 | 15-20 轮 | 5-8 轮 |
| 单次任务总消耗 | ~120k-160k token | ~15k-20k token |
| 节省 | — | **80-90%** |

---

## 九、本项目专属快捷约定

### 常用搜索入口
`init_db`, `generate_token`, `login_required`, `UPLOAD_FOLDER`, `REPORT_PAGE_SIZE`, `calculate_overtime_duration`, `getAuthHeaders`

### 项目 CLAUDE.md 精简版（当前生效）
```markdown
# 智慧管理中心 (Echo) — 单用户 Flask + 原生JS SPA，SQLite

## 命令
python app.py              # :5001
python test_api.py         # smoke test（需服务运行中）
pip install -r requirements.txt

## 关键约束（违反则故障）
- 端口 5001（非 5000）
- SQLite 占位符 ?（非 %s）
- CSV 导出必须 GBK + UTF-8 BOM
- init_db() 只接受 ALTER TABLE ADD COLUMN；仅 __main__ 时运行
- JWT 7天过期；路由 @login_required；所有查询必加 WHERE user_id=?
- 上传文件扩展名白名单 png/jpg/jpeg/gif/webp

## 业务规则
- 加班：工作日 19:00-23:59；周末 09:00-23:00 扣午休 2h；同日唯一约束

## 前后端入口
- 后端 app.py（get_db() 存 g，rows = sqlite3.Row）
- 前端 static/index.html（API_URL='/api'，token=localStorage，REPORT_PAGE_SIZE=10）
```

---

> 💡 **最重要的一句话：每一轮对话都会重发全部历史 + CLAUDE.md。省 token 的核心不是少说话，而是让 Claude 用最少轮数、最小工具输出（Grep 而非 Read）完成精确任务，并在完成后立即 /compact 压缩历史。**

## 相关链接
- [[architecture/overview]] - 系统架构总览
- [[TEST_OPTIMIZATION_MASTER]] - 测试优化指南
- [[TEST_TOKEN_OPTIMIZATION]] - 测试 Token 优化
- [[guides/coding-standards]] - 编码规范
- [[BUG_FIX_LESSONS]] - Bug 修复经验
