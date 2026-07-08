# 测试架构师 Token 优化指南

> 从测试架构师视角，针对测试活动的全生命周期（设计→编写→执行→调试→报告）进行 token 消耗优化。
> 测试是 token 消耗大户：读源码、读测试文件、读失败输出、反复调试，每一项都在烧 token。

---

## 一、测试文件架构优化（治本）

### 1.1 当前问题：文件冗余与重叠

```
test_api.py              (30 行)   ← 最小 smoke，与 smoke_test 重叠
smoke_test.py            (111 行)  ← 注册+全模块 CRUD smoke
test_api_comprehensive.py (517 行) ← 完整 API 测试（类结构）
test_ui_e2e.py           (481 行)  ← Playwright UI 测试
test_server.py           (废弃?)   ← 旧版
test_server2.py          (废弃?)   ← 旧版
test_sql.py              (废弃?)   ← 旧版
```

**问题：** 让 Claude "跑测试" 时不知道该读哪个文件；"修测试" 时可能读错文件。

### 1.2 优化方案：分层 + 单一职责

```
tests/
├── conftest.py              ← 共享 fixtures（client, auth_headers, test_user）
├── test_auth.py             ← 认证模块（P0: 注册/登录/鉴权/越权）
├── test_articles.py         ← 知识库模块
├── test_kiwi_sales.py       ← 猕猴桃销售模块
├── test_overtime.py         ← 加班模块
├── test_expenses.py         ← 消费记账模块
└── test_ui_e2e.py           ← Playwright UI（独立，因依赖浏览器）
```

**Token 收益：** 修 `test_overtime.py` 时不再加载 `test_api_comprehensive.py` 的 517 行。

### 1.3 测试分层与标记（pytest markers）

```python
# conftest.py
import pytest

@pytest.fixture(scope="session")
def client():
    # 复用单一 session，避免每测试重新注册
    ...

@pytest.fixture(scope="session")
def auth(client):
    # 一次登录，全 session 复用 token
    ...

# test_overtime.py
import pytest

@pytest.mark.p0
@pytest.mark.smoke
def test_create_overtime_weekday(auth):
    ...

@pytest.mark.p1
def test_overtime_lunch_deduction(auth):
    ...
```

**执行命令与 token 收益：**

```bash
# 只跑 P0 smoke（最快反馈，最少 token）
pytest -m "p0 and smoke" -q

# 只跑加班模块
pytest tests/test_overtime.py -q

# 跑全量（发版前）
pytest -q
```

**Token 收益：** 日常调试只跑 `-m p0` 的 10-15 个用例，而非全量 50+ 个。

---

## 二、测试提示词工程（核心省 token 手段）

### 2.1 测试编写提示词

#### ❌ 浪费写法
```
帮我给加班模块写一套完整的测试用例，要覆盖各种边界情况，
包括正常流程和异常流程，最好还能有性能测试和并发测试，
因为之前出了个 bug 是并发写入导致的，我想一次性写全。
```

#### ✅ 节约写法
```
在 tests/test_overtime.py 新增 P0 测试：
- 用例1：工作日 19:00-21:00 创建成功，duration=2
- 用例2：周末 09:00-17:00 创建成功，duration=6（扣午休2h）
- 用例3：同日重复创建返回 400
参考 conftest.py 的 auth fixture。只写这 3 个，不扩展。
```

**对比：** 浪费写法 → Claude 读 app.py 全文 + 写 50 行测试 + 解释 ≈ 3000 token
节约写法 → Claude 只读 conftest + 写 15 行 ≈ 800 token

### 2.2 测试调试提示词

#### ❌ 浪费写法
```
test_overtime.py 跑失败了，你帮我看看怎么回事，
可能是数据库的问题，也可能是代码逻辑的问题，
我昨天改过加班计算的函数，不知道有没有改错。
```

#### ✅ 节约写法
```
pytest tests/test_overtime.py::test_create_overtime_weekday -q 失败。
错误：assert 2.5 == 2.0。
只读 app.py calculate_overtime_duration() 函数，不改其他代码。
```

**对比：** 浪费写法 → Claude 读测试文件 + 读 app.py 全文 + 读 DB + 猜测 ≈ 4000 token
节约写法 → Claude 读 1 个函数 + 定位 1 个 bug ≈ 600 token

### 2.3 测试执行提示词

#### ❌ 浪费写法
```
帮我跑一下所有测试，看看有没有问题，
然后把结果汇总给我，失败的用例详细分析一下原因。
```

#### ✅ 节约写法
```
1. pytest -m p0 -q → 只报失败用例名
2. 对失败的用例，告诉我：用例名 + 期望值 vs 实际值 + 对应源码行号
3. 不分析原因，只报事实
```

### 2.4 测试提示词模板速查

