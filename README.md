# 通讯录 · Web 版（极限编程作业）

软件工程（FZU–MU）Extreme Programming 课程作业。一个可用的 Web 通讯录：
支持**收藏联系人**、**一人多联系方式（一对多）**、**Excel 导入导出**，以及配套的搜索与演示素材。

技术栈刻意保持"零构建"：后端 Flask + 标准库 sqlite3，前端原生 HTML/CSS/JS，打开页面即可用，任何一台装了 Python 的电脑都能跑。

---

## 一、功能清单

| 功能 | 说明 |
| --- | --- |
| 联系人增删改查 | 姓名、公司、备注、收藏状态 |
| 收藏（书签） | 星标即时切换并落库，「只看收藏」筛选 |
| 多联系方式 | 一个联系人可挂多条，类型含 电话/邮箱/微信/地址/其他，可动态增删行 |
| 关键词搜索 | 姓名、公司、备注、联系方式值四类字段模糊匹配 |
| Excel 导出 | 一行一联系人，多联系方式按类型分列；超出槽位用换行拼接，不丢数据 |
| Excel 导入 | 固定表头校验、空姓名跳过、单事务写入、错误明细回传 |
| 导入模板 | 一键下载空白模板 |

## 二、技术栈

- Python 3.10+（开发环境 3.12.6）
- Flask（含 flask-cors）
- SQLite（标准库 `sqlite3`，**不使用 ORM**）
- openpyxl（Excel 读写）
- 前端：原生 HTML5 / CSS3 / ES6，**无框架、无构建工具、无外链 CDN**

## 三、目录结构

```
极限编程作业/
├── app.py                  # Flask 入口：注册蓝图、CORS、静态托管、错误兜底
├── db.py                   # 连接、建表、初始化、清库
├── seed.py                 # 种子数据（5 个联系人，2 个收藏，4 个多条联系方式）
├── requirements.txt
├── README.md
├── .gitignore
├── api/
│   ├── __init__.py
│   ├── contacts.py         # 联系人 CRUD + 收藏 + 多联系方式
│   └── excel_io.py         # 导入 / 导出 / 模板
├── utils/
│   ├── __init__.py
│   └── excel_schema.py     # 表头常量、行 <-> 对象转换
├── data/                   # SQLite 文件（运行时生成，不入版本库）
├── static/                 # 前端
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── templates/              # 预留目录（本作业前端为纯静态，未使用模板渲染）
├── tests/
│   └── smoke_test.py       # 接口冒烟 + Excel 往返一致性测试
└── docs/
    ├── 演示脚本.md
    └── deploy.md
```

## 四、快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 灌入演示数据（可选，但录视频前建议执行）

```bash
python seed.py
```

会清空现有数据并写入 5 个联系人，便于截图与录屏。

### 3. 启动

```bash
python app.py
```

浏览器打开 <http://127.0.0.1:5000/> 即可。

> 服务监听 `0.0.0.0:5000`，同一局域网的手机也能访问（`http://你的内网IP:5000/`），方便演示响应式布局。

### 4. 跑接口测试（可选）

另开一个终端，保持服务运行：

```bash
python tests/smoke_test.py
```

覆盖 9 个接口，并做一次「导出 → 清空 → 导入 → 比对」的往返验证。

## 五、接口文档

统一返回结构：

- 成功：`{"code": 0, "data": ...}`
- 失败：`{"code": 非0, "message": "中文错误提示"}`

字段一律 **camelCase**。所有接口已开启 CORS（允许所有来源），前端可直接跨端口调用。

### 联系人对象

```json
{
  "id": 1,
  "name": "张三",
  "company": "福州某公司",
  "note": "大学同学",
  "isFavorite": true,
  "methods": [
    {"type": "phone", "label": "手机", "value": "13800000000"},
    {"type": "email", "label": "工作邮箱", "value": "zhangsan@x.com"}
  ]
}
```

`type` 枚举仅限：`phone` / `email` / `wechat` / `address` / `other`，非法值按 `other` 处理。
`label` 可为空，为空时后端回落为该类型的默认中文标签（手机 / 邮箱 / 微信 / 地址 / 其他）。

---

### 1) 列表 / 筛选 / 搜索

```
GET /api/contacts?favorite=1&keyword=福州
```

两个参数都可省略。排序规则：收藏优先，其次按更新时间倒序。

```json
{"code": 0, "data": [ {联系人对象}, {联系人对象} ]}
```

### 2) 详情

```
GET /api/contacts/1
```

```json
{"code": 0, "data": {"id": 1, "name": "张三", "methods": [ ... ]}}
```

不存在时返回 `{"code": 404, "message": "联系人不存在"}`。

### 3) 新增

```
POST /api/contacts
Content-Type: application/json

{
  "name": "李四",
  "company": "厦门某公司",
  "note": "前同事",
  "isFavorite": false,
  "methods": [
    {"type": "phone", "label": "手机", "value": "13900000001"},
    {"type": "wechat", "label": "", "value": "lisi_wx"}
  ]
}
```

校验规则：`name` 非空且 ≤ 50 字；每条 method 的 `value` 非空且 ≤ 200 字。
成功返回新建的完整联系人对象（含 `id`）。

失败示例：

```json
{"code": 1, "message": "姓名不能为空"}
```

### 4) 修改（全量）

```
PUT /api/contacts/1
```

