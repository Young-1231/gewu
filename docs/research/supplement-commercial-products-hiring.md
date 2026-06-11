# 补充调研：金融研究 AI 商业产品现状 与 国内金融机构 AI 岗位招聘趋势（2025–2026）

> 调研日期：2026-06-11。方法：一轮聚焦 Web 检索 + 关键页面核读。
> 标注约定：**[已核实]** = 两个及以上独立来源或官方一手来源；**[单一来源待证]** = 仅一处来源，引用时需谨慎。

---

## 主题 A：金融研究分析 AI 商业产品现状

### A1. 海外产品

#### AlphaSense **[已核实]**
- **核心功能**：市场情报检索平台。2025 年 1 月把 Generative Search 升级为端到端"研究智能体"（多 Agent 架构），可找文档、答复杂问题、自动化工作流、产出交付物；2025 年又推出 Financial Data，把结构化财务数据（财报、KPI、交易数据）与专家访谈纪要、券商研报、公告等定性内容融合检索，强调句级引用、防幻觉。([官方 2025 产品回顾](https://www.alpha-sense.com/resources/product-articles/product-releases-2025/)、[Financial Data 发布稿](https://www.prnewswire.com/news-releases/alphasense-launches-financial-data-to-offer-powerful-integrated-view-of-quantitative-and-qualitative-market-intelligence-302577534.html))
- **目标用户**：买方/卖方机构、企业战略与咨询。2025 年入选 CNBC Disruptor 50（[CNBC](https://www.cnbc.com/2025/06/10/alphasense-cnbc-disruptor-50.html)）。
- **定价**：年订阅制，从约 $10,000+/年 起，企业级可达百万美元（[第三方评测](https://intuitionlabs.ai/articles/alphasense-platform-review)，区间为已核实，精确价单一来源待证）。
- **与开源差距**：核心壁垒是"围墙花园"内容（券商研报、专家访谈库）+ 句级引用工程，开源项目难以复制数据资产，但 Agent 编排与引用链路可复现。

#### Rogo **[已核实]**
- **核心功能**：面向投行/私募的 Agent 平台：接入交易数据、市场数据库、监管文件、CRM，自动化分析师级工作流；新产品 Felix 可自动生成 PPT/模型/文档，做交易筛选、CIM 撰写、买家触达、数据室尽调。自训金融推理模型 + 权限/审计/合规治理。([产品页](https://rogo.ai/product)、[PR Newswire](https://www.prnewswire.com/news-releases/rogo-raises-160m-series-d-to-scale-the-agentic-platform-for-finance-302756546.html))
- **融资**：2025-04 Series B $50M（Thrive 领投，$350M 估值）；2026-04 Series D $160M（Kleiner Perkins 领投，估值 $2B，总融资 $300M+）。客户 250+ 机构、35,000+ 专业用户（Rothschild、Jefferies、Lazard、Moelis、野村）。([SiliconANGLE](https://siliconangle.com/2026/04/29/rogo-raises-160m-speed-financial-analysis-ai-agents/)、[TFN](https://techfundingnews.com/rogo-160m-series-d-kleiner-perkins-investment-banking-ai/))
- **与开源差距**：差距主要在私有部署合规体系、专业标注数据训练的金融推理模型、与机构内部系统（CRM/数据室）的深度集成。

#### Fiscal.ai（原 FinChat）**[已核实]**
- **核心功能**：散户/半专业投资者的"AI 副驾"研究平台：标准化财务数据 + 公司 KPI 历史 + 对话式 Copilot + 看板。2025 年中从 FinChat 更名并完成 $10M Series A（[TinySeed](https://tinyseed.com/latest/fiscal-ai-10m-future-ai-finance)）。
- **定价**：Free / Pro（年付 $39/月，月付 $49）/ Max / API & MCP 四档（[官方定价页](https://fiscal.ai/pricing/)、[第三方评测](https://www.matchmybroker.com/tools/fiscal-ai-review)）。
- **与开源差距**：主要壁垒是 10–15 年人工清洗的 KPI/分部数据，不在模型能力。值得注意它已把 **API+MCP** 作为单独产品线卖给开发者。

#### Perplexity Finance **[已核实，细节多为评测来源]**
- **核心功能**：2025 年中上线的金融垂类：实时行情、Earnings Hub（财报电话会实时转写+AI 摘要+关键指标抽取）、SEC 文件问答、筛选器、热力图、组合跟踪、自动化研究任务。免费为主，定位"轻量 Bloomberg 替代"。([官方筛选器页](https://www.perplexity.ai/finance/screener)、[评测](https://techpoint.africa/guide/perplexity-finance-review/))
- **与开源差距**：免费 + 通用搜索入口带来的流量是其优势；数据深度（机构级历史数据、研报）弱于 AlphaSense/Bloomberg，开源项目反而可在垂直深度上差异化。

#### Morgan Stanley AskResearchGPT **[已核实]**
- **核心功能**：内部工具（非对外产品）。基于 GPT-4 检索综合大摩研究库（年产 7 万+ 份研报），机构证券部门销售/交易员使用；专利工作流支持一键把答案转成客户邮件草稿。销售响应客户询问耗时降至原来的约 1/10。([官方新闻稿](https://www.morganstanley.com/press-releases/morgan-stanley-research-announces-askresearchgpt)、[CNBC](https://www.cnbc.com/2024/10/23/morgan-stanley-rolls-out-openai-powered-chatbot-for-wall-street-division.html))
- **启示**：大行路线是"自有研报库 RAG + 工作流嵌入"，而非通用问答。

#### Kensho（S&P Global）**[已核实]**
- **核心功能**：从直接做应用转向做 **AI 基础设施**：LLM-ready API / MCP Server，让 Claude、ChatGPT 等以自然语言/函数调用方式查询 Capital IQ 财务、交易、电话会纪要等数据集；2025–2026 年随 Claude 插件生态推出 S&P Global Plugin，提供公司 tearsheet、行业交易流摘要等"金融技能"。([官方文档](https://docs.kensho.com/llmreadyapi/overview)、[发布稿](https://press.spglobal.com/2024-11-13-S-P-Global-Launches-Kensho-LLM-ready-API-beta-,-Making-its-Structured-Data-Accessible-for-Generative-AI))
- **启示**：数据商正在主动"MCP 化"，开源 Agent 接入官方数据源的门槛在下降。

#### BloombergGPT 产品化 **[已核实]**
- 50B 参数金融 LLM（2023 论文）本身未单独售卖，而是化整为零进入 Terminal：AI 新闻摘要、公司新闻 AI 总结、Document Insights（2025 年底推出的跨文档问答/对照分析，可对多份电话会纪要、研报提问并以表格交叉核对）。([Bloomberg 官方](https://www.bloomberg.com/company/press/investors-harness-bloombergs-expanded-ai-tools-to-discover-and-summarize-news/)、[IT Brew 2025-11](https://www.itbrew.com/stories/2025/11/19/bloomberg-new-ai-tool-for-terminal))
- **启示**：自研大模型路线已让位于"任务级 AI 功能 + 终端分发"。

### A2. 中文生态

#### 同花顺 问财 / HithinkGPT
- **核心功能**：C 端"金融查询+投资咨询+内容生成"全链路：覆盖 A 股/基金/ETF/港美股/债券/宏观等 15 个业务矩阵、50 余类技能（查询、对比、解读、归因、预测、回测等）。**[已核实]**（[每经/申万宏源研报](https://www.nbd.com.cn/articles/2024-01-15/3208051.html)、[杭州日报](https://hznews.hangzhou.com.cn/jingji/content/2025-02/26/content_8868308.htm)）
- **定价**：问财进阶版 40 元/月、388 元/年；专业版 108 元/月、998 元/年。**[单一来源待证]**（出自券商研报转述）
- **与开源差距**：实时行情+用户规模是壁垒；但 2025 年知乎等渠道有用户对其回答质量的负面反馈（[知乎](https://zhuanlan.zhihu.com/p/1913175853837313421)，单一来源），说明体验上限不高，开源项目在"深度研究"维度有空间。

#### 东方财富 妙想大模型 **[已核实]**
- 国内首批通过网信办备案的金融大模型之一；2025-03-21 正式向所有用户开放并登陆东方财富 App。聚合全球行情、宏观、财报公告、产业链数据，覆盖热点追踪→选股择时→标的诊断→交易全流程；依托自建"金融超脑数据库"，信源分级、回答可溯源。C 端目前免费内嵌于 App。([证券时报](https://www.stcn.com/article/detail/1603690.html)、[经济参考网](http://www.jjckb.cn/20250325/c7357013f0c944c0a6aa21b041f20c7e/c.html))

#### 通联数据 萝卜投研 **[已核实（官方信息为主）]**
- 面向机构与个人的智能投研平台：金融搜索引擎、研报/公告信息抽取聚合、知识图谱（股权穿透、关联交易挖掘）、财务预测建模工具；称服务 2000+ 金融机构。([官方](https://robo.datayes.com/uqer/data/browse)、[未央网](https://www.weiyangx.com/362573.html))。机构版定价不公开、需商务洽谈（[知乎讨论](https://www.zhihu.com/question/56182286)，待证）。

#### 恒生电子 WarrenQ / LightGPT **[已核实]**
- LightGPT：金融行业大模型（4000 亿+ tokens 金融语料、80+ 金融任务指令微调），为投顾、客服、投研、风控、合规等场景供底层能力；WarrenQ 智能投研平台推出 WarrenQ-Chat 与 ChatMiner，把"搜读算写"升级为"Chat 读算写"；另有金融智能助手"光子"。主要以 B 端解决方案卖给金融机构。([钛媒体](https://www.tmtpost.com/nictation/6592526.html?rss=souhu)、[中国基金报](https://www.chnfund.com/article/AR2023102117240059835397))
- 注：公开信息密集在 2023–2024，2025 年后以行业标准编制、机构落地为主（[中国日报](https://tech.chinadaily.com.cn/a/202309/22/WS650d3ddea310936092f23212.html)）。

#### 蚂蚁财富 支小宝 / 蚂小财 **[已核实]**
- 国内首个基于大模型的智能理财助理（支小宝 2.0，2023 备案后上线），后演进为"蚂小财"；2025-06-23 接入推理大模型并做金融增强，新增盯盘、诊基等功能；已服务超 4300 万个人投资者；Pro 版同步用于机构投研。免费，嵌在支付宝/蚂蚁财富生态内。([证券时报](https://www.stcn.com/article/detail/2187524.html)、[财联社](https://www.cls.cn/detail/2064499)、[21 经济网](https://www.21jingji.com/article/20250915/herald/1eaaf8f4dc041931fe63a61dd1ca8696.png))

#### 2025–2026 券商新品与行业面
- 2025 年 DeepSeek 引爆券商"大模型军备竞赛"：截至 2025-02 已有约 25 家券商本地化部署 DeepSeek-R1/V3。**[已核实]**（[财联社](https://www.cls.cn/detail/1730733)、[东吴证券研报](https://pdf.dfcfw.com/pdf/H3_AP202502251643491486_1.pdf)）
- 华泰证券"AI 涨乐"：称行业首款 AI 原生 App，"主 Agent + 多专家 Agent"架构，2026-01 发 1.0 版，发布当日用户数破 240 万。**[单一来源待证]**（[东方财富财富号测评](https://caifuhao.eastmoney.com/news/20260209090704341326810)）
- 国泰君安："1+N"行业大模型方案，落地投行智能问答、灵犀智能投顾、千机 Chat。**[单一来源待证]**（同上）
- 2026 年报道称 28 家券商累计投入约 250 亿元押注 AI。**[单一来源待证]**（[新浪财经](https://finance.sina.com.cn/wm/2026-04-24/doc-inhvqfhe4518665.shtml)）

### A3. 商业产品 vs 开源项目的总体能力差距
1. **数据资产**（研报库、专家访谈、清洗后的 KPI 历史、实时行情牌照）是最硬的壁垒，开源无法复制。
2. **引用与合规工程**（句级引用、信源分级、审计日志、备案）是机构买单的关键，开源项目常缺。
3. **Agent 编排、RAG、报告生成**等"能力层"差距最小——这恰是开源项目可对标展示的部分。
4. 趋势：数据商 MCP 化（Kensho、Fiscal.ai API+MCP），意味着开源 Agent + 官方 MCP 数据源的组合正变得可行。

---

## 主题 B：2025–2026 国内银行/券商/基金 AI Agent / 大模型岗位招聘趋势

### B1. 典型 JD 证据
- **浦发银行（浦银金科，2025-09 社招）**：明确要求 AI Agent 建设经验——Python、**LangChain、LangGraph、LlamaIndex** 技术栈，以及 **Dify、n8n、Coze** 等 Agent 平台的架构与定制化实施能力。**[单一来源待证]**（[银行招聘网](http://m.yinhangzhaopin.com/m/202813.htm)）
- **中国银行（2025-07 社招，官方 PDF）**：大模型 Prompt 模板开发调优、**RAG 应用开发、向量数据库**使用；有银行业大模型项目实施经验者优先。**[已核实（官方一手）]**（[中行招聘 PDF](https://pic.bankofchina.com/bocappd/appform/202507/P020250702344144547288.pdf)）
- **招商银行（2025 总行社招+校招）**：社招大模型岗要求 NLP/深度学习功底、大模型预训练与训练数据构造经验、**LoRA/QLoRA 微调、Prompt 工程**，发表 AI 顶会/顶刊论文优先；校招设 10 名"数字金融生（AI 方向）"定向培养。**[已核实]**（[中国电子银行网](https://www.cebnet.com.cn/20250226/102982489.html)、[证券时报](https://www.stcn.com/article/detail/1609801.html)）
- **工商银行（软开中心社招/校招）**：上海/杭州研发部设大模型数据工程专家、大模型算法岗、前沿 LLM 算法岗；2026 校招设总行"人工智能+"专项。**[已核实]**（[ICBC 岗位表](https://job.icbc.com.cn/api/v1/chunkserver/TRM-default/_/MAtt1742463041430eff57ff93fee4b6191577015d9e7158b.xls)、[21 经济网](https://www.21jingji.com/article/20241015/herald/3fdbbee0c24dd3ae7bd99f2e45c2496e.html)）
- **平安银行**：金融科技部算法岗含"NLP、大模型、知识图谱探索及银行场景落地"；校招设科技专场。**[单一来源待证]**（[财经客户端](https://news.caijingmobile.com/article/detail/556325?source_id=40)）
- **券商**：DeepSeek 热潮后算法工程师供不应求，浙商证券招"大模型应用开发工程师""大模型算法与应用研究员"，方向集中在智能投顾/投研、风控、客户行为 NLP。**[已核实]**（[证券时报①](https://www.stcn.com/article/detail/1543573.html)、[②](https://www.stcn.com/article/detail/1546893.html)）
- **基金**：华夏基金"大模型应用工程师"最高 80 万年薪，要求 3 年+ ML/NLP/大模型经验、有调优与应用开发经验者优先；易方达 2025 校招设 AI 人才专场（深度学习研究员、AI 应用工程师等）。**[已核实]**（[中国基金报](https://www.chnfund.com/article/AR20109c53-03fa-fef9-5ec7-3a1854c355ad)、[财联社](https://www.cls.cn/detail/2245221)、[易方达校招页](https://tc.seu.edu.cn/2025/0606/c25660a530859/page.htm)）

### B2. 高频技能关键词（按出现频率/强度排序）
据一份 2025 年 101 个 AI Agent 岗位的抽样调研（**[单一来源待证]**，[panzhixiang.cn](https://panzhixiang.cn/2025/ai-agent/)）并与上述银行/券商 JD 交叉印证：
1. **Python**（断层第一，125 次提及）
2. **RAG + 向量数据库**（123 次，事实上的标配；与中行、招行 JD 一致）
3. **LangChain / LangGraph**（最高频框架，要求"熟练/精通"）
4. **微调（LoRA/QLoRA/SFT）**（42 次；高薪岗位几乎必备，招行 JD 印证）
5. **Prompt 工程**、**Agent/智能体编排**、**MCP**（2025 下半年起在 JD 中快速出现）
6. 低代码 Agent 平台：**Dify / Coze / n8n**（银行系偏好，便于业务部门交付）
7. 工程化：容器化（55 次）、微服务（42 次）、云平台
8. **金融业务知识**：几乎所有金融机构 JD 都写"有金融行业大模型落地经验者优先"

### B3. 加分项与项目作品偏好
- **加分项**：多 Agent 系统经验、多模态 RAG、垂直行业（金融/医疗）落地案例、顶会论文（招行明示）、银行业项目实施经验（中行明示）、国产化/本地化部署经验（DeepSeek 本地部署潮的直接后果）。
- **作品偏好**：相比刷榜，更看重**端到端可演示的落地项目**——能讲清数据链路、检索质量评估、幻觉控制、引用溯源与成本控制的真实系统。薪资面：抽样中 59.6% 岗位月薪 >25K，北京均值 >40K；银行 AI 岗校招最高开到 80 万年薪级别（华夏基金为基金口径）。**[部分单一来源待证]**

---

## 对求职项目的启示

1. **技术栈对表 JD**：项目应显式使用并在 README 中点名 **LangGraph（或等价自研编排）+ RAG + 向量库 + 微调（LoRA）** 中至少三项，这是银行/券商 JD 的最大公约数；额外接一个 **MCP 数据源**（如公开财务数据 MCP）正踩在 2026 年趋势上。
2. **对标商业产品讲故事**：面试叙事可定位为"开源版 AlphaSense Generative Search / 妙想"——商业产品的壁垒在数据而非能力层，演示中突出**句级引用、信源分级、可溯源回答**这三个商业产品的卖点，最能体现专业度。
3. **金融正确性 > 功能数量**：金融机构最在意幻觉与合规。项目里加一套**检索/回答质量评估**（如带标注的金融问答评测集、引用命中率指标），比多做两个功能更打动招聘方。
4. **覆盖一个"全流程"场景**：参照华泰"主 Agent + 专家 Agent"与问财"查询→解读→归因→回测"的链路，做一条窄而深的端到端流水线（如"财报发布 → 自动摘要 → 同业对比 → 生成带引用的研究简报"），对应 JD 里"业务场景落地"的要求。
5. **准备本地化部署叙事**：券商 25 家部署 DeepSeek 的背景下，项目支持**国产/开源模型可替换**（DeepSeek/Qwen 一键切换）是面向银行券商的直接加分项。
6. **待证信息使用提醒**：问财定价、华泰 AI 涨乐用户数、250 亿投入等数字引用前应再核实原始来源。
