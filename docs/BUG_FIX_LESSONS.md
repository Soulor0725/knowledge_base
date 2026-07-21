# Echo 系统升级 Bug 修复经验沉淀

> 从 Git 历史中提取，覆盖 v2.1.0 → v2.5.7 全部修复提交。目标：让同样的 bug 不再出现，让排查路径可复用。

---

## 一、数据库连接类

### 🔴 Bug #1：数据库连接泄漏 → `database is locked` 500

- **版本**：v2.2.0
- **现象**：高并发或连续操作时 500，日志报 `database is locked`
- **根因**：`get_db()` 把连接存进 `flask.g`，但**从未注册 `teardown_appcontext`** 来关闭。连接堆积，SQLite 文件锁争抢
- **修复**：
  ```python
  @app.teardown_app
  def close_db(e=None):
      db = g.pop('db', None)
      if db is not None:
          db.close()
  ```
- **教训**：
  - 任何存 `g` 的资源（连接、文件句柄）**必须**注册 `teardown_appcontext`
  - SQLite 单文件写串行，连接越少越好 — 请求结束立刻还
  - 搜索关键词：`database is locked`、`too many connections` → 先查连接关闭

### 🔴 Bug #2：`int()` 强转失败导致 500

- **版本**：v2.5.3 (ca0d6ce)
- **现象**：统计接口在某些参数下 500
- **根因**：`params.append(int(start_month))` — 参数是字符串 `"2026-07"` 时 `int()` 抛 `ValueError`
- **修复**：去掉多余 `int()`，直接 `params.append(start_month)`；前端已限定格式
- **教训**：
  - 不要把 `int()`/`float()` 当"类型保险"用 — 异常会直接 500
  - 入参校验集中在边界（路由入口），不在 SQL 拼接处强转

---

## 二、用户输入校验类

### 🔴 Bug #3：空 `.strip()` 抛 NoneType 异常

- **版本**：v2.3.0
- **现象**：注册/登录提交空字段时 500
- **根因**：`data.get('username').strip()` — `get` 返回 `None` 时调 `.strip()` 抛 `AttributeError`
- **修复**：`(data.get('username') or '').strip()`
- **教训**：
  - **所有** `request.json.get(k)` 做 `.strip()`/`.lower()` 前都要 `or ''` 兜底
  - 模板：`(data.get('field') or '').strip()`
  - 注册/登录/文章在 v2.3.0 一并修，说明这是**模式性问题**非单点

### 🔴 Bug #4：分类名未校验 → XSS / SQL 注入入口

- **版本**：v2.3.0
- **现象**：数据库里发现含 `<script>` 的分类名
- **根因**：创建分类时只查长度，没查特殊字符
- **修复**：
  ```python
  if len(name) > 50:
      return jsonify({'error': '分类名称不能超过50个字符'}), 400
  import re
  if re.search(r'[<>"\'&]', name):
      return jsonify({'error': '分类名称不能包含特殊字符'}), 400
  ```
- **教训**：
  - 所有用户输入字段**三件套**：必填检查 + 长度限制 + 字符白名单/黑名单
  - SQLite 是用 `?` 占位防注入，但 XSS 仍靠前端渲染转义 — 双端都要校

---

## 三、数据迁移/结构类

### 🔴 Bug #5：CSV 导出编码错误（乱码）

- **版本**：v2.1.0
- **现象**：导出的 CSV 在 Excel（中文 Windows）里打开乱码
- **根因**：早期用 UTF-8 写 CSV，中文 Windows Excel 默认用 GBK 读
- **修复**：GBK 编码 + UTF-8 BOM（前面已修正为 GBK + BOM）
  ```python
  response.headers['Content-Type'] = 'text/csv; charset=gbk'
  # 写入 UTF-8 BOM 头让 Excel 识别
  ```