| 场景 | 模板 |
|------|------|
| **新增测试** | `在 tests/test_XXX.py 新增 P0 测试：[用例列表]。参考 conftest.py 的 auth fixture。只写这 N 个，不扩展。` |
| **调试失败** | `pytest path::name -q 失败。错误：assert X == Y。只读 app.py 第 N 行函数，不改其他代码。` |
| **回归验证** | `pytest tests/test_XXX.py -q。只报失败用例名 + 期望 vs 实际。不分析原因。` |
| **补测试** | `app.py:45-60 的 calculate_overtime_duration 缺少周末测试。在 test_overtime.py 补 2 个用例。不扩展。` |
| **修测试** | `test_overtime.py:89 的断言值过时，改为 2.0。只改这一行。` |

---

## 三、测试数据管理（Fixture 复用）

### 3.1 当前问题

```python
# smoke_test.py — 每个测试文件都重新注册用户
u = 'smk_' + ''.join(random.choices(string.ascii_lowercase, k=5))
p = 'SmT' + str(random.randint(1000, 9999))
r = requests.post(BASE + '/auth/register', ...)

# test_api_comprehensive.py — 又注册一个
name = f"test_{random_str()}"
resp = self.session.post(f'{API_URL}/auth/register', ...)
```

**问题：** 每次运行测试都重新注册 → 浪费时间 + 浪费 token（Claude 读测试文件时看到这些）。

### 3.2 优化方案：conftest.py 共享 fixtures

```python
# tests/conftest.py
import pytest, requests, random, string

BASE_URL = 'http://localhost:5001/api'

@pytest.fixture(scope="session")
def client():
    """复用单一 requests.Session"""
    s = requests.Session()
    s.headers.update({'Content-Type': 'application/json'})
    yield s
    s.close()

@pytest.fixture(scope="session")
def auth(client):
    """一次登录，全 session 复用 token"""
    u = 't_' + ''.join(random.choices(string.ascii_lowercase, k=6))
    r = client.post(f'{BASE_URL}/auth/register', json={
        'username': u, 'password': 'Test1234', 'name': u
    })
    token = r.json()['token']
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

@pytest.fixture(scope="session")
def sample_article(auth, client):
    """预置一篇测试文章，供查询/更新/删除用例复用"""
    r = client.post(f'{BASE_URL}/articles', headers=auth, json={
        'title': 'Fixture Article', 'content': 'Fixture content', 'category': '技术'
    })
    return r.json()['id']
```

**Token 收益：** 每个测试文件省掉 20-30 行重复 setup 代码，Claude 读测试文件时 context 更小。

### 3.3 测试数据工厂（复杂场景）

```python
# tests/factories.py
def make_overtime_payload(overtime_type='weekday', date='2026-07-07', 
                          start='19:00', end='21:00'):
    return {
        'overtime_type': overtime_type,
        'date': date,
        'start_time': start,
        'end_time': end,
        'remark': 'test'
    }

# 测试中直接调用
def test_weekday(auth, client):
    r = client.post(f'{BASE_URL}/overtime', headers=auth, 
                    json=make_overtime_payload())
    assert r.status_code == 201
```

---

## 四、手工测试用例文档优化

### 4.1 当前问题

```
Test_Team/Test_Case/
├── API_认证模块.md         (273 行, 27 用例)
├── API_知识库模块.md       (401 行, 50 用例)
├── API_猕猴桃销售模块.md   (293 行, 30 用例)
├── API_加班模块.md         (262 行, 30 用例)
├── API_消费记账模块.md     (347 行, 40 用例)
├── TC_认证模块.md          (229 行, 15 用例)
├── TC_知识库模块.md        (269 行, 26 用例)
├── TC_猕猴桃销售模块.md    (183 行, 18 用例)
├── TC_加班模块.md          (209 行, 20 用例)
├── TC_消费记账模块.md      (252 行, 25 用例)
├── TC_UI专项.md            (227 行, 20 用例)
└── README.md               (97 行)
```

**总计：3119 行手工用例。** 如果让 Claude "参考测试用例写自动化"，它会读这些 MD → 巨大 token 消耗。

### 4.2 优化方案：索引 + 按需加载

#### 方案 A：只读 README.md 索引（省 token 首选）

```
让 Claude 做测试时：
❌ "参考 Test_Team 的用例" → Claude 可能读全部 3119 行
✅ "参考 Test_Team/Test_Case/README.md 的 P0 用例清单" → 只读 97 行索引
✅ "参考 API_加班模块.md 的前 5 条用例" → 只读 1 个文件的部分
```

#### 方案 B：用例结构化（便于精确引用）

```markdown
## API_加班模块.md（优化后格式）

### TC_OT_001 | P0 | 工作日加班创建
- **接口**: POST /api/overtime
- **输入**: {"overtime_type":"weekday","date":"2026-07-07","start_time":"19:00","end_time":"21:00"}
- **期望**: 201, duration=2.0
- **对应自动化**: test_overtime.py::test_create_overtime_weekday
```

