"""Excel 导入导出接口。

导出规则：一个联系人一行，联系方式按类型落到对应列；同类型超出槽位数量时
用换行拼接到该类型最后一列，确保不丢数据。
导入规则：逐列比对表头，姓名为空的行跳过并记入 errors，整批写入放在一个
事务里，任何写库异常都回滚并返回 code=1002。
"""
from datetime import datetime
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

import db
from utils.excel_schema import (
    COL_ADDRESS,
    COL_COMPANY,
    COL_EMAIL_1,
    COL_EMAIL_2,
    COL_FAVORITE,
    COL_NAME,
    COL_NOTE,
    COL_OTHER,
    COL_PHONE_1,
    COL_PHONE_2,
    COL_PHONE_3,
    COL_WECHAT,
    HEADERS,
    contact_to_row,
    header_matches,
    parse_row,
)

excel_bp = Blueprint("excel_io", __name__, url_prefix="/api")

XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

#: 列宽，姓名/公司/地址放宽一些，便于截图展示。
COLUMN_WIDTHS = {
    COL_NAME: 14,
    COL_COMPANY: 20,
    COL_NOTE: 20,
    COL_FAVORITE: 10,
    COL_PHONE_1: 16,
    COL_PHONE_2: 16,
    COL_PHONE_3: 16,
    COL_EMAIL_1: 24,
    COL_EMAIL_2: 24,
    COL_WECHAT: 16,
    COL_ADDRESS: 30,
    COL_OTHER: 20,
}

#: 这些列的内容可能有多行，需要自动换行。
WRAP_COLUMNS = (COL_ADDRESS, COL_OTHER, COL_PHONE_3, COL_EMAIL_2)

CODE_HEADER_MISMATCH = 1001
CODE_IMPORT_ROLLBACK = 1002


def ok(data):
    """构造成功响应。"""
    return jsonify({"code": 0, "data": data})


def fail(message, code=1):
    """构造失败响应。"""
    return jsonify({"code": code, "message": message})


def _now():
    """当前时间字符串。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _style_header(sheet):
    """首行加粗居中、冻结首行、设置列宽。"""
    for index, header in enumerate(HEADERS, start=1):
        cell = sheet.cell(row=1, column=index, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        sheet.column_dimensions[get_column_letter(index)].width = COLUMN_WIDTHS.get(header, 16)
    sheet.freeze_panes = "A2"


def _build_workbook(rows):
    """把若干行数据装配成一个工作簿对象。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "通讯录"
    _style_header(sheet)

    for row_index, values in enumerate(rows, start=2):
        for column_index, value in enumerate(values, start=1):
            header = HEADERS[column_index - 1]
            cell = sheet.cell(row=row_index, column=column_index, value=value)
            cell.alignment = Alignment(
                vertical="top", wrap_text=header in WRAP_COLUMNS
            )
    return workbook


def _load_all_contacts():
    """读出全部联系人，顺序与列表接口一致。"""
    connection = db.get_connection()
    try:
        contacts = connection.execute(
            "SELECT * FROM contacts ORDER BY is_favorite DESC, updated_at DESC, id DESC"
        ).fetchall()
        result = []
        for row in contacts:
            methods = connection.execute(
                "SELECT type, label, value FROM contact_methods "
                "WHERE contact_id = ? ORDER BY sort_order, id",
                (row["id"],),
            ).fetchall()
            result.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "company": row["company"] or "",
                    "note": row["note"] or "",
                    "isFavorite": bool(row["is_favorite"]),
                    "methods": [
                        {
                            "type": method["type"],
                            "label": method["label"] or "",
                            "value": method["value"],
                        }
                        for method in methods
                    ],
                }
            )
        return result
    finally:
        connection.close()


@excel_bp.get("/export")
def export_contacts():
    """导出全部联系人为 xlsx 文件下载。"""
    contacts = _load_all_contacts()
    rows = [contact_to_row(contact) for contact in contacts]
    workbook = _build_workbook(rows)

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    filename = "contacts_{}.xlsx".format(datetime.now().strftime("%Y%m%d"))
    return send_file(
        stream,
        as_attachment=True,
        download_name=filename,
        mimetype=XLSX_MIMETYPE,
    )


@excel_bp.get("/export/template")
def export_template():
    """下载空白导入模板（只有表头）。"""
    workbook = _build_workbook([])
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return send_file(
        stream,
        as_attachment=True,
        download_name="contacts_template.xlsx",
        mimetype=XLSX_MIMETYPE,
    )


@excel_bp.post("/import")
def import_contacts():
    """上传 xlsx 导入联系人，返回新增/跳过数量与错误明细。"""
    uploaded = request.files.get("file")
    if uploaded is None or not (uploaded.filename or "").strip():
        return fail("请选择要导入的 .xlsx 文件")

    if not uploaded.filename.lower().endswith(".xlsx"):
        return fail("只支持 .xlsx 格式的文件，请下载模板后填写", CODE_HEADER_MISMATCH)

    try:
        workbook = load_workbook(BytesIO(uploaded.read()), data_only=True)
    except Exception:  # noqa: BLE001 - 损坏的文件统一按格式错误处理
        return fail("文件无法解析，请下载模板后填写", CODE_HEADER_MISMATCH)

    sheet = workbook.active
    if sheet is None or sheet.max_row < 1:
        return fail("表头不符合模板，请下载模板后填写", CODE_HEADER_MISMATCH)

    header_values = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    if not header_matches(header_values):
        return fail("表头不符合模板，请下载模板后填写", CODE_HEADER_MISMATCH)

    inserted = 0
    skipped = 0
    errors = []

    connection = db.get_connection()
    try:
        now = _now()
        for line_no, values in enumerate(
            sheet.iter_rows(min_row=2, values_only=True), start=2
        ):
            if values is None:
                continue
            if all(value is None or str(value).strip() == "" for value in values):
                continue

            contact, row_errors = parse_row(values, line_no)
            errors.extend(row_errors)
            if contact is None:
                skipped += 1
                continue

            cursor = connection.execute(
                "INSERT INTO contacts (name, company, note, is_favorite, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    contact["name"],
                    contact["company"],
                    contact["note"],
                    1 if contact["isFavorite"] else 0,
                    now,
                    now,
                ),
            )
            contact_id = cursor.lastrowid
            for index, method in enumerate(contact["methods"]):
                connection.execute(
                    "INSERT INTO contact_methods (contact_id, type, label, value, sort_order) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (contact_id, method["type"], method["label"], method["value"], index),
                )
            inserted += 1
        connection.commit()
    except Exception as exc:  # noqa: BLE001
        connection.rollback()
        return fail("导入失败，数据已回滚：{}".format(exc), CODE_IMPORT_ROLLBACK)
    finally:
        connection.close()

    print("[import] inserted={} skipped={}".format(inserted, skipped))
    return ok({"inserted": inserted, "skipped": skipped, "errors": errors})
