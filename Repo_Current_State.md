# 项目当前真实状态

## 当前状态

- 版本范围：Codex 重置公共日历 v0.1A。
- 当前实施者：S4 窗口 `01a08566-609c-7f11-bc15-9e7d70727575`，iPhone 订阅与双提醒实机验收进行中。
- S0：完成。项目规范基线提交为 `562d681`，四个阶段窗口已创建并完成首次只读检查。
- S1：本地验证通过；同步脚本、固定依赖、状态与 ICS、固定样例及 22 项 unittest 已完成。
- S2：发布准备完成；本地工作流检查、发布模拟和 39 项回归已通过，云端未验证。
- S3：公共服务验证通过；公开仓库、Pages、手动运行、真实定时运行、无变化行为和故障模拟均有云端证据。
- S4：实机验收进行中；生产订阅和初始测试事件可见性已通过，正在验证同 UID 改期。
- 远程：`origin` 为 `https://github.com/dingfanchen1/codex-reset-calendar.git`，默认分支为 `main`。
- 生产订阅地址：`https://dingfanchen1.github.io/codex-reset-calendar/calendar/codex-reset.ics`。
- 代码/依赖/测试/工作流：本地与 GitHub Actions 均已验证。
- 公开发布：完成；iPhone 实机验证：部分通过，改期、替换、清空和双提醒待验收。

## 最近验收

2026-09-10 S3 公共服务核验：公开 ICS 匿名请求返回 HTTP 200 和 `text/calendar`，UTF-8、CRLF 与解析均通过，日历名称为“Codex 重置日历”，当前零事件；线上与本地 SHA-256 均为 `a7fbb8794f69de93e0d00105a83afc6def846df682f5610ed258a4a8602b1925`。首次发布、手动无变化运行和真实定时运行均成功；无变化时没有同步提交或重复部署。详细链接见 Manual_Verification_Guide.md。

## 下一阶段

发布同 UID 改期版本并等待原 iPhone 订阅自动刷新；确认无重复后继续新 UID 替换、清空和双提醒。

## 交接记录

### S0 项目初始化（已完成）

- 完成内容：建立八份规范/导航文件、本地 Git 基线和四个阶段窗口；真实窗口 ID 已写入 Tickets.md。
- 验证：基线提交 `562d681` 存在；四个窗口的首次只读任务均已完成；共享工作区未被阶段窗口修改；无 Git 远程。
- 限制：本轮只建文档、Git 和阶段窗口，不实施 S1–S4。
- 下一阶段输入：已提交规范、S1 任务说明。

### S1 本地转换与自动化测试（已完成）

- 完成内容：固定 Python 依赖；实现上游获取、字段校验、规范化状态、稳定 UID/SEQUENCE、零或一事件 ICS、双提醒、失败保留与两文件回滚；加入固定样例和 unittest。
- 验证：Python 3.12 下 22 项 unittest 通过；字节码编译通过；2026-09-09T10:04:14Z 实时上游本地转换及重复输入核对通过。详细记录见 Manual_Verification_Guide.md。
- 证据：`tests/test_sync_reset.py`、`tests/fixtures/reset_scheduled.json`、`data/current.json`、`public/calendar/codex-reset.ics`。
- 限制：当前实时上游是零事件，只能证明空日历实况；有事件路径由固定样例验证。GitHub Actions、Pages 与 iPhone 通知未验证。
- 下一阶段输入：S1 已验证的同步入口、状态文件、生产 ICS 路径和回归测试命令；S2 可据此实现发布准备。

### S2 自动化工作流与发布准备（已完成）

- 完成内容：实现定时、手动、`main` 与拉取请求入口；测试、同步、显式内容提交、线上比较、Pages artifact/deploy、部署后字节核对；加入最小权限、串行控制、提交竞态保护、公开白名单及独立验收日历生成器。
- 验证：Python 3.12 下 39 项 unittest 通过；字节码编译、Ruby YAML 解析、actionlint 1.7.12 与 `git diff --check` 通过；首次、无变化、不匹配和失败恢复模拟通过。详细记录见 Manual_Verification_Guide.md。
- 证据：`.github/workflows/sync-calendar.yml`、`scripts/pages_release.py`、`scripts/acceptance_calendar.py`、`tests/test_pages_release.py`、`tests/test_workflow_contract.py`、`tests/test_acceptance_calendar.py`。
- 限制：无远程、无 Actions 运行、无 Pages 配置或公共 URL；独立验收日历当前仅有本地生成能力，未公开；iPhone 未验收。
- 下一阶段输入：已固定的官方 Actions 引用、只含生产 ICS 的公开白名单、手动强制部署入口、线上比较与恢复逻辑；S3 先核对公开清单和账号，取得独立授权后再创建/推送/部署。

### S3 GitHub Pages 发布与线上验收（已完成）

- 完成内容：创建公开仓库并推送 `main`；配置 Pages 的 GitHub Actions 发布源；完成首次部署、匿名公共 ICS 核对、无变化手动运行、真实定时运行和云端故障模拟。
- 验证：首次运行 `34372887540`、手动运行 `34373133962`、真实定时运行 `34443169054` 均成功；公开 ICS 为 HTTP 200、`text/calendar`、UTF-8、CRLF、可解析且与本地字节一致；无变化运行未提交或部署。
- 证据：生产地址 `https://dingfanchen1.github.io/codex-reset-calendar/calendar/codex-reset.ics`；运行链接和故障模拟边界见 Manual_Verification_Guide.md。
- 限制：故障行为由 GitHub Actions 中的固定模拟测试验证，没有故意破坏生产部署；iPhone 的订阅刷新与两个实际通知均待 S4。
- 下一阶段输入：固定生产订阅地址、当前零事件日历和独立验收日历生成器；S4 使用独立测试源完成改期、替换、清空和双提醒实机验收。

后续每阶段追加同样结构：完成内容、测试命令与结果、证据、限制、下一阶段输入。不得把待验收项提前标为通过。
