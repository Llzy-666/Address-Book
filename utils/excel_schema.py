"""Excel 表头定义以及「表格行 <-> 联系人对象」的双向转换。

本模块只依赖标准库，集中管理四件事：

1. 12 列表头的固定顺序（导入导出共用同一份常量，杜绝两边写歪）；
2. 联系方式类型枚举与各类型的默认中文标签；
3. 导出时的槽位分配——同类型联系方式超出槽位数量时，用换行拼接在
   该类型最后一列里，保证不丢数据；
4. 导入时的单元格解析——支持 ``标签:值`` 写法，从而实现导出后再导入
   的往返一致（round-trip）。

约定：``label`` 为空时一律回落为该类型的默认标签；导出时若 ``label``
正好等于默认标签，则只写值本身，不写 ``标签:`` 前缀，让表格保持干净。
"""

TYPE_PHONE = "phone"
TYPE_EMAIL = "email"
TYPE_WECHAT = "wechat"
TYPE_ADDRESS = "address"
TYPE_OTHER = "other"

#: 允许的联系方式类型，顺序即前端下拉框顺序。
METHOD_TYPES = (TYPE_PHONE, TYPE_EMAIL, TYPE_WECHAT, TYPE_ADDRESS, TYPE_OTHER)

#: 各类型的默认中文标签。
DEFAULT_LABELS = {
    TYPE_PHONE: "手机",
    TYPE_EMAIL: "邮箱",
    TYPE_WECHAT: "微信",
    TYPE_ADDRESS: "地址",
    TYPE_OTHER: "其他",
}

COL_NAME = "姓名"
COL_COMPANY = "公司"
COL_NOTE = "备注"
COL_FAVORITE = "是否收藏"
COL_PHONE_1 = "联系人电话1"
COL_PHONE_2 = "联系人电话2"
COL_PHONE_3 = "联系人电话3"
COL_EMAIL_1 = "邮箱1"
COL_EMAIL_2 = "邮箱2"
COL_WECHAT = "微信号"
COL_ADDRESS = "地址"
COL_OTHER = "其他"

#: 表头固定顺序，导入时必须逐列比对。
HEADERS = (
    COL_NAME,
    COL_COMPANY,
    COL_NOTE,
    COL_FAVORITE,
    COL_PHONE_1,
    COL_PHONE_2,
    COL_PHONE_3,
    COL_EMAIL_1,
    COL_EMAIL_2,
    COL_WECHAT,
    COL_ADDRESS,
    COL_OTHER,
)

#: 每种类型占用的列，顺序即填充顺序。
COLUMN_SLOTS = {
    TYPE_PHONE: (COL_PHONE_1, COL_PHONE_2, COL_PHONE_3),
    TYPE_EMAIL: (COL_EMAIL_1, COL_EMAIL_2),
    TYPE_WECHAT: (COL_WECHAT,),
    TYPE_ADDRESS: (COL_ADDRESS,),
    TYPE_OTHER: (COL_OTHER,),
}

FAVORITE_YES = "是"
FAVORITE_NO = "否"

#: 解析 ``标签:值`` 时，标签里不允许出现的字符，避免把网址、邮箱误判成标签。
_LABEL_FORBIDDEN_CHARS = ("/", "\\", "@")
_LABEL_MAX_LENGTH = 20
_MAX_NAME_LENGTH = 50
_MAX_VALUE_LENGTH = 200


def normalize_type(method_type):
    """把任意输入收敛到合法的类型枚举，非法值按 other 处理。"""
    text = (method_type or "").strip().lower()
    return text if text in METHOD_TYPES else TYPE_OTHER


def normalize_label(method_type, label):
    """标签为空时回落为该类型的默认中文标签。"""
    text = (label or "").strip()
    if text:
        return text
    return DEFAULT_LABELS.get(normalize_type(method_type), DEFAULT_LABELS[TYPE_OTHER])


