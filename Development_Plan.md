# Codex 重置公共日历 v0.1A 开发规范

## 1. 产品范围与来源

目标：用户订阅固定公共 ICS 地址一次，后续由 Apple 日历刷新当前 Reset 事件。

唯一输入：

```text
https://raw.githubusercontent.com/yuanlang12/The-Reset-Company/main/public/data/reset.json
```

只显示当前事件；不读 history.json、不积累历史。保留提前 15 分钟和到点双提醒。过点后不自行清理，跟随上游替换或清空。接受上游及客户端延迟，不保证每次真实公告都有提前提醒。

不做 X API、开发者注册、支付、爬虫、Mac 悬浮面板、Widget、数据库、网页界面、个人账户查询或重置执行。

2026-09-08 规划阶段核查：上游 schemaVersion=1，记录有 state、resetAt、sourceId、sourceUrl、sourceAuthor、announcedAt、confidence。该次 resetAt 为 2026-09-08T02:00:00Z、state 为 rolling-out，仅为当时上游快照，不能当作后续当前数据或个人账户完成证据。

当时上游工作流为每日 UTC 01:17（北京时间 09:17）；我们的十分钟同步不能加速上游发现。上游只有内容变化时写入检查信息，旧 lastCheckedAt 不能独立证明监控停止。S1 实时核对数据契约，S3 再核对平台行为，发现不兼容应报告而非擅自换源。

