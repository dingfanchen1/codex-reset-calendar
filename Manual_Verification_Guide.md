# 手动验收指南

S1 本地验证、S2 发布准备和 S3 公共服务验证已有执行记录；S4 实机验收尚未开始。按 S1 → S2 → S3 → S4 依次记录，不能以计划步骤当作证据。

## S1 本地核对

1. 根据 S1 补全后的 README 安装固定依赖并运行 unittest，记录命令、通过数量和退出码。
2. 使用真实 reset.json 运行一次本地转换，记录读取时间、规范化字段与输出结果，不转存帖子全文。
3. 对照 UTC 时间、UID、事件数量、来源和双提醒；2026-09-08T02:00:00Z 的上海时间应为 10:00、东京为 11:00，此值只是固定测试样例。
4. 再次处理相同输入，确认输出无变化。

### S1 执行记录（2026-09-09）

- Python：3.12；icalendar：7.3.0。
- 自动化测试：`.venv/bin/python -m unittest discover -s tests -v`，22 项通过，退出码 0。
- 实时读取开始时间：2026-09-09T10:04:14Z（北京时间 18:04:14）。规范化结果为 `state=none`、`resetAt=null`、零事件；未保存 `sourceText`。
- ICS 解析结果：日历名称为“Codex 重置日历”，事件数为 0，使用 UTF-8 与 CRLF。
- 重复同步返回 `changed=false`；`data/current.json` 的 SHA-256 为 `30df6aa26e1646ed1237eed67cd669767ec3aa517c915d5745d89dce2fa5f780`，`public/calendar/codex-reset.ics` 为 `a7fbb8794f69de93e0d00105a83afc6def846df682f5610ed258a4a8602b1925`，两次一致。
- 固定事件样例已自动核对 UTC、UID、版本、中文、来源与两个 VALARM；两个提醒仍需 S4 iPhone 实机观察。

## S2 发布前准备

检查工作流触发、权限、串行行为；模拟首次发布、无变化、线上不匹配及部署恢复；回归通过。公共产物清单不含状态文件、密钥、日志或其他用户数据。尚无 GitHub 实际运行时明确写“云端待验证”。

### S2 执行记录（2026-09-09）

- 自动化测试：`.venv/bin/python -m unittest discover -s tests -v`，39 项通过，退出码 0；其中包含 S1 的 22 项回归。
- 工作流静态检查：Ruby YAML 解析通过；actionlint 1.7.12 校验通过，下载包 SHA-256 与官方发布值 `aba9ced2dee8d27fecca3dc7feb1a7f9a52caefa1eb46f3271ea66b6e0e6953f` 一致。
- 发布模拟：自动化测试覆盖首次 404、线上字节一致、线上不匹配、临时 503 重试恢复、部署后旧内容等待更新及持续不匹配失败。
- 公开清单：`scripts/pages_release.py validate-public --root public` 通过；仅有 `calendar/codex-reset.ics`，SHA-256 为 `a7fbb8794f69de93e0d00105a83afc6def846df682f5610ed258a4a8602b1925`。
- 测试/生产隔离：生产工作流没有 `--input-file` 或测试参数；独立验收日历 CLI 的事件与清空命令已在临时目录运行通过，且标题明确为“验收测试，非真实 Reset”。
- 并发与恢复：同一生产组串行且 `cancel-in-progress=false`；测试提交若不再是当前 `main` 会停止；同步提交不强推，部署失败后由下一次线上不匹配触发重试。
- 云端边界：没有远程仓库，未运行 GitHub Actions、未配置 Pages、未取得公共 URL；以上只构成“发布准备完成”。

## S3 公共服务验收

公开前先取得明确创建仓库和推送授权。拟定仓库、地址不能冒充真实结果。

1. 核实账号、仓库、默认分支、Pages 的 GitHub Actions 发布源；记录配置，不记录令牌。
2. 运行首次手动工作流，取得实际 Pages 地址与运行链接。
3. 无登录请求生产 ICS：HTTP 200，Content-Type 为 text/calendar，UTF-8，可解析；核对事件与本轮产物一致。类型不符记录为问题。
4. 等待并记录至少一次真实定时运行；不能拿手动运行冒充定时。
5. 无变化再次执行，确认无多余提交和部署。
6. 在独立验收通路模拟读取失败、部署失败及恢复；生产源保持有效，不注入虚假事件。
7. 记录每项结果及证据。平台调度延迟不伪造成功，待运行项保持待验证。

### S3 发布前检查记录（2026-09-09）

- Git：`main` 工作区清洁，HEAD 为 `0cfc268`，本地未配置远程。
- GitHub：CLI 已登录账号 `dingfanchen1`；截至 2026-09-09T15:40:38Z，拟定仓库 `dingfanchen1/codex-reset-calendar` 不存在。
- 公开 artifact：白名单复核通过，仅含 `calendar/codex-reset.ics`；SHA-256 为 `a7fbb8794f69de93e0d00105a83afc6def846df682f5610ed258a4a8602b1925`。
- 代码检查：39 项 unittest 全部通过；当前树及 Git 历史未命中常见密钥模式，未发现超过 1 MiB 的已跟踪文件。
- 授权边界：尚未创建公开仓库、配置远程、推送、启用 Pages 或运行云端工作流。上述动作等待用户单独明确授权。