**Token 收益：** 结构化后 Claude 可以"按用例名引用"，无需读全文。

#### 方案 C：手工用例 ↔ 自动化用例映射表

```markdown
## 映射表（在 README.md 追加）

| 手工用例 | 自动化测试 | 状态 |
|---------|-----------|------|
| TC_OT_001 | test_overtime.py::test_create_overtime_weekday | ✅ 已自动化 |
| TC_OT_002 | test_overtime.py::test_create_overtime_weekend | ✅ 已自动化 |
| TC_OT_003 | — | ⏳ 待自动化 |
```

**Token 收益：** 一张表看清哪些手工用例已被自动化覆盖，避免重复写。

### 4.3 手工用例文档使用规范

| 操作 | 正确做法 | 避免 |
|------|---------|------|
| 查某模块有多少用例 | 读 README.md 索引 | 读完整 TC_*.md |
| 查某条用例详情 | `grep -n "TC_OT_003" TC_加班模块.md` | Read 整个文件 |
| 写自动化前先确认覆盖 | 读映射表 | 读全部 3119 行 |
| 批量检查自动化覆盖 | `grep "✅ 已自动化" README.md` | 逐文件读 |

---

## 五、测试执行 Token 优化

### 5.1 执行前：明确范围

```bash
# 日常开发（最省 token）
pytest -m p0 -q                    # 只跑 P0，安静模式

# 模块改动后
pytest tests/test_overtime.py -q   # 只跑相关模块

# 发版前
pytest -q                          # 全量

# 调试单个失败
pytest tests/test_overtime.py::test_name -q -s  # 单个用例 + 输出
```

### 5.2 执行中：控制输出

```bash
# 安静模式（只显示结果，不显示过程）
pytest -q

# 只显示失败（不显示通过的）
pytest -q --tb=line

# 失败时立即停止（不继续跑）
pytest -x

# 上次失败的优先跑
pytest --lf
```

### 5.3 执行后：结果分析

#### ❌ 浪费
```
pytest 全量跑完了，把结果分析一下，
哪些失败是代码问题，哪些是测试问题，
哪些需要修复，哪些可以跳过。
```

#### ✅ 节约
```
pytest -q --tb=line 结果：
- 失败 3 个：test_A, test_B, test_C
- 只报：用例名 + assert 行号 + 期望 vs 实际
- 不分析原因，不猜测，不扩展
```

---

## 六、测试调试 Token 优化（最重要）

测试调试是 token 消耗的**最大户**——反复读代码、读测试、读输出、改代码、再跑。

### 6.1 调试循环优化

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

### 6.2 调试信息模板

```
pytest <文件>::<用例名> -q 失败。
错误信息：<assert 行号 + 期望 vs 实际>
只读 <文件>:<行号范围> 的 <函数名> 函数。
不改其他代码。不分析原因，只定位。
```

### 6.3 避免重复读取

```
❌ 第 3 次问："test_overtime 还是失败" → Claude 重新读全部
✅ 第 3 次问："基于之前读的 app.py:45-60，问题在 lunch_end 判断。
            直接改第 52 行。"
```

---

## 七、测试代码质量与 Token 的关系

### 7.1 高质量测试代码 = 低 Token 消耗

| 质量属性 | 对 token 的影响 |
|---------|---------------|
| **单一职责**（一个用例只测一件事） | 失败时定位快，不用读多个场景 |
| **描述性命名**（`test_create_overtime_weekday_19_21`） | 用例名即文档，不用读测试体 |
| **无 magic number**（`EXPECTED_DURATION = 2.0`） | 断言失败时一眼看出期望值 |
| **共享 fixtures** | 测试文件短，读起来 token 少 |
| **参数化**（`@pytest.mark.parametrize`） | 1 个参数化用例替代 5 个重复用例 |

### 7.2 参数化示例

```python
# ❌ 浪费：5 个几乎相同的用例
def test_weekday_19_21(): ...
def test_weekday_19_22(): ...
def test_weekday_19_23(): ...
def test_weekend_09_17(): ...
def test_weekend_09_19(): ...

# ✅ 节约：1 个参数化用例
@pytest.mark.parametrize("otype,date,start,end,expected", [
    ("weekday", "2026-07-07", "19:00", "21:00", 2.0),
    ("weekday", "2026-07-07", "19:00", "22:00", 3.0),
    ("weekday", "2026-07-07", "19:00", "23:00", 4.0),
    ("weekend", "2026-07-11", "09:00", "17:00", 6.0),
    ("weekend", "2026-07-11", "09:00", "19:00", 8.0),
])
def test_overtime_duration(auth, client, otype, date, start, end, expected):
    r = client.post(f'{BASE_URL}/overtime', headers=auth,
                    json={"overtime_type": otype, "date": date,
                          "start_time": start, "end_time": end})
    assert r.json()['duration'] == expected
```

