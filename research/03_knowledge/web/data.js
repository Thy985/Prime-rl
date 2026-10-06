// 由 knowledge_graph.json 生成（source of truth 是 JSON，勿手改此处；
// 重新生成：读取 JSON 后包裹成 window.KG 赋值即可。）
window.KG = {
  "meta": {
    "project": "Agent Runtime Intervention on SWE Agent Behaviour",
    "branch": "exp/swe-verifier-terrain",
    "freeze": "research-p8c-final = a5975ac74",
    "date": "2026-10-06",
    "headline": "给固定模型/固定预算/固定工具集的 agent，在每个决策回合重复注入当前阶段上下文（user 角色），会重新分配它固定数量的动作，从而在小预算下提高成功率。不是推理变强、不是更努力、不是更早动手、不是工具开关。",
    "sourceOfTruth": "本 JSON 与 map.md / nodes/*.md 同源；网页只从这里渲染。",
    "pathNote": "所有 path 均为 repo-root 相对。web/ 位于 research/03_knowledge/web/，故 webPathPrefix 为 '../../../'（3 级回到 repo root）。",
    "webPathPrefix": "../../../"
  },
  "nodeTypes": [
    "experiment",
    "hypothesis",
    "mechanism",
    "design",
    "failure",
    "concept",
    "open question"
  ],
  "edgeTypes": [
    "leads_to",
    "tests",
    "supports",
    "rejects",
    "refines",
    "replaces",
    "depends_on",
    "connects_to",
    "corrects"
  ],
  "statuses": {
    "supported": "绿/稳",
    "narrowed": "蓝/缩水",
    "rejected": "红/被否",
    "retracted": "深红/撤回",
    "replaced": "紫/改名",
    "frozen": "深绿/冻结",
    "untested": "橙/未测",
    "open": "橙/开放"
  },
  "nodes": [
    {
      "id": "N01",
      "title": "起点：奖励能塑造可迁移能力吗？",
      "type": "design",
      "status": "retracted",
      "experiment": "E01",
      "phase": "P0",
      "plain": "反转文本任务上验证 reward 能不能塑造能力。SFT 确实建了能力（0/18→7/18），但两个头条结论双双撤回：一个协议 bug、一个学习率假象。真正剩下的产出是测量纪律。",
      "questions": [
        "奖励函数的长相决定学不学得会吗？",
        "学会的能力在继续训练时会被覆盖吗？",
        "怎么知道测量到的变好是真的变好？"
      ],
      "answer": "奖励形状在可比较之前先被协议污染排除；能力确实能建（SFT 0/18→7/18）；测量先于能力结论。",
      "changed": {
        "before": "奖励形状决定学习结果，可以比较奖励。",
        "after": "任何能力断言以「protocol 单一来源 + 非破坏性更新 regime」为前提。"
      },
      "evidence": [
        {
          "label": "E01 实验记录",
          "path": "research/02_experiments/E01_reverse_text.md"
        },
        {
          "label": "撤回台账 PLAN.md §0",
          "path": "tools/swe_lab/PLAN.md"
        },
        {
          "label": "失败台账 F02/F03/F04",
          "path": "research/05_process/failure_ledger.md"
        }
      ],
      "concepts": [
        "reward ablation",
        "protocol invariance",
        "non-destructive lr"
      ],
      "file": "research/03_knowledge/nodes/N01_start_reward.md"
    },
    {
      "id": "N02",
      "title": "验证器审计：tests green 不是 verifier",
      "type": "mechanism",
      "status": "supported",
      "experiment": "E02",
      "phase": "P1",
      "plain": "先审计给奖励的程序：只看退出码/通过率的验证器会给作弊修复 1.000、给真实部分修复 0.571。改成结构化 verdict + Golden Episode + replay acceptance，奖励才可信。",
      "questions": [
        "测试全绿等于修好了吗？",
        "怎么证明验证器没在看错的东西？",
        "每个难度 tier 的验证器有区分度吗？"
      ],
      "answer": "测试全绿不等于修好；tampering 会骗过 naive scalar；结构化 verdict 修复了它。",
      "changed": {
        "before": "奖励 = 测试通过率，越高越好。",
        "after": "奖励必须识别真修复/耍诈/部分修复；后续所有指标纷争都是这次审计的子孙。"
      },
      "evidence": [
        {
          "label": "E02 实验记录",
          "path": "research/02_experiments/E02_verifier_audit.md"
        },
        {
          "label": "commits 498fca529 / 56a6c91d1",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "verifier 源码 deps/verifiers",
          "path": "research/06_artifacts/code_map.md"
        }
      ],
      "concepts": [
        "verifier",
        "Golden Episode",
        "replay acceptance"
      ],
      "file": "research/03_knowledge/nodes/N02_verifier_audit.md"
    },
    {
      "id": "N03",
      "title": "难度阶梯 + 预算前沿：headroom 从哪来",
      "type": "design",
      "status": "narrowed",
      "experiment": "E03",
      "phase": "P2-P3",
      "plain": "造了 tier1–5 难度阶梯并逐级审计。难度本身没有创造区分度（tier5 也没让 H_A 脱敏）；真正制造 headroom 的是绑定 turn 预算。还修了两个测量 bug（endpoint 错误率、被藏起来的预算效果）。",
      "questions": [
        "把任务改难，agent 表现会平滑下降吗？",
        "悬崖是难度差异还是测量假象？",
        "什么条件让不同 harness 可比？"
      ],
      "answer": "不会平滑下降会出悬崖；悬崖部分是 endpoint 错误率假象；绑定预算才能比较 harness。",
      "changed": {
        "before": "难度是天然区分度；pool 几遍就能下结论。",
        "after": "operating point（任务集+预算）要先于 harness 比较选好；饱和基线不是实验设置。"
      },
      "evidence": [
        {
          "label": "E03 实验记录",
          "path": "research/02_experiments/E03_swe_micro.md"
        },
        {
          "label": "5ef3bf8ee / 6004a7559",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "frontier_budget.json",
          "path": "tools/swe_lab/runs/frontier_budget.json"
        }
      ],
      "concepts": [
        "difficulty ladder",
        "budget frontier",
        "headroom"
      ],
      "file": "research/03_knowledge/nodes/N03_difficulty_ladder.md"
    },
    {
      "id": "N04",
      "title": "工具即杠杆？第一次 Harness A/B/C",
      "type": "experiment",
      "status": "narrowed",
      "experiment": "E04",
      "phase": "P3",
      "plain": "同一模型同一任务只改一件事：给不给 edit 工具。移走 edit 掉 44 分（n=1 读数）。但 H_C 加完成条件绑定的效果在 n=32 反转、被撤回。稳定说法：tool support 是真实杠杆；难度是 task × harness 交互。",
      "questions": [
        "拿走 edit 工具还解得出来吗？",
        "44 分稳定吗？",
        "失败是没动手还是写错了？"
      ],
      "answer": "拿走 edit 掉 44 分；H_C 部分反转撤回；失败主形态是 no-write（根本没动手改）。",
      "changed": {
        "before": "工具集就是杠杆；单次 run 能命名机制。",
        "after": "大且稳的效应能扛复制，小效应必须复制后再命名——「复制先于命名」成为全档案模板。"
      },
      "evidence": [
        {
          "label": "E04 实验记录",
          "path": "research/02_experiments/E04_harness.md"
        },
        {
          "label": "d43b15861 / 6a1177c45（撤回）",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "失败台账 F09",
          "path": "research/05_process/failure_ledger.md"
        }
      ],
      "concepts": [
        "action affordance",
        "completion bound",
        "no-write failure"
      ],
      "file": "research/03_knowledge/nodes/N04_tool_lever.md"
    },
    {
      "id": "N05",
      "title": "分阶段运行时 H_D：planner 框架撤回",
      "type": "concept",
      "status": "replaced",
      "experiment": "E05/E06",
      "phase": "P4",
      "plain": "分阶段运行时（recon→execute→feedback）在 lab 显著提升。但 120 episodes 审计发现：planner 回合真写计划的 0/120。「plan/execute 架构」的框架被自己的 trace 推翻，改名 staged action allocation。H_F 归因显示增益主要来自阶段提示文本。",
      "questions": [
        "分阶段运行时会改变结果吗？",
        "因为它更像 planner/executor 架构吗？",
        "是提示文本还是工具门控在起作用？"
      ],
      "answer": "会改变结果；但不是 planner 架构（0/120 写计划）；H_F 显示阶段提示文本是大头。",
      "changed": {
        "before": "H_D gain = planner/executor 架构有效。",
        "after": "gain = staged action allocation（对固定回合预算做结构化分配）；名字必须反映数据。"
      },
      "evidence": [
        {
          "label": "E05 记录 design / E06 H_F",
          "path": "research/02_experiments/E05_real_swe.md"
        },
        {
          "label": "7cdbc5980（改名）",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "决策日志 D03",
          "path": "research/05_process/decision_log.md"
        }
      ],
      "concepts": [
        "staged runtime",
        "planner/executor",
        "attribution control"
      ],
      "file": "research/03_knowledge/nodes/N05_staged_runtime_HD.md"
    },
    {
      "id": "N06",
      "title": "真实 SWE 校准：+32pt 缩水到 +10pt",
      "type": "experiment",
      "status": "supported",
      "experiment": "E05",
      "phase": "P5",
      "plain": "把 H_D vs H_A 搬到真实 SWE-bench Verified（无 Docker，自建 containerless verifier）。pilot 5 实例 +32pt 很亮眼；扩到 20 实例两仓库后缩到 +10pt——pilot 高估约 4 倍。第二模型（bunny）方向复现（+12pt）。",
      "questions": [
        "没有容器怎么验证真实 SWE 修复？",
        "效果多大？",
        "更宽的预算/任务集上还成立吗？"
      ],
      "answer": "自建 containerless verifier；pilot +32pt、wide +10pt；效果真实但量级与任务集强相关。",
      "changed": {
        "before": "pilot 的 +32pt 是效果规模。",
        "after": "诚实的规模是 wide 集 +10pt；方向可复现、量级不可（先别庆祝，先扩大样本）。"
      },
      "evidence": [
        {
          "label": "E05 实验记录",
          "path": "research/02_experiments/E05_real_swe.md"
        },
        {
          "label": "22f40cd41 / 6bc971c6b",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "budget-sweep 逐格可复现表",
          "path": "research/02_experiments/E05_real_swe.md"
        }
      ],
      "concepts": [
        "containerless verifier",
        "pilot",
        "calibration"
      ],
      "file": "research/03_knowledge/nodes/N06_real_swe_calibration.md"
    },
    {
      "id": "N07",
      "title": "静态散文假设被否：文字不是控制信号",
      "type": "hypothesis",
      "status": "rejected",
      "experiment": "E05",
      "phase": "P5",
      "plain": "把 H_D 的行为指南写成一段静态文字放进 H_A 系统提示（H_A-prime）。结果 1/16 vs H_A 2/16 vs H_D 7/16——静态散文一点都恢复不了差距。说出来 ≠ 会执行。",
      "questions": [
        "效果是「提示词写得好」吗？",
        "同一段文字，静态放 vs 每回合注入等价吗？"
      ],
      "answer": "不是；完全不等价。同样的文字，注入方式不同就是不同变量。",
      "changed": {
        "before": "可能只是 prompt 措辞问题。",
        "after": "静态 instruction 文本不是控制信号；为「注入是机制」铺路。"
      },
      "evidence": [
        {
          "label": "E05 H_A-prime 段",
          "path": "research/02_experiments/E05_real_swe.md"
        },
        {
          "label": "625653bb4",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "假设台账 H09",
          "path": "research/00_index/hypothesis_ledger.md"
        }
      ],
      "concepts": [
        "static instruction",
        "system prompt"
      ],
      "file": "research/03_knowledge/nodes/N07_static_prose_rejected.md"
    },
    {
      "id": "N08",
      "title": "预算形状效应：效果是预算的函数",
      "type": "hypothesis",
      "status": "rejected",
      "experiment": "E05",
      "phase": "P5",
      "plain": "扫 max_turns ∈ {2,4,6,8}：gap +6→+32→+19→−6pt。效果在 T=4 峰值、T=8 反超消失——H_A 在宽预算下自己学会了 inspect→edit→test→repair。分阶段引导是回合紧张时的省钱技巧。",
      "questions": [
        "H_D 价值是结构性的还是预算效率的？",
        "预算很充裕时 H_A 会自己补上行为吗？"
      ],
      "answer": "是预算效率；会。T=8 时 H_A 自发现 verify+repair，引导反而开始拖后腿。",
      "changed": {
        "before": "H_D = 结构性改进（任意预算有效）。",
        "after": "effect is budget-shaped；真实含义收窄为 unit-budget efficiency；行为可自发涌现。"
      },
      "evidence": [
        {
          "label": "E05 Reconstructability 表",
          "path": "research/02_experiments/E05_real_swe.md"
        },
        {
          "label": "a867f112d",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "swe_budget_sweep.md",
          "path": "tools/swe_lab/runs/swe_budget_sweep.md"
        }
      ],
      "concepts": [
        "interaction budget",
        "budget-shaped effect",
        "unit-budget efficiency"
      ],
      "file": "research/03_knowledge/nodes/N08_budget_shape.md"
    },
    {
      "id": "N09",
      "title": "蒸馏路线被拒：学生拿到文本没拿到环境",
      "type": "failure",
      "status": "rejected",
      "experiment": "E05",
      "phase": "P4/P5",
      "plain": "用 dots3 的 H_D 轨迹训 Qwen3-0.6B（20 步 LoRA SFT），裸 H_A 评估：SFT 前后都 0/10 工具调用、0/10 resolve。学生连「调用工具」都没学会——这条蒸馏路线不通（route-specific）。",
      "questions": [
        "0.6B 学生能学会工具调用吗？",
        "是容量/步数/格式对齐哪个环节断了？"
      ],
      "answer": "学不会（0/10 工具调用）；轨迹本身不是完整的 capability transfer unit；该路线被拒。",
      "changed": {
        "before": "轨迹 = 完整传输单元（文本给够就行）。",
        "after": "轨迹不是传输单元；工具格式对齐是硬前提；结论严格限定为一条路线。"
      },
      "evidence": [
        {
          "label": "E05 蒸馏段",
          "path": "research/02_experiments/E05_real_swe.md"
        },
        {
          "label": "1df2989df",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "假设台账 H07 / 矩阵 C10",
          "path": "research/00_index/claim_evidence_matrix.md"
        }
      ],
      "concepts": [
        "distillation",
        "tool-format alignment",
        "trajectory"
      ],
      "file": "research/03_knowledge/nodes/N09_distillation_rejected.md"
    },
    {
      "id": "N10",
      "title": "gating 被否：banner 才是机制",
      "type": "experiment",
      "status": "supported",
      "experiment": "E06",
      "phase": "P6",
      "plain": "2×2 因子：banner × gate。H_P（提示无门控）25% = H_D（提示+门控）25%；H_G（只门控无提示）1/20 地板。pilot 上 H_P 精确复现 H_D（7/16=44%）。藏住 edit 工具没有用，每回合提醒才有用。自适应调度器也赢不了固定分段。",
      "questions": [
        "H_D 效果是提示还是门控给的？",
        "自适应调度器能超过固定分段吗？"
      ],
      "answer": "提示（banner）全权负责；门控贡献≈0；H_ADAPT 从未胜过固定分段且有 recon-2 税。",
      "changed": {
        "before": "工具集是杠杆 + gate 假设。",
        "after": "gate falsified；机制改名 per-turn control-plane signaling；banner 是后续所有工作的支点。"
      },
      "evidence": [
        {
          "label": "E06 实验记录",
          "path": "research/02_experiments/E06_mechanism.md"
        },
        {
          "label": "6aea58419 / ce618eed3",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "假设台账 H11",
          "path": "research/00_index/hypothesis_ledger.md"
        }
      ],
      "concepts": [
        "affordance gating",
        "2x2 factorial",
        "control-plane signaling"
      ],
      "file": "research/03_knowledge/nodes/N10_gating_falsified.md"
    },
    {
      "id": "N11",
      "title": "banner 分解：重复、内容、角色三杠杆",
      "type": "experiment",
      "status": "narrowed",
      "experiment": "E07",
      "phase": "P7",
      "plain": "固定 dots3+wide20+T=6+edit 永远可用，只改 banner 变体：H_A 0%、H_ONCE 5%、H_NEUTRAL 5%、H_ACTION 15%、H_P 25%、H_SYS 15%。三个独立杠杆：重复（once→every-turn）、内容（neutral→action）、角色（user→system）。中性文字惰性，三杠杆不可互相替代。",
      "questions": [
        "每回合重复是必要的吗？",
        "发什么内容重要吗？",
        "用哪个角色发重要吗？"
      ],
      "answer": "重复必要（5%→15–25%）；内容次要（5%→15%）；角色有影响（25%→15%）；三者独立。",
      "changed": {
        "before": "banner = 一条提示，改措辞就行。",
        "after": "banner 是三维变量（repetition×content×role），各自贡献、不可替代。"
      },
      "evidence": [
        {
          "label": "E07 实验记录",
          "path": "research/02_experiments/E07_banner.md"
        },
        {
          "label": "3b4f0286e / 610450d35",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "假设台账 H12/H13/H14",
          "path": "research/00_index/hypothesis_ledger.md"
        }
      ],
      "concepts": [
        "cadence",
        "content",
        "role"
      ],
      "file": "research/03_knowledge/nodes/N11_banner_decomposition.md"
    },
    {
      "id": "N12",
      "title": "角色对比收窄：system ≠ user，不是中断因果",
      "type": "design",
      "status": "narrowed",
      "experiment": "E07",
      "phase": "P7",
      "plain": "H_SYS（同文字 system 角色）15% vs H_P（user 角色）25%——角色有影响。但明确设界：只能证明 system-role ≠ user-role，不能证明「中断是因果」。术语收窄为 user-turn runtime intervention。",
      "questions": [
        "角色影响能推广成「中断是因果」吗？",
        "system vs user 在什么意义上不同？"
      ],
      "answer": "不能推广；只是身份有影响。中断因果是更强主张，没有证据——明确 not claim。",
      "changed": {
        "before": "角色杠杆 → 中断因果（可能）。",
        "after": "role 对比是 injection position 对比，不是中断测试；「harness 必须中断模型」被否。"
      },
      "evidence": [
        {
          "label": "E07 H_SYS 段",
          "path": "research/02_experiments/E07_banner.md"
        },
        {
          "label": "决策日志 D15",
          "path": "research/05_process/decision_log.md"
        },
        {
          "label": "矩阵 C17 + must-not-claim 4",
          "path": "research/00_index/claim_evidence_matrix.md"
        }
      ],
      "concepts": [
        "message role",
        "user-turn runtime intervention",
        "control-plane injection"
      ],
      "file": "research/03_knowledge/nodes/N12_role_narrowed.md"
    },
    {
      "id": "N13",
      "title": "复制修正 n=60：25% 是种子噪声，timing 死亡",
      "type": "experiment",
      "status": "supported",
      "experiment": "E08",
      "phase": "P8C",
      "plain": "4 arms × 3 seeds × 20 tasks = n=60。H_P 25%（单 seed）→ 13%（seed-1 重跑 0/20）。H_REPLAY（回合 1/3/5 注入）17% > H_P 13%，p=0.77——timing 不是维度。两个配对主张活下来：banner vs none p=0.031；multiple vs single p=0.008。",
      "questions": [
        "单 seed 的 25% 是真的吗？",
        "注入位置是第四维度吗？"
      ],
      "answer": "25% 是种子噪声（真实 13%）；位置不重要（p=0.77）；配对比较活、聚合率比较死。",
      "changed": {
        "before": "E07 绝对值（0/5/5/15/25）是结果。",
        "after": "绝对值修正（7/3/13/17）；timing 维度死亡；配对（同实例）对比才可信。"
      },
      "evidence": [
        {
          "label": "E08 逐 seed 表",
          "path": "research/02_experiments/E08_expanded_n.md"
        },
        {
          "label": "a5975ac74（freeze）",
          "path": "research/00_index/git_snapshot.md"
        },
        {
          "label": "失败台账 F11",
          "path": "research/05_process/failure_ledger.md"
        }
      ],
      "concepts": [
        "paired McNemar",
        "seed",
        "single-seed artifact"
      ],
      "file": "research/03_knowledge/nodes/N13_replication_n60.md"
    },
    {
      "id": "N14",
      "title": "action allocation：同数量动作换了分配",
      "type": "mechanism",
      "status": "supported",
      "experiment": "E08",
      "phase": "P8C",
      "plain": "n=60 轨迹 mediation：state-chg 比例 0.04→0.07（solved-only 0.17→0.30）；总调用数不变；first_edit 不提前；最长的 inspect run 变短。agent 没有更努力/更早/更聪明——把同样数量动作重新分配了。",
      "questions": [
        "banner 是让模型更努力吗？",
        "更早动手吗？",
        "还是只改了做什么的分配？"
      ],
      "answer": "全排除前两者：n_calls 平、first_edit 不提前；唯一变化是 action allocation。",
      "changed": {
        "before": "机制可能是多干活/早动手/想得更深。",
        "after": "都是 action allocation；这是 headline 的机制核心（观测性链条，非正式因果）。"
      },
      "evidence": [
        {
          "label": "E08 mediation 段",
          "path": "research/02_experiments/E08_expanded_n.md"
        },
        {
          "label": "0807caa0c",
          "path": "research/00_index/git_milestones.md"
        },
        {
          "label": "矩阵 C16",
          "path": "research/00_index/claim_evidence_matrix.md"
        }
      ],
      "concepts": [
        "action allocation",
        "mediation chain",
        "state-changing call"
      ],
      "file": "research/03_knowledge/nodes/N14_action_allocation.md"
    },
    {
      "id": "N15",
      "title": "跨模型 H18：被 provider 阻断，不是被实验否定",
      "type": "open question",
      "status": "untested",
      "experiment": "E08",
      "phase": "P8A",
      "plain": "计划在 bunny / DeepSeek-v4-flash 上复制 banner 研究，从未完成：bunny 被 deep-ep 的 aarch64 元数据问题卡住（--no-sync 修复后 smoke 通过），随后用户终止所有 bunny 任务；DeepSeek 从未运行。8A run 目录不存在 = 物理证据。H18 = untested。",
      "questions": [
        "banner 效果在别的模型上成立吗？",
        "provider 失败和模型失败怎么区分？"
      ],
      "answer": "没有效果观测——只有「未测」。provider 失败 ≠ 模型失败：诊断顺序 probe endpoint → dependency → model。",
      "changed": {
        "before": "cross-model 是计划中的一步。",
        "after": "H18 永远记录为 untested（不是 negative）；被外部依赖卡住的研究腿要正式归档。"
      },
      "evidence": [
        {
          "label": "E08 Phase 8A 段",
          "path": "research/02_experiments/E08_expanded_n.md"
        },
        {
          "label": "失败台账 F08/F10/F14",
          "path": "research/05_process/failure_ledger.md"
        },
        {
          "label": "决策日志 D16/D17/D18",
          "path": "research/05_process/decision_log.md"
        }
      ],
      "concepts": [
        "cross-model replication",
        "provider failure",
        "untested (blocked)"
      ],
      "file": "research/03_knowledge/nodes/N15_cross_model_blocked.md"
    },
    {
      "id": "N16",
      "title": "当前最终理解：三层模型",
      "type": "concept",
      "status": "frozen",
      "experiment": "synthesis",
      "phase": "freeze",
      "plain": "存活证据收拢为三层：Phase5 harness 改变行为 → Phase6 不是工具门控 → Phase7 注入的性质（role/cadence/content）都起作用。最终 headline 小而稳：重复 user 角色阶段注入 → action allocation → 小预算下提高成功率。",
      "questions": [
        "把五天证据压成一句，哪句安全？",
        "哪些 claim 强、哪些弱？"
      ],
      "answer": "headline 一句话（见 meta）；强证据只有两个配对 p 值（0.031/0.008），其余 moderate 及以下。",
      "changed": {
        "before": "可能有一个大机制故事（规划/验证/工具哲学）。",
        "after": "小的、稳的、边界清楚的故事；研究收尾 = 反复做减法。"
      },
      "evidence": [
        {
          "label": "最终报告",
          "path": "research/04_synthesis/final_report.md"
        },
        {
          "label": "回顾 retrospective",
          "path": "research/04_synthesis/retrospective.md"
        },
        {
          "label": "结论矩阵 C01–C18",
          "path": "research/00_index/claim_evidence_matrix.md"
        }
      ],
      "concepts": [
        "three-layer model",
        "headline claim"
      ],
      "file": "research/03_knowledge/nodes/N16_final_understanding.md"
    },
    {
      "id": "N17",
      "title": "开放问题：没做的不是失败的",
      "type": "open question",
      "status": "open",
      "experiment": "synthesis",
      "phase": "after freeze",
      "plain": "六条开放项，每条带「为什么没做」：跨模型复制（H18）、正式 mediation、更多 seed、T=8 区域、任务族分层、工具格式对齐蒸馏。不是失败——是研究故意停下的地方。",
      "questions": [
        "跨模型是否成立？",
        "action allocation 的正式因果估计？",
        "更多 seed 下绝对值多少？"
      ],
      "answer": "全部未答；其中跨模型是第一条，不是机制问题，是需要可用 provider 的复制问题。",
      "changed": {
        "before": "研究结束 = 问题结束。",
        "after": "研究结束 = 把已答和未答精确分账；开放问题清单是最后一项 deliverable。"
      },
      "evidence": [
        {
          "label": "最终报告 §10",
          "path": "research/04_synthesis/final_report.md"
        },
        {
          "label": "E08 limitations",
          "path": "research/02_experiments/E08_expanded_n.md"
        },
        {
          "label": "H18 状态 F14",
          "path": "research/05_process/failure_ledger.md"
        }
      ],
      "concepts": [
        "open question",
        "power"
      ],
      "file": "research/03_knowledge/nodes/N17_open_questions.md"
    }
  ],
  "edges": [
    {
      "from": "N01",
      "to": "N02",
      "type": "leads_to",
      "why": "E01 两个撤回逼出「先验证验证器」"
    },
    {
      "from": "N02",
      "to": "N03",
      "type": "leads_to",
      "why": "验证器可信，难度阶梯才有意义"
    },
    {
      "from": "N03",
      "to": "N04",
      "type": "leads_to",
      "why": "headroom 确定，harness 比较才不饱和"
    },
    {
      "from": "N04",
      "to": "N05",
      "type": "leads_to",
      "why": "工具存在但时间表不同 → 分阶段运行时"
    },
    {
      "from": "N05",
      "to": "N04",
      "type": "replaces",
      "why": "移除工具 → staged action allocation：旧的机制命名被替代"
    },
    {
      "from": "N10",
      "to": "N04",
      "type": "refines",
      "why": "2×2 缩窄「工具即杠杆」：机制不是工具开关（N04 的 −44pt 成立但解释被换掉）"
    },
    {
      "from": "N05",
      "to": "N06",
      "type": "leads_to",
      "why": "实验室效果 → 真实 SWE 验证"
    },
    {
      "from": "N06",
      "to": "N07",
      "type": "rejects",
      "why": "H_A-prime 1/16：静态散文不携带效果"
    },
    {
      "from": "N06",
      "to": "N08",
      "type": "rejects",
      "why": "T=8 反超：效果依赖预算"
    },
    {
      "from": "N06",
      "to": "N09",
      "type": "rejects",
      "why": "蒸馏 0/10 tool calls：此路线不通"
    },
    {
      "from": "N06",
      "to": "N10",
      "type": "tests",
      "why": "下一步怀疑 gate 是机制"
    },
    {
      "from": "N06",
      "to": "N15",
      "type": "connects_to",
      "why": "跨模型腿被 provider 阻断（H18 untested）"
    },
    {
      "from": "N10",
      "to": "N11",
      "type": "leads_to",
      "why": "banner 是机制 → 拆它的性质"
    },
    {
      "from": "N10",
      "to": "N05",
      "type": "rejects",
      "why": "2×2：gate 不承载 H_D 效果（H_P=H_D）"
    },
    {
      "from": "N11",
      "to": "N12",
      "type": "connects_to",
      "why": "角色对比 → 收窄主张边界"
    },
    {
      "from": "N11",
      "to": "N13",
      "type": "leads_to",
      "why": "单 seed 证据 → 复制到 n=60"
    },
    {
      "from": "N13",
      "to": "N11",
      "type": "corrects",
      "why": "H_P 25% 是 seed 噪声，实际 13%"
    },
    {
      "from": "N13",
      "to": "N11",
      "type": "supports",
      "why": "multiple vs single p=0.008；banner vs none p=0.031"
    },
    {
      "from": "N13",
      "to": "N14",
      "type": "leads_to",
      "why": "存活主张 → 测量其机制"
    },
    {
      "from": "N14",
      "to": "N16",
      "type": "supports",
      "why": "mediation 链：同数量动作，不同分配"
    },
    {
      "from": "N14",
      "to": "N16",
      "type": "leads_to",
      "why": "机制定型 → 三层模型收拢"
    },
    {
      "from": "N15",
      "to": "N16",
      "type": "connects_to",
      "why": "跨模型始终未测 → 边界条件保留"
    },
    {
      "from": "N16",
      "to": "N17",
      "type": "leads_to",
      "why": "理解停在哪 → 接下来做什么"
    }
  ],
  "concepts": [
    {
      "name": "harness",
      "observation": "同一个模型，包它的代码不同，成功率就不同。",
      "nodes": [
        "N04",
        "N10"
      ]
    },
    {
      "name": "verifier",
      "observation": "判断修复对不对的程序；只看测试绿不绿会被作弊骗过。",
      "nodes": [
        "N02"
      ]
    },
    {
      "name": "action affordance",
      "observation": "环境允许 agent 执行的动作集合（能不能用 edit）。",
      "nodes": [
        "N04",
        "N10"
      ]
    },
    {
      "name": "interaction budget",
      "observation": "回合数给少时引导很值钱，给多时自己就会了。",
      "nodes": [
        "N03",
        "N08"
      ]
    },
    {
      "name": "staged runtime",
      "observation": "把交互拆成有顺序的阶段（recon→execute→feedback）。",
      "nodes": [
        "N05"
      ]
    },
    {
      "name": "gating",
      "observation": "按阶段隐藏工具；藏住 edit 本身没有用。",
      "nodes": [
        "N10"
      ]
    },
    {
      "name": "banner",
      "observation": "每回合注入阶段上下文；效果与完整 H_D 相同。",
      "nodes": [
        "N10",
        "N11"
      ]
    },
    {
      "name": "runtime intervention",
      "observation": "运行中以 user 回合形式注入上下文；user/system 角色效果不同。",
      "nodes": [
        "N12"
      ]
    },
    {
      "name": "action allocation",
      "observation": "总调用数没变、第一次 edit 没提前，但改状态的比例涨了。",
      "nodes": [
        "N14"
      ]
    },
    {
      "name": "distilled trajectory",
      "observation": "用大模型轨迹训练小模型；这条路线被拒（0/10 工具调用）。",
      "nodes": [
        "N09"
      ]
    },
    {
      "name": "paired McNemar",
      "observation": "同一批实例上的配对比较；唯一活过复制的统计。",
      "nodes": [
        "N13"
      ]
    },
    {
      "name": "single-seed artifact",
      "observation": "只在一个随机种子上成立的数字（H_P 25% → 13%）。",
      "nodes": [
        "N13"
      ]
    }
  ]
};