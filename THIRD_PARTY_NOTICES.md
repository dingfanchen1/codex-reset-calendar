# 第三方依赖说明

## icalendar

- 项目：https://github.com/collective/icalendar
- 固定版本：7.3.0
- 许可证：BSD-2-Clause
- 用途：生成和解析 RFC 5545 iCalendar（ICS）文件。

本项目不复制 `icalendar` 源代码。安装依赖时，完整许可证文本随该软件包提供。

为保证安装可复现，requirements.txt 同时固定其传递依赖：

| 组件 | 版本 | 软件包元数据中的许可证 |
|---|---:|---|
| python-dateutil | 2.9.0.post0 | Dual License |
| six | 1.17.0 | MIT |
| typing-extensions | 4.16.0 | PSF-2.0 |
| tzdata | 2026.3 | Apache-2.0 |

这些组件只通过 Python 包管理器安装，本仓库不复制其源代码。各包的完整许可证文本随安装包提供。