**Token 收益：** 修这 5 个场景的断言时，读 1 个函数而非 5 个。

---

## 八、测试报告 Token 优化

### 8.1 报告生成提示词

#### ❌ 浪费
```
把这次测试结果整理成一份详细的测试报告，
包括测试概述、执行情况、缺陷统计、风险分析、改进建议，
最好能按模块分开，每个模块列出通过率和失败用例。
```

#### ✅ 节约
```
pytest -q 结果 → 输出格式：
## 结果
通过: X / 失败: Y / 跳过: Z
## 失败清单
- test_name (文件:行号) — 期望 X 实际 Y
## 风险
只列 P0 失败项
其他不写
```

### 8.2 测试覆盖率报告

```bash
# 只报总体覆盖率（最省 token）
pytest --cov=app --cov-report=term-missing -q

# 只报某模块
pytest tests/test_overtime.py --cov=app --cov-report=term-missing -q
```

---

## 九、测试架构师 Token 优化检查清单

| # | 检查项 | 节省量级 | 优先级 |
|---|--------|---------|--------|
| 1 | 测试文件按模块拆分（单一职责） | 高 | P0 |
| 2 | conftest.py 共享 fixtures | 高 | P0 |
| 3 | pytest markers（p0/p1/p2, smoke/regression） | 高 | P0 |
| 4 | 调试时给 `file:line` 定位，不让 Claude 全量搜索 | 极高 | P0 |
| 5 | 手工用例只读 README.md 索引，不读全文 | 高 | P1 |
| 6 | 手工用例 ↔ 自动化映射表 | 中 | P1 |
| 7 | 参数化替代重复用例 | 中 | P1 |
| 8 | pytest -q --tb=line 安静模式 | 中 | P1 |
| 9 | 调试信息模板（用例名 + assert + 行号） | 极高 | P0 |
| 10 | 复用之前读过的代码，不重复 Read | 高 | P0 |
| 11 | 测试执行范围控制（日常 p0，发版全量） | 高 | P1 |
| 12 | 测试报告模板化（固定格式，不自由发挥） | 中 | P2 |

---

## 十、本项目测试优化路线图

### Phase 1：立即可做（0 代码改动）
- [ ] 测试提示词按本规范模板化
- [ ] 调试时强制给 `file:line` 定位
- [ ] 手工用例只读 README.md 索引
- [ ] pytest 执行加 `-q --tb=line`

### Phase 2：短期（1-2 小时）
- [ ] 创建 `tests/conftest.py`（共享 client/auth fixtures）
- [ ] 给现有测试加 `@pytest.mark.p0/p1/p2` markers
- [ ] 废弃 `test_server.py` / `test_server2.py` / `test_sql.py`（确认无价值后删除）

### Phase 3：中期（半天）
- [ ] 合并 `test_api.py` + `smoke_test.py` → `tests/test_smoke.py`
- [ ] 拆分 `test_api_comprehensive.py` → 按模块独立文件
- [ ] 给高频失败的用例加参数化
- [ ] 建立手工用例 ↔ 自动化映射表

### Phase 4：长期
- [ ] 手工用例 MD 文件结构化（每条用例固定格式：接口/输入/期望/映射）
- [ ] CI 集成（GitHub Actions / 本地 pre-commit hook 自动跑 p0）
- [ ] 测试覆盖率门禁（< 80% 不允许发版）
- [ ] 性能测试 / 并发测试独立套件（避免拖慢日常 smoke）

---

## 十一、测试 Token 消耗速查表

| 活动 | 浪费模式（token） | 节约模式（token） | 节省 |
|------|------------------|------------------|------|
| 写 1 个测试 | 读源码全文 + 写 + 解释（3000） | 给函数名 + 行号 + 期望（800） | 73% |
| 调试 1 次失败 | 读测试 + 读源码 + 猜（4000） | 给 assert + 行号 + 只读函数（600） | 85% |
| 跑全量测试 | 读全部测试文件 + 分析（5000） | pytest -q --tb=line（500） | 90% |
| 查手工用例 | 读 3119 行 MD（6000） | 读 README 索引（200） | 97% |
| 生成测试报告 | 自由格式长篇（2000） | 固定模板 3 行（200） | 90% |
| 调试循环（5轮） | 每轮重读全部（15000） | 每轮只读差异行（3000） | 80% |

---

> 💡 **测试架构师的核心洞察：** 测试活动的 token 浪费主要不在"写测试"，而在"调试循环"。
> 80% 的 token 花在反复读代码、反复猜测、反复修改上。
> 省 token 的最强手段是：**精确给定位（file:line）+ 控制范围（只读什么）+ 复用之前的结果（不重复读）**。