- **教训**：
  - **中文 Windows Excel 只认 GBK**，UTF-8 CSV 必乱码
  - 导出文件命名用 `secure_filename` + ASCII，避免中文路径
  - 测试方法：中文 Windows 双击打开，不用其它工具验证

### 🔴 Bug #6：分类删除后侧栏残留 + 文章成孤儿

- **版本**：v2.2.3
- **现象**：删除分类后，侧栏的分类名仍在；该分类下的文章在 DB 里 category 字段为已删名字
- **根因**：`DELETE FROM categories` 时没把引用该分类的文章重定向到"未分类"
- **修复**：
  ```python
  cursor.execute("UPDATE articles SET category = '未分类'
                 WHERE category = ? AND user_id = ?", (cat_name, g.user_id))
  ```
- **教训**：
  - **删除有外键意义的字段时**，必须同步更新所有引用行
  - 修复后加"Where user_id" — 修复不能破坏多用户隔离
  - 手动 SQL 验证流程：`SELECT * FROM articles WHERE category='已删名'`

---

## 四、前端/UI 类

### 🔴 Bug #7：弹窗关闭后页面滚动锁死

- **版本**：v2.5.3 / ca0d6ce
- **现象**：登录/注册弹窗关闭后，背景页面无法滚动
- **根因**：弹窗打开时设 `document.body.style.overflow = 'hidden'`，关闭时**忘了还原**
- **修复**：
  ```javascript
  document.body.style.overflow = '';   /* 关闭时还原 */
  ```
- **教训**：
  - 所有"打开时修改 body 样式"的代码，必须在**所有关闭路径**（点击遮罩、ESC、登录成功、注册成功、点X）都还原
  - 搜索技巧：搜 `overflow = 'hidden'` → 确认对称位置有清空

### 🔴 Bug #8：新建记录默认日期缺失 → 修复引入 UTC 时区回归

- **版本**：v2.5.4（初修）/ v2.5.7（回归修复）
- **v2.5.4 现象**：猕猴桃订单、加班记录、消费记录的日期输入框为空，要手动选
- **v2.5.4 根因**：新建逻辑没填默认值，编辑逻辑也没处理 `!id` 分支
- **v2.5.4 修复（有缺陷）**：
  ```javascript
  // ❌ 有缺陷的写法 —— toISOString() 返回 UTC 日期
  if (!id) {
      _$('kiwiOrderDate').value = new Date().toISOString().slice(0, 10);
      _$('overtimeDate').value   = new Date().toISOString().slice(0, 10);
  }
  _$('expenseDate').value = new Date().toISOString().slice(0, 10); // 消费记录
  ```
