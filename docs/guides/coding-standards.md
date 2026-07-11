# 编码规范

## Python 后端

### 代码风格
- 遵循 PEP 8
- 使用 4 空格缩进
- 行长度限制 120 字符
- 使用 `snake_case` 命名

### 函数规范
```python
def get_articles():
    """获取文章列表"""
    # 1. 获取参数
    page, page_size = clamp_pagination(...)
    
    # 2. 构建查询
    conditions = ['user_id = ?']
    params = [g.user_id]
    
    # 3. 执行查询
    cursor.execute(query, params)
    
    # 4. 返回结果
    return jsonify(result)
```

### 错误处理
```python
# 使用 safe_get_json() 解析请求体
data, err = safe_get_json()
if err:
    return err

# 使用 safe_commit() 提交事务
err = safe_commit(db)
if err:
    return err
```

### 日志记录
```python
import logging
logger = logging.getLogger(__name__)

# 记录警告和错误
logger.warning('操作失败: %s', e)
logger.error('严重错误: %s', e)
```

## 前端 JS

### 命名规范
- 变量/函数: `camelCase`
- 常量: `UPPER_SNAKE_CASE`
- DOM ID: `camelCase`

### 函数结构
```javascript
// 异步函数
async function loadArticles() {
    try {
        const result = await apiRequest('/articles');
        renderArticles(result.articles);
    } catch (error) {
        console.error('加载失败:', error);
    }
}
```

### 安全规则
- 所有用户输入必须 `escapeHtml()` 后再拼入 innerHTML
- 使用 `_$()` 缓存 DOM 查询
- API 调用统一使用 `apiRequest()`

## Git 规范

### Commit 格式
```
<type>: <description>

[optional body]
```

### 类型
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

### 示例
```
feat: 添加密码修改功能
fix: 修复分页按钮对齐问题
docs: 更新认证模块文档
```

## 文档规范

### Obsidian 文档
- 使用 `[[]]` 链接相关文档
- 使用 `#tag` 标签分类
- 保持文档间互链

### 代码注释
- 函数 docstring 描述用途
- 复杂逻辑添加行注释
- 不重复代码已表达的信息

## 测试规范

### 单元测试
```python
def test_register():
    """测试用户注册"""
    # Arrange
    data = {'username': 'test', 'password': 'Test1234'}
    
    # Act
    response = client.post('/api/auth/register', json=data)
    
    # Assert
    assert response.status_code == 201
```

### API 测试
```python
def test_login():
    """测试登录"""
    # 注册
    client.post('/api/auth/register', json=register_data)
    
    # 登录
    response = client.post('/api/auth/login', json=login_data)
    
    # 验证
    assert 'token' in response.json
```
