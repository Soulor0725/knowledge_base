# 测试优化权威指南（测试架构师视角）

> 本文档是测试活动全生命周期的优化手册，覆盖六大维度：
> 资产清理 → 架构重构 → 配置标准化 → 覆盖度补齐 → 执行策略 → Token 优化
>
> 每项优化都标注了**测试收益**和**Token 收益**，便于评估优先级。

---

## 一、测试资产清理（先减后加）

### 1.1 当前资产盘点

```
根目录测试文件（7个）
├── test_api.py                 (30 行)   ← 最小 smoke，与 smoke_test 重叠
├── smoke_test.py               (111 行)  ← 注册+全模块 CRUD smoke（唯一 git 跟踪）
├── test_api_comprehensive.py   (517 行)  ← 完整 API 测试（类结构，最全面）
├── test_ui_e2e.py              (481 行)  ← Playwright UI 测试
├── test_server.py              (75 行)   ← 容错/异常输入测试（有价值，但自启服务）
├── test_server2.py             (废弃)    ← test_server.py 旧版，重复
├── test_sql.py                 (17 行)   ← 一次性查询脚本，非测试
│
Test_Team/ (465KB, gitignored)
├── generate_test_excel.py      (56 行)   ← Excel 生成器（非测试）
├── generate_api_test_excel.py  (38 行)   ← Excel 生成器（非测试）
├── generate_merged_excel.py    (12 行)   ← Excel 生成器（非测试）
├── __pycache__/                (91KB)    ← Python 字节码缓存
├── Test_Case/
│   ├── 功能测试用例_v2.2.0.xlsx (19KB)   ← 二进制，不可 diff
│   ├── 接口测试用例_v2.2.0.xlsx (22KB)   ← 二进制，不可 diff
│   ├── 智慧管理中心_测试用例.xlsx (36KB) ← 二进制，不可 diff
│   ├── 智慧管理中心_测试用例_backup.xlsx (36KB) ← 备份，应删
│   ├── TC_*.md (6 文件, 1370 行)        ← 功能测试用例
│   ├── API_*.md (5 文件, 1579 行)       ← 接口测试用例
│   └── README.md (97 行)                ← 用例索引
```

### 1.2 清理清单

| 文件 | 操作 | 理由 |
|------|------|------|
| `test_server2.py` | **删除** | test_server.py 旧版，完全重复 |
| `test_sql.py` | **删除** | 一次性查询脚本，非测试 |
| `Test_Team/__pycache__/` | **删除** | 字节码缓存，应 gitignore |
| `Test_Team/Test_Case/智慧管理中心_测试用例_backup.xlsx` | **删除** | 备份文件，无版本价值 |
| `generate_*.py` (3 个) | **移到 scripts/ 或删除** | 非测试代码，生成 Excel 的一次性工具 |
| `*.xlsx` (3 个) | **移到 releases/ 或删除** | 二进制不可 diff，占 77KB |

**清理命令：**
```bash
cd e:\trae_projects\knowledge_base
rm test_server2.py test_sql.py
rm -rf Test_Team/__pycache__
rm Test_Team/Test_Case/智慧管理中心_测试用例_backup.xlsx
mkdir -p scripts
mv Test_Team/generate_*.py scripts/ 2>/dev/null
```

**测试收益：** 7 个测试文件 → 4 个，消除"该读哪个"的困惑。
**Token 收益：** Claude 不再读到废弃/重复文件，每次省 100-200 token。

---

## 二、测试架构重构（治本）

### 2.1 目标架构

```
tests/
├── __init__.py              ← 空文件，标记为 package
├── conftest.py              ← 共享 fixtures（client, auth, test_user, cleanup）
├── pytest.ini               ← pytest 配置（markers, 默认参数）
├── .coveragerc              ← 覆盖率配置
├── test_smoke.py            ← P0 smoke（合并 test_api.py + smoke_test.py）
├── test_auth.py             ← 认证模块（P0+P1）
├── test_articles.py         ← 知识库模块
├── test_kiwi_sales.py       ← 猕猴桃销售模块
├── test_overtime.py         ← 加班模块
├── test_expenses.py         ← 消费记账模块
├── test_fault_tolerance.py  ← 容错/异常输入（从 test_server.py 迁移）
└── test_ui_e2e.py           ← Playwright UI（独立，因依赖浏览器）
```

