# 文档索引

## 当前操作与实现

- [运行资源](resources.md)：Python直接依赖、ADB、专用XLSX运行时。
- [连续采集](keeta-continuous-guide.md)：参数、状态/成功率、持久化、恢复、单条离线诊断。
- [设备排错](keeta-debug-guide.md)：连接、锁屏、地址和访问异常的处理。
- [清理记录](cleanup-notes.md)：移除项、保留项、可恢复归档。

运行命令唯一入口为[README](../README.md)，当前状态唯一入口为[TODO](../TODO.md)。

## 保留的研究与参考

下列各有独立调查/需求信息，未作为重复文件删除。内容反映其采集日期，不表示当前运行状态；旧试运行目录的原始证据已转本地ZIP，见清理记录，历史路径可按manifest还原。

- [官方接入、访问异常与规模化](oc-keeta-access-and-scale-research.md)：已核验来源及准入范围。
- [字段来源调查](oc-keeta-field-coverage.md)：早期16→22字段路径和用户确认口径；测试数量等为当时快照。
- [网页调查](oc-scrape-findings.md)：分享URL、网页限制及后续更正。
- [巴西市场背景](keeta-brazil-research.md)。
- [早期结算截图转录](ac-br-抓取小结.md)：历史样例金额，不是当前实时报价。
- [pt-BR界面文案](keeta-checkout-fields-cn.md)。
- [API与风控评估](ac-br-API与风控评估.md)、[采集可行性分析](keeta-data-collection-analysis.md)：独立方案评估，推断/速率估算不视为实测保证；获准范围以官方接入核实为准。
- [15000条业务待确认](待确认清单-15000条.md)：业务问题清单，待与project.md核定。
