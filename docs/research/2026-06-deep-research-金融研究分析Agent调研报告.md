# 金融研究分析 AI Agent 领域深度调研报告

> 调研日期：2026-06-11
> 方法：5 路并行检索 → 25 个来源抓取 → 提取 120 条可证伪论断 → 对 25 条关键论断做 3 票对抗式核验（23 条确认、2 条否决）→ 合并去重后形成 11 条高/中置信度发现。
> 目的：为自建「A股为主、兼容美股、OpenAI 兼容 API（默认 DeepSeek）」的金融研究分析 Agent 开源项目（本仓库 **格物 Gewu**）提供选型与差异化依据。

---

## 一、执行摘要

竞品格局已清晰：**TauricResearch/TradingAgents**（约 85k stars，LangGraph 多 agent）、其中文衍生 **TradingAgents-CN**（28.2k stars，A股生态最大竞品）、**virattt/ai-hedge-fund**（约 60k stars）、**FinRobot**（7.2k stars，AutoGen 四层架构）构成必须对标的头部开源项目。DeepSeek/Qwen 等国产模型接入已被普遍实现——**「OpenAI 兼容 API + 默认 DeepSeek」本身不构成差异化**。

经交叉验证，真正的空白点有三：

1. **A股本土数据源深度集成**——TradingAgents 仅靠 Yahoo 后缀 ticker 覆盖 A股、ai-hedge-fund 完全依赖美股商业 API、FinRobot 数据层全是美股生态，均无 akshare/tushare/巨潮/东财 F10 的可用代码路径；
2. **真正完整开源**——最大中文竞品 TradingAgents-CN 采用混合授权（app/ 与 frontend/ 专有、v2.0 因盗版暂不开源）；
3. **严谨评测**——KDD 2026 的 FINSABER 论文证明 FinMem/FinAgent/TradingAgents 等的短窗口回测因幸存者偏差与数据窥探偏差高估了有效性，且 LLM 策略存在「牛市过度保守、熊市过度激进」的系统性失败模式。**内置防泄漏 point-in-time 评测是全行业缺失的能力。**

**结论**：本项目以「LangGraph 分析师团队 + 多空辩论」架构对标 TradingAgents（社区已验证的范式），但以 **A股本土数据栈、中文研报生成、Apache-2.0 完全开源、内置防泄漏 PIT 评测** 为核心卖点。

---

## 二、已验证发现（按置信度排序）

### F1. TradingAgents 是 star 数最高的开源多 agent 金融框架 ⭐ 高置信（3-0 ×2）

2026-06-11 GitHub API 实测：**84,989 stars / 16,438 forks**，Apache-2.0，2024-12-28 创建，2026-06-01 仍有 push。同日横向比对：OpenBB 68,884、virattt/ai-hedge-fund 59,955、microsoft/qlib 44,256、FinGPT 20,458、RD-Agent 13,408、FinRobot 7,227。

- 来源：<https://github.com/tauricresearch/tradingagents>、<https://arxiv.org/abs/2412.20138>
- 证据：GitHub API 当日逐项核验 stars/forks/license/created_at/pushed_at；仓库含真实源码（tradingagents/ 包、cli/、tests/、Dockerfile）。

### F2. TradingAgents 架构 =「分析师团队 + 多空辩论 + 层级审批」，基于 LangGraph ⭐ 高置信（3-0 ×2）

五层管线：基本面/情绪/新闻/技术四类分析师 → Bull/Bear 研究员结构化辩论（Research Manager 主持）→ 交易员 → 风险管理团队 → 组合经理审批，模拟真实交易公司组织结构。是本项目架构的直接参照。

- 来源：同 F1
- 细微差别：代码中激进/保守/中性风险偏好在风控辩论内实现，而非多个平行交易员 agent。

### F3. 「兼容 DeepSeek + 覆盖 A股代码」已不构成差异化 ⭐ 高置信（3-0）

