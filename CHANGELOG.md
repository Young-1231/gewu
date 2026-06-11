# Changelog

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.2.0] - 2026-06-11

### 新增
- **公告 RAG 问答**（`gewu ask`）：巨潮定期报告全文 + BM25 检索 + 页码级引用，答案复用数字溯源审计
- **真实公告日 PIT**：A股财报可见性按巨潮真实公告时间判定（法定披露截止日兜底）；修复公告时间戳 UTC→北京时间转换（消除 8 小时前视窗口）
- **行业对比分析师**（`gewu analyze --peers`）：同 PIT 口径的同行估值/成长对比表，第五分析师接入 LangGraph
- **SEC EDGAR 集成**：美股财务采用真实 `filed` 申报日 PIT；年度 EPS 按申报日阶梯化构建 PE(静态) 历史序列与五年分位；EDGAR 不可用（部分地区 403）时自动降级 yfinance
- **金融基准跑分**（`gewu benchmark`）：FinEval 兼容格式的多选题 harness，附自写格式样例（不分发基准数据）
- Dockerfile、CONTRIBUTING、py.typed

### 变更
- README 产品化重写；调研文档移除个人化表述
- 缓存支持 schema 校验（`required_columns`），格式漂移/外部篡改自动清除重抓

## [0.1.0] - 2026-06-11

### 新增
- LangGraph 多智能体管线：四分析师并行 → 多空辩论（轮数可配）→ 研究主管评级
- A股多源降级数据层（东财→新浪→腾讯）+ parquet 原子缓存（损坏自愈）+ 全局限速
- Point-in-Time 数据视图：法定披露截止日规则，历史模式公司概况最小化（防 *ST 等前视泄漏）
- 数字溯源审计：研报实质性数字逐一回溯 agent 输入语料，审计附录随报告输出
- 中文研报生成（评级/投资要点/分析师观点/辩论纪要/风险提示）+ 价格与估值图表
- PIT 走查回测：动量/买入持有基线对照、历史沪深300成分股票池（baostock）、强制局限性声明
- OpenAI 兼容 LLM 层（默认 DeepSeek）+ 离线 Mock；typer CLI；60 项离线确定性测试
