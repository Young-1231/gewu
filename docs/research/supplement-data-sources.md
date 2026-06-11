# A股及美股免费金融数据源工程可行性对比（2025–2026 现状）

> 调研日期：2026-06-11，桌面调研（WebSearch/WebFetch），未做代码实测。各事实附来源 URL，时效以「截至」标注。所有免费源均为非官方逆向/爬取性质（SEC EDGAR、中证指数官网除外），上游随时可能变动。

## 1. akshare

- **维护活跃度：高**。截至 2026-05-27 最新版 1.18.64，GitHub 20.2k stars，MIT 协议，开放 issue 仅 21 个；发布频率接近每日 1–2 版，绝大多数是修复上游变动（[GitHub](https://github.com/akfamily/akshare)、[Changelog](https://akshare.akfamily.xyz/changelog.html)）。
- **接口数量**：官方文档未给确切总数，数据字典覆盖股票/指数/期货/期权/基金/宏观等，社区普遍称千级接口（[数据字典](https://akshare.akfamily.xyz/data/index.html)）。
- **频率限制/封禁风险：中等且不透明**。akshare 本身无限流，风险全在上游：用户报告频繁调用巨潮、新浪接口会被限制，加 4 秒 sleep 可恢复（[issue #6990](https://github.com/akfamily/akshare/issues/6990)）；2025 年东财 `push2.eastmoney.com` 曾对部分网络直接断连，官方将 39 个文件切换到 `push2delay` 域名修复（[issue #6091](https://github.com/akfamily/akshare/issues/6091)）；核心行情接口 `stock_zh_a_hist`、`stock_individual_info_em` 也有间歇性失效报告（[issue #6092](https://github.com/akfamily/akshare/issues/6092)、[#7051](https://github.com/akfamily/akshare/issues/7051)、[#6100](https://github.com/akfamily/akshare/issues/6100)）。
- **破坏性变更**：以重命名为主而非删除。2025-10 的 1.17.68 一次性重命名 8 个期权接口，2025-10/11 多个期货接口改名；历史上整体移除过英为财情、funddb、南华指数等上游失效的接口（[Changelog](https://akshare.akfamily.xyz/changelog.html)）。锁版本 + 关注 changelog 是必要工程实践。
- **上游依赖**：东财为主、新浪/腾讯/巨潮为辅。东财、新浪、同花顺均已部署行为识别+流量控制的多级反爬（[CSDN 问答](https://ask.csdn.net/questions/9145592)）。官方声明数据仅供学术研究、商用风险自负（[introduction](https://akshare.akfamily.xyz/introduction.html)）。

**结论**：免费源中维护最好、覆盖最广，但单接口可用性是「最终一致」而非 SLA，必须自带重试/降速/缓存层。

## 2. tushare

- **积分制（门槛制，不消耗）**：注册 100 分+完善资料 20 分=120 分基础档，可调大部分基础数据（非复权日线等），50 次/分钟、8000 次/天；2000 分解锁个股资金流、**指数成分权重 `index_weight`** 等特色接口；5000 分以上基本不限频（[积分频次表](https://tushare.pro/document/1?doc_id=290)、[CSDN 积分规则](https://blog.csdn.net/fulk6667g78o8/article/details/121187851)）。捐助 1:10（200 元≈2000 分，年度有效）；学生/教师有免费积分通道（[学生](https://tushare.pro/document/1?doc_id=360)、[教师](https://tushare.pro/document/1?doc_id=361)）。
- **独立付费权限（与积分无关）**：新闻资讯 1000 元/年、公告信息 1000 元/年、港股日线 1000 元/年、美股日线 2000 元/年、港美股财报各 500 元/年（[doc_id=290](https://tushare.pro/document/1?doc_id=290)）。即新闻和公告在 tushare 体系内**不免费**。
- **商用条款**：服务协议明确为「个人、不可转让、非商业用途」的可撤销授权，仅限个人查看；商用需单独授权（[数据服务协议](https://tushare.pro/document/1?doc_id=405)）。
- 已知问题：`index_weight` 部分指数权重更新不及时（[issue #1004](https://github.com/waditu/tushare/issues/1004)）。

**结论**：数据规整、SQL 化程度高，适合做「校验源/兜底源」；纯免费层（120 分）只够基础行情+财报，关键的成分权重要 2000 分（约 200 元/年捐助可达）。

## 3. 备选库（截至 2026-06）

| 库 | 定位 | 短板 |
|---|---|---|
| [baostock](https://baostock.com/) | 免费、免 token 的官方化 A 股日线/财务/**历史指数成分**服务 | 无分钟级实时、无新闻公告；功能更新缓慢，但服务持续可用（社区 2023–2024 大量使用案例）；复权价为非负规范值，与东财系有差异（[知乎对比](https://zhuanlan.zhihu.com/p/594951746)） |
| [efinance](https://github.com/Micro-sheep/efinance) | 东财单一上游的轻量封装，3.8k stars，v0.5.5（2025-03） | 接口少、文档薄；1 分钟线仅当日、5 分钟线仅近 2 月；声明仅供学习不得商用 |
| [qstock](https://github.com/tkfy920/qstock) | 数据+选股+回测一体的个人研究包（东财/同花顺/新浪聚合），1.8k stars | 提交历史极少，**维护基本停滞**，不宜作依赖 |
| [adata](https://github.com/1nchaos/adata) | 多数据源融合+动态代理保高可用，专注 A 股量化 | 社区较小，接口广度不及 akshare |
| [mootdx](https://github.com/mootdx/mootdx) | 通达信协议读取（pytdx 已停维护/归档，mootdx 是活跃封装，v0.11.7） | 依赖通达信行情服务器 IP 池（曾批量失效后修复自动选优）；无财务/公告/新闻文本 |

## 4. 财报与公告原文

- **巨潮资讯（cninfo）**：无官方免费批量 API；通行做法是 POST `hisAnnouncement/query` 取公告元数据 JSON 再下载 PDF，存在反爬（需 UA/Referer、随机延时、限速分段），社区有多个可用爬虫项目（[CNInfoHedgeCrawler](https://github.com/Interstellar1217/CNInfoHedgeCrawler)、[Annualreport_tools](https://github.com/legeling/Annualreport_tools)、[CSDN 实例](https://blog.csdn.net/2301_81084742/article/details/149022848)）。akshare 也封装了巨潮公告/财报披露接口（[股票数据文档](https://akshare.akfamily.xyz/data/stock/stock.html)）。合规上公告本身是法定公开信息披露，爬取风险主要在访问频率而非内容授权。
- **东方财富 F10**：经 akshare 封装（个股资料、财务摘要等），逆向接口，间歇失效见上文 issue；东财已有行为识别反爬，需控频。
- **问财（同花顺 iwencai）**：[pywencai](https://github.com/zsrl/pywencai) 通过执行 `hexin-v.bundle.js` 动态生成 token 模拟请求；2025 年起因接口策略调整**必须手动提供 cookie**，token 频繁失效需更新 JS 依赖（[CSDN 指南](https://blog.csdn.net/gitblog_00087/article/details/154485594)、[hexin-v 逆向](https://blog.csdn.net/weixin_47481982/article/details/127619823)）。同花顺反爬最激进，只宜作低频补充，不宜进关键路径。

## 5. 新闻舆情

- **东财全球财经快讯**：akshare `stock_info_global_em`（7×24 快讯），当前最稳的免费新闻流（[akshare 资讯数据](https://zhuanlan.zhihu.com/p/670059296)）。
- **新浪财经**：akshare `stock_info_global_sina`，可用但新浪侧限频较敏感（见 issue #6990 的 4 秒间隔经验）。
- **财联社电报**：akshare `stock_info_global_cls` 2025-02 已有不返回数据的报告（[issue #5732](https://github.com/akfamily/akshare/issues/5732)）；第三方工具包 a-stock-data 记录财联社旧 API 截至 2026-05 已全部 404，并以东财快讯替代（[a-stock-data](https://github.com/simonlin1212/a-stock-data)）。**财联社免费通道应视为已不可靠**。

## 6. 美股

- **yfinance**：非官方爬取。Yahoo 自 2024 起持续收紧，2025-04 起大量用户报 `YFRateLimitError: Too Many Requests`（[issue #2422](https://github.com/ranaroussi/yfinance/issues/2422)）；社区估计单 IP 每日几百请求即可能被限流，缓解手段为 sleep、批量化、本地缓存（[Medium 分析](https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01)）。可用于低频日线补数，不可作高频依赖。
- **SEC EDGAR 官方 API：免费层首选**。`data.sec.gov` 提供 submissions / companyfacts / companyconcept / frames（XBRL 财务）等结构化接口，完全免费；限速 10 请求/秒（2021-07-27 起执行），超限 403 封约 10 分钟，必须声明含联系方式的 User-Agent（[SEC 官方](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)、[限速公告](https://www.sec.gov/filergroup/announcements-old/new-rate-control-limits)）。
- **Finnhub**：免费层 60 次/分钟，美股实时报价可用，国际市场多数数据需付费（[对比](https://www.quadratichq.com/blog/alpha-vantage-vs-finnhub-api-workflow-vs-integrated)）。
- **Alpha Vantage**：免费层已降至 **25 次/天**（早年为 500/天），仅适合极低频用途（[2026 指南](https://alphalog.ai/blog/alphavantage-api-complete-guide)、[免费 API 对比](https://qveris.ai/guides/stock-api-free-comparison/)）。

## 7. 历史指数成分与退市股（评测模块关键依赖）

- **baostock 是免费历史成分的最优解**：`query_hs300_stocks(date)`、`query_zz500_stocks(date)`、`query_sz50_stocks(date)` 支持按任意历史日期取成分，可半年/月度采样重建全历史（[CSDN 示例](https://blog.csdn.net/li727507857/article/details/131780058)、[baostock](https://baostock.com/)）。
- **tushare `index_weight`**：月度成分+权重，回溯完整但需 2000 积分，且有权重更新滞后的报告（[文档](https://tushare.pro/document/2?doc_id=96)、[issue #1004](https://github.com/waditu/tushare/issues/1004)）。可作 baostock 的交叉校验源。
- **中证指数官网**：免费提供现行成份股列表下载与历次调样公告（PDF），是最权威的人工校验基准（[csindex.com.cn](https://www.csindex.com.cn/)）；东财数据中心亦有[沪深300](https://data.eastmoney.com/other/index/hs300.html)/[中证500](https://data.eastmoney.com/other/index/zz500.html)成分页。akshare `index_stock_cons_csindex` 仅取**当前**成分，不解决历史问题。
- **退市股**：akshare `stock_info_sh_delist` / `stock_info_sz_delist` 取沪深两所终止上市名单（[文档](https://akshare.akfamily.xyz/data/stock/stock.html)、[示例](https://zhuanlan.zhihu.com/p/142219022)）；tushare `stock_basic(list_status='D')` 120 积分即可取退市清单；baostock `query_stock_basic` 含上市/退市日期，且其日线库保留已退市股票历史行情，是免费源中做防幸存者偏差回测最可行的组合。

## 8. 推荐数据栈

**总原则**：主选 akshare（覆盖面）+ baostock（历史成分/退市股的稳定基座）+ SEC EDGAR（美股基本面），tushare 2000 分档作可选校验源；所有上游统一加缓存层与 2–4 秒限速，锁定 akshare 版本按月升级。

| 数据域 | 主选 | 备选/校验 |
|---|---|---|
| A股日线/分钟行情 | akshare `stock_zh_a_hist`（东财） | baostock `query_history_k_data_plus`；efinance；mootdx（通达信） |
| A股财务报表 | akshare 东财/巨潮财报接口 | baostock 季频财务；tushare（120 分） |
| 公告原文 | akshare 巨潮披露接口 + 自建 cninfo PDF 下载器（限速） | 东财 F10（akshare） |
| 新闻快讯 | akshare `stock_info_global_em`（东财 7×24） | `stock_info_global_sina`；财联社已不可靠不入栈 |
| 指数历史成分 | **baostock `query_hs300_stocks(date)` 等** | tushare `index_weight`（2000 分）；中证官网公告人工校验 |
| 退市股名单/行情 | baostock（含退市股历史 K 线） | akshare `stock_info_s[hz]_delist`；tushare `stock_basic` |
| 美股行情 | yfinance（低频+缓存+退避） | Finnhub 免费层（60/min） |
| 美股财报/公告 | **SEC EDGAR 官方 API**（10 req/s，声明 UA） | Alpha Vantage（25/天，仅应急） |

**风险提示**：akshare/efinance/tushare 免费层均限个人研究用途，商用需另行授权或切换商业数据商；东财是事实上的单点上游，建议评测模块的关键数据（成分、退市）落库快照，不依赖在线重取。