- **v2.5.7 回归现象**：北京时间 00:00–07:59 新建记录时，默认日期显示为**昨天**。任选一个模块选昨天后，其他模块新建也变成昨天（看似"跨模块污染"，实为三处独立的同一个错误写法各自算出同一个错误结果）
- **v2.5.7 根因**：`Date.prototype.toISOString()` 返回 **UTC** 日期，不返回本地日期。中国在 UTC+8，本地 08:00 前 UTC 时钟仍指向前一天 → `slice(0,10)` 截出的是昨天
- **v2.5.7 修复**：统一抽取本地时间构造器，替换全部 `toISOString` 用法
  ```javascript
  /** 本地时间 YYYY-MM-DD（禁止使用 toISOString） */
  function todayLocalISO(d = new Date()) {
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${y}-${m}-${day}`;
  }
  // 三个模块统一调用
  _$('kiwiOrderDate').value = todayLocalISO();
  _$('expenseDate').value    = todayLocalISO();
  _$('overtimeDate').value   = todayLocalISO();
  ```
- **教训**：
  - 日期字段的新建表单**必须**默认当天本地日期，减少用户操作；所有"新建"入口都要补
  - **判别法**：`toISOString()` 只用于需要 UTC ISO 格式的场景（如 API 线传）；凡是给人看的日历日期，一律用 `getFullYear() / getMonth() / getDate()` 或封装好的本地构造器
  - 同一段"取今天"逻辑不要 copy-paste 三份 → 抽成单一函数，从源头消灭不一致
  - 搜索关键词：`toISOString().slice` → 逐一人眼复核是否该用本地时间

### 🔴 Bug #13：消费记录列表月份筛选改造为"日消费" + 新增当日合计

- **版本**：v2.5.7
- **现象**：消费记录列表仅支持"月份"（YYYY-MM）筛选；列表与侧边栏"消费统计"页面功能部分重复；用户希望**按具体某天**查看并在列表区展示所选日期合计
- **根因**：原列表接口 `GET /api/expenses` 只接受 `month` 参数配合 `substr()` 做月度范围匹配，没有"精确到天"的筛选维度；且无独立的"当日合计"接口，前端列表页无法在不翻页全量拉取的前提下给出可靠汇总
- **修复**：
  - 接口层：`GET /api/expenses` 的筛选参数由 `month` 改为 `date`（精确匹配 `date = ?`，经 `validate_date` 校验），兼容不传参=返回全部；导出接口 `/api/expenses/export` 同步改为 `?date=`；侧边栏保留"消费统计"（月度视图与列表日视图互补，非重复）
  - 新增独立聚合接口 `GET /api/expenses/today?date=`：返回 `{date, count, total}`，**无视分页**地对目标日期做 `COUNT/SUM`，`user_id` 隔离，`date` 缺失时默认本地当天
  - 前端层：
    - `expenseMonthFilter` → `expenseDateFilter`，默认 `todayLocalISO()`（复用 Bug #8 构造器，不再引入新 UTC 路径）
    - UI 标签"月份"→"日消费"，控件由 `type="month"` 改为 `type="date"`
    - 列表页顶端新增"合计"栏，调用 `/api/expenses/today` 跟随所选日期刷新，文案"合计：¥xxx / 共 n 笔"
    - 错误反馈由静默显示 `0.00 / 0` 改为 `加载失败 / -`，避免与"真实零消费"混淆
- **踩坑经验（生产环境）**：
  - 用户"已重启但接口仍 404"：**旧进程未真正退出**。Git Bash 下 `start "Echo" python app.py` 不可靠，进程树残留导致 5001 仍由旧实例监听 → 返回 404 `{"error":"资源不存在"}`。正确查证法：`netstat -ano | grep 5001` 拿到 PID，`tasklist | grep python` 交叉核对，必要时 `taskkill //F //PID <id>`。前端不应静默吞错（会误导为"零数据"）
  - 接口命名：`/api/expenses/today` 名字暗示"今日"但实际接受任意 `date`，初次误解为写死今天。更合适的命名是 `/api/expenses/daily?date=`，但若改动路径需同步更新前端 + 测试，视为后续重构项
  - 跨模块协同：日期相关改造同时涉及 `static/index.html` 3 处表单、3 处列表筛选、1 处导出 + 后端 2 个接口。全部改完后必须用真实数据跨 08:00 前后跑一遍（China UTC+8 时区陷阱）

### 🔴 Bug #14：删除"消费统计"侧边栏引发误删回滚

- **版本**：v2.5.7
- **现象**：用户原话"消费记录页面月份统计和消费统计模块功能重复"被误读为"删除消费统计模块"整块删除，用户明确要求找回
- **根因**：需求语句歧义——"重复"是指"列表月筛选 + 统计页的月度视图存在重叠"，可优化整合，但**不是删除整个模块**
- **修复**：立即从 `git show HEAD:static/index.html` 还原 `showExpenseStats` 全量子函数（269 行）+ 侧边栏入口
- **教训**：
  - **删除模块级功能前，必须 AskUserQuestion 确认范围**，不能按字面直接删除
  - 治理重复的正确路径：让两者差异化（列表=日视图，统计=月/趋势视图），而非简单删除
  - 大型删除前先 `wc -l` 确认影响面，并提醒用户"即将删除 N 行"

