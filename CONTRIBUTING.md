# 贡献指南

感谢关注格物 Gewu。

## 开发环境

```bash
uv sync                       # Python 3.12+，依赖与虚拟环境
uv run pytest                 # 测试必须全离线通过（夹具在 tests/fixtures/）
uv run ruff check src tests   # lint
```

## 约定

- **测试离线**：单元测试不得发起网络请求。涉及上游接口的改动，用录制的数据快照
  更新 `tests/fixtures/cache/`，或构造合成数据。
- **PIT 纪律**：任何让 agent 在 `as_of` 时点看到此后数据的改动都是 bug，
  必须有对应的回归测试（参见 `tests/test_pit.py`）。
- **数字纪律**：注入 LLM 上下文的数字一律由代码预计算；新增上下文渲染时
  确认其数字会进入溯源审计语料（`tests/test_fact_check.py`）。
- **数据源新增**：进 `_try_sources` 降级链，标注实测可用性，失败必须可降级。
- **提交信息**：一句话说清动机与影响面，中文或英文均可。

## 提交流程

1. Fork 并从 `main` 拉分支；
2. 改动 + 测试 + `ruff check` 全绿；
3. 提 PR，描述动机、方案与验证方式。

## 报告问题

Issue 请附：复现命令、完整报错、`gewu version` 输出、网络环境（部分数据源有地区差异）。
