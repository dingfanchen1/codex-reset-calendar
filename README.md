# Codex 重置公共日历

复用 The Reset Company 的公开 `reset.json`，转换为公共 ICS 日历，经 GitHub Pages 供 Apple 日历订阅。

## 当前阶段

项目规范已固定；功能尚未实现。当前仅建立本地 Git 管理，不创建远程仓库或推送。生产订阅地址尚不存在。

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

当前没有可运行脚本或测试，不应把下列计划命令当成已执行结果。S1 实现后补全环境安装与运行命令，测试入口固定为：

```bash
python3 -m unittest discover -s tests -v
```

## 来源与边界

数据来自 [The Reset Company](https://github.com/yuanlang12/The-Reset-Company)。本项目不是 OpenAI 官方服务，不读取个人账户、不执行额度重置。上游时间可能为近似值，订阅日历不是实时推送。
