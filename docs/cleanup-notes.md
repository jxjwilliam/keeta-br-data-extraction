# 清理与同步记录

日期：2026-10-23。整理前采集进程已结束；本次不启动手机采集，不改动已采有效结果。

## 活动文件

维护脚本只保留stream、v4字段模块和两个不同用途的XLSX导出器，见README脚本表。Muse为独立实验方案，保留既有内容和暂存状态，未作为重复项删除。

操作文档合并：README（安装/运行）、resources（依赖）、continuous-guide（实现/恢复/输出）、debug-guide（设备排错）。删除重复且过期的keeta-rerun-guide，其有用的单条诊断说明并入continuous-guide。研究文档有独立来源，保留并用docs/README索引，历史陈述不覆盖当前实现。

移除活动探针：scripts/keeta_scripe-v1.py、v2.py、v3.py、keeta_capture.py、test1.py。旧源码有本地归档，已跟踪版本也可从Git历史恢复。

## 输出

- outputs/final保留X3/X6两组非空连续会话CSV/XLSX，以及history中的3份早期样例，原文件字节不变。
- 两个只有表头的CSV和空会话移出活动目录。
- 旧outputs/internal/runs和可再生成的draft/snapshot/records.json/预览归档后移除，不再和当前会话混放。
- 有效会话SQLite、字段来源、原始XML/截图及失败日志保留，现有恢复路径不变。
- 后续连续导出的JSON/XLSX放系统临时目录，成功后释放；最终CSV/XLSX、账本和错误日志继续保留。

## 本地可恢复归档

[ZIP](../outputs/internal/archives/cleanup-20261023/retired-and-regenerable.zip) · [逐文件SHA256清单](../outputs/internal/archives/cleanup-20261023/manifest.json) · [保留结果SHA256](../outputs/internal/archives/cleanup-20261023/preserved-final-sha256.json)。归档属于本地内部输出，不随代码分发。

共147个文件入档（包括7份改写前文档备份），140个废弃/可再生成文件从活动目录移除。每个入档文件已解压读回核对SHA256，通过后才移除原文件；采集结果、测试fixtures及assets没有删除。清理前后7份非空/历史交付物SHA256一致。

ZIP内条目保留原仓库相对路径。恢复时先解压到临时目录，按清单选择文件，不要整包覆盖当前代码、文档或会话账本。

## 本次验证

32项离线测试通过；复制当前账本到临时目录完成真实CSV/XLSX导出（14条审计行、连续采集和成功率两表），确认会话不残留records.json/snapshot.xlsx。所有本地Markdown链接可达，7份保留交付物SHA256一致。未更改既有Git暂存内容、未提交；工作区删除/新增需在下一次提交时显式暂存。
