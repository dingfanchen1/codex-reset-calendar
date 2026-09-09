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

## GitHub Actions

工作流使用 GitHub 官方 Actions，并固定到 2026-09-09 核验的不可变提交：

| Action | 版本 | 提交 | 许可证 |
|---|---:|---|---|
| actions/checkout | 7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | MIT |
| actions/setup-python | 7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` | MIT |
| actions/upload-pages-artifact | 5.0.0 | `fc324d3547104276b827a68afc52ff2a11cc49c9` | MIT |
| actions/deploy-pages | 5.0.1 | `368f82528645a54fb793d4d04e342629a3f51346` | MIT |

这些 Actions 在 GitHub 托管运行器中执行，本仓库不复制其源代码。版本升级时需重新核对官方发布说明、权限和兼容性。