---

## 五、安全加固类

### 🔴 Bug #9：CORS 全开放 + SECRET_KEY 硬编码

- **版本**：v2.3.0
- **现象**：`CORS(app)` 全域名开放；密钥写源码里 `"your-secret-key-here"`
- **修复**：
  ```python
  CORS(app, origins=['http://localhost:5001', 'http://127.0.0.1:5001'])
  app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or os.urandom(32).hex()
  app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传
  ```
- **教训**：
  - **生产部署三件套**：CORS 白名单 + 密钥走环境变量 + 限制请求/上传大小
  - `os.urandom(32).hex()` 随机密钥可行，但重启会让所有 token 失效（已在 v2.5.x 之后加 `.secret_key` 文件持久化）
  - 调试接口 `/api/test` 上线前必须删

---

## 六、复用检查清单

在每次版本升级跑测试之前，过一遍：

| 检查项 | 验证命令/方法 |
|--------|--------------|
| 所有 `g.xxx` 资源都有 teardown | 搜 `g.` + 确认对称有 `teardown_appcontext` |
| 所有 `.strip()` 都有 `or ''` 兜底 | 搜 `\)\.strip()` |
| 所有删除操作都处理引用行 | 搜 `DELETE FROM` + 确认有对称 `UPDATE` |
| 新建表单日期字段有默认值 | 搜 `if (!id)` 或 `if not id` |
| CORS/密钥/上传限制到位 | 搜 `CORS(app)` （应带 origins 参数） |
| 弹窗关闭路径都还原 body 样式 | 搜 `overflow` |
| 中文 CSV 是 GBK + BOM | 搜 `charset=gbk` |
| 手动 SQL 验证 | `SELECT COUNT(*) FROM x WHERE <已删条件>` |

---

## 七、Bug 出现频率排行（v2.1.0 → v2.5.4）

| 模式 | 出现次数 | 累计版本 |
|------|---------|---------|
| 用户输入校验缺失 | 3 | v2.3.0 (x2), v2.5.2/v2.5.1 |
| 前端状态未还原 | 2 | v2.5.3, ca0d6ce |
| 数据库连接/事务问题 | 2 | v2.2.0, v2.5.3 |
| 编码/导出问题 | 1 | v2.1.0 |
| 删除级联缺失 | 1 | v2.2.3 |
| 安全配置不当 | 1 | v2.3.0 |
| 默认值缺失 | 1 | v2.5.4 |

> **结论**：出现最多的是"用户输入校验缺失"和"前端状态未还原"。写代码时优先盯这两个模式。

---

## 八、v2.5.5 全量审计新增发现（2026-07-09）

> 本次采用 6 角度并行扫描（安全/性能/质量/业务/前端/配置），从 117 个候选中验证确认 9 个真实问题。

### 🔴 死锁（并发类新模式）

- **Bug #10：嵌套锁死锁**
  - **现象**：`/api/stats`、`/api/tags` 首次命中缓存时请求永久挂起
  - **根因**：`_get_cached` 函数体内连续写了两行 `with _cache_lock:`，`threading.Lock()` 不可重入
  - **修复**：删除内层多余的 `with _cache_lock:`
  - **教训**：
    - 搜索关键词：`with .*lock` → 检查同一函数内是否有同一锁重复获取
    - 需要可重入场景改用 `threading.RLock()`
    - **新增检查清单项**：搜 `with .*lock` + 确认无同一锁嵌套

### 🔴 连接泄漏（初始化阶段新模式）

- **Bug #11：init_db 无 try-finally**
  - **现象**：首次迁移 ALTER TABLE 异常时 SQLite 连接未关闭，WAL 锁残留
  - **根因**：`init_db()` 直接用 `sqlite3.connect()` 而无 try-finally
  - **修复**：包裹 `try: ... finally: conn.close()`
  - **教训**：
    - 搜索关键词：`sqlite3.connect` → 确认有 `close()` 且在 `finally` 里
    - 搜索关键词：`def init_` → 确认资源型函数有 try-finally

