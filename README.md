# 麦麦三问局

**最多三问，选定一餐；价格、热量、用料等级一起看。**

想吃麦当劳又懒得翻菜单时用的一句话 Skill。接入麦当劳中国官方 MCP，先确认门店，再用最多三个问题收齐预算、用餐类型和候选偏好，给出**一份主推 + 一份备选**：真实核价、单项与整餐热量，以及附官方来源的汉堡用料等级。只选餐报价，默认到店自取，不下单不支付。

> 麦当劳程序员创意开发大赛参赛作品，使用 WorkBuddy 开发，非麦当劳官方产品。

## 目标用户

- 站在柜台前或打开外卖，不想翻完整菜单的人
- 有预算和忌口（不要辣、只想吃鸡肉）却拿不定主意的人
- 想同时比较花多少钱、吃进多少 kcal 的人

## 核心能力

| 能力 | 说明 |
|---|---|
| 真实核价 | `calculate-price` 得出应付总价，菜单标价不作最终报价 |
| 热量核算 | 官方 `energyKcal` 优先，按规格与数量汇总整餐 |
| 用料等级 | 每个汉堡给出档次、理由和官方资料链接，未收录显示「待评」 |
| 主推 + 备选 | 两份不同方案，各配一句对应用户回答的理由 |
| 随时改单 | 换餐、换饮品、改数量后重新核价与汇总，不重开三问 |

## 快速开始

1. **申请 Token**：在[麦当劳 MCP 平台](https://open.mcd.cn/mcp)注册并激活 MCP Token。
2. **连接 MCP**：添加自定义连接器，地址 `https://mcp.mcd.cn`，传输 `streamablehttp`，请求头 `Authorization: Bearer ${MCD_MCP_TOKEN}`，参考 [mcp-config.example.json](mcp-config.example.json)。Token 只填在本机连接器设置，不进仓库、不进对话。
3. **加载 Skill**：导入 [SKILL.md](SKILL.md) 所在目录，保留 `scripts/` 与 `references/`。WorkBuddy 中在「技能 → 添加技能 → 上传技能」导入 `mcd-three-questions.zip`，详见[官方文档](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。

宿主需支持对话 Skill 与远程 MCP；汇总脚本仅依赖 Python 3.9+ 标准库。

## 使用示例

```text
开一局麦麦三问，帮我选一顿。
我在人民广场附近，自取，25 元以内，鸡肉正餐，不要辣。
```

```text
第1问 这顿最多花多少？        → 25 元
第2问 正餐 / 解馋小食 / 喝点东西？ → 正餐
第3问 候选里更想要牛肉还是鸡肉？   → 鸡肉
→ 输出主推与备选：餐品明细、核价、热量、用料等级
后续「饮料换掉、汉堡改两个」→ 重新核价，不重开三问
```

已给过的条件不再追问；门店未确认时先定位门店（不计入三问）；回答「随便」直接按偏好与价格收局。

## 数据口径

- **价格**：取 `calculate-price` 的 `data.price`（单位为分，÷100 得元）；未核价标「待核价」，不填估价。
- **热量**：优先官方 `energyKcal`（含 0），仅缺失时用 `energyKj ÷ 4.184`；单份 × 数量后汇总取整，套餐只展开子项，不重复计父项。
- **缺失**：不计为零，显示已知合计与未计入项。
- **等级**：项目自定义分类（Lv.3 臻选 / Lv.2 升级 / Lv.1 经典），不是官方品质分，不覆盖用户偏好；映射与来源见 [burger-grades.json](references/burger-grades.json)。
- **只读**：不调用领券、支付、下单、取消等写操作。

## 目录结构

```text
SKILL.md                  对话流程与规则（宿主入口）
scripts/meal_summary.py   热量换算、等级匹配、Markdown 汇总
references/               等级资料表与输入数据契约
examples/                 演示输入输出、真实调用快照
tests/                    16 项单元测试
MCP_INTEGRATION.md        MCP 工具、调用链、联调记录
workbuddy.md              WorkBuddy 开发上下文
```

## 本地验证

没有 Token 也能跑通计算与展示（演示数值为虚构输入）：

```bash
python scripts/meal_summary.py examples/demo.json
python -m unittest discover -s tests -v
```

2026-10-24 已完成官方 MCP 真实只读联调：门店、菜单、营养、详情、计价共 12 次调用成功，覆盖三档等级与超预算分支，结果见 [live-output.md](examples/live-output.md)。

## 参赛材料

`README.md` · `CONTEST_DECLARATION.md`（官方原文，未改动）· `MCP_INTEGRATION.md` · `mcp-config.example.json`（仅环境变量占位）· `workbuddy.md` · `SKILL.md` 与脚本。活动规则以[官方仓库](https://github.com/M-China/mcd-developer-innovation-challenge)为准。
