"""接口冒烟测试：覆盖 9 个接口，并做一次「导出 → 清空 → 导入」的往返一致性验证。

用法（先启动 app.py）::

    python tests/smoke_test.py

脚本只用标准库，不引入额外依赖；跑完后会重新灌入种子数据。
"""
import json
import os
import sys
import urllib.error
import urllib.request
from io import BytesIO
from urllib.parse import quote

BASE = "http://127.0.0.1:5000"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    """记录一条断言结果。"""
    if condition:
        PASSED.append(name)
        print("[PASS] {}{}".format(name, (" - " + detail) if detail else ""))
    else:
        FAILED.append(name)
        print("[FAIL] {}{}".format(name, (" - " + detail) if detail else ""))


def http_json(method, path, payload=None):
    """发一个 JSON 请求并返回解析后的响应体。"""
    url = BASE + path
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def http_bytes(path):
    """下载二进制响应。"""
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        return response.read()


def http_upload(path, filename, content):
    """以 multipart/form-data 上传一个文件。"""
    boundary = "----SmokeTestBoundary"
    body = (
        "--{}\r\n".format(boundary).encode("utf-8")
        + 'Content-Disposition: form-data; name="file"; filename="{}"\r\n'.format(
            filename
        ).encode("utf-8")
        + b"Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet\r\n\r\n"
        + content
        + "\r\n--{}--\r\n".format(boundary).encode("utf-8")
    )
    request = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize(contacts):
    """把联系人列表归一化成可比较的结构（忽略 id 与顺序）。"""
    items = []
    for contact in contacts:
        items.append(
            (
                contact["name"],
                contact.get("company", ""),
                contact.get("note", ""),
                bool(contact.get("isFavorite")),
                tuple(
                    (method["type"], method.get("label", ""), method["value"])
                    for method in contact.get("methods", [])
                ),
            )
        )
    return sorted(items)


def test_crud():
    """列表、筛选、搜索、详情、增删改、收藏。"""
    result = http_json("GET", "/api/contacts")
    check("GET /api/contacts 返回 code=0", result["code"] == 0)
    base_count = len(result["data"])
    check("列表非空", base_count >= 5, "{} 条".format(base_count))

    favorite_list = http_json("GET", "/api/contacts?favorite=1")["data"]
    check(
        "favorite=1 只返回收藏",
        len(favorite_list) >= 2 and all(item["isFavorite"] for item in favorite_list),
        "{} 条".format(len(favorite_list)),
    )

    keyword_list = http_json("GET", "/api/contacts?keyword=" + quote("福州"))["data"]
    check("keyword 搜索可用", len(keyword_list) >= 1, "{} 条".format(len(keyword_list)))

    detail = http_json("GET", "/api/contacts/{}".format(result["data"][0]["id"]))
    check("GET 详情含 methods", detail["code"] == 0 and "methods" in detail["data"])

    created = http_json(
        "POST",
        "/api/contacts",
        {
            "name": "测试新增",
            "company": "测试公司",
            "note": "冒烟测试",
            "isFavorite": False,
            "methods": [
                {"type": "phone", "label": "手机", "value": "13500000000"},
                {"type": "email", "label": "工作邮箱", "value": "test@example.com"},
            ],
        },
    )
    contact_id = created["data"]["id"]
    check("POST 新增成功", created["code"] == 0 and contact_id > 0)
    check("POST 返回 methods 两条", len(created["data"]["methods"]) == 2)

    updated = http_json(
        "PUT",
        "/api/contacts/{}".format(contact_id),
        {
            "name": "测试更新",
            "company": "测试公司2",
            "note": "",
            "isFavorite": True,
            "methods": [{"type": "wechat", "label": "微信", "value": "test_wx"}],
        },
    )
    check(
        "PUT 全量更新",
        updated["data"]["name"] == "测试更新"
        and len(updated["data"]["methods"]) == 1
        and updated["data"]["isFavorite"] is True,
    )

    favorited = http_json(
        "POST", "/api/contacts/{}/favorite".format(contact_id), {"isFavorite": False}
    )
    check("POST favorite 取消收藏", favorited["data"]["isFavorite"] is False)

    deleted = http_json("DELETE", "/api/contacts/{}".format(contact_id))
    check("DELETE 返回 id", deleted["code"] == 0 and deleted["data"]["id"] == contact_id)

    missing = http_json("GET", "/api/contacts/{}".format(contact_id))
    check("删除后详情返回 code!=0", missing["code"] != 0, missing.get("message", ""))

    invalid = http_json("POST", "/api/contacts", {"name": "", "methods": []})
    check("空姓名被拒绝", invalid["code"] != 0)