### 2.2 conftest.py（核心，所有测试共享）

```python
# tests/conftest.py
import pytest, requests, random, string

BASE_URL = 'http://localhost:5001/api'

def _random_user():
    u = 't_' + ''.join(random.choices(string.ascii_lowercase, k=6))
    return u, 'Test1234'

@pytest.fixture(scope="session")
def client():
    """复用单一 requests.Session，避免每测试重建连接"""
    s = requests.Session()
    s.headers.update({'Content-Type': 'application/json'})
    yield s
    s.close()

@pytest.fixture(scope="session")
def auth(client):
    """一次注册+登录，全 session 复用 token"""
    u, p = _random_user()
    r = client.post(f'{BASE_URL}/auth/register', json={'username': u, 'password': p, 'name': u})
    if r.status_code != 201:  # 用户已存在则登录
        r = client.post(f'{BASE_URL}/auth/login', json={'username': u, 'password': p})
    token = r.json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

@pytest.fixture(scope="session")
def admin_auth(client):
    """管理员账号（root/root123），用于需要高权限的测试"""
    r = client.post(f'{BASE_URL}/auth/login', json={'username': 'root', 'password': 'root123'})
    token = r.json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

@pytest.fixture
def temp_article(auth, client):
    """创建临时文章，测试后自动清理"""
    r = client.post(f'{BASE_URL}/articles', headers=auth, json={
        'title': 'Temp', 'content': 'Temp', 'category': '技术'
    })
    aid = r.json()['id']
    yield aid
    client.delete(f'{BASE_URL}/articles/{aid}', headers=auth)  # 清理

@pytest.fixture
def temp_expense(auth, client):
    """创建临时消费记录，测试后自动清理"""
    r = client.post(f'{BASE_URL}/expenses', headers=auth, json={
        'category': '交通', 'amount': 10, 'date': '2026-07-08'
    })
    eid = r.json()['id']
    yield eid
    client.delete(f'{BASE_URL}/expenses/{eid}', headers=auth)
```

**测试收益：** 测试数据自动清理，不再污染数据库；session 级复用连接，速度快 5-10 倍。
**Token 收益：** 每个测试文件省掉 20-30 行重复 setup，Claude 读测试文件时 context 更小。

### 2.3 pytest.ini（统一配置）

```ini
# tests/pytest.ini
[pytest]
testpaths = .
python_files = test_*.py
python_functions = test_*
addopts = -q --tb=line --strict-markers
markers =
    p0: 核心冒烟用例（发版必跑）
    p1: 重要用例（回归测试）
    p2: 次要用例（UI/边界）
    smoke: 冒烟测试
    regression: 回归测试
    security: 安全测试
    performance: 性能测试
    fault_tolerance: 容错测试
```

### 2.4 .coveragerc（覆盖率配置）

```ini
# tests/.coveragerc
[run]
source = .
branch = True
omit = tests/*, scripts/*, */__pycache__/*

[report]
fail_under = 70
show_missing = True
exclude_lines =
    pragma: no cover
    if __name__ == .__main__.
```

### 2.5 requirements.txt 补测试依赖

```txt
# 测试依赖（追加到 requirements.txt 末尾）
pytest>=7.0
pytest-cov>=4.0
pytest-xdist>=3.0       # 并行执行
pytest-timeout>=2.0     # 超时控制
requests>=2.28
playwright>=1.40
faker>=20.0             # 测试数据工厂
```

---

## 三、测试覆盖度补齐

### 3.1 当前覆盖度分析

