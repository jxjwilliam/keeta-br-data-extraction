# 输出入口

只看final/中的CSV/XLSX。连续会话按圣保罗启动时间命名continuous_YYYYMMDD_HHMMSS；同会话逐条更新，恢复路径不变。history/是更早需复核的转录样例。

internal/streams/保存有效会话账本/证据/失败日志；internal/incidents/为访问异常证据；internal/archives/为已核对可恢复历史归档。没有表头CSV冒充结果，没有PNG/XML混入final。

当前状态/成功率以工作簿为准，运行命令见仓库README，数据口径见docs/keeta-continuous-guide.md。
