# 脚本入口

| 文件 | 状态/用途 |
| --- | --- |
| keeta_stream.py | 维护入口：连续导航、有限恢复、全尝试审计、SQLite/CSV |
| keeta_scripe-v4.py | 维护模块：捕获、30字段解析、金额校验、单条诊断CLI |
| export_keeta_stream.mjs | 维护导出器：全尝试XLSX与成功率页 |
| export_keeta.mjs | 维护辅助：单条诊断XLSX及来源页（由v4调用） |
| muse_keeta_scrape.py | 独立实验；当前维护流程未调用，不与stream同时控制设备 |

运行和安装命令见根README，资源见docs/resources.md。历史v1–v3、capture、test1已从此目录移除，本地可恢复副本见docs/cleanup-notes.md；不要以它们为运行入口。