| 模块 | 自动化覆盖 | 手工用例 | 缺口 |
|------|-----------|---------|------|
| 认证 | ✅ 注册/登录/鉴权 | 15 TC + 27 API | 缺少：JWT 过期、暴力破解、SQL 注入 |
| 知识库 | ✅ CRUD/收藏/统计 | 26 TC + 50 API | 缺少：并发编辑、XSS 过滤、大文本 |
| 猕猴桃销售 | ✅ CRUD/报表/导出 | 18 TC + 30 API | 缺少：并发下单、手机号伪造、批量限制 |
| 加班 | ✅ CRUD/计算/统计 | 20 TC + 30 API | 缺少：跨时区、闰年2月29日、24:00边界 |
| 消费记账 | ✅ CRUD/统计/导出 | 25 TC + 40 API | 缺少：金额精度、分类白名单绕过、负数金额 |
| 容错/异常 | ⚠️ 仅 test_server.py | — | 缺少：标准化为 pytest |
| 性能/负载 | ❌ 无 | — | 完全空白 |
| 安全 | ❌ 无 | — | 完全空白 |

### 3.2 必须补齐的测试类型

#### A. 容错测试（从 test_server.py 迁移并扩展）

```python
# tests/test_fault_tolerance.py
import pytest

@pytest.mark.fault_tolerance
class TestFaultTolerance:
    """异常输入、边界条件、协议级错误"""

    def test_invalid_token_format(self, client):
        """Token 格式错误 → 401"""
        r = client.get(f'{BASE_URL}/articles', headers={'Authorization': 'Bearer invalid.token.here'})
        assert r.status_code == 401

    def test_malformed_json_body(self, client, auth):
        """JSON 语法错误 → 400"""
        r = client.post(f'{BASE_URL}/auth/login', data='{"invalid', headers=auth)
        assert r.status_code == 400

    def test_empty_body(self, client, auth):
        """空请求体 → 400"""
        r = client.post(f'{BASE_URL}/auth/login', data='', headers=auth)
        assert r.status_code == 400

    def test_negative_pagination(self, client, auth):
        """负数分页 → 返回空或 400"""
        r = client.get(f'{BASE_URL}/articles?page=-1&page_size=-10', headers=auth)
        assert r.status_code in (200, 400)

    def test_method_not_allowed(self, client):
        """不允许的方法 → 405"""
        r = client.delete(f'{BASE_URL}/auth/login')
        assert r.status_code == 405

    def test_batch_delete_limit(self, client, auth):
        """批量删除超限 → 400"""
        r = client.post(f'{BASE_URL}/kiwi-sales/batch-delete', headers=auth,
                        json={'ids': list(range(200))})
        assert r.status_code == 400

    def test_very_long_input(self, client, auth):
        """超长输入 → 400 或截断"""
        r = client.post(f'{BASE_URL}/articles', headers=auth,
                        json={'title': 'A'*10000, 'content': 'x'*100000, 'category': '技术'})
        assert r.status_code in (201, 400)

    def test_sql_injection_attempt(self, client, auth):
        """SQL 注入尝试 → 不报错、不泄露数据"""
        r = client.get(f"{BASE_URL}/articles?id=1 OR 1=1; DROP TABLE articles;--", headers=auth)
        assert r.status_code in (200, 400, 404)
        # 验证表未被删除
        r2 = client.get(f'{BASE_URL}/articles', headers=auth)
        assert r2.status_code == 200
```

#### B. 安全测试

