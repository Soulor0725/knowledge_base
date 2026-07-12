# 智慧管理中心 (Smart Management Center)

一个基于 Flask 和 JavaScript 的综合管理系统，包含个人知识库、猕猴桃销售管理和消费记录管理功能。


## 当前版本

**v2.5.9**
> 修复：加班记录编辑时分钟显示为空的问题（分钟下拉框从 00/15/30/45 改为 00-59 全部选项）。

## ✨ 功能特性

### 📚 知识库模块
- **Markdown 编辑器**：支持 Markdown 语法，包含预览功能
- **代码高亮**：支持多种编程语言的代码块高亮显示
- **图片上传**：支持在文章中插入图片
- **用户认证**：支持用户注册、登录和个人资料管理
- **分类管理**：支持文章分类，可创建和删除分类
- **文章管理**：支持创建、编辑、删除文章
- **收藏功能**：支持收藏文章
- **搜索功能**：支持文章标题和内容搜索
- **导航功能**：支持上一篇/下一篇文章导航
- **浏览统计**：记录文章浏览次数
- **响应式设计**：适配不同屏幕尺寸
- **工作日报适配**：在「工作日报」分类下，界面文案自动切换为「日报」（v2.2.0）

### 🍋 猕猴桃销售模块
- **订单管理**：支持创建、编辑、删除销售订单
- **规格选择**：支持5斤装、10斤装规格备注
- **数量管理**：记录销售数量
- **金额统计**：记录支付金额，保留2位小数
- **状态管理**：支持已发货、未发货状态
- **运单管理**：支持记录运单号码
- **物流查询**：点击运单号直接跳转快递100查询物流信息（v2.5.0）
- **导出功能**：支持导出订单到Excel（CSV格式）
  - 支持多选导出
  - 支持全选导出
  - 无选择时按所选日期/全量导出
  - 编码完美支持Excel（GBK编码）
- **批量删除**：支持批量删除订单
- **报表统计**：
  - 按客户分组统计
  - 按规格汇总统计
  - 总数量和总金额统计
  - 分页显示，每页10个客户

### 📋 消费记录模块
- **记录管理**：支持创建、编辑、删除消费记录（默认当天本地日期，UTC+8 已验证）
- **分类管理**：支持多种消费分类（燃气费、电费、话费、网费、香烟、菜肉米面油、交通、物业费、水果、其他）
- **日消费视图**：列表页支持按具体某天筛选，顶部"合计"栏实时展示所选日期金额与笔数（独立聚合接口，无视分页）
- **月度统计**：独立"消费统计"侧边栏入口，按分类汇总、饼图、年度月度趋势筛选（与日视图互补）
- **金额统计**：记录消费金额，保留2位小数；所选日期自动汇总
- **日期管理**：记录消费日期
- **导出功能**：支持导出记录到Excel（CSV格式）
  - 支持多选导出
  - 支持全选导出
  - 无选择时按所选日期/全量导出
  - 编码完美支持Excel（GBK编码）

### ⏰ 加班管理模块
- **加班记录**：支持平时加班（19:00-23:59）和周末加班（09:00-23:00）
- **自定义时间选择器**：下拉框选择小时/分钟，横线分隔显示，完美适配深色主题
- **时长计算**：自动计算加班时长，支持手动修改
- **月度统计**：按自然月统计平时/周末加班时长和记录数
- **周期统计**：按上月21日至本月20日周期统计加班时长
- **同日唯一**：同一天只能有一条加班记录
- **批量删除**：支持批量删除加班记录

## 🛠️ 技术栈

- **后端**：Python Flask（模块化架构，Blueprint）
- **前端**：HTML5, CSS3, JavaScript（SPA）
- **数据库**：SQLite（WAL 模式）
- **Markdown 解析**：Marked.js
- **代码高亮**：CodeMirror + highlight.js
- **图标**：Font Awesome
- **知识库**：Obsidian

## 📦 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/Soulor0725/knowledge_base.git
cd knowledge_base
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 初始化数据库

运行应用时会自动创建数据库文件。

### 4. 启动服务