请求体同新增。**全量更新语义**：先删除该联系人旧的联系方式，再按请求体重新插入，
因此前端每次提交都要带上完整的 `methods` 数组。返回更新后的对象。

### 5) 删除

```
DELETE /api/contacts/1
```

```json
{"code": 0, "data": {"id": 1}}
```

联系方式随外键 `ON DELETE CASCADE` 一并删除。

### 6) 收藏 / 取消收藏

```
POST /api/contacts/1/favorite
Content-Type: application/json

{"isFavorite": true}
```

返回更新后的联系人对象。

### 7) 导出 Excel

```
GET /api/export
```

直接返回文件下载，响应头：

```
Content-Disposition: attachment; filename=contacts_YYYYMMDD.xlsx
```

### 8) 下载导入模板

```
GET /api/export/template
```

返回只有表头一行的空白 xlsx。

### 9) 导入 Excel

```
POST /api/import
Content-Type: multipart/form-data
字段名: file
```

成功示例：

```json
{
  "code": 0,
  "data": {
    "inserted": 5,
    "skipped": 0,
    "errors": []
  }
}
```

带容错的示例（第 3 行姓名为空）：

```json
{
  "code": 0,
  "data": {
    "inserted": 4,
    "skipped": 1,
    "errors": ["第3行：姓名不能为空"]
  }
}
```

错误码：

| code | 含义 |
| --- | --- |
| 1001 | 表头不符 / 不是 `.xlsx` / 文件无法解析 |
| 1002 | 写库失败，整批已回滚 |

### 错误兜底

未匹配的路由、方法不允许、上传超限、服务器异常，全部返回 JSON 的 `code` 结构，
不会吐 HTML 错误页：

```json
{"code": 404, "message": "请求的资源不存在"}
```

## 六、Excel 格式说明

### 表头（第一行固定，顺序固定，不可增删）

```
姓名 | 公司 | 备注 | 是否收藏 | 联系人电话1 | 联系人电话2 | 联系人电话3 | 邮箱1 | 邮箱2 | 微信号 | 地址 | 其他
```

### 导出规则

- 一个联系人占一行。
- 联系方式按类型落到对应列：`phone` → 电话1/2/3，`email` → 邮箱1/2，`wechat` → 微信号，`address` → 地址，`other` → 其他。
- 同类型数量超出槽位时，多出的值用**换行**拼接到该类型最后一列的同一个单元格里，不会丢数据。
- `是否收藏` 写「是」/「否」。
- 样式：首行加粗、冻结首行；列宽设为 姓名 14、公司 20、地址 30 等便于阅读的值。

### 标签（label）如何处理

`label` 不占独立列。当 `label` 与类型默认名不同（例如「工作邮箱」）时，该单元格写成
`标签:值` 的形式，例如：

| 邮箱1 |
| --- |
| 工作邮箱:zhangsan@example.com |

导入时会识别 `标签:` 前缀并还原成对应的 label，因此**导出后再导入可以 100% 还原**，
包括自定的标签。`tests/smoke_test.py` 里的「往返一致」断言就是在验证这一点。

### 导入规则

- 必须是 `.xlsx`；表头逐列比对，缺列或顺序不符 → `code=1001`，提示「表头不符合模板，请下载模板后填写」。
- 姓名为空的行跳过，并记入 `errors`；空单元格直接跳过，不生成对应 method。
- `是否收藏` 只识别「是」为 true，其余一律 false。
- 整批写入放在一个事务里，任一行写库失败即回滚并返回 `code=1002`。
- 导入完成后控制台打印 `[import] inserted=n skipped=m`。

### 导出 → 导入的往返示例

```bash
# 1. 导出
curl -o contacts.xlsx http://127.0.0.1:5000/api/export
# 2. 清空后重新导入
curl -F "file=@contacts.xlsx" http://127.0.0.1:5000/api/import
# 3. 数据与原库一致（含自定义 label）
```

## 七、数据库设计

```sql
contacts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  company TEXT,
  note TEXT,
  is_favorite INTEGER NOT NULL DEFAULT 0,
  created_at TEXT,
  updated_at TEXT
);

contact_methods(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  contact_id INTEGER NOT NULL,
  type TEXT NOT NULL,
  label TEXT,
  value TEXT NOT NULL,
  sort_order INTEGER DEFAULT 0,
  FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);
```

- 每个连接都执行 `PRAGMA foreign_keys = ON`，保证级联删除生效。
- `is_favorite` 以 0/1 存储，对外输出为布尔 `isFavorite`。

## 八、安全与规范

- 所有 SQL 使用参数化占位符，不做字符串拼接。
- 服务端二次校验姓名长度与联系方式值长度，前端校验只是体验优化。
- 遵循 PEP8：snake_case 命名、常量全大写、函数短小、每个接口函数带中文 docstring。
- 前端 `app.js` 分三层：`request()` 统一解包 `code/message`、`render` 渲染、事件绑定；CSS 用变量统一色板并带 BEM 风格类名。

## 九、常见问题

**Q：`Address already in use` / 5000 端口被占用？**
Windows 上 5000 端口可能被系统服务占用。改 `app.py` 末尾的 `port=5000` 为 `5001`，
前端同源访问无需改任何 JS。

**Q：导入报「表头不符合模板」？**
务必先点「下载模板」，在模板文件里填写，不要自己新建表头或调整列序。

**Q：数据库想重置？**
删掉 `data/address_book.db`，或直接跑 `python seed.py`（会清空并重建种子数据）。
