"""示例种子数据：5 个联系人，其中 2 个已收藏、4 个含多条联系方式。

用法::

    python seed.py

脚本会清空现有数据后重新写入，便于反复录演示视频。
"""
import db

#: (姓名, 公司, 备注, 是否收藏, [联系方式...])
SEED_CONTACTS = (
    (
        "张三",
        "福州某科技有限公司",
        "大学同学，做后端的",
        True,
        [
            ("phone", "手机", "13800000000"),
            ("email", "工作邮箱", "zhangsan@example.com"),
            ("wechat", "微信", "zhangsan_wx"),
        ],
    ),
    (
        "李四",
        "厦门海沧贸易",
        "前同事，负责采购",
        False,
        [
            ("phone", "手机", "13900000001"),
            ("phone", "备用电话", "0591-88880001"),
            ("address", "公司地址", "福建省厦门市海沧区滨湖路 18 号"),
        ],
    ),
    (
        "王五",
        "福州大学计算机学院",
        "导师，论文的事找他",
        True,
        [
            ("email", "学校邮箱", "wangwu@fzu.edu.cn"),
            ("email", "私人邮箱", "wangwu@example.com"),
            ("wechat", "微信", "wangwu_fzu"),
        ],
    ),
    (
        "赵六",
        "个人",
        "健身房认识的",
        False,
        [
            ("phone", "手机", "13700000003"),
            ("address", "住址", "福建省福州市鼓楼区五四路 200 号"),
        ],
    ),
    (
        "孙七",
        "宁德时代",
        "项目对接人，微信最先联系",
        False,
        [
            ("phone", "手机", "13600000004"),
            ("email", "邮箱", "sunqi@catl.com"),
            ("wechat", "微信", "sunqi_catl"),
            ("other", "钉钉", "sunqi_dingtalk"),
        ],
    ),
)


def insert_contact(connection, name, company, note, is_favorite, methods):
    """写入一个联系人及其联系方式，返回新 id。"""
    cursor = connection.execute(
        "INSERT INTO contacts (name, company, note, is_favorite, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, datetime('now', 'localtime'), datetime('now', 'localtime'))",
        (name, company, note, 1 if is_favorite else 0),
    )
    contact_id = cursor.lastrowid
    for index, (method_type, label, value) in enumerate(methods):
        connection.execute(
            "INSERT INTO contact_methods (contact_id, type, label, value, sort_order) "
            "VALUES (?, ?, ?, ?, ?)",
            (contact_id, method_type, label, value, index),
        )
    return contact_id


def main():
    """清空并重建种子数据。"""
    db.init_db()
    db.reset_db()
    connection = db.get_connection()
    try:
        for name, company, note, is_favorite, methods in SEED_CONTACTS:
            insert_contact(connection, name, company, note, is_favorite, methods)
        connection.commit()
    finally:
        connection.close()
    favorite_count = sum(1 for item in SEED_CONTACTS if item[3])
    multi_count = sum(1 for item in SEED_CONTACTS if len(item[4]) > 1)
    print(
        "[seed] 已写入 {} 个联系人，其中收藏 {} 个、多条联系方式 {} 个".format(
            len(SEED_CONTACTS), favorite_count, multi_count
        )
    )


if __name__ == "__main__":
    main()