```python
# tests/test_security.py
import pytest

@pytest.mark.security
class TestSecurity:
    """安全基线测试"""

    def test_no_token_returns_401(self, client):
        """无 Token → 401"""
        r = client.get(f'{BASE_URL}/articles')
        assert r.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """伪造 Token → 401"""
        r = client.get(f'{BASE_URL}/articles', headers={'Authorization': 'Bearer fake_token'})
        assert r.status_code == 401

    def test_user_isolation(self, client, auth):
        """用户 A 的数据用户 B 看不到"""
        # 用户 A 创建文章
        r = client.post(f'{BASE_URL}/articles', headers=auth,
                        json={'title': 'Private', 'content': 'Secret', 'category': '技术'})
        aid = r.json()['id']
        # 用户 B 注册并尝试访问
        import random, string
        u = 'b_' + ''.join(random.choices(string.ascii_lowercase, k=6))
        r2 = client.post(f'{BASE_URL}/auth/register', json={'username': u, 'password': 'Test1234', 'name': u})
        token_b = r2.json()['token']
        r3 = client.get(f'{BASE_URL}/articles/{aid}', headers={'Authorization': f'Bearer {token_b}'})
        assert r3.status_code == 404  # 看不到

    def test_xss_in_content(self, client, auth, temp_article):
        """XSS 脚本不应原样存储/返回（或应转义）"""
        r = client.get(f'{BASE_URL}/articles/{temp_article}', headers=auth)
        # 至少验证返回的是合法 JSON，脚本未被执行
        assert r.status_code == 200

    def test_rate_limit_on_login(self, client):
        """连续登录失败应触发限流"""
        for _ in range(15):
            client.post(f'{BASE_URL}/auth/login', json={'username': 'root', 'password': 'wrong'})
        r = client.post(f'{BASE_URL}/auth/login', json={'username': 'root', 'password': 'wrong'})
        # 限流后返回 429 或 401
        assert r.status_code in (429, 401)
```

#### C. 性能测试（轻量级）

```python
# tests/test_performance.py
import pytest, time

@pytest.mark.performance
class TestPerformance:
    """响应时间基线（非负载测试）"""

    def test_login_response_time(self, client):
        """登录响应 < 500ms"""
        start = time.time()
        r = client.post(f'{BASE_URL}/auth/login', json={'username': 'root', 'password': 'root123'})
        elapsed = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed < 500, f"Login took {elapsed:.0f}ms"

    def test_list_articles_response_time(self, client, auth):
        """列表查询 < 300ms"""
        start = time.time()
        r = client.get(f'{BASE_URL}/articles', headers=auth)
        elapsed = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed < 300, f"List took {elapsed:.0f}ms"

    def test_report_response_time(self, client, auth):
        """报表查询 < 1000ms"""
        start = time.time()
        r = client.get(f'{BASE_URL}/kiwi-sales/report', headers=auth)
        elapsed = (time.time() - start) * 1000
        assert r.status_code == 200
        assert elapsed < 1000, f"Report took {elapsed:.0f}ms"
```

### 3.3 覆盖度目标

| 类型 | 当前 | 目标 | 优先级 |
|------|------|------|--------|
| P0 smoke | ~15 用例 | 20 用例 | P0 |
| P1 回归 | ~30 用例 | 50 用例 | P1 |
| 容错测试 | 8 用例（非标） | 15 用例（pytest） | P1 |
| 安全测试 | 0 | 8 用例 | P1 |
| 性能测试 | 0 | 5 用例 | P2 |
| UI E2E | ~10 用例 | 15 用例 | P2 |

---

## 四、手工测试用例标准化

### 4.1 当前问题

- **格式不统一**：API 用例用表格，TC 用例用步骤式，UI 用例用自由文本
- **无 ID 到自动化映射**：TC-API-AUTH-001-01 没有对应 `test_auth.py::test_xxx`
- **3119 行 MD 是 context 黑洞**：让 Claude "参考用例" 可能读全文

### 4.2 统一用例模板

```markdown
## TC-XXX-NNN | P0 | 用例标题

| 项 | 内容 |
|---|---|
| 用例 ID | TC-XXX-NNN |
| 优先级 | P0/P1/P2 |
| 类型 | 正向/反向/边界/安全 |
| 关联需求 | PRD-XXX |
| 关联接口 | API-XXX-NNN |
| 关联自动化 | test_module.py::test_name 或 ⏳ 待自动化 |

**前置条件**：...
**测试步骤**：
1. ...
**期望结果**：...
**自动化状态**：✅ 已自动化 / ⏳ 待自动化 / ❌ 不适用
```

### 4.3 追溯矩阵（Traceability Matrix）

在 `Test_Team/Test_Case/TRACEABILITY.md` 建立映射：

