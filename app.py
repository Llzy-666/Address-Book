"""Flask 应用入口：注册蓝图、开启 CORS、托管静态前端、统一错误兜底。

启动：``python app.py``，然后浏览器打开 http://127.0.0.1:5000/
"""
import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import db
from api.contacts import contacts_bp
from api.excel_io import excel_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

#: 上传文件大小上限，避免误传大文件撑爆内存。
MAX_UPLOAD_BYTES = 16 * 1024 * 1024


def create_app():
    """组装 Flask 应用对象。"""
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    # 让 jsonify 直接输出中文，而不是 \uXXXX 转义。
    app.json.ensure_ascii = False

    app.register_blueprint(contacts_bp)
    app.register_blueprint(excel_bp)

    @app.get("/")
    def index():
        """前端首页。"""
        return send_from_directory(STATIC_DIR, "index.html")

    @app.get("/favicon.ico")
    def favicon():
        """浏览器默认请求的图标，直接返回空响应避免日志噪音。"""
        return "", 204

    @app.errorhandler(404)
    def handle_not_found(error):
        """未匹配路由也返回统一的 code 结构，不吐 HTML 错误页。"""
        return jsonify({"code": 404, "message": "请求的资源不存在"}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """方法不允许。"""
        return jsonify({"code": 405, "message": "不支持的请求方法"}), 405

    @app.errorhandler(413)
    def handle_too_large(error):
        """上传体积超限。"""
        return jsonify({"code": 413, "message": "上传文件过大"}), 413

    @app.errorhandler(500)
    def handle_server_error(error):
        """服务器内部错误兜底。"""
        return jsonify({"code": 500, "message": "服务器内部错误"}), 500

    return app


def bootstrap():
    """启动前确保数据库与表结构存在。"""
    path = db.init_db()
    print("[db] SQLite 就绪：{}".format(path))


bootstrap()
app = create_app()

if __name__ == "__main__":
    print("通讯录已启动：http://127.0.0.1:5000/")
    app.run(host="0.0.0.0", port=5000, debug=True)