#### 方法 1：直接运行

```bash
python app.py
```

#### 方法 2：使用批处理脚本

```bash
# Windows
start.bat

# 或自动启动脚本
auto_start.bat
```

## 🌐 访问方式

- **本地访问**：http://localhost:5001
- **内网访问**：http://[你的IP地址]:5001

## 📝 使用指南

### 知识库模块

#### 1. 用户注册/登录

- 首次访问时，点击右上角的"登录"按钮
- 点击"注册"标签页，填写用户名、密码和中文名字
- 注册成功后自动登录

#### 2. 创建文章

- 点击"+ 新建"按钮
- 填写标题、选择分类、添加标签
- 在编辑器中编写 Markdown 内容
- 点击"保存"按钮保存文章
- 点击"保存草稿"按钮保存为草稿

#### 3. 编辑文章

- 在文章列表中点击文章标题进入详情页
- 点击"编辑"按钮
- 修改内容后点击"保存"按钮

#### 4. 管理分类

- 点击左侧分类区域的"+"按钮添加分类
- 右键点击分类名称删除分类

#### 5. 搜索文章

- 在顶部搜索框输入关键词
- 点击搜索按钮或按回车键

#### 6. 个人资料管理

- 点击右上角的"编辑资料"按钮
- 修改中文名字
- 上传头像
- 点击"保存"按钮

### 猕猴桃销售模块

#### 1. 创建订单

- 在左侧菜单点击"销售订单"
- 点击"+ 新增订单"按钮
- 填写客户名称、运单号码
- 选择规格（5斤装/10斤装）
- 输入数量和支付金额
- 选择发货状态（已发货/未发货）
- 点击"保存"按钮

#### 2. 编辑订单

- 在订单列表中点击"编辑"按钮
- 修改订单信息后点击"保存"

#### 3. 删除订单

- 勾选要删除的订单
- 点击"删除选中"按钮

#### 4. 导出订单

- 点击"导出Excel"按钮
- 系统会自动下载CSV格式的订单文件

#### 5. 查看报表

- 点击"销售报表"菜单
- 查看按客户分组的统计数据
- 查看按规格汇总的统计数据
- 使用分页控件浏览更多客户

## 📁 项目结构