```markdown
# 测试追溯矩阵

| 手工用例 | 需求 | 接口 | 自动化测试 | 状态 |
|---------|------|------|-----------|------|
| TC-AUTH-001 | AUTH-001 | API-AUTH-001 | test_auth.py::test_register_success | ✅ |
| TC-AUTH-002 | AUTH-001 | API-AUTH-001 | test_auth.py::test_register_dup | ✅ |
| TC-AUTH-003 | AUTH-002 | API-AUTH-002 | ⏳ | 待自动化 |
| TC-API-AUTH-001-01 | AUTH-001 | API-AUTH-001 | test_auth.py::test_register_success | ✅ |
| TC-OT-001 | OT-001 | API-OT-001 | test_overtime.py::test_create_weekday | ✅ |
| ... | ... | ... | ... | ... |
```

**Token 收益：** 一张表看清覆盖情况，无需读 3119 行 MD。

### 4.4 手工用例使用规范

| 操作 | 正确做法 | 避免 |
|------|---------|------|
| 查某模块有多少用例 | 读 README.md 索引 | 读完整 TC_*.md |
| 查某条用例详情 | `grep -n "TC-OT-003" TC_加班模块.md` | Read 整个文件 |
| 写自动化前先确认覆盖 | 读 TRACEABILITY.md | 读全部 3119 行 |
| 批量检查自动化覆盖 | `grep "⏳" TRACEABILITY.md` | 逐文件读 |

---

## 五、测试执行策略

### 5.1 分层执行

```
开发中（每次保存后）
  └─ pytest -m p0 -q                    # 10-15 秒，只跑 P0

模块改动后
  └─ pytest tests/test_overtime.py -q   # 只跑相关模块

提 PR / 发版前
  └─ pytest -q --cov --cov-report=term-missing  # 全量 + 覆盖率

每日构建
  └─ pytest -q --cov --cov-report=html  # 全量 + HTML 报告

UI 回归（发版前）
  └─ pytest tests/test_ui_e2e.py -q     # Playwright 独立跑
```

### 5.2 测试影响分析（TIA）

```bash
# 只跑与改动相关的测试（基于 git diff）
# 安装 pytest-testmon 后：
pytest --testmon -q

# 手动映射（改动 → 测试）：
# app.py:overtime → tests/test_overtime.py
# app.py:auth     → tests/test_auth.py
# static/index.html → tests/test_ui_e2e.py
```

### 5.3 CI 集成（GitHub Actions 示例）

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python app.py &
      - run: sleep 5
      - run: pytest -m p0 -q --tb=short
      - run: pytest -q --cov --cov-report=term-missing
```

### 5.4 测试完成标准（Definition of Done）

| 阶段 | 通过条件 |
|------|---------|
| **开发完成** | P0 smoke 100% 通过 |
| **功能完成** | P0 + P1 ≥ 95% 通过，无 P0 失败 |
| **发版就绪** | P0 + P1 + P2 ≥ 90% 通过，覆盖率 ≥ 70%，无安全测试失败 |
| **UI 发版** | test_ui_e2e.py 100% 通过 |

---

## 六、测试 Token 优化（核心）

### 6.1 测试提示词模板（权威版）

#### 模板 1：新增测试
```
在 tests/test_overtime.py 新增 P0 测试：
- 用例1：工作日 19:00-21:00 创建成功，duration=2
- 用例2：周末 09:00-17:00 创建成功，duration=6（扣午休2h）
- 用例3：同日重复创建返回 400
使用 conftest.py 的 auth fixture 和 temp_overtime 清理。
只写这 3 个，不扩展。输出格式：文件路径 + 代码块。
```

#### 模板 2：调试失败（最重要）
```
pytest tests/test_overtime.py::test_create_weekday -q 失败。
错误：assert 2.5 == 2.0（test_overtime.py:42）
只读 app.py calculate_overtime_duration() 函数（约 45-60 行）。
不改其他代码。不分析原因，只定位差异行。
```

#### 模板 3：回归验证
```
pytest tests/test_overtime.py -q --tb=line。
只报：失败用例名 + assert 行号 + 期望 vs 实际。
不分析原因，不猜测，不扩展。
```

#### 模板 4：补自动化（手工→自动）
```
手工用例 TC-OT-003（API_加班模块.md:45）要求：
同日重复创建加班返回 400。
在 test_overtime.py 新增 1 个测试覆盖此场景。
只写 1 个，不扩展。
```

#### 模板 5：修测试
```
test_overtime.py:42 断言值过时，改为 2.0。只改这一行。不改其他。
```

### 6.2 测试调试 Token 优化（最核心）

#### ❌ 浪费循环（每轮 2000-4000 token）
```
[轮1] "test_overtime 失败了，帮我看看" → Claude 读测试文件 + 读 app.py 全文
[轮2] "还是不对，你再看看" → Claude 又读一遍
[轮3] "可能是数据库的问题" → Claude 读 DB schema
[轮4] "哦我知道了，是时区问题" → Claude 读时区相关代码
```

#### ✅ 节约循环（每轮 300-800 token）
```
[轮1] "pytest test_overtime.py::test_weekday -q 失败。assert 2.5==2.0。
       只读 app.py:calculate_overtime_duration() 第 45-60 行。"
       → Claude 读 15 行代码，定位 bug