### 🟠 业务逻辑竞态

- **Bug #12：加班同日唯一约束竞态**
  - **现象**：双端同时提交同日加班记录，一方收到 500
  - **根因**：先 SELECT 再 INSERT，两步无原子性；UNIQUE INDEX 触发 IntegrityError 未捕获
  - **修复**：`INSERT` 包在 `try/except sqlite3.IntegrityError` 中返回友好 400
  - **教训**：
    - 搜索关键词：`SELECT.*WHERE.*=.*INSERT` → 竞态模式，需包 IntegrityError 捕获
    - **新增检查清单项**：搜 `fetchone()` 后跟 `INSERT` → 确认有 IntegrityError 兜底

### 🟠 Stored XSS（前端安全）

- **Bug #13：表格 date/remark 未转义**
  - **现象**：用户备注写入 `<img src=x onerror=...>` 在所有人浏览器执行
  - **根因**：`renderExpenseTable` / `renderOvertimeTable` 中 `${r.date}` / `${r.remark}` 直接插入 innerHTML
  - **修复**：所有用户可控字段改用 `escapeHtml()`
  - **教训**：
    - 搜索关键词：`innerHTML.*\${` → 确认每个插值都经过 escapeHtml()
    - 搜索关键词：`title="\${` → 属性注入同样危险
    - **新增检查清单项**：搜 `innerHTML +=` 或 `innerHTML =` + 确认无未转义插值

### 🟡 信息泄露

- **Bug #14：健康检查端点泄露内部错误**
  - **现象**：`/api/health` 异常时返回 `str(e)` 暴露数据库细节
  - **根因**：错误分支直接返回异常字符串
  - **修复**：返回固定 `"unavailable"`，详情仅走服务端 logger
  - **教训**：
    - 搜索关键词：`except.*:.*str(e)` → 异常字符串不应返回客户端
    - **新增检查清单项**：搜 `return.*str(e)` 或 `return.*repr(e)` → 移除

### 🟡 索引缺失（查询优化）

- **Bug #15：substr 函数导致全表扫描**
  - **现象**：月度统计接口随数据增长响应变慢
  - **根因**：`substr(date,6,2)` 无法匹配任何已有索引
  - **修复**：新增表达式索引 `CREATE INDEX ... ON expenses(user_id, substr(date, 6, 2))`
  - **教训**：
    - 搜索关键词：`substr(date` → 确认有匹配的表达式索引
    - **新增检查清单项**：搜 `substr(` + 确认 WHERE 条件列有对应表达式索引

### 测试方法论沉淀

| 方法 | 本次实践效果 |
|------|------------|
| **6 角度并行扫描** | 安全/性能/质量/业务/前端/配置各自独立跑，覆盖盲区 |
| **候选→验证两步法** | 117 候选经 1 投票验证 → 9 个确认，避免"狼来了" |
| **文件逐行+diff 结合** | 历史 diff 抓趋势，全量阅读抓存量 |
| **失败型测试思维** | 不问"能不能用"，问"什么输入让它挂" |

**验证后确认的高频陷阱 TOP 5：**
1. 嵌套锁死锁（threading.Lock 不可重入）
2. sqlite3.connect 无 try-finally
3. SELECT+INSERT 竞态无 IntegrityError 兜底
4. innerHTML 直接插用户值无 escapeHtml
5. 异常字符串返回客户端

## 相关链接
- [[architecture/overview]] - 系统架构总览
- [[modules/auth]] - 认证模块
- [[modules/articles]] - 文章模块
- [[modules/kiwi-sales]] - 猕猴桃销售模块
- [[modules/overtime]] - 加班记录模块
- [[modules/expenses]] - 记账模块
- [[TEST_OPTIMIZATION_MASTER]] - 测试优化指南
- [[AUDIT_REPORT]] - 安全审计报告
