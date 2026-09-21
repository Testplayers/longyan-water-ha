# 龙岩水发自来水 · Home Assistant 集成

> 把**龙岩水发自来水**网厅（`service.fjlyzls.com`）的水表数据接入 Home Assistant：
> 账户余额、欠费、本期用水量、表读数、水价、应缴金额、抄表日期，全部自动更新。

![HA](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.12%2B-yellow)

---

## 项目亮点

| 能力 | 说明 |
|---|---|
| 🤖 **全自动登录** | 内嵌验证码识别（颜色聚类 + 模板匹配），token 失效自动重登，**无需人工干预** |
| 🔁 **自动刷新** | 默认每 6 小时拉取一次（可调） |
| 📊 **8 个传感器** | 余额 / 欠费 / 本期用水量 / 本期读数 / 上期读数 / 水价 / 本期应缴 / 上次抄表日期 |
| ⚡ **能源面板** | 用水量带 `total_increasing`，可直接接入 HA 能源仪表板 |
| 🖐️ **人工兜底** | 自动识别失败时，配置界面会直接显示验证码图片，手动输入即可 |
| 📦 **零外部依赖** | 除 HA 自带的 Pillow 外不依赖任何第三方库 |

> 本项目通过**分析网厅前端 JavaScript** 得到接口（非官方 API），如网厅改版可能失效，修复方法见 [更新与维护](docs/06-更新与维护.md)。

---

## 快速开始

```text
1. 把 custom_components/longyan_water 复制到 HA 的 /config/custom_components/
2. 重启 Home Assistant
3. 设置 → 设备与服务 → 添加集成 → 搜索「龙岩水发自来水」
4. 输入网厅的手机号 + 密码，完成
```

详细步骤（含远程 SSH 一键部署）见 **[docs/03-安装部署.md](docs/03-安装部署.md)**。

---

## 文档目录

| 文档 | 内容 |
|---|---|
| [01 · 项目简介](docs/01-项目简介.md) | 背景、能拿到什么数据、代码结构 |
| [02 · 接口原理](docs/02-接口原理.md) | 逆向出的网厅接口、参数格式、字段含义、自己重新抓包的方法 |
| [03 · 安装部署](docs/03-安装部署.md) | 手动 / SSH 一键部署 / Samba 上传 |
| [04 · 使用说明](docs/04-使用说明.md) | 配置流程、实体清单、能源面板、自动化示例、改刷新频率 |
| [05 · 常见问题](docs/05-常见问题.md) | 验证码识别失败、登录报错、数据不更新等 |
| [06 · 更新与维护](docs/06-更新与维护.md) | **网厅改版后怎么修**、重新生成验证码模板、如何部署与回滚 |

---

## 目录结构

```
longyan-water-ha/
├── custom_components/longyan_water/   # 集成本体（复制到 HA 的 custom_components 即可用）
│   ├── api.py                # 网厅 API 客户端（登录 / 户号查询）
│   ├── ocr.py                # 验证码识别（颜色聚类 + 模板匹配）
│   ├── captcha_templates.json# 验证码字符模板（约 1.9 MB，36 字符 × 63 变体）
│   ├── coordinator.py        # 数据更新协调器（6h 刷新 + token 自愈）
│   ├── config_flow.py        # 配置流程（OCR 自动 + 人工输入兜底）
│   ├── sensor.py             # 8 个传感器
│   ├── entity.py             # 实体基类 / 设备信息
│   ├── const.py              # 域名、接口路径、固定参数
│   └── manifest.json         # 集成元数据
├── docs/                      # 文档
└── tools/
    ├── deploy.py              # 一键部署到远程 HA（SSH 流式传输）
    ├── publish.py             # 一键把本仓库同步到 GitHub（改完代码发布用）
    └── gen_captcha_templates.py # 重新生成验证码模板
```

---

## 兼容性

- Home Assistant **2024.1.0+**（2026.x 实测可用）
- 数据源：龙岩水发自来水网厅 <https://service.fjlyzls.com>
- 同平台（杭州水务 `iwater`）的其他水司理论上也能用，需改 `const.py` 里的 `BASE_URL` 与 `waterCorpId`

---

## 免责声明

本项目为个人自用工具，接口来自对公开网厅页面的前端分析，**非官方接口**。
仅用于查询自己账户的数据，请勿用于批量爬取或任何商业用途。使用风险自负。

## License

MIT
