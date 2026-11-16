# 云部署说明（可选 15 分）

> **当前状态：未部署到公网。本地已跑通（http://127.0.0.1:5000/），没有服务器，因此不提供公网地址。**
>
> 这一节是可直接照做的部署步骤。等你买到 ECS 并把地址填进最后一节，就算完成可选项。

---

## 一、目标形态

```
公网用户 → Nginx(80) → gunicorn(127.0.0.1:8000) → Flask 应用 → SQLite 文件
```

- Nginx 负责 80 端口、静态资源、反向代理 `/api`。
- gunicorn 起 3 个 worker 进程，只监听回环地址，不直接暴露公网。
- SQLite 文件放在应用目录的 `data/` 下，保证 gunicorn 用户有写权限。

## 二、服务器准备

以 Ubuntu 22.04 / 24.04 为例（阿里云、华为云、便宜云 ECS 均可）：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx

# 拉代码（把仓库地址换成你自己的）
cd /opt
sudo git clone <你的仓库地址> address-book
sudo chown -R $USER:$USER /opt/address-book
cd /opt/address-book
```

### 安全组 / 防火墙

- 云控制台的**安全组**：放行入方向 `22`（SSH）、`80`（HTTP）；如果要 HTTPS，再放行 `443`。
- 服务器本机防火墙：

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

> 只放行 80/443，**不要**放行 5000 和 8000。Flask 开发服务器和 gunicorn 都不该直接对外。

## 三、创建虚拟环境并安装依赖

```bash
cd /opt/address-book
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

## 四、初始化数据库与种子数据

```bash
cd /opt/address-book
source .venv/bin/activate
python seed.py          # 可选：灌演示数据
```

确认 `data/address-book.db` 已生成，且当前用户可写：

```bash
ls -l data/
```

## 五、用 gunicorn 启动

先手动验证一次：

```bash
cd /opt/address-book
source .venv/bin/activate
gunicorn -w 3 -b 127.0.0.1:8000 "app:app" --timeout 60
```

浏览器用服务器本地 `curl` 验证：

```bash
curl -s http://127.0.0.1:8000/api/contacts | head -c 200
```

能返回 `{"code":0,...}` 说明应用正常，`Ctrl+C` 停掉，改由 systemd 托管。

### systemd 服务

`/etc/systemd/system/address-book.service`：

```ini
[Unit]
Description=Address Book (Flask + gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/address-book
Environment="PATH=/opt/address-book/.venv/bin"
ExecStart=/opt/address-book/.venv/bin/gunicorn -w 3 -b 127.0.0.1:8000 "app:app" --timeout 60
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo chown -R www-data:www-data /opt/address-book/data
sudo chmod 775 /opt/address-book/data

sudo systemctl daemon-reload
sudo systemctl enable --now address-book
sudo systemctl status address-book
sudo journalctl -u address-book -f
```

> gunicorn 用 3 个 worker 写同一个 SQLite 文件时，写并发较高会短暂遇到 `database is locked`。
> 本作业的访问量远低于这个阈值；若真遇到，把 `-w 3` 改成 `-w 1` 即可。

## 六、Nginx 反向代理

`/etc/nginx/sites-available/address-book`：

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 20m;

    # 静态资源交给 Nginx，命中率高
    location /static/ {
        alias /opt/address-book/static/;
        expires 1h;
        access_log off;
    }

    # 页面与接口统一反代给 gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/address-book /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

此时用服务器公网 IP 访问 `http://<公网IP>/` 应该能看到页面。

## 七、上线后自检清单

| 检查项 | 命令 / 做法 | 期望 |
| --- | --- | --- |
| 首页可访问 | 浏览器打开 `http://<公网IP>/` | 页面正常、无 404 |
| 接口可用 | `curl http://<公网IP>/api/contacts` | 返回 `{"code":0,...}` |
| 静态资源 | `curl -I http://<公网IP>/static/css/style.css` | `200 OK` |
| 导出可用 | 点页面「导出」 | 下载到 xlsx |
| 导入可用 | 点「导入」上传文件 | 返回成功/失败面板 |
| 数据落盘 | `ls -l /opt/address-book/data/` | 数据库文件存在且在更新 |
| 服务自启 | `sudo reboot` 后等待 1 分钟 | 页面仍可访问 |
| 写权限 | 新增一个联系人 | 刷新后仍在 |

## 八、可选：HTTPS

有域名时用 certbot 一条命令搞定：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your.domain.com
```

## 九、部署记录（部署完成后填写）

| 项目 | 内容 |
| --- | --- |
| 公网访问地址 | **（未部署，待填写）** |
| 服务器规格 | （未购买） |
| 部署日期 | （待填写） |
| 备注 | 本地已完整跑通；公网部署未做，不伪造地址 |