def _cell_text(method):
    """把一条联系方式渲染成单元格文本。"""
    method_type = normalize_type(method.get("type"))
    value = (method.get("value") or "").strip()
    label = normalize_label(method_type, method.get("label"))
    if label and label != DEFAULT_LABELS.get(method_type):
        return "{}:{}".format(label, value)
    return value


def contact_to_row(contact):
    """把一个联系人对象转换成 12 列的一行数据。"""
    row = dict.fromkeys(HEADERS, "")
    row[COL_NAME] = (contact.get("name") or "").strip()
    row[COL_COMPANY] = (contact.get("company") or "").strip()
    row[COL_NOTE] = (contact.get("note") or "").strip()
    row[COL_FAVORITE] = FAVORITE_YES if contact.get("isFavorite") else FAVORITE_NO

    buckets = {method_type: [] for method_type in METHOD_TYPES}
    for method in contact.get("methods") or []:
        method_type = normalize_type(method.get("type"))
        buckets[method_type].append(_cell_text(method))

    for method_type, slots in COLUMN_SLOTS.items():
        texts = buckets[method_type]
        filled = texts[: len(slots)]
        overflow = texts[len(slots):]
        for index, column in enumerate(slots):
            row[column] = filled[index] if index < len(filled) else ""
        if overflow:
            last_column = slots[-1]
            head = [row[last_column]] if row[last_column] else []
            row[last_column] = "\n".join(head + overflow)

    return [row[header] for header in HEADERS]


def parse_entry(text):
    """把单元格中的一条记录拆成 ``(label, value)``。

    没写 ``标签:`` 前缀时 label 返回 None，由调用方补默认标签。
    """
    raw = (text or "").strip()
    if ":" in raw:
        prefix, _, rest = raw.partition(":")
        prefix = prefix.strip()
        rest = rest.strip()
        looks_like_label = (
            prefix
            and rest
            and len(prefix) <= _LABEL_MAX_LENGTH
            and not any(ch in prefix for ch in _LABEL_FORBIDDEN_CHARS)
        )
        if looks_like_label:
            return prefix, rest
    return None, raw


def cell_to_methods(text, method_type):
    """把一个单元格拆成若干条联系方式（换行分隔，空行忽略）。"""
    methods = []
    for part in str(text or "").splitlines():
        part = part.strip()
        if not part:
            continue
        label, value = parse_entry(part)
        value = value.strip()
        if not value:
            continue
        if len(value) > _MAX_VALUE_LENGTH:
            value = value[:_MAX_VALUE_LENGTH]
        methods.append(
            {
                "type": method_type,
                "label": label or DEFAULT_LABELS[method_type],
                "value": value,
            }
        )
    return methods


def parse_row(values, line_no):
    """把一行 Excel 数据转换成联系人字典。

    返回 ``(contact, errors)``；姓名为空时 contact 为 None。
    """
    cells = [("" if value is None else str(value)).strip() for value in values]
    cells += [""] * (len(HEADERS) - len(cells))
    mapping = dict(zip(HEADERS, cells))

    name = mapping[COL_NAME]
    if not name:
        return None, ["第{}行：姓名不能为空".format(line_no)]
    if len(name) > _MAX_NAME_LENGTH:
        name = name[:_MAX_NAME_LENGTH]

    methods = []
    for method_type, slots in COLUMN_SLOTS.items():
        for column in slots:
            methods.extend(cell_to_methods(mapping[column], method_type))

    contact = {
        "name": name[:50],
        "company": mapping[COL_COMPANY],
        "note": mapping[COL_NOTE],
        "isFavorite": mapping[COL_FAVORITE] == FAVORITE_YES,
        "methods": methods,
    }
    return contact, []


def header_matches(values):
    """逐列比对表头是否与模板完全一致（顺序也要一致）。"""
    cells = [("" if value is None else str(value)).strip() for value in values]
    cells += [""] * (len(HEADERS) - len(cells))
    return tuple(cells[: len(HEADERS)]) == HEADERS