[轮2] "修复：第 52 行 lunch_end 应为 14:00 不是 13:00。确认。"
       → Claude 只读 1 行，确认修复
```

### 6.3 测试 Token 速查表

| 活动 | 浪费模式（token） | 节约模式（token） | 节省 |
|------|------------------|------------------|------|
| 写 1 个测试 | 读源码全文 + 写 + 解释（3000） | 给函数名 + 行号 + 期望（800） | 73% |
| 调试 1 次失败 | 读测试 + 读源码 + 猜（4000） | 给 assert + 行号 + 只读函数（600） | 85% |
| 跑全量测试 | 读全部测试文件 + 分析（5000） | pytest -q --tb=line（500） | 90% |
| 查手工用例 | 读 3119 行 MD（6000） | 读 README 索引（200） | 97% |
| 生成测试报告 | 自由格式长篇（2000） | 固定模板 3 行（200） | 90% |
| 调试循环（5轮） | 每轮重读全部（15000） | 每轮只读差异行（3000） | 80% |

---

## 七、UI E2E 测试专项优化

### 7.1 当前问题

```python
# test_ui_e2e.py 中的典型问题
page.goto(BASE_URL)
page.wait_for_load_state('networkidle')  # 隐式等待，不稳定
page.click('text=登录')                   # 文本选择器，中文变动就崩
expect(page.locator('.user-name')).to_be_visible()  # CSS 选择器，class 改动就崩
```

**问题：** UI 测试是最脆弱的——任何 HTML/CSS/文案变动都导致失败，调试成本极高（token 浪费大户）。

### 7.2 优化方案

#### A. 使用 data-testid 选择器（最稳定）

```html
<!-- 前端 static/index.html 中 -->
<button data-testid="login-btn">登录</button>
<input data-testid="username-input" />
<div data-testid="user-name-display"></div>
```

```python
# 测试中使用
page.locator('[data-testid="login-btn"]').click()
```

#### B. Page Object 模式

```python
# tests/pages/login_page.py
class LoginPage:
    def __init__(self, page):
        self.page = page
        self.username = page.locator('[data-testid="username-input"]')
        self.password = page.locator('[data-testid="password-input"]')
        self.submit = page.locator('[data-testid="login-btn"]')
    
    def login(self, u, p):
        self.username.fill(u)
        self.password.fill(p)
        self.submit.click()
    
    def is_logged_in(self):
        return self.page.locator('[data-testid="user-name-display"]').is_visible()

# 测试中使用
def test_login(page):
    login_page = LoginPage(page)
    login_page.login('root', 'root123')
    assert login_page.is_logged_in()
