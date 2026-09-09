# 项目当前真实状态

## 当前状态

- 版本范围：Codex 重置公共日历 v0.1A。
- 当前实施者：无。
- S0：完成。项目规范基线提交为 `562d681`，四个阶段窗口已创建并完成首次只读检查。
- S1：本地验证通过；同步脚本、固定依赖、状态与 ICS、固定样例及 22 项 unittest 已完成。
- S2：发布准备完成；本地工作流检查、发布模拟和 39 项回归已通过，云端未验证。
- S3：可开始发布前检查；未取得远程创建/推送授权，GitHub Actions 与 Pages 均未验证。
- S4：待验收，前置 S3 未通过。
- 远程：未配置；生产订阅地址：不存在。
- 代码/依赖/测试/工作流：S2 本地准备与验证已完成；云端工作流尚未运行。
- 公开发布和 iPhone 实机验证：未进行。

## 最近验收

2026-09-09 S2 本地核验：Python 3.12 环境中 39 项 unittest 全部通过，退出码 0；YAML 解析、actionlint 1.7.12、字节码编译和公开目录白名单均通过。首次发布、无变化、线上不匹配、暂时失败恢复及部署后核对均由离线模拟覆盖。未配置远程，未进行云端或实机验收。

## 下一阶段

由用户在 S3 窗口 `01a08566-696b-7210-8fb4-4375d8f33575` 发送“开始 S3”。该口令只授权发布前检查；创建公开仓库和推送仍需独立明确授权。

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

后续每阶段追加同样结构：完成内容、测试命令与结果、证据、限制、下一阶段输入。不得把待验收项提前标为通过。