来源：
- [上游数据](https://raw.githubusercontent.com/yuanlang12/The-Reset-Company/main/public/data/reset.json)
- [上游工作流](https://github.com/yuanlang12/The-Reset-Company/blob/main/.github/workflows/monitor-reset.yml)
- [上游同步逻辑](https://github.com/yuanlang12/The-Reset-Company/blob/main/scripts/check-reset.mjs)

## 2. 架构与最小技术栈

```text
公开 reset.json → GitHub Actions → 字段校验与变化判断
              → 当前状态 JSON + ICS → Pages 明确部署 → Apple 日历
```

Python 3.12 为目标运行时；标准库负责 HTTP、字段校验、JSON、文件比较及 unittest；icalendar 负责 ICS 序列化。S1 固定 `icalendar==7.3.0` 及其传递依赖，不使用开发预览版。icalendar 采用 BSD-2-Clause，来源与许可证说明见 THIRD_PARTY_NOTICES.md；维护成本为依赖更新和兼容检查。参考 [官方文档](https://icalendar.readthedocs.io/en/stable/)。

建议工程职责：scripts/sync_reset.py 为同步入口；data/current.json 保存规范化事件与版本元数据；public/calendar/codex-reset.ics 为生产产物；tests/ 放固定样例和测试；.github/workflows/ 放自动化。依赖锁定和具体辅助函数由对应阶段按最小实现落地，不增加配置框架。

公共目录只放明确允许公开的产物。内部当前状态不直接作为公共 API，避免锁定不必要的数据结构。日志和输出不得带帖子全文或秘密。

本次上游文件树未发现许可证文件。只读取必要结构化数据，不复制其代码、前端、采集器、图片或帖子全文；公开可读不等于可以任意复制。对外文档注明数据来源和非官方属性。

## 3. 输入契约与变化行为

- schemaVersion 必须为 1。允许额外字段，但不擅自解释新版本或新状态。
- 已知状态：scheduled、announced、rolling-out、completed、estimated、none。
- resetAt 字段必须存在：null 表示明确无时间；非 null 必须为含时区的有效 ISO 时间，统一归一为 UTC。
- none 或有效契约下明确 resetAt=null：生成零事件的订阅日历，地址保持不变，不保留旧日程作为历史。
- 其他已知状态有有效 resetAt 时生成一个事件。需要非空 sourceId 及有效 HTTPS sourceUrl；sourceAuthor 若给出，必须符合上游 Tibo 来源。
- 缺少必需字段、非法 JSON、非法或无时区时间、未知状态/版本：失败，保留上次成功文件；不能把错误当成清空。
- 同 sourceId 修改时间或有效说明：更新原 UID。不同 sourceId：生产源只保留新事件。
- 时间过去不触发本地删除，也不推断 completed 状态。
- estimated 或非 high 置信度：说明中明确可能为近似时间；缺失置信度标为未知，不提升为 high。
- 只保留必要规范化字段，忽略 sourceText。lastCheckedAt 等检查信息单独变化不更新事件版本。
- 当前状态文件保存最近事件 UID、版本及修改时间。事件清空后保留最近版本元数据，允许同一来源再次出现时续用 UID 与递增版本；这不是历史事件列表。

先完整校验再提交候选结果，不进行部分文件更新。网络请求超时 20 秒；网络错误、429、5xx 最多三次总尝试，采用短暂退避；其他非成功 HTTP 响应直接报错。首次失败不发布假日历，后续失败保持最后成功版本，日志给出错误类别。

## 4. ICS 公共输出契约

| 项目 | 规则 |
|---|---|
| 日历名称 | Codex 重置日历 |
| 生产路径 | calendar/codex-reset.ics |
| 事件数量 | 零或一 |
| SUMMARY | ⚡ Codex Reset |
| UID | codex-reset-{sourceId}@codex-reset-calendar |
| DTSTART | resetAt 的 UTC 时间 |
| DTEND | DTSTART 后 5 分钟，仅为显示占位 |
| DESCRIPTION | 中文说明、上游状态、置信度、来源及非官方属性；近似值明确标注 |
| URL | 有效 HTTPS sourceUrl |
| 提醒 | 两个 DISPLAY VALARM，TRIGGER 分别 -PT15M 与 PT0S |
| 忙闲 | TRANSP:TRANSPARENT |
| 格式 | UTF-8、CRLF、正确文本转义和按字节长行折叠 |

VCALENDAR 使用 VERSION:2.0、固定 PRODID、CALSCALE:GREGORIAN；作为订阅源发布，不生成会议邀请。没有事件时保留日历容器，须通过解析及客户端空订阅验收。

首次事件 SEQUENCE=0；同 UID 的有效内容变化才递增。DTSTAMP 和 LAST-MODIFIED 使用该事件版本生成时间，不能用 Reset 开始时间代替。输入不变时版本、时间戳及全部输出字节保持不变，保证无变化不提交。

标准参考：[RFC 5545](https://www.rfc-editor.org/rfc/rfc5545)。事件中的两个提醒字段正确只是本地验收，不能等同 iPhone 已通知。

## 5. GitHub Actions 与 Pages

S2 编写，S3 经发布授权后启用。定时入口为每小时第 7、17、27、37、47、57 分钟，另有手动运行及默认分支更新入口；拉取请求只运行测试。

一次生产流程：测试 → 获取并校验 → 生成候选 → 有有效变化才提交明确文件 → 比较线上 ICS 与候选 → 需要时上传 Pages 产物并明确部署 → 获取公共 ICS 核对。

无内容变化不重复提交或部署。首次发布/手动恢复允许强制部署；在线 404 可视为首次发布，其他在线请求错误先重试并报告，不当成合法空日历。部署失败后下一次即使上游未变，仍依据线上不匹配重试。避免“文件已提交但线上永远停旧版本”。

Pages Source 必须选择 GitHub Actions，使用官方 upload-pages-artifact/deploy-pages 流程。不能靠默认 GITHUB_TOKEN 推送触发分支式 Pages 构建。S2 按 2026-09-09 官方版本固定到不可变提交：checkout v7.0.1、setup-python v7.0.0、upload-pages-artifact v5.0.0、deploy-pages v5.0.1；版本与提交见工作流和 THIRD_PARTY_NOTICES.md。

同步提交使用 contents:write，部署使用 pages:write 和 id-token:write，按 job 分配，使用内置令牌，不新增长期个人令牌。串行发布、不取消正在部署的运行、不强推解冲突、不无限重试。普通分支推送冲突使本轮失败并保留线上成功版本。

日志记录检查结果、上游状态、变化原因、部署结果。暂不新增外部告警或账户凭证。README 记录调度可能延迟、公共仓库无活动 60 天可能禁用定时任务；维护者按月检查并按文档恢复，不加无意义保活提交。

参考：
- [Pages 发布源与默认令牌限制](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)
- [Actions 触发与调度](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [禁用和启用工作流](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows)

拟定仓库 dingfanchen1/codex-reset-calendar，拟定 URL 为 https://dingfanchen1.github.io/codex-reset-calendar/calendar/codex-reset.ics；webcal 链接使用同一主机和路径。以上尚未创建/验证。发布时核实账户和名称；一旦公开不随意改路径。

## 6. 分阶段验收与发布隔离

阶段任务详见 Tickets.md，人工步骤详见 Manual_Verification_Guide.md。

S1：固定样例覆盖正常、UTC 换算、重复输入、同 UID 改期、新 UID 替换、清空、过去时间、未知版本、无时区、网络错误、中文转义、双提醒、检查字段变化。运行 unittest；实时上游只做另一次本地核对，不能成为离线测试的依赖。

S2：工作流静态验证与本地模拟首次/无变化/线上不匹配/失败恢复，回归通过；明确云端未验证。准备独立测试日历，生产定时工作流不接受测试输入。

S3：经明确授权公开；公共 ICS 200、无需登录、text/calendar、UTF-8、可解析、内容一致；手动和至少一次真实定时成功；验证故障保留与部署恢复。任何故障演练只用测试通路，不把假公告发入生产。

S4：生产订阅加独立测试源；验证原 UID 改期、新 UID 替换、清空、时区和双提醒。测试源明确“验收测试，非真实 Reset”，提供至少两小时后的事件，使用同一生成逻辑。发布测试变更后等待真实刷新并记录时刻，不能靠重新订阅掩盖更新失败。

只能分别宣告“本地验证通过”“公共服务验证通过”“iPhone 实机验收通过”。缺少设备或通知证据时保持待验收；真实公告能否提前到达受已接受的上游延迟约束。
