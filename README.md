# 麦麦三问局

**最多三问，选定一餐；价格、热量、汉堡用料等级一起看。**

面向「想吃麦当劳但懒得翻菜单」的对话 Skill。用麦当劳中国官方 MCP 读真实门店菜单，问最多三个问题就给出**一份主推 + 一份备选**，附带真实核价、单项与整餐热量，以及有官方来源的用料等级。首版只选餐报价，默认到店自取。

> 麦当劳程序员创意开发大赛参赛作品，使用 WorkBuddy 开发，非麦当劳官方产品。

## 目标用户

- 打开外卖或站在柜台前，不想翻完整菜单的人
- 有预算和忌口（不要辣、只想吃鸡肉）但拿不定主意的人
- 想同时比较「花多少钱」和「吃进多少 kcal」的人

## 它能做什么

| 能力 | 说明 |
|---|---|
| 真实核价 | 用 `calculate-price` 算出实际应付总价，菜单标价不作最终报价 |
| 热量核算 | 官方 `energyKcal` 优先，按单品规格与数量汇总整餐 |
| 用料等级 | 每个汉堡给出档次、理由和可点击的官方资料链接 |
| 主推 + 备选 | 两份不同的可行方案，各配一句对应用户回答的理由 |
| 随时改单 | 换餐、换饮品、改数量后重新核价与汇总，不重开三问 |

## 快速开始

**1. 申请 Token**：在[麦当劳 MCP 平台](https://open.mcd.cn/mcp)注册并激活 MCP Token。

**2. 连接 MCP**：在宿主中添加自定义连接器，地址 `https://mcp.mcd.cn`，传输 `streamablehttp`，请求头 `Authorization: Bearer ${MCD_MCP_TOKEN}`。可直接参考 [mcp-config.example.json](mcp-config.example.json)。Token 只填在本机连接器设置里，不要写进仓库或对话。

**3. 加载 Skill**：把本目录整体导入宿主，入口为 [SKILL.md](SKILL.md)，需同时保留 `scripts/` 与 `references/`。WorkBuddy 中在「技能 → 添加技能 → 上传技能」导入 `mcd-three-questions.zip`，详见[官方文档](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。

环境要求：支持对话 Skill 与远程 MCP 的宿主；跑汇总脚本需 Python 3.9+，无第三方依赖。

## 使用示例

```
开一局麦麦三问，帮我选一顿。
```

信息给得越全，问题越少：

```
我在人民广场附近，到店自取，25 元以内，鸡肉正餐，不要辣。
```

```
第1问 这顿最多花多少？  →  25 元
第2问 正餐 / 解馋小食 / 喝点东西？  →  正餐
第3问 候选里更想要牛肉还是鸡肉？  →  鸡肉
→ 输出主推与备选：餐品明细、核价、热量、用料等级
后续：把饮料换掉，汉堡改两个 → 重新核价，不重开三问
```

已说过的条件不再追问；门店未确认时先定位门店（这一步不计入三问）。第三问回答「随便」时直接按偏好与价格结束。

## 数据口径

- **价格**：`calculate-price` 返回的 `data.price` 单位为分，除以 100 得到元；未核价时标「待核价」，不填估价。
- **热量**：优先官方 `energyKcal`（包含 0），仅缺失时用 `energyKj ÷ 4.184`；单份 × 数量后汇总取整。套餐只原子项计入，不重复计父项；缺失值不计为零，显示已知合计与未计入项。
- **等级**：项目按公开用料与定位自定义的分类（Lv.3 臻选 / Lv.2 升级 / Lv.1 经典），不是官方品质分或口感评分。未收录的汉堡显示「待评」。映射与查阅日期见 [burger-grades.json](references/burger-grades.json)。
- **只读**：不调用领券、支付、下单、取消等写操作；等级不覆盖用户偏好，也不因等级擅自提价。

## 目录结构

```text
SKILL.md                  对话流程与规则（宿主入口）
scripts/meal_summary.py   本地汇总：热量换算、等级匹配、Markdown 表格
references/               等级资料表与输入数据契约
examples/                 演示输入输出、真实调用快照
tests/                    16 项单元测试
MCP_INTEGRATION.md        MCP Server / Tool / 调用链 / 联调记录
workbuddy.md              WorkBuddy 开发上下文
CONTEST_DECLARATION.md    参赛声明（官方原文，未改动）
```

## 离线演示与测试

无需 Token，只验证本地计算与展示（演示数值为虚构输入）：

```bash
python scripts/meal_summary.py examples/demo.json
python scripts/meal_summary.py examples/demo.json --output local-demo.md
python -m unittest discover -s tests -v
```

## 已验证范围

2026-10-24 已完成官方 MCP 真实只读联调：认证、门店、菜单、营养、详情、计价共 12 次调用全部成功，覆盖三档等级与超预算分支；快照见 [live-output.md](examples/live-output.md)，明细见 [MCP_INTEGRATION.md](MCP_INTEGRATION.md)。完整宿主对话的端到端演示仍以实际运行结果为准。

## 参赛材料

| 文件 | 状态 |
|---|---|
| `README.md` | 项目介绍、安装、示例、目标用户 |
| `CONTEST_DECLARATION.md` | 官方原文，未改动 |
| `MCP_INTEGRATION.md` | 实际使用的 Server、Tool、调用链、业务价值 |
| `mcp-config.example.json` | 仅环境变量占位 |
| `workbuddy.md` | WorkBuddy 开发上下文 |
| `SKILL.md` + `scripts/` + `references/` | 可运行主体 |

参赛声明见 [CONTEST_DECLARATION.md](CONTEST_DECLARATION.md)，活动规则以[官方仓库](https://github.com/M-China/mcd-developer-innovation-challenge)为准。
