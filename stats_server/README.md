# 飞书日程匿名使用统计服务

该服务为桌面应用提供匿名安装心跳和聚合统计，仅使用 Python 标准库和
SQLite。接口固定为：

- `GET /health`
- `POST /v1/heartbeat`
- `GET /v1/stats`

线上入口为 `https://www.airtraffic.site/feishu-calendar-stats/`。

## 数据与隐私

- 客户端首次运行生成 32 位随机 `install_id`，不包含硬件、账号或网络标识。
- 服务端只保存 `sha256(pepper + install_id)`，不保存原始安装标识。
- 数据库记录唯一的安装哈希、首次/最后出现时间、应用版本和操作系统平台。
- 服务端不记录 IP；Nginx 位置片段关闭访问日志并清空转发地址头。
- 不采集飞书账号、日历内容、主机名、MAC 地址或设备指纹。

「累计使用人数」是数据库中唯一安装数，「近 30 天活跃」是按最后心跳时间
统计的活跃安装数。

## 部署到 HP 服务器

以下命令在服务器执行。先创建目录并上传服务文件：

```bash
sudo install -d -o ubuntu -g ubuntu -m 0750 /home/ubuntu/feishu-calendar-stats
sudo install -o ubuntu -g ubuntu -m 0640 \
  app.py /home/ubuntu/feishu-calendar-stats/app.py
sudo install -m 0644 \
  feishu-calendar-stats.service /etc/systemd/system/feishu-calendar-stats.service
```

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now feishu-calendar-stats
sudo systemctl status --no-pager feishu-calendar-stats
curl -fsS http://127.0.0.1:8010/health
```

预期健康检查响应：

```json
{"status":"ok"}
```

## 配置 Nginx

在 `www.airtraffic.site` 的 HTTPS `server` 块内引入
`nginx-location.conf`，或在现有配置中粘贴其内容。修改前先备份：

```bash
sudo cp -a /etc/nginx/sites-available/www.airtraffic.site \
  /etc/nginx/sites-available/www.airtraffic.site.bak-$(date +%Y%m%d-%H%M%S)
sudo nginx -t
sudo systemctl reload nginx
```

配置使用以下反向代理：

```nginx
location ^~ /feishu-calendar-stats/ {
    proxy_pass http://127.0.0.1:8010/;
}
```

完整片段见 `nginx-location.conf`。生产环境只开放 HTTPS 入口，Python
服务本身仅监听 `127.0.0.1:8010`，不需要开放公网端口。

## 验证接口

```bash
curl -fsS https://www.airtraffic.site/feishu-calendar-stats/health
curl -fsS https://www.airtraffic.site/feishu-calendar-stats/v1/stats
```

模拟一次心跳：

```bash
curl -fsS -X POST \
  -H 'Content-Type: application/json' \
  -d '{"install_id":"0123456789abcdef0123456789abcdef","version":"2.1.3","platform":"win32"}' \
  https://www.airtraffic.site/feishu-calendar-stats/v1/heartbeat
```

响应示例：

```json
{
  "cumulative_users": 1,
  "active_users_30d": 1,
  "generated_at": 1789570000
}
```

## 备份与运维

查看最近日志：

```bash
sudo journalctl -u feishu-calendar-stats -n 100 --no-pager
```

在线备份 SQLite：

```bash
sqlite3 /home/ubuntu/feishu-calendar-stats/stats.db \
  ".backup '/home/ubuntu/feishu-calendar-stats/stats-$(
    date +%Y%m%d-%H%M%S
  ).db'"
```

更新服务代码：

```bash
sudo install -o ubuntu -g ubuntu -m 0640 \
  app.py /home/ubuntu/feishu-calendar-stats/app.py
sudo systemctl restart feishu-calendar-stats
curl -fsS http://127.0.0.1:8010/health
```

回滚时先移除 Nginx 位置片段并执行 `sudo nginx -t && sudo systemctl reload nginx`，
再按需停止服务：

```bash
sudo systemctl disable --now feishu-calendar-stats
```
