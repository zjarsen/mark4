# 广播门户 (Broadcast Portal)

一个基于 Flask 的 Web 应用，用于向 Telegram 机器人用户发送广播消息。

## 功能特性

### 1. 用户筛选系统
- **VIP等级筛选**: 普通用户、VIP用户、黑金VIP
- **积分余额筛选**: 设置最小/最大积分余额范围
- **活跃时间筛选**: 根据用户最后活跃时间筛选
- **用户类型筛选**: 付费用户 vs 免费用户
- **实时用户计数**: 根据筛选条件实时显示匹配的用户数量

### 2. 消息编辑器
- **Markdown / HTML 格式支持**: 支持粗体、斜体、链接等格式
- **内联按钮**: 添加带有链接的内联按钮
- **实时预览**: 在发送前预览消息格式
- **草稿功能**: 保存、加载和删除消息草稿

### 3. 安全功能
- **测试发送**: 先发送给自己测试消息效果
- **发送确认**: 弹窗确认以避免误操作
- **进度跟踪**: 显示发送进度和结果统计

### 4. 历史记录
- **查看历史**: 查看所有已发送的广播记录
- **详细信息**: 查看每条广播的详细信息和筛选条件
- **消息复用**: 从历史记录中复用消息内容

## 安装说明

### 前置条件

确保已安装以下依赖：
- Python 3.8+
- pip

### 安装步骤

1. **安装 Python 依赖**

```bash
cd /home/zj-ars/test_server/mark4
pip install flask python-telegram-bot python-dotenv
```

2. **配置环境变量**

确保 `.env` 文件包含以下配置：

```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_PATH=data/mark4_bot.db
BROADCAST_PORT=5002  # 可选，默认 5002
```

3. **启动广播门户**

```bash
cd /home/zj-ars/test_server/mark4/broadcast
python app.py
```

或者从项目根目录启动：

```bash
cd /home/zj-ars/test_server/mark4
python -m broadcast.app
```

4. **访问 Web 界面**

在浏览器中打开：
```
http://localhost:5002
```

## 使用指南

### 发送广播消息

1. **设置筛选条件**
   - 在左侧面板勾选要包含的用户类型
   - 可选：设置积分余额范围、活跃时间等
   - 查看匹配的用户数量

2. **编写消息**
   - 在中间面板的文本框中输入消息内容
   - 选择 Markdown 或 HTML 格式
   - 可选：添加内联按钮
   - 在右侧面板查看实时预览

3. **测试发送**
   - 输入你的 Telegram ID（只需一次）
   - 点击"测试发送"按钮
   - 在你的 Telegram 中检查消息效果

4. **发送广播**
   - 点击"发送广播"按钮
   - 确认发送对象数量
   - 等待发送完成
   - 查看成功/失败统计

### 使用草稿

1. **保存草稿**
   - 编写完消息后点击"保存草稿"
   - 输入草稿名称
   - 草稿将出现在左侧草稿箱中

2. **加载草稿**
   - 在草稿箱中点击草稿名称
   - 消息内容和设置会自动填充

3. **删除草稿**
   - 点击草稿旁边的垃圾桶图标

### 查看历史

1. 点击顶部导航栏的"历史记录"
2. 查看所有已发送的广播列表
3. 点击"查看详情"按钮查看完整信息
4. 点击"复用此消息"将历史消息加载到编辑器

## Markdown 格式示例

```markdown
**粗体文字**
*斜体文字*
_下划线文字_
[链接文字](https://example.com)

这是一条广播消息示例
```

## 技术架构

### 后端
- **Flask**: Web 框架
- **python-telegram-bot**: Telegram Bot API 封装
- **SQLite**: 用户数据库
- **JSON**: 历史记录和草稿存储

### 前端
- **Bootstrap 5**: UI 框架
- **Bootstrap Icons**: 图标库
- **Vanilla JavaScript**: 前端交互逻辑

### 文件结构

```
broadcast/
├── app.py                          # Flask 应用主文件
├── services/
│   └── broadcast_service.py        # 广播服务核心逻辑
├── templates/
│   ├── base.html                   # 基础模板
│   ├── dashboard.html              # 主界面
│   └── history.html                # 历史记录页面
├── static/
│   ├── css/
│   │   └── broadcast.css           # 自定义样式
│   └── js/
│       └── broadcast.js            # JavaScript 工具函数
├── data/
│   ├── history.json                # 广播历史记录
│   └── drafts.json                 # 消息草稿
└── README.md                       # 本文件
```

## API 端点

### GET `/`
主仪表盘页面

### GET `/history`
历史记录页面

### POST `/api/users/count`
获取匹配筛选条件的用户数量

**请求体:**
```json
{
  "filters": {
    "vip_tiers": ["none", "vip"],
    "min_balance": 0,
    "max_balance": 100
  }
}
```

**响应:**
```json
{
  "count": 42
}
```

### POST `/api/broadcast/test`
发送测试消息给管理员

**请求体:**
```json
{
  "message": "测试消息",
  "parse_mode": "Markdown",
  "buttons": [[{"text": "按钮", "url": "https://example.com"}]],
  "admin_id": 123456789
}
```

### POST `/api/broadcast/send`
发送广播消息

**请求体:**
```json
{
  "message": "广播消息",
  "parse_mode": "Markdown",
  "filters": {...},
  "buttons": [...]
}
```

**响应:**
```json
{
  "successful": 40,
  "failed": 2,
  "failed_users": [123, 456]
}
```

### GET `/api/drafts`
获取所有草稿

### POST `/api/drafts`
保存新草稿

### DELETE `/api/drafts/<draft_id>`
删除指定草稿

## 注意事项

1. **Telegram API 限制**
   - 每秒最多发送 30 条消息
   - 应用已实现自动速率限制（35ms 延迟）

2. **用户屏蔽**
   - 如果用户屏蔽了机器人，发送会失败
   - 失败的发送会被记录但不会中断进程

3. **消息格式**
   - Markdown 和 HTML 格式需遵循 Telegram 规范
   - 错误的格式可能导致发送失败

4. **数据存储**
   - 历史记录保存在 `data/history.json`
   - 草稿保存在 `data/drafts.json`
   - 最多保留 100 条历史记录

## 故障排除

### 端口已被占用

如果 5002 端口被占用，修改 `.env` 文件：
```env
BROADCAST_PORT=5003
```

### 无法连接到数据库

确保 `DATABASE_PATH` 指向正确的数据库文件：
```bash
ls -l /home/zj-ars/test_server/mark4/data/mark4_bot.db
```

### 发送失败

1. 检查 `BOT_TOKEN` 是否正确
2. 确认机器人有发送消息的权限
3. 检查用户是否屏蔽了机器人

### 用户数量显示为 0

1. 检查数据库中是否有用户数据
2. 确认筛选条件是否过于严格
3. 尝试点击"重置筛选"按钮

## 开发与扩展

### 添加新的筛选条件

1. 在 `broadcast_service.py` 的 `get_target_users()` 方法中添加 SQL 查询逻辑
2. 在 `dashboard.html` 的筛选器部分添加 UI 控件
3. 在 `getFilters()` JavaScript 函数中添加数据收集逻辑

### 自定义样式

编辑 `static/css/broadcast.css` 文件以修改样式。

### 添加新功能

1. 在 `app.py` 中添加新的 Flask 路由
2. 在相应的模板中添加 UI
3. 在 `broadcast_service.py` 中实现业务逻辑

## 许可证

本项目仅供内部使用。

## 支持

如有问题或建议，请联系开发团队。
