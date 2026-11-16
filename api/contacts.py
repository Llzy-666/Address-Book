"""联系人增删改查、收藏与多联系方式接口。

统一返回结构：成功 ``{"code": 0, "data": ...}``；失败 ``{"code": 非0, "message": "中文提示"}``。
所有 SQL 一律使用参数化占位符，不做字符串拼接。
"""
from datetime import datetime

from flask import Blueprint, jsonify, request

import db
from utils.excel_schema import DEFAULT_LABELS, METHOD_TYPES, normalize_label, normalize_type

contacts_bp = Blueprint("contacts", __name__, url_prefix="/api")

NAME_MAX_LENGTH = 50
VALUE_MAX_LENGTH = 200


def ok(data):
    """构造成功响应。"""
    return jsonify({"code": 0, "data": data})


def fail(message, code=1):
    """构造失败响应。"""
    return jsonify({"code": code, "message": message})


def _now():
    """当前时间字符串，用于 created_at / updated_at。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_methods(connection, contact_id):
    """读取某个联系人的全部联系方式，按 sort_order 排序。"""
    rows = connection.execute(
        "SELECT type, label, value FROM contact_methods "
        "WHERE contact_id = ? ORDER BY sort_order, id",
        (contact_id,),
    ).fetchall()
    return [
        {"type": row["type"], "label": row["label"] or "", "value": row["value"]}
        for row in rows
    ]


def _serialize(connection, row):
    """把数据库行转换成契约中的联系人对象。"""
    return {
        "id": row["id"],
        "name": row["name"],
        "company": row["company"] or "",
        "note": row["note"] or "",
        "isFavorite": bool(row["is_favorite"]),
        "methods": _load_methods(connection, row["id"]),
    }


def _fetch_row(connection, contact_id):
    """按 id 取一行，不存在返回 None。"""
    return connection.execute(
        "SELECT * FROM contacts WHERE id = ?", (contact_id,)
    ).fetchone()


def _insert_methods(connection, contact_id, methods):
    """写入联系方式，sort_order 决定展示与导出的先后。"""
    for index, method in enumerate(methods):
        connection.execute(
            "INSERT INTO contact_methods (contact_id, type, label, value, sort_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (contact_id, method["type"], method["label"], method["value"], index),
        )


def _replace_methods(connection, contact_id, methods):
    """先删旧的联系方式再插新的，实现全量更新。"""
    connection.execute("DELETE FROM contact_methods WHERE contact_id = ?", (contact_id,))
    _insert_methods(connection, contact_id, methods)


def _validate_payload(payload):
    """校验并规整请求体，返回 ``(data, error_message)``。"""
    if not isinstance(payload, dict):
        return None, "请求体必须是 JSON 对象"

    name = (payload.get("name") or "").strip()
    if not name:
        return None, "姓名不能为空"
    if len(name) > NAME_MAX_LENGTH:
        return None, "姓名长度不能超过 {} 个字符".format(NAME_MAX_LENGTH)

    raw_methods = payload.get("methods")
    if raw_methods is None:
        raw_methods = []
    if not isinstance(raw_methods, list):
        return None, "methods 必须是数组"

    methods = []
    for index, item in enumerate(raw_methods, start=1):
        if not isinstance(item, dict):
            return None, "第{}条联系方式格式不正确".format(index)
        value = (item.get("value") or "").strip()
        if not value:
            return None, "第{}条联系方式的值不能为空".format(index)
        if len(value) > VALUE_MAX_LENGTH:
            return None, "第{}条联系方式的值不能超过 {} 个字符".format(index, VALUE_MAX_LENGTH)
        method_type = normalize_type(item.get("type"))
        methods.append(
            {
                "type": method_type,
                "label": normalize_label(method_type, item.get("label")),
                "value": value,
            }
        )

    return {
        "name": name,
        "company": (payload.get("company") or "").strip(),
        "note": (payload.get("note") or "").strip(),
        "isFavorite": bool(payload.get("isFavorite")),
        "methods": methods,
    }, None


@contacts_bp.get("/contacts")
def list_contacts():
    """联系人列表，支持 favorite=1 只看收藏、keyword 关键词搜索。"""
    favorite = (request.args.get("favorite") or "").strip().lower()
    keyword = (request.args.get("keyword") or "").strip()

    conditions = []
    params = []
    if favorite in ("1", "true", "yes"):
        conditions.append("is_favorite = 1")
    if keyword:
        like = "%{}%".format(keyword)
        conditions.append(
            "(name LIKE ? OR company LIKE ? OR note LIKE ? OR id IN ("
            "SELECT contact_id FROM contact_methods WHERE value LIKE ?))"
        )
        params.extend([like, like, like, like])

    sql = "SELECT * FROM contacts"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY is_favorite DESC, updated_at DESC, id DESC"

    connection = db.get_connection()
    try:
        rows = connection.execute(sql, params).fetchall()
        return ok([_serialize(connection, row) for row in rows])
    finally:
        connection.close()


@contacts_bp.get("/contacts/<int:contact_id>")
def get_contact(contact_id):
    """联系人详情，包含 methods 数组。"""
    connection = db.get_connection()
    try:
        row = _fetch_row(connection, contact_id)
        if row is None:
            return fail("联系人不存在", 404)
        return ok(_serialize(connection, row))
    finally:
        connection.close()


@contacts_bp.post("/contacts")
def create_contact():
    """新增联系人，成功返回新建对象。"""
    data, error = _validate_payload(request.get_json(silent=True))
    if error:
        return fail(error)

    connection = db.get_connection()
    try:
        now = _now()
        cursor = connection.execute(
            "INSERT INTO contacts (name, company, note, is_favorite, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                data["name"],
                data["company"],
                data["note"],
                1 if data["isFavorite"] else 0,
                now,
                now,
            ),
        )
        contact_id = cursor.lastrowid
        _insert_methods(connection, contact_id, data["methods"])
        connection.commit()
        return ok(_serialize(connection, _fetch_row(connection, contact_id)))
    except Exception as exc:  # noqa: BLE001 - 统一兜底成 code 结构
        connection.rollback()
        return fail("保存联系人失败：{}".format(exc), 500)
    finally:
        connection.close()


@contacts_bp.put("/contacts/<int:contact_id>")
def update_contact(contact_id):
    """全量更新联系人及其联系方式。"""
    data, error = _validate_payload(request.get_json(silent=True))
    if error:
        return fail(error)

    connection = db.get_connection()
    try:
        if _fetch_row(connection, contact_id) is None:
            return fail("联系人不存在", 404)
        connection.execute(
            "UPDATE contacts SET name = ?, company = ?, note = ?, is_favorite = ?, "
            "updated_at = ? WHERE id = ?",
            (
                data["name"],
                data["company"],
                data["note"],
                1 if data["isFavorite"] else 0,
                _now(),
                contact_id,
            ),
        )
        _replace_methods(connection, contact_id, data["methods"])
        connection.commit()
        return ok(_serialize(connection, _fetch_row(connection, contact_id)))
    except Exception as exc:  # noqa: BLE001
        connection.rollback()
        return fail("更新联系人失败：{}".format(exc), 500)
    finally:
        connection.close()


@contacts_bp.delete("/contacts/<int:contact_id>")
def delete_contact(contact_id):
    """删除联系人，联系方式随外键级联删除。"""
    connection = db.get_connection()
    try:
        if _fetch_row(connection, contact_id) is None:
            return fail("联系人不存在", 404)
        connection.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        connection.commit()
        return ok({"id": contact_id})
    except Exception as exc:  # noqa: BLE001
        connection.rollback()
        return fail("删除联系人失败：{}".format(exc), 500)
    finally:
        connection.close()


@contacts_bp.post("/contacts/<int:contact_id>/favorite")
def set_favorite(contact_id):
    """收藏或取消收藏，body 为 {"isFavorite": true/false}。"""
    payload = request.get_json(silent=True) or {}
    if "isFavorite" not in payload:
        return fail("缺少 isFavorite 字段")
    is_favorite = bool(payload.get("isFavorite"))

    connection = db.get_connection()
    try:
        if _fetch_row(connection, contact_id) is None:
            return fail("联系人不存在", 404)
        connection.execute(
            "UPDATE contacts SET is_favorite = ?, updated_at = ? WHERE id = ?",
            (1 if is_favorite else 0, _now(), contact_id),
        )
        connection.commit()
        return ok(_serialize(connection, _fetch_row(connection, contact_id)))
    except Exception as exc:  # noqa: BLE001
        connection.rollback()
        return fail("更新收藏状态失败：{}".format(exc), 500)
    finally:
        connection.close()
