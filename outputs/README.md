# 输出入口

你只需要查看 `final/`。

- `final/latest_YYYYMMDD_HHMMSS.xlsx`、`final/latest_YYYYMMDD_HHMMSS.csv`：最新一轮通过地址和金额校验的结果；两者对应同一轮。
- `final/history/`：历史 XLSX/CSV。文件名含 `needs-review` 的是旧样例，存在已知问题，不代表新版验证通过。
- `internal/`：截图、XML、JSON、日志、调试和失败草稿，供程序排错，不作为交付入口。

当前还没有新版完整实机验收结果，因此暂不提供 `latest`，避免把旧的 16 字段样例误认为新结果。下一轮通过后自动生成。