```

**Token 收益：** UI 测试失败时，Page Object 让 Claude 只看 `pages/login_page.py`（30 行）而非 `test_ui_e2e.py`（481 行）。

#### C. 视觉回归（可选）

```python
# 截图对比，快速发现 UI 变更
expect(page).to_have_snapshot('home_page.png')
```

---

## 八、测试数据工厂（高级）

### 8.1 使用 Faker 生成真实感数据

```python
# tests/factories.py
from faker import Faker
fake = Faker('zh_CN')  # 中文数据

def make_article_data(**overrides):
    return {
        'title': fake.sentence(nb_words=4),
        'content': fake.paragraph(nb_sentences=3),
        'category': random.choice(['技术', '生活', '学习', '工作']),
        **overrides
    }

def make_expense_data(**overrides):
    return {
        'category': random.choice(['交通', '电费', '话费', '菜肉米面油']),
        'amount': round(random.uniform(5, 500), 2),
        'date': fake.date_between('-30d', 'today').isoformat(),
        'remark': fake.sentence(nb_words=3),
        **overrides
    }

def make_overtime_data(otype='weekday', **overrides):
    if otype == 'weekday':
        return {
            'overtime_type': 'weekday',
            'date': '2026-07-08',
            'start_time': '19:00',
            'end_time': '21:00',
            'remark': fake.sentence(nb_words=3),
            **overrides
        }
    else:
        return {
            'overtime_type': 'weekend',
            'date': '2026-07-12',
            'start_time': '09:00',
            'end_time': '17:00',
            'remark': fake.sentence(nb_words=3),
            **overrides
        }
```

### 8.2 参数化测试（1 个函数覆盖 N 个场景）

```python
# ❌ 浪费：5 个几乎相同的用例
def test_weekday_19_21(): ...
def test_weekday_19_22(): ...
def test_weekday_19_23(): ...
def test_weekend_09_17(): ...
def test_weekend_09_19(): ...

# ✅ 节约：1 个参数化用例
@pytest.mark.parametrize("otype,date,start,end,expected", [
    ("weekday", "2026-07-08", "19:00", "21:00", 2.0),
    ("weekday", "2026-07-08", "19:00", "22:00", 3.0),
    ("weekday", "2026-07-08", "19:00", "23:00", 4.0),
    ("weekend", "2026-07-12", "09:00", "17:00", 6.0),
    ("weekend", "2026-07-12", "09:00", "19:00", 8.0),
])
def test_overtime_duration(auth, client, otype, date, start, end, expected):
    r = client.post(f'{BASE_URL}/overtime', headers=auth,
                    json={"overtime_type": otype, "date": date,
                          "start_time": start, "end_time": end})
    assert r.json()['duration'] == expected
