# Concept 索引 — 术语都是标签，问题才是入口

规则：这里**只收录真实研究过程中被反复使用的术语**。每个术语必须回答
「我到底观察到了什么」而不是「这个词什么意思」。不制造字典。

## 概念总表

| 概念 | 我的观察（大白话） | 首次出现 | 关键节点 |
| --- | --- | --- | --- |
| harness | 一层包在 agent 外面的代码，决定它能用什么、看到什么提示 | E04 | N04, N10 |
| verifier | 判断「这个修复对不对」的程序；「测试绿了」不等于它 | E02 | N02 |
| action affordance | 环境允许 agent 执行的动作集合（能不能用 edit） | E04 | N04, N10 |
| interaction budget | 允许的交互回合数（max_turns） | E03 | N03, N08 |
| staged runtime | 把交互拆成有顺序的阶段（recon→execute→feedback） | E05 | N05 |
| gating | 按阶段隐藏工具（侦察阶段不给 edit） | E06 | N10 |
| banner | 每回合注入的阶段上下文提示 | E06 | N10, N11 |
| runtime intervention | 运行中、以 user 回合形式注入的上下文 | E07 | N12 |
| action allocation | 同样数量的动作，换了一种分配方式 | E08 | N14 |
| distilled trajectory | 用大模型轨迹训练小模型（这条路线被拒） | E05 | N09 |
| paired McNemar | 同一批实例上的配对比较（唯一活过复制的统计） | E08 | N13 |
| single-seed artifact | 只在一个随机种子上成立的数字 | E08 | N13 |

## 每个概念从「观察」讲起

### harness
观察：同一个模型，包它的代码不同，成功率就不同。
本项目：`tools/swe_lab_env/swe_lab_*.py` 是 harness 的实现。
不要误用：harness 不是「agent 本身」，是 agent 外层的运行环境。

### verifier
观察：怎么知道 agent 的修改是对的？只看测试绿不绿会被作弊骗过
（篡改测试得 1.000，真实部分修复 0.571）。
本项目：结构化 verdict（per_test/fixed_targets/regressions/tampered）。
不要误用：测试通过 ≠ 修复有效。

### action affordance
观察：给不给你 edit 工具，结果差 44 分（H_B vs H_A）。
本项目：gate 机制后来被否——**工具在不在 ≠ 效果来源**。
不要误用：affordance 的变化可以影响结果，但不一定是某个效果的机制。

### interaction budget
观察：回合数给少时，分阶段引导很值钱；给多时自己就会了。
本项目：T ∈ {2,4,6,8}；T=4 峰、T=8 反超。
不要误用：预算不是噪音，是实验的操作点（operating point）。

### staged runtime
观察：把「先看、再改、再查」拆成三段，每段有自己的提示。
本项目：recon→execute→feedback；曾误叫 planner（0/120 写计划）。
不要误用：模型并没有「规划」，它只是被结构化分配了动作。

### gating
观察：侦察阶段藏起 edit 工具，agent 就不得不先看。
本项目：H_G 1/20（地板）——**藏工具本身没有用**。
不要误用：gating 是 H_D 的一个成分，但不是机制。

### banner
观察：每回合提醒「现在是阶段 X」，效果和完整 H_D 一样。
本项目：H_P = H_D（pilot 精确复现 7/16）；banner 即机制。
不要误用：banner 不是「提示词写得好」，是「重复 + 时机 + 角色」的组合。

### runtime intervention
观察：同一个消息，user 角色发和 system 角色发效果不同。
本项目：H_SYS 15% vs H_P 25%；术语定为 user-turn runtime intervention。
不要误用：「中断是因果」这个更强的主张没有证据（必须 not claim）。

### action allocation
观察：干预后总调用数没变、第一次 edit 没提前，但「改状态」的比例涨了。
本项目：state_chg 0.04→0.07（solved-only 0.17→0.30），n_calls 平。
不要误用：不等于「更努力」「更早」「更聪明」——只是分配变了。

### distilled trajectory
观察：把 H_D 轨迹喂给 0.6B 学生，学生连工具都不会调（0/10）。
本项目：dots3→Qwen3-0.6B，20 步 LoRA，H_A eval：0/10 resolve。
不要误用：这是**一条路线被拒**，不是「蒸馏不可能」（C10）。

### paired McNemar
观察：同 20 实例上配对比较，banner vs none p=0.031 → 活过复制。
本项目：聚合率比较全死了，配对比较全活了（F11）。
不要误用：不加配对结构的独立性假设，这里没有。

### single-seed artifact
观察：H_P 的 25% 在 seed-1 重跑变成 0/20。
本项目：n=60 后 25% → 13%；E07 的绝对值被修正。
不要误用：单 seed 数字是假设，不是结果（F11 教训）。