TradingAgents 已代码级原生支持 DeepSeek、Qwen（DashScope 双端点）、GLM、MiniMax、OpenRouter、Ollama，并通过 Yahoo 后缀支持 A股（600519.SS/.SZ）。**但其 A股支持仅限 Yahoo ticker 行情，全仓库 143 个文件无 akshare/tushare/巨潮/东财 F10 集成，情绪源为 StockTwits/Reddit（美股中心）**——A股本土数据源与中文研报深度才是真实空白。

- 来源：<https://github.com/tauricresearch/tradingagents>（README L202/226 provider 列表；`tradingagents/llm_clients/api_key_env.py`；README L176-182 茅台示例）

### F4. TradingAgents 论文评测窗口仅 3 个月 / 3 只美股，结论不可直接引用为「显著盈利」 ⭐ 高置信（3-0）

评测指标组合（累计收益 CR、夏普 SR、最大回撤 MDD vs Buy-and-Hold 与规则基线）是该领域典型套路（FinMem arXiv:2311.13743、FinAgent arXiv:2402.18485 同款），可借鉴；但其实验仅 2024 年 1-3 月、AAPL/GOOGL/AMZN 三只股票，论文自承规则基线 MDD 更优、SR>2 超出作者预期经验范围。

- 来源：<https://arxiv.org/abs/2412.20138>（Table 1、Sec 6.1.3、脚注）

### F5. ai-hedge-fund：DeepSeek 已是一等公民，但数据层完全锁死在美股商业 API ⭐ 高置信（3-0 ×2）

约 60k stars。`src/tools/api.py` 六个端点全部指向商业的 api.financialdatasets.ai（需 API key），示例 ticker 均为 AAPL/MSFT/NVDA，仓库内 akshare/tushare 零命中；DeepSeek 经 langchain ChatDeepSeek 接入（非默认，且 DeepSeek 下 JSON mode 被代码禁用）。社区 A股 fork 的存在印证了缺口。

- 来源：<https://github.com/virattt/ai-hedge-fund>
- 注：免费档覆盖 AAPL/GOOGL/MSFT/NVDA/TSLA 少数 ticker 可无 key。

### F6. TradingAgents-CN：A股最大竞品，但混合授权、并非完整开源 ⭐ 高置信（3-0 ×4）

2026-06-11 实测 **28,206 stars / 5,983 forks**，支持 A股（Tushare/AkShare/通达信）/港股/美股，LLM 层覆盖 DeepSeek、阿里百炼、OpenAI 等。**但根 LICENSE 为 Mixed License：app/（FastAPI 后端）与 frontend/（Vue 前端）为 Proprietary…All rights reserved，README 明言 v1.x 商用须授权、v2.0「因存在盗版问题，暂时不进行开源」**（GitHub license 字段 Other/NOASSERTION）。次大 A股 LLM-agent 仓库 KylinMountain/TradingAgents-AShare 仅 559 stars。

- 来源：<https://github.com/hsliuping/TradingAgents-CN>
- **「真正完整开源的 A股分析 Agent」是可占领的差异化空白。**

### F7. FinRobot：AutoGen 四层架构 + Equity Research 方向验证，但完全美股 ⭐ 高置信（3-0 ×4 + 2-1）

7,227 stars / Apache-2.0 / 活跃（2026-05-10 push）。四层架构：Financial AI Agents（Financial Chain-of-Thought 提示法）/ Financial LLMs / LLMOps & DataOps / 多源基础模型；agent 工作流为 Perception-Brain-Action。**其 v1.0.0（2026-03-20）主打 "FinRobot Equity Research" 报告生成——印证研报生成是该赛道功能高地**。数据层仅 Finnhub/FMP/SEC/yfinance/finnlp/reddit；requirements 里的 tushare 从未被 import，eastmoney 新闻函数整段被注释。