### S3 公共服务执行记录（2026-09-09 至 2026-09-10）

- 仓库与 Pages：公开仓库为 <https://github.com/dingfanchen1/codex-reset-calendar>，默认分支 `main`；Pages 使用 GitHub Actions 发布源并强制 HTTPS。
- 首次发布：运行 [34372887540](https://github.com/dingfanchen1/codex-reset-calendar/actions/runs/34372887540) 成功，测试、生产同步、artifact、部署及部署后字节核对全部通过。
- 公共文件：<https://dingfanchen1.github.io/codex-reset-calendar/calendar/codex-reset.ics> 匿名请求返回 HTTP 200 和 `text/calendar`；UTF-8、CRLF、ICS 解析及“Codex 重置日历”名称核对通过。2026-09-10T10:31:42Z 线上与本地 SHA-256 均为 `a7fbb8794f69de93e0d00105a83afc6def846df682f5610ed258a4a8602b1925`，当前为零事件。
- 手动无变化：运行 [34373133962](https://github.com/dingfanchen1/codex-reset-calendar/actions/runs/34373133962) 成功，日志为 `changed=false`、`No content change`、`online-match`；发布 jobs 全部跳过，远端提交未变化。
- 真实定时：运行 [34443169054](https://github.com/dingfanchen1/codex-reset-calendar/actions/runs/34443169054) 由 `schedule` 触发并成功，日志同样为 `changed=false` 和 `online-match`；没有同步提交或重复部署。
- 故障模拟：上述真实定时运行的云端 test job 通过了网络错误重试、非法输入保留旧产物、暂时在线错误恢复以及部署后持续不匹配失败等固定测试。没有故意制造真实平台故障；生产 ICS 在验证前后均保持 HTTP 200 和字节一致。
- S3 结论：公共服务验证通过。iPhone 是否及时刷新及两个 VALARM 是否真实通知仍待 S4，不能由本次结果代替。

## S4 iPhone 实机

### 准备

记录 iPhone 型号、iOS 版本、当前时区、网络环境（只记录必要概况，不记录 IP 或凭证）。通过日历的“添加订阅日历”入口添加 URL；具体 UI 以设备当前版本为准，不使用下载 ICS 一次性导入代替订阅。

确认系统日历通知、订阅日历事件提醒开启，检查专注模式等实际影响。官方参考：[iPhone 多日历与事件提醒](https://support.apple.com/guide/iphone/use-multiple-calendars-iph3d1110d4/ios)。

### 生产订阅

核对生产 URL、日历名称、当前事件和本地时间。若上游明确无事件，日历订阅可存在但无日程，不以此判失败。

### 独立测试订阅

测试源标题明确“验收测试，非真实 Reset”，与生产 URL 隔离，采用同一事件生成逻辑。

1. 发布至少两小时后的未来测试事件，等待手机实际同步并记录可见时刻。
2. 同 UID 改期，等待刷新，确认原事件更新且无重复，不重新订阅。
3. 新 UID 替换，等待刷新，确认只保留新事件。
4. 发布空日历，等待刷新，确认事件移除而订阅保留。
5. 再发布至少两小时后的提醒测试事件，确保提前 15 分钟之前已同步；分别观察提前 15 分钟、到点通知。
6. 如测试事件未及时同步到手机，重新安排未来事件并如实记录，不将缺通知认定为代码成功或失败而不调查。

### 证据表（填写后才构成验收）

| 项目 | 期望 | 实际结果 | 时间/证据 | 状态 |
|---|---|---|---|---|
| 生产订阅 | 名称、事件、时区正确 | 未执行 | 无 | 待验收 |
| 同 UID 改期 | 无重复，时间更新 | 未执行 | 无 | 待验收 |
| 新 UID 替换 | 只有新事件 | 未执行 | 无 | 待验收 |
| 清空 | 无事件，订阅仍在 | 未执行 | 无 | 待验收 |
| 提前 15 分钟 | 实际通知一次 | 未执行 | 无 | 待验收 |
| 到点 | 实际通知一次 | 未执行 | 无 | 待验收 |

截图只留必要日历内容，避免包含用户其他日程或通知隐私；不要自动公开设备证据。测试通知缺失必须记录为待调查/未通过，两个 VALARM 不是实机证据。

## 运维记录

S2 已准备手动 `force_deploy` 恢复入口、线上不匹配自动重试及每月 Actions 检查要求。S3 落地后补全实际公开 URL、运行链接和界面操作证据。上游事件长时间未变不等于故障；公共仓库定时任务可能因长期无活动禁用。不得写入无意义保活提交或自动新增提醒服务。
