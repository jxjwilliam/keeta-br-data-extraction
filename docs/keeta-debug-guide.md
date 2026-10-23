# 设备与采集排错

本文件只讲操作，运行命令见 [README](../README.md)，当前状态见 [TODO](../TODO.md)。

## 连接与投屏

```bash
adb devices -l
scrcpy --serial f753a0f3 --window-title keeta
```

先确认实际设备编号。当前使用X3 f753a0f3，X6 979f0245是独立历史设备；不要混用会话。若unauthorized，在手机确认USB调试；若无设备，检查线缆/连接/USB模式；手机离线不是Keeta限流。

保持解锁，可在手机设置充电时保持唤醒。脚本发送KEYCODE_WAKEUP，但不能绕过锁屏。不要自动扩大安全权限或安装额外服务。

## UI读取

```python
import uiautomator2 as u

d = u.connect("f753a0f3")
d.jsonrpc.setConfigurator({"waitForIdleTimeout": 0})
xml = d.dump_hierarchy()
```

标准adb uiautomator dump可能因idle超时失败。当前uiautomator2通过jsonrpc设置；不要用不支持的d.settings写法。输出应存内部目录并按capture()脱敏，不能把联系人/账号内容打印到文档或提交。

## 常见停止原因

| 现象 | 处理 |
| --- | --- |
| 空树/锁屏/离线 | 先解锁、恢复USB，再恢复同设备会话 |
| Select a delivery address | 确认7550保存地址确实被选中；提示气泡不算 |
| 单店商品/金额失败 | 结果保留partial；先检查证据离线修解析，不立即重进店 |
| 优惠券/支付/广告/未知页 | 通用恢复有界返回，旧动作作废；恢复失败再人工核对 |
| Access error/安全验证 | 停止保留结果；人工确认恢复再使用--access-restored，不反复Refresh |
| 购物车冲突/外部支付/已提交订单页 | 停止等待用户核对；不清购物车、不提交订单 |
| XLSX导出失败 | CSV/账本先保留，检查resources.md中的专用运行时和内部xlsx.log |

日志中的旧stop.log是最近一次记录的停止，不表示当前进程状态；以当前终端、CSV及账本为准。不要把进程启动说成采集成功。完整率口径见 [采集指南](keeta-continuous-guide.md)。

巴西IP/SIM/GPS不是已证实前置条件，VPN不能保证避免访问限制；不根据历史估算采购设备或承诺生产容量。官方接入能力及来源见 [调查](oc-keeta-access-and-scale-research.md)。
