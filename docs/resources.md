# 运行资源

仅描述维护中的 stream/v4 流程；独立 Muse 实验脚本不在此依赖验收范围。安装/运行命令统一见 [README](../README.md)。

| 资源 | 用途 |
| --- | --- |
| Python 3.12（本机实测） | 主程序、标准库SQLite、离线测试 |
| requirements.txt | uiautomator2 3.7.0、Pillow 11.0.0；直接依赖锁定，非完整传递依赖锁文件 |
| Android手机、USB、已授权ADB | 已登录的Keeta App实时页面 |
| 系统adb | 设备连接与保持唤醒；当前Mac通过Homebrew安装 |
| scrcpy（可选） | 观看手机操作，不是解析依赖 |
| Codex bundled Node + @oai/artifact-tool | XLSX导出；不是普通npm install即可复现的已发布依赖 |

XLSX运行时默认根目录 `~/.cache/codex-runtimes/codex-primary-runtime/dependencies`，需包含 `node/bin/node`、`node/node_modules/@oai/artifact-tool`。迁移环境用 `KEETA_RUNTIME` 指向同样结构的可用运行时。本仓库不提供该专用运行时安装器；在当前Codex环境外运行，必须先具备它。缺失/导出失败时CSV和SQLite仍应保留，Excel可能停在上一版。

`KEETA_RUNTIME` 是唯一可选运行时配置；脚本不自动加载.env。登录在手机App内完成，代码不要求填写密码、Cookie或API key。

数据为本地SQLite（outputs/internal/streams/会话/records.sqlite）及本地CSV/XLSX、证据文件。不需要数据库服务器、Docker、Web服务、Redis或云服务。当前代码不是公开商家API客户端。
