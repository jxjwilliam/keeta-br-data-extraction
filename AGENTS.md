# Repository Guidelines

## 项目与入口

Keeta Brazil Android UI报价采集试运行项目，包含Python/uiautomator2、XLSX导出器、离线测试及研究文档。先读TODO.md当前状态，再读project.md需求、README.md字段表与运行命令。

- scripts/keeta_stream.py：唯一当前连续采集入口。
- scripts/keeta_scripe-v4.py：字段模块及单条诊断；export_keeta_stream.mjs为连续导出，export_keeta.mjs为单条诊断导出。
- scripts/muse_keeta_scrape.py：独立实验方案，未作为维护入口验收；不要与主程序同时控制手机。
- requirements.txt、docs/resources.md：依赖；docs/keeta-continuous-guide.md：运行/恢复/成功率；docs/keeta-debug-guide.md：设备排错。
- docs/README.md：研究与规划索引。docs/cleanup-notes.md：旧探针/历史证据归档。
- tests/fixtures与assets保留可复现实验/原始需求；不要把模拟数据写入final。

## 命令与验证

安装与设备运行命令以README为准；离线测试：`python3 -m unittest discover -s tests -v`。没有Web服务或npm测试命令。

文档改动核对链接，代码改动运行相关离线测试。涉及字段解析须覆盖缺失/0、金额/跨页一致性；涉及恢复须验证停止预算、状态识别及旧动作作废。不为普通文档更改重复运行手机采集。

## 数据约束

- 不伪造未见字段：未知None/CSV空，0是有效值。保留30业务字段顺序，审计字段另附。
- BRL整数分；商品原价、商品折后、配送、服务费、总额和已用优惠核算一致才complete。可用未应用券不参与。单一服务费按项目口径两列相同，不固定金额99。
- ETA为同页送达时刻减带日期/时区的采集时间后向上取整分钟，保留原时窗；过期/跨日歧义留空。
- 账号类型0单→0，1–4单→1，≥5单→2；订单空历史才有0证据，不能数可见订单卡推算累计。
- 不同设备/账号/过期轮次不得拼接。用户默认7550保存地址，地址提示气泡不算已选择。
- failed/partial保留已读取字段和原因，不等于close。只明确Open/Closed才填状态。complete不代表30项满值；navigation不算店铺成功率分母。
- 原始截图转录、网页研究与实机报价分开；官方商家API存在，但全市场消费者报价能力未核实。

## 设备与操作边界

当前X3 f753a0f3，X6 979f0245为独立历史设备；不混会话。未经实测不要假定输入权限、网络或GPS配置。

不下单/支付、不应用券、不清未知购物车、不修改账号/安全权限。意外页有界返回后重新定位，不能沿用旧坐标。访问限制/验证码/外部支付/已提交订单/锁屏暂停；不换账号/网络/设备绕过。不承诺防封或15000条生产能力。

## 存储与隐私

outputs/final只放交付CSV/XLSX；outputs/internal为SQLite、证据、日志和本地归档。中断不删已有记录；只清可再生成文件，历史移除项留可核对恢复副本。

密码、Cookie、OTP、账号联系人和个人信息不进入文档/提交；捕获使用脱敏逻辑。不要擅自提交outputs或内部证据，部分final文件已有Git跟踪并不表示自动获准公开；遵守现有.gitignore。

## 文档与Git

中文文档用标题、短段落和列表。研究来源前缀：p1=Perplexity、oc=OpenAI Codex、ac=Anthropic Claude、mm=Meta Muse；操作文档普通描述名，新参考图按weixin-4.png编号。

提交前git status，显式git add具体路径，不用git add -A；保留用户/并发会话已有修改和暂存状态。提交用docs:/chore:/feat:简洁祈使句，报告验证，不擅自提交/发布。路径/图片链接须复核可达。
