# 最终文件

每轮有效结果按采集时间戳命名为 `latest_YYYYMMDD_HHMMSS.xlsx` 和 `latest_YYYYMMDD_HHMMSS.csv`，可直接用 Excel 打开。首次新版实机校验通过前，这两个文件暂不存在。

`history/` 保留迁移前的历史结果，新结果直接按时间戳保存在本目录。本次迁移的旧样例：

| 文件 | 状态 |
| --- | --- |
| `20261021-16fields-needs-review.xlsx` | 原有 16 字段历史样例；保留原样 |
| `20261022-133314-16fields-needs-review.xlsx` | 原有 16 字段；地址未确认、Excel 时间展示待纠正 |
| `20261022-133314-16fields-needs-review.csv` | 同轮原有 16 字段 CSV；地址未确认 |

旧记录没有补造字段或与新研究证据混拼。新结果按圣保罗采集时间命名，直接保存在本目录；不再创建固定名称的 latest 文件。同一时间戳已存在时拒绝覆盖。