```
knowledge_base/
├── app.py                     # Flask 入口（139行）
├── config.py                  # 配置常量
├── db.py                      # 数据库管理（init_db / get_db）
├── auth_utils.py              # 认证工具（JWT / login_required）
├── utils.py                   # 通用工具函数
├── cache.py                   # 缓存系统（thread-safe）
├── routes/                    # 路由模块（Blueprint 星型拓扑）
│   ├── __init__.py            # 蓝图定义（12行）
│   ├── auth.py                # 认证路由（185行）
│   ├── articles.py            # 文章路由（420行）
│   ├── kiwi_sales.py          # 猕猴桃销售路由（421行）
│   ├── overtime.py            # 加班记录路由（334行）
│   └── expenses.py            # 消费记录路由（352行）
├── static/
│   ├── index.html             # 前端单文件 SPA（~6000 行）
│   ├── favicon.ico
│   └── uploads/               # 用户上传的图片（png/jpg/webp）
├── docs/                      # Obsidian 知识库（已 git 追踪）
│   ├── index.md               # 知识库首页
│   ├── ARCHITECTURE.md        # 架构总览（34KB）
│   ├── PRD.md                 # 产品需求文档（37KB）
│   ├── INTERACTION_DESIGN.md  # 交互设计（18KB）
│   ├── BUG_FIX_LESSONS.md     # Bug 修复经验沉淀（17KB）
│   ├── AUDIT_REPORT.md        # 审计报告（16KB）
│   ├── ALIYUN_DEPLOY.md       # 阿里云部署指南
│   ├── PLAYWRIGHT_SETUP.md    # E2E 测试搭建
│   ├── TOKENT_*.md            # Token 优化系列（3 篇）
│   ├── TEST_*.md              # 测试优化系列（2 篇）
│   ├── architecture/          # 架构图集（overview）
│   ├── modules/               # 模块文档（auth/articles/kiwi/overtime/expenses）
│   ├── decisions/             # 决策记录 ADR（001-flask / 002-sqlite）
│   ├── guides/                # 开发指南（setup/coding-standards/deployment）
│   ├── templates/             # 文档模板（ADR/Bug/模块/会议）
│   ├── bugs/                  # Bug 归档
│   ├── meetings/              # 会议记录
│   └── research/              # 技术调研
├── .obsidian/                 # Obsidian vault 配置（本地，gitignore）
│   ├── plugins/obsidian-git/  # Git 自动同步插件 v2.38.6
│   └── data.json              # 自动 commit+push 配置
├── tests/                     # pytest 测试套件
│   ├── conftest.py            # 共享 fixture
│   ├── test_security.py       # 安全测试
│   ├── test_performance.py    # 性能测试
│   ├── test_smoke.py          # P0 冒烟
│   ├── test_utils.py          # 工具测试
│   └── test_fault_tolerance.py # 容错测试
├── scripts/                   # 辅助脚本
│   ├── generate_api_test_excel.py
│   ├── generate_test_excel.py
│   └── generate_merged_excel.py
├── .github/                   # GitHub 配置（copilot / workflows）
├── knowledge_base.db          # SQLite 数据库（运行时生成）
├── requirements.txt           # Python 依赖
├── CLAUDE.md                  # Claude Code 项目约束
├── AGENTS.md                  # AI 协作指引
├── CODE_QUALITY_REPORT.md     # 代码质量报告
├── PERFORMANCE_AUDIT.md       # 性能审计报告
├── RELEASE_NOTES.md           # 发布说明（v2.1→v2.2）
├── VERSION.md                 # 完整版本历史（v1.0→v2.5.8）
├── start.bat / auto_start.bat # Windows 启动脚本
├── deploy.sh / update.sh      # 部署脚本
├── smoke_test.py              # 快速冒烟测试
├── locustfile.py              # Locust 压测脚本
└── test_*.py                  # 根目录测试脚本
```

## 🔄 自动同步

通过 Obsidian **Git 插件**（obsidian-git v2.38.6）实现知识库自动版本控制：

- **触发**：每 5 分钟自动 commit，每 30 分钟自动 push
- **远端**：`https://github.com/Soulor0725/knowledge_base.git`（master 分支）
- **范围**：整个仓库（代码 + docs/ 文档统一提交）
- **提示**：状态栏图标 + toast 通知（commit/push/pull/冲突）
- **配置**：`.obsidian/plugins/obsidian-git/data.json`

## 📝 版本历史

完整版本历史请查看 [VERSION.md](VERSION.md)（v1.0.0 → v2.5.8）。
发布说明（v2.1.0 → v2.2.1）另见 [RELEASE_NOTES.md](RELEASE_NOTES.md)。

## 🔧 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SECRET_KEY | JWT 密钥 | 随机生成 |

### 端口配置

默认端口为 5001，可在 `app.py` 中修改。

### 数据库配置

默认使用 SQLite 数据库，数据库文件为 `knowledge_base.db`，配置在 `config.py` 中。

### 分页配置

各模块分页默认每页5条，可配置在 `config.py` 中。


## 安全修复 (v2.5.5)

2026-07-09 全面安全审计修复 16 项问题：

| 优先级 | 修复内容 |
|--------|---------|
| P0 | 全局缓存并发读写加锁 |
| P0 | batch-delete id 整数类型校验 |
| P0 | CSV 导出 sanitize_csv_field 防注入 |
| P0 | views 自增异常 logger.warning |
| P1 | 前端 3 处 escapeHtml() XSS 遗漏 |
| P1 | 文件上传 magic bytes 校验 |
| P1 | kiwi CSV generator 空行 bug |
| P1 | datetime.now() 改为 UTC 时区 |
| P2 | 抽取 kiwi 重复校验为辅助函数 |

详见 AGENTS.md 的 Bug Fix 经验教训部分。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 联系

- GitHub: [Soulor0725](https://github.com/Soulor0725)

---

**✨ 开始使用你的智慧管理中心吧！** ✨