def test_excel_roundtrip():
    """导出 → 清空 → 导入 → 比对，验证往返一致。"""
    from openpyxl import load_workbook

    snapshot = http_json("GET", "/api/contacts")["data"]
    exported = http_bytes("/api/export")

    workbook = load_workbook(BytesIO(exported))
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    from utils.excel_schema import HEADERS

    check("导出表头与契约一致", tuple(headers) == HEADERS)
    check(
        "导出一行一联系人",
        sheet.max_row - 1 == len(snapshot),
        "{} 行数据".format(sheet.max_row - 1),
    )

    template = load_workbook(BytesIO(http_bytes("/api/export/template"))).active
    check("模板只有表头", template.max_row == 1)

    for contact in snapshot:
        http_json("DELETE", "/api/contacts/{}".format(contact["id"]))
    check("清空后列表为空", len(http_json("GET", "/api/contacts")["data"]) == 0)

    imported = http_upload("/api/import", "contacts.xlsx", exported)
    check(
        "导入成功且无错误",
        imported["code"] == 0 and imported["data"]["inserted"] == len(snapshot),
        str(imported.get("data")),
    )

    restored = http_json("GET", "/api/contacts")["data"]
    check(
        "往返一致（字段含 label 完全还原）",
        normalize(restored) == normalize(snapshot),
        "{} vs {}".format(len(restored), len(snapshot)),
    )
    return snapshot


def test_import_errors():
    """表头不符与空姓名的容错。"""
    from openpyxl import Workbook

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["姓名", "公司"])  # 故意缺列
    sheet.append(["某人", "某公司"])
    stream = BytesIO()
    workbook.save(stream)
    bad = http_upload("/api/import", "bad.xlsx", stream.getvalue())
    check("表头不符返回 1001", bad["code"] == 1001, bad.get("message", ""))

    workbook2 = Workbook()
    sheet2 = workbook2.active
    from utils.excel_schema import HEADERS

    sheet2.append(list(HEADERS))
    sheet2.append(["", "无姓名公司", ""] + [""] * 9)
    sheet2.append(["有姓名", "", ""] + [""] * 9)
    stream2 = BytesIO()
    workbook2.save(stream2)
    mixed = http_upload("/api/import", "mixed.xlsx", stream2.getvalue())
    check(
        "空姓名被跳过并记入 errors",
        mixed["code"] == 0
        and mixed["data"]["skipped"] == 1
        and mixed["data"]["inserted"] == 1
        and any("姓名不能为空" in item for item in mixed["data"]["errors"]),
        str(mixed.get("data")),
    )


def main():
    """依次执行三组测试并汇总。"""
    print("=" * 60)
    try:
        test_crud()
        test_excel_roundtrip()
        test_import_errors()
    except (urllib.error.URLError, ConnectionError) as exc:
        print("无法连接服务，请先运行 python app.py：{}".format(exc))
        return 2

    print("=" * 60)
    print("通过 {} 项，失败 {} 项".format(len(PASSED), len(FAILED)))
    if FAILED:
        for name in FAILED:
            print("  失败：{}".format(name))
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