- 来源：<https://github.com/ai4finance-foundation/finrobot>、<https://arxiv.org/abs/2405.14767>

### F8. ⚠️ 学术引用警示：芝大「GPT-4 财务分析胜过人类分析师」论文已撤稿 ⭐ 高置信（3-0）

Kim/Muhn/Nikolaev《Financial Statement Analysis with Large Language Models》已于 **2025-02-20 在 arXiv 正式撤稿**（v3），原因是合著者复现时发现数据与分析不一致；截至 2026-06 无恢复版本。**本项目 README/文档论证 LLM 财务分析能力时必须避开此论文。**

- 来源：<https://arxiv.org/abs/2407.17866>（撤稿声明逐字核验；其结论性表述在本次核验中被 0-3 否决，与撤稿一致）

### F9. FinEval：可直接采用的中文金融评测基准（含 616 题 Financial Agent 子集） ⭐ 高置信（3-0 ×2）

上财 FinEval（NAACL 2025）论文版 8,351 题，分金融学术知识（4,661）/金融行业知识（1,434）/金融安全知识（1,640）/**金融 Agent（616）** 四类；Agent 子集评测工具调用、API 检索、多文档 QA、多轮对话、CoT、任务规划与 RAG。注意：官方仓库已扩展至 FinEval 6.0（26,000+ 题），引用需区分论文版与现行版。

- 来源：<https://arxiv.org/abs/2308.09975>、<https://github.com/SUFE-AIFLM-Lab/FinEval>

### F10. FINSABER（KDD 2026）：评测方法论的关键反面证据 ⭐ 高置信（3-0 ×3）

在 2000-2024 约 20 年、100+ 只股票（含退市股，用历史 S&P 500 成分表控制幸存者偏差）的系统回测下，**此前文献报告的 LLM 择时优势显著衰减**：论文点名 FinMem、FinAgent、FinRobot、FinCon、TradingAgents 等受窄时间窗、有限股票池、幸存者偏差与数据窥探偏差影响而高估有效性；实测 FinMem 仅在 TSLA 上稳定跑赢、两个被复测 agent 均无统计显著 alpha（所有 p>0.34）。**系统性失败模式：牛市过度保守跑输被动基准、熊市过度激进招致重大亏损。**

- 来源：<https://arxiv.org/abs/2505.07078>、<https://dl.acm.org/doi/10.1145/3770854.3785702>、<https://github.com/waylonli/FINSABER>（开源代码）
- 限定：基于美股 2000-2024 与所测 LLM 骨干；TradingAgents 被点名但未被实际复测；外推到 A股属未验证假设。

### F11. 差异化机会综合建议 ◆ 中置信（由多条 3-0 发现派生的分析性结论）

四个可占领空白：
(a) **A股本土数据栈**：akshare（免注册）为主、tushare 为备、巨潮/东财 F10 财报公告为研报数据底座；
(b) **完全开源**：全仓 Apache-2.0，与 TradingAgents-CN 混合授权形成直接对照；
(c) **中文研报生成**：FinRobot 验证了 equity research 是功能高地，但仅限美股英文；中文结构化研报 pipeline 尚无头部开源实现；
(d) **严谨评测**：内置 point-in-time 防泄漏回测（FINSABER 方法论：长周期、宽截面、含退市股、报告 CR/SR/MDD 并对比被动基线）+ FinEval Agent 子集打分，README 坦承牛熊 regime 局限——「自带反过拟合评测」正是全行业缺失的，也直击金融机构对风控与严谨性的核心要求。

架构推荐：对标 TradingAgents 的 LangGraph「分析师团队 + 多空辩论 + 风控审批」（85k stars 验证的社区范式）；LLM 层做通用 OpenAI 兼容 base-URL 设计（默认 DeepSeek）即可，**不必作为宣传点**。

---

## 三、被否决的论断（引用前必须重新核实）

| 论断 | 票数 | 说明 |
|---|---|---|
| ai-hedge-fund 共 19 个 agent（14 个投资人人格 + 估值/情绪/基本面/技术专家 + Risk/Portfolio Manager） | 0-3 ✗ | 具体构成与仓库现状不符，引用其 agent 数量前必须重新核实 |
| Kim/Muhn/Nikolaev：GPT-4 仅凭匿名化财报预测盈余方向胜过人类分析师 | 0-3 ✗ | 论文已撤稿（见 F8） |

## 四、覆盖缺口与诚实声明

1. **维度3（商业产品）与维度4（数据源对比）未产生通过三票验证的 claim**，本报告对这两维度实质缺失 → 已另行启动补充调研，见同目录 `supplement-commercial-products.md` 与 `supplement-data-sources.md`；数据源可行性另以本仓库代码实测为准。
2. FinGPT、OpenBB、Qlib、RD-Agent、FinMem、FinAgent、StockAgent、gpt-researcher、BloombergGPT、FinBen 仅出现在 star 数横向比对或 FINSABER 点名中，未形成独立验证发现。
3. 所有 star/fork 数为 2026-06-11 GitHub API 快照；TradingAgents-CN 最近 push 为 2026-04-20，「活跃」表述偏宽松。
4. FinRobot「数据源完全面向美股」子项以 2-1 通过，但多数派有浅克隆代码级 grep 证据，整体可信。
5. FINSABER 结论外推到 A股属未验证假设；A股历史成分股与退市股数据可得性是评测模块的关键未知数（补充调研覆盖）。

## 五、对本项目（格物 Gewu）的直接落地决策

| 决策点 | 选择 | 依据 |
|---|---|---|
| 编排框架 | LangGraph StateGraph | F2：85k stars 社区验证范式；银行 JD 高频技能 |
| 架构 | 四分析师 → 多空辩论 → 研究主管 → 数字事实核查 | F2 + F11(c)：研报场景将"交易员/组合经理"替换为"研究主管+核查"更贴投研 |
| 数据层 | akshare 主、tushare 备、yfinance 美股；统一 as_of PIT 接口 | F3/F5/F7：头部项目集体空白 |
| LLM 层 | OpenAI 兼容 base-URL，默认 DeepSeek，不作为卖点 | F3/F5：已商品化 |
| 许可证 | Apache-2.0 全仓 | F6：对照 TradingAgents-CN 混合授权 |
| 评测 | PIT 防泄漏回测 + 方向命中率 vs 动量/持有基线 + 数字 grounding 审计 | F4/F10：全行业短板 |
| 文档姿态 | 坦承局限（regime 失败模式、回测≠实盘） | F8/F10：严谨性本身是核心价值主张 |

## 附：核验统计与全部来源

- 5 个搜索角度 / 25 个来源 / 120 条论断提取 / 25 条核验 / 23 确认 2 否决 / 合并后 11 条发现 / 107 个子 agent。

主要来源（primary）：
- <https://github.com/tauricresearch/tradingagents>
- <https://github.com/virattt/ai-hedge-fund>
- <https://github.com/hsliuping/TradingAgents-CN>
- <https://github.com/ai4finance-foundation/finrobot>
- <https://arxiv.org/abs/2412.20138>（TradingAgents）
- <https://arxiv.org/abs/2405.14767>（FinRobot）
- <https://arxiv.org/abs/2407.17866>（已撤稿，警示用）
- <https://arxiv.org/abs/2308.09975>（FinEval）
- <https://arxiv.org/abs/2505.07078>（FINSABER）
- <https://github.com/waylonli/FINSABER>
- <https://github.com/SUFE-AIFLM-Lab/FinEval>

次要/博客来源（佐证用）：21经济网、证券时报、财联社、腾讯新闻、新浪财经、人人都是产品经理、zeeklog 数据源评测、HKUDS/AI-Trader issue #76 等（详见核验日志）。
