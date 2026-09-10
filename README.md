# Codex 重置公共日历

复用 The Reset Company 的公开 `reset.json`，转换为公共 ICS 日历，经 GitHub Pages 供 Apple 日历订阅。

## 当前阶段

S3 公共服务验证已通过。S4 实机验收正在进行；生产订阅以及独立测试订阅的改期、替换、清空已通过，两次实际通知仍需取得 iPhone 证据。

## 订阅地址

- HTTPS：<https://dingfanchen1.github.io/codex-reset-calendar/calendar/codex-reset.ics>
- Apple 日历订阅：`webcal://dingfanchen1.github.io/codex-reset-calendar/calendar/codex-reset.ics`
- S4 独立测试日历：<https://dingfanchen1.github.io/codex-reset-calendar/acceptance/calendar/codex-reset-test.ics>
- 公开仓库：<https://github.com/dingfanchen1/codex-reset-calendar>

## 已确认范围

- 只保留上游当前事件；不读取历史、不维护历史日历。
- 写入提前 15 分钟和到点两次提醒；实际通知需 iPhone 验收。
- 过点后跟随上游保留、替换或清空，不推断个人账户是否已重置。
- 每十分钟尝试同步；接受上游发现及 Apple 刷新的延迟。
- Python、icalendar、GitHub Actions、GitHub Pages；不做 X API、支付、爬虫、Mac App、Widget、数据库或网页界面。

## 阶段导航

所有窗口共用当前目录，必须依次开始。窗口编号见 [Tickets.md](Tickets.md)。

| 顺序 | 任务窗口 | 启动口令 | 阶段终点 |
|---|---|---|---|
| 1 | S1｜本地转换与自动化测试 | 开始 S1 | 本地验证通过 |
| 2 | S2｜自动化工作流与发布准备 | 开始 S2 | 发布准备完成，云端未验证 |
| 3 | S3｜GitHub Pages 发布与线上验收 | 开始 S3 | 公共服务验证通过，需单独发布授权 |
| 4 | S4｜iPhone 订阅与双提醒实机验收 | 开始 S4 | 实机证据完整 |

## 文档入口

- [AGENTS.md](AGENTS.md)：协作规则、串行约束与 Git 边界。
- [Development_Plan.md](Development_Plan.md)：数据、ICS、自动化的完整规范。
- [Repo_Current_State.md](Repo_Current_State.md)：当前真实状态与交接。
- [Manual_Verification_Guide.md](Manual_Verification_Guide.md)：发布及设备验收。
- [Prompt_Playbook.md](Prompt_Playbook.md)：各窗口可独立使用的提示词。

## 运行与验证

目标运行时是 Python 3.12。先创建项目专用虚拟环境并安装已固定版本的依赖：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

运行离线自动化测试：

```bash
.venv/bin/python -m unittest discover -s tests -v
```

从唯一生产上游同步一次：

```bash
.venv/bin/python scripts/sync_reset.py
```

也可以用固定样例做不访问网络的本地转换；为避免覆盖生产路径，这里显式指定临时输出位置：

```bash
.venv/bin/python scripts/sync_reset.py \
  --input-file tests/fixtures/reset_scheduled.json \
  --state-file /tmp/codex-reset-current.json \
  --output /tmp/codex-reset-calendar.ics
```

正式本地结果写入 `data/current.json` 和 `public/calendar/codex-reset.ics`。同步会先完整校验并生成两个候选文件；失败时保留上次成功结果。相同有效输入不会改变文件字节。

S1 已在 2026-09-09 使用 Python 3.12 和 `icalendar==7.3.0` 运行 22 项测试，结果全部通过；实时上游核对当时为 `state=none`、零事件，重复同步无文件变化。此证据不代表云端或 iPhone 已验收。

## 自动化与发布准备

`.github/workflows/sync-calendar.yml` 的生产流程按每小时第 7、17、27、37、47、57 分钟运行，也支持手动运行和 `main` 更新；拉取请求只运行离线测试。生产同步命令固定为 `python scripts/sync_reset.py`，工作流不接受测试输入。

生产流程先测试，再同步并仅提交 `data/current.json` 与 `public/calendar/codex-reset.ics`。它随后比较线上与本地 ICS：线上一致时不部署；404、内容不匹配或手动选择 `force_deploy` 时部署。部署后再次按字节核对；部署失败时，下一次运行会因线上不匹配重新部署。生产流程串行执行且不取消正在运行的发布。

本地运行发布前检查：

```bash
.venv/bin/python scripts/pages_release.py validate-public --root public
.venv/bin/python -m unittest discover -s tests -v
```

当前公开白名单只有生产日历 `public/calendar/codex-reset.ics` 和明确标注的 S4 测试日历 `public/acceptance/calendar/codex-reset-test.ics`。状态文件、日志、固定样例和其他文件都会被拒绝上传。

独立验收日历使用同一 UID、版本、ICS 与双提醒生成逻辑，但标题和说明固定标注“验收测试，非真实 Reset”，输出路径必须与生产隔离。例如把测试文件写入临时目录：

```bash
.venv/bin/python scripts/acceptance_calendar.py \
  --state-file /tmp/codex-reset-acceptance-current.json \
  --output /tmp/codex-reset-acceptance.ics \
  event --reset-at 2099-01-01T12:00:00Z --source-id acceptance-1

.venv/bin/python scripts/acceptance_calendar.py \
  --state-file /tmp/codex-reset-acceptance-current.json \
  --output /tmp/codex-reset-acceptance.ics \
  clear
```

验收事件要求至少安排在运行时刻两小时后。S4 使用同一生成逻辑把测试日历写入独立路径，状态保存在不公开的 `acceptance/data/current.json`。生产同步命令仍只读取固定上游，不接受测试输入；Pages 会分别比较并核对生产和测试 ICS，任一线上文件落后时才重新部署。

GitHub Pages 必须在仓库设置中选择 **GitHub Actions** 作为发布源。公开仓库的定时工作流可能因 60 天无仓库活动而停用；维护者应每月检查 Actions，必要时从界面重新启用，不创建无意义保活提交。

## 来源与边界

数据来自 [The Reset Company](https://github.com/yuanlang12/The-Reset-Company)。本项目不是 OpenAI 官方服务，不读取个人账户、不执行额度重置。上游时间可能为近似值，订阅日历不是实时推送。

第三方组件的版本、用途与许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
