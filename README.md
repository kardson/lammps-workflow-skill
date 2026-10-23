# LAMMPS Workflow Skill

以 `lammps-md-workflow` skill 协助开展 LAMMPS 分子动力学研究，首版侧重半导体气相沉积工作流，支持经验势与现成机器学习势的应用，不包含势函数训练。

沿用 [VASP 工作流](https://github.com/kardson/dft-workflow-skill) 的六步研究协作方式：环境证据 → 问题与材料 → 确认方案 → 输入准备与检查 → 授权执行与取证 → 分析与科学判断。势的适用性、动态增原子、表面热处理和统计判据按 MD 问题重新建立。

## 使用

将完整仓库安装为 `lammps-md-workflow` skill，保留根目录 `SKILL.md`、`agents/`、`references/`、`tools/` 和 `templates/`。详细步骤见 [安装与项目接入](references/installation.md)。

可以直接告诉 agent：

> 使用 $lammps-md-workflow，先检查已有环境和势函数，再整理沉积模拟方案；暂不运行计算。

研究数据使用独立私有工作区。公开仓库不包含连接配置、研究结果、模型权重、上游源码副本或已配置的计算后端。

## 首版实际能力

| 内容 | 状态 |
|---|---|
| skill 路由、六步流程、沉积与势函数检查要求 | 已提供 |
| 项目初始化、一次性环境/帮助检查、势文件身份、离线手册检索 | 已提供标准库工具 |
| 方案、模型卡、执行尝试记录 | 已提供未确认模板 |
| 远程提交、重启、在线监控、生产输入生成 | agent 按项目适配；未提供通用自动执行器 |
| 势函数精度、GPU 数值一致性、沉积与续算 | 需要实际验证；本仓库不宣称已通过 |

工具需要 Python 3.10+ 标准库；ASE、OVITO 等按任务在研究环境单独安装。流程说明见 [能力目录](references/capabilities.md)，验证方式为 `python -m unittest discover -s tests -v`。

当前为初始准备版。许可尚未指定，与参考 VASP 仓库保持一致；公开可见不等于已授予开源再分发许可。[第三方说明](THIRD_PARTY.md)。