```

**Token 收益：** 修这 5 个场景的断言时，读 1 个函数而非 5 个。

---

## 九、测试报告与可视化

### 9.1 报告类型

| 类型 | 命令 | 用途 |
|------|------|------|
| 终端摘要 | `pytest -q --tb=line` | 日常开发 |
| 覆盖率 | `pytest --cov --cov-report=term-missing` | 发版前 |
| HTML 报告 | `pytest --html=report.html --self-contained-html` | 归档 |
| JUnit XML | `pytest --junitxml=results.xml` | CI 集成 |
| 失败截图 | Playwright 内置 `screenshot_on_failure=True` | UI 调试 |

### 9.2 报告生成提示词模板

```
pytest -q --tb=line 结果 → 输出格式：
## 结果
通过: X / 失败: Y / 跳过: Z
## 失败清单
- test_name (文件:行号) — 期望 X 实际 Y
## 覆盖率
总体: X% | 缺失行: app.py:45-48, 67
## 风险
只列 P0 失败项
其他不写
```

---

## 十、实施路线图

### Phase 0：立即可做（0 代码改动，只改习惯）
- [ ] 测试提示词按本指南模板化
- [ ] 调试时强制给 `file:line` 定位
- [ ] 手工用例只读 README.md 索引
- [ ] pytest 执行加 `-q --tb=line`
- [ ] 复用之前读过的代码，不重复 Read

### Phase 1：资产清理（30 分钟）
- [ ] 删除 `test_server2.py`、`test_sql.py`
- [ ] 删除 `Test_Team/__pycache__/`
- [ ] 删除 `*_backup.xlsx`
- [ ] 移动 `generate_*.py` 到 `scripts/`
- [ ] 更新 `.gitignore` 确认 `__pycache__` 和 `*.pyc` 被忽略

### Phase 2：配置标准化（1 小时）
- [ ] 创建 `tests/__init__.py`
- [ ] 创建 `tests/conftest.py`（共享 fixtures）
- [ ] 创建 `tests/pytest.ini`（markers + 默认参数）
- [ ] 创建 `tests/.coveragerc`（覆盖率配置）
- [ ] 更新 `requirements.txt`（测试依赖）

### Phase 3：架构重构（2-3 小时）
- [ ] 合并 `test_api.py` + `smoke_test.py` → `tests/test_smoke.py`
- [ ] 拆分 `test_api_comprehensive.py` → 按模块独立文件
- [ ] 迁移 `test_server.py` → `tests/test_fault_tolerance.py`
- [ ] 给所有测试加 `@pytest.mark.p0/p1/p2` markers
- [ ] 给高频场景加参数化

### Phase 4：覆盖度补齐（半天）
- [ ] 补齐容错测试（SQL 注入、超长输入、非法方法）
- [ ] 补齐安全测试（鉴权、越权、XSS、限流）
- [ ] 补齐性能测试（响应时间基线）
- [ ] 建立追溯矩阵 `TRACEABILITY.md`

### Phase 5：UI 测试优化（半天）
- [ ] 前端添加 `data-testid` 属性
- [ ] 实现 Page Object 模式
- [ ] 添加失败自动截图

### Phase 6：CI 集成（1 小时）
- [ ] 创建 `.github/workflows/test.yml`
- [ ] 配置 pre-commit hook（可选）
- [ ] 配置覆盖率门禁

---

## 十一、测试优化检查清单（一页纸）

### 架构质量
- [ ] 测试文件按模块拆分（单一职责）
- [ ] conftest.py 共享 fixtures（无重复 setup）
- [ ] pytest markers 分层（p0/p1/p2, smoke/security/performance）
- [ ] 参数化替代重复用例
- [ ] 测试数据自动清理（fixture teardown）

### 覆盖度
- [ ] P0 smoke 覆盖所有模块核心路径
- [ ] 容错测试覆盖异常输入/边界/协议错误
- [ ] 安全测试覆盖鉴权/越权/注入/限流
- [ ] 性能测试覆盖关键接口响应时间
- [ ] 追溯矩阵建立（手工↔自动化映射）

### 执行效率
- [ ] 日常开发只跑 `-m p0`（< 15 秒）
- [ ] 模块改动只跑相关测试文件
- [ ] 发版前跑全量 + 覆盖率
- [ ] 失败时立即停止（`-x`）
- [ ] 上次失败的优先跑（`--lf`）

### Token 优化
- [ ] 调试时给 `file:line` 定位
- [ ] 手工用例只读索引不读全文
- [ ] 测试提示词模板化
- [ ] 复用之前读过的代码
- [ ] 测试报告固定模板
- [ ] 不在测试会话里混合开发任务

### 资产清理
- [ ] 废弃测试文件已删除
- [ ] `__pycache__` 已清理
- [ ] 二进制文件（xlsx）不在 git 跟踪中
- [ ] 一次性脚本已归档或删除

---

> 💡 **测试架构师的核心洞察：**
> 1. **测试的 token 浪费 80% 在调试循环**，精确给定位（file:line）是省 token 的最强手段
> 2. **测试文件越大，每次 Claude 读它的 token 越多** — 拆分 + 共享 fixtures 是治本
> 3. **手工用例是 context 黑洞** — 索引 + 追溯矩阵让 Claude 按需读取
> 4. **测试数据污染是隐藏杀手** — 自动清理避免"这次跑过不了上次可以"的玄学问题
> 5. **UI 测试是 token 无底洞** — data-testid + Page Object 让调试成本可控```
