"""Export the fitted parameter registry, uncertainty report and diagnostic notebook."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import sys
import zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import mistune
import nbformat

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'reliable-calibration';RESULTS=ROOT/'results'
NAMES=['beta_income','beta_jobs','beta_rent','beta_distance','beta_education','beta_childcare']

def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))

def main():
    irs=read('irs-fit-report.json');beta=read('beta-fit-report.json');ext=read('extension-fit-report.json')
    precision=read('precision-fix-report.json');scale=read('extended-scale-report.json')
    research=read('research-design-fit-report.json')
    assert precision['passed'] and beta['deterministic_repeat_max_difference']==0 and ext['repeat_max_difference']==0
    theta=irs['chosen_theta'];target=beta['target'];oldparams=json.loads((ROOT/'raw-rebuild/kernel-with-legacy.json').read_text())['parameters']
    environment={'python':sys.version,**{name:importlib.metadata.version(name) for name in ['numpy','pandas','scipy','matplotlib','joblib','nbformat','nbclient','nbconvert','ipykernel','mistune']}}
    assert sys.version_info[:3]==(3,10,18)
    inputs=[ROOT/'raw-rebuild/state-inputs-reconstructed.csv',ROOT/'raw-rebuild/irs-routes-reconstructed.csv',
        ROOT/'raw-rebuild/rebuilt/acs_young_adult_interstate_move_rate.csv',ROOT/'raw-rebuild/rebuilt/pums_external_origin_competition.csv',
        ROOT/'download/CITS4403-GROUP-PROJECT-master/0914-1_v8.ipynb',ROOT/'deployment/master/0914-1_v8.ipynb',ROOT/'raw_model.py',ROOT/'reliable_worker.py']
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    shutil.copy2(ROOT/'raw-rebuild/source-manifest.json',OUT/'input-source-manifest.json')
    parameters={'schema_version':1,'profile':'new','state_codes':['CA','TX','NY','FL','MA','NC','IL','WA'],
        **dict(zip(NAMES,theta[:6])),'destination_effects':dict(zip(['CA','TX','NY','FL','MA','NC','IL','WA'],[0.]+theta[6:])),
        'beta_current_state':beta['chosen_beta'],
        'beta_by_design':{'1000x20':beta['chosen_beta'],**({'600x12':research['chosen_beta']} if research['validation_criteria_passed'] else {})},
        'design_validation':{'1000x20':beta['validation_criteria_passed'],'600x12':research['validation_criteria_passed']},
        'network_beta_by_decay':{'0.0':research['chosen_beta'],**{str(r['decay']):r['beta_current_state'] for r in ext['network'] if r['validation_criteria_passed']}},
        'external_rate_by_capacity':{r['capacity_mode']:r['external_rate'] for r in ext['open'] if r['validation_criteria_passed']},
        'external_origin_target':ext['external_origin_target'],'final_scalar_precision_decimals':4,
        'interaction_levels':{'weak':.6,'medium':1.,'strong':1.4},
        'fit_temperature':.85,'simulation_temperature':.90,
        'case_scope':{'core_calibration':{'policy':'baseline','interaction':'medium'},'network_calibration':{'agents':600,'years':12,'policy':'baseline','interaction':'medium'},'external_calibration':{'agents':600,'years':12,'policy':'baseline','intensity':0.,'interaction':'medium'}},
        'fixed_structural_assumptions':{k:v for k,v in oldparams.items() if k not in NAMES+['beta_current_state']},
        'provenance':{'irs_fit':'Origin-group CV of regularized route-share fitting; historical IL/WA holdout evaluated without retuning.',
            'stay_fit':'16 training seeds, 1000 agents x 20 years, staged grid, target independently rebuilt ACS rate.',
            'simulation_validation_seeds':list(range(1901,1933)),'network_fit':'Match closed-model rate at 600 agents x 12 years; controlled comparison.',
            'research_design_fit':'32 training seeds 901-932; fresh validation 3001-3032 after failed transfer diagnostic; separate conditional 600x12 beta.',
            'external_fit':'Match raw PUMS outside-eight-state origin share at 600 agents x 12 years.','source_sha256':hashes,'environment':environment},
        'limits':['Scenario, demographic, policy and social coefficients listed as fixed assumptions are not newly estimated.',
            'The 1000x20 beta failed a 600x12 transfer check; use the separately calibrated design parameter. Other designs require calibration.',
            'Parameters are conditional on model, priors and aggregate data; not identified causal effects or precise individual behavior estimates.',
            'Research-wide policy CSVs and video have not been regenerated with this new profile. Do not mix them with the fitted registry.']}
    (OUT/'parameters.json').write_text(json.dumps(parameters,indent=2,ensure_ascii=False),encoding='utf-8')
    rows=[]
    for i,k in enumerate(NAMES):
        stability=irs['coefficient_stability'][k]
        rows.append({'parameter':k,'old':oldparams[k],'new':theta[i],'source':'IRS route-share fit','p025':stability['bootstrap_p025'],'p975':stability['bootstrap_p975']})
    rows.append({'parameter':'beta_current_state','old':3.925,'new':beta['chosen_beta'],'source':'ACS target / current V8 simulator','p025':beta['beta_seed_bootstrap_p025'],'p975':beta['beta_seed_bootstrap_p975']})
    rows.append({'parameter':'beta_current_state_600x12','old':3.925,'new':research['chosen_beta'],'source':'ACS target / conditional 600x12 design','p025':research['beta_seed_bootstrap_p025'],'p975':research['beta_seed_bootstrap_p975']})
    frame=pd.DataFrame(rows);frame.to_csv(OUT/'parameter-comparison.csv',index=False)
    # Upgrade the initial checkpoint fingerprint to ignore timing-only report fields.
    fingerprint=hashlib.sha256(json.dumps({'chosen_theta':irs['chosen_theta'],'original_theta':irs['original_theta'],'source_sha256':irs['source_sha256']},sort_keys=True).encode()).hexdigest()
    (OUT/'beta-checkpoint-input.json').write_text(json.dumps({'model_fingerprint':fingerprint}),encoding='utf-8')
    matplotlib.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,3,figsize=(15,4.8))
    grid=pd.read_csv(OUT/'beta-grid.csv').drop_duplicates('beta_current_state').sort_values('beta_current_state')
    axes[0].plot(grid.beta_current_state,grid['mean']*100,'o-',color='#087f8c',ms=3)
    axes[0].axhline(target*100,color='#b14c31',ls='--',label='ACS target')
    axes[0].axvline(beta['chosen_beta'],color='#36454f',ls=':',label='Selected beta')
    axes[0].set(xlabel='Stay preference beta',ylabel='Mean annual move rate (%)',title='Training-seed grid');axes[0].legend(fontsize=9)
    v=[beta['validation_published'],beta['validation_new']]
    axes[1].errorbar([0,1],[r['mean']*100 for r in v],yerr=[r['ci95_halfwidth']*100 for r in v],fmt='o',capsize=6,color='#087f8c')
    axes[1].axhline(target*100,color='#b14c31',ls='--');axes[1].set_xticks([0,1],['Published profile','New fitted profile'])
    axes[1].set(ylabel='Move rate (%)',title='32 independent simulation seeds')
    evaluation=irs['heldout_evaluation'];values=[evaluation['historical_regularization_refit']['weighted_rmse'],evaluation['cv_selected_training_fit']['weighted_rmse']]
    axes[2].bar([0,1],values,color=['#92a4ad','#087f8c']);axes[2].set_xticks([0,1],['Original penalty','CV-selected penalty'])
    axes[2].set(ylabel='Weighted RMSE',title='Historical IL/WA route holdout')
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.suptitle('Calibration evidence: conditional model fit, not causal validation',fontsize=14);fig.tight_layout()
    fig.savefig(OUT/'calibration-evidence.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    rg=pd.read_csv(OUT/'research-design-grid.csv').drop_duplicates('beta_current_state').sort_values('beta_current_state')
    axes[0].plot(rg.beta_current_state,rg['mean']*100,'o-',color='#087f8c',ms=4)
    axes[0].axhline(target*100,color='#b14c31',ls='--',label='ACS target')
    axes[0].axvline(research['chosen_beta'],color='#36454f',ls=':',label='Selected 600x12 beta')
    axes[0].set(xlabel='Stay preference beta',ylabel='Mean annual move rate (%)',title='600x12: 32 training seeds');axes[0].legend(fontsize=9)
    checks=[scale,research['validation_primary_beta_control'],research['validation_new']]
    axes[1].errorbar(range(3),[r['mean']*100 for r in checks],
        yerr=[(r['ci95_high']-r['ci95_low'])*50 for r in checks],fmt='o',capsize=6,color='#087f8c')
    axes[1].axhline(target*100,color='#b14c31',ls='--')
    axes[1].set_xticks(range(3),['3.825: transfer\nseeds 2001-2032','3.825: control\nseeds 3001-3032','3.820: selected\nseeds 3001-3032'])
    axes[1].set(ylabel='Move rate (%)',title='600x12: retain failed diagnostic and fresh check')
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(OUT/'research-design-evidence.png',dpi=180);plt.close(fig)
    ptable='\n'.join(f"| `{r.parameter}` | {r.old:.8g} | {r.new:.8g} | {r.p025:.6g}–{r.p975:.6g} |" for r in frame.itertuples(index=False))
    ntable='\n'.join(f"| {r['decay']:g} | {r['beta_current_state']:.4f} | {r['training']['mean']:.5%} | {r['validation']['mean']:.5%} | {r['validation_paired_difference']['mean']*100:.5f} | {'通过' if r['validation_criteria_passed'] else '未通过'} |" for r in ext['network'])
    otable='\n'.join(f"| {r['capacity_mode']} | {r['external_rate']:.4f} | {r['training']['mean']:.4%} | {r['validation']['mean']:.4%} | {r['validation']['ci95_low']:.4%}–{r['validation']['ci95_high']:.4%} | {'通过' if r['validation_criteria_passed'] else '未通过'} |" for r in ext['open'])
    test=beta['validation_new'];published=beta['validation_published'];hold=irs['heldout_evaluation']
    accepted_network='、'.join(f"{r['decay']:g}" for r in ext['network'] if r['validation_criteria_passed']) or '无'
    rejected_network='；'.join(f"衰减{r['decay']:g}未通过：与封闭基线平均差{r['validation_paired_difference']['mean']*100:.5f}个百分点，配对差区间{r['validation_paired_difference']['ci95_low']*100:.5f}–{r['validation_paired_difference']['ci95_high']*100:.5f}个百分点" for r in ext['network'] if not r['validation_criteria_passed']) or '所有网络候选通过对应标准'
    md=f'''# 当前 V8：新参数校准与可复现性验证

## 结论与使用范围

**已完成基于现有核验数据的新参数拟合、独立模拟种子验证、参数不确定性分析与精度修复控制。**新核心配置的独立验证迁移率为 **{test['mean']:.5%}**，ACS 目标为 **{target:.5%}**；原发布配置在同一验证种子上的结果为 **{published['mean']:.5%}**。

本次是在当前 V8 机制、官方输入和明确假设下提高拟合与可复现性。它不证明参数是唯一真实值，也不证明政策效果已经因果识别。当前数据没有足够依据重新估计全部社会、人口和政策情景参数。

本报告的“95%模拟区间”均指跨独立随机种子计算的平均指标的t置信区间；不是单次运行的预测区间，不是未来现实迁移率区间，也不包含调查抽样误差。验收容差是预先声明的数值拟合标准，不是领域公认的可靠性阈值。

主校准预先规定的训练与验证标准：训练均值误差不超过 0.05 个百分点；32个独立验证种子的均值误差不超过 0.10 个百分点，且95%模拟区间覆盖 ACS 目标。训练标准 **{'通过' if beta['training_criterion_passed'] else '未通过'}**，独立验证标准 **{'通过' if beta['validation_criteria_passed'] else '未通过'}**。

**新参数没有替换 GitHub 和原项目的政策结果缓存。**原4140行政策实验、研究图表与视频仍属于旧发布配置。这里交付的是有完整依据的新参数、运行入口和验证报告；采用新配置的研究政策结论需要重新运行关联实验，不能把旧结果换一个参数标签后继续使用。

**验收边界：**主设置通过：{beta['validation_criteria_passed']}；600×12设置通过：{research['validation_criteria_passed']}；通过的网络衰减：{accepted_network}。{rejected_network}。未通过者不纳入可用默认配置，报告保留失败结果。情景强度和社会/人口结构仍是假设；开放系统的各模式状态见下表。

![校准证据](reliable-calibration/calibration-evidence.png)

## 拟合参数与稳定性

| 参数 | 原配置 | 新配置 | 条件 bootstrap 2.5%–97.5% |
|---|---:|---:|---:|
{ptable}

六个路线系数的区间来自 **200次按出发州整组重采样**，只有八个州，且先验、范围和正则化强度固定。租金、距离系数区间较宽；就业、教育和托育的窄区间也部分受先验约束影响，不能当作完全由数据确定的精确估计。留州参数的区间来自 **1000次训练模拟种子重采样**，未传播 IRS 参数和 ACS 调查抽样的不确定性。

β={beta['chosen_beta']:.4f} 是固定数值实现；训练种子重采样的区间为 **{beta['beta_seed_bootstrap_p025']:.4f}–{beta['beta_seed_bootstrap_p975']:.4f}**，说明四位小数用于复现，不代表统计精确到四位。

目的地效应的八州值另见 [parameters.json](reliable-calibration/parameters.json)。社会联系强度0.6/1.0/1.4、政策强度、人口机制、0.85拟合温度和0.90模拟温度等沿用明确的结构或情景假设，没有伪称本次已从观察数据估计。

## IRS 路线拟合方法

使用已从官方2022–2023 IRS数据重建的50条路线和88个州级输入。与原程序相同：四组大学/非大学与有孩/无孩混合概率，六个效用系数与七个目的地效应，报税迁移数平方根加权的份额均方误差，加上系数与目的地效应正则化，带原范围约束的 L-BFGS-B 优化。

为提高执行效率，使用解析梯度和向量计算。与原 pandas 实现的目标函数最大差 **{irs['original_objective_max_difference']:.3g}**；解析梯度与中心差分最大差 **{irs['gradient_max_difference']:.3g}**，均已检查。

在六个训练出发州进行留一出发州交叉验证，预先比较原惩罚强度的0.25、1、4倍。采用“一标准误规则”选择可接受候选中较强的正则化，结果选中 **{irs['selected_scale']}倍**；对应系数惩罚 λ={.02*irs['selected_scale']:.4g}，目的地效应惩罚 λ={.05*irs['selected_scale']:.4g}。先验数值和参数范围属于建模约束，不是官方统计直接给出的偏好参数。

随后只评估预先选好的候选，对历史指定的 IL/WA 留出集不再调参：

| 指标 | 原惩罚强度重新拟合 | CV选择候选 |
|---|---:|---:|
| 加权 RMSE | {hold['historical_regularization_refit']['weighted_rmse']:.6f} | {hold['cv_selected_training_fit']['weighted_rmse']:.6f} |
| 加权 MAE | {hold['historical_regularization_refit']['weighted_mae']:.6f} | {hold['cv_selected_training_fit']['weighted_mae']:.6f} |
| 相关系数 | {hold['historical_regularization_refit']['correlation']:.6f} | {hold['cv_selected_training_fit']['correlation']:.6f} |

候选通过既定采用规则后，使用全部八个出发州拟合最终参数；三组固定起点取损失较小解。重复同一起点优化的参数差为 **{irs['deterministic_optimizer_repeat_max_difference']}**。IRS 路线不专属于18–35岁，是宏观迁移方向代理；历史留出集已在以前开发中使用，因此不是新外部验证，也不能解释为个体因果效应。

## 当前模型的迁移率校准

目标来自先前已独立重建的2023 ACS PUMS，准确年龄18–35，PWGTP加权。主设置固定1000代理、20年、无政策、中等联系，训练种子 **901–916**，验证种子 **1901–1932**互不重叠。

在3.4–4.6的粗网格、最佳点附近0.025细网格和0.005精网格中，以训练均值距目标的绝对误差选参数。验证种子没有参与选择。训练均值 **{beta['training']['mean']:.6%}**，目标 **{target:.6%}**。

| 配置 | 32个独立模拟种子的均值 | 95%模拟区间 | 对ACS目标的绝对误差（百分点） |
|---|---:|---|---:|
| 原发布IRS参数与β=3.925 | {published['mean']:.5%} | {published['ci95_low']:.5%}–{published['ci95_high']:.5%} | {published['absolute_bias']*100:.6f} |
| 新IRS参数与β={beta['chosen_beta']:.4f} | {test['mean']:.5%} | {test['ci95_low']:.5%}–{test['ci95_high']:.5%} | {test['absolute_bias']*100:.6f} |

改善来自新的完整核心配置，不能只归因于β变化。实际又重新执行三个验证案例，全部输出最大差 **{beta['deterministic_repeat_max_difference']}**。核心网格、验证与初始规模检查共 **{beta['unique_simulations']} 个不同模拟案例**。

## 运行规模的适用性

| 设置 | 种子数 | 新配置平均迁移率 | 95%模拟区间 |
|---|---:|---:|---|
| 主设置1000代理×20年 | 32 | {test['mean']:.5%} | {test['ci95_low']:.5%}–{test['ci95_high']:.5%} |
| 600代理×12年 | 32 | {scale['mean']:.5%} | {scale['ci95_low']:.5%}–{scale['ci95_high']:.5%} |
| 2000代理×20年 | 8 | {beta['transfer_checks'][1]['mean']:.5%} | {beta['transfer_checks'][1]['ci95_low']:.5%}–{beta['transfer_checks'][1]['ci95_high']:.5%} |

**1000×20的β={beta['chosen_beta']:.4f}直接移用于600×12，扩展到32个种子后未通过检查**：目标不在95%模拟区间内，绝对偏差为{scale['absolute_bias']*100:.6f}个百分点。失败记录保留，不能把该参数称为所有规模通用的校准值。

因此为600×12建立单独协议，使用32个训练种子901–932，预先定义3.70–3.95、步长0.025的粗网格，最佳训练点附近步长0.005的精网格。选择仍只依赖训练均值；采用未用于选择参数的新验证种子3001–3032，并保留之前失败的2001–2032诊断。新的条件参数 **β={research['chosen_beta']:.4f}**；训练均值 **{research['training']['mean']:.6%}**。

32个新验证种子的平均迁移率 **{research['validation_new']['mean']:.6%}**，95%模拟区间 **{research['validation_new']['ci95_low']:.6%}–{research['validation_new']['ci95_high']:.6%}**，绝对偏差 **{research['validation_new']['absolute_bias']*100:.6f}个百分点**。采用与主设置相同的标准，训练检查 **{'通过' if research['training_criterion_passed'] else '未通过'}**，独立验证检查 **{'通过' if research['validation_criteria_passed'] else '未通过'}**。训练种子bootstrap区间 **{research['beta_seed_bootstrap_p025']:.4f}–{research['beta_seed_bootstrap_p975']:.4f}**；三个真实重跑案例最大差 **{research['deterministic_repeat_max_difference']}**。

这次失败暴露了运行设计敏感性与随机波动问题，不能单凭一次区间检验认定系统性的规模偏差，也不意味着现实人的偏好随代理数变化。两个设计的参数区间有重叠；同一β=3.8250在新的600×12验证种子上也得到{research['validation_primary_beta_control']['mean']:.6%}，说明选择某一验证批次会影响表面误差。600×12参数按对应设计保存，1000×20参数也仅在该设计下得到充分检查。2000×20目前只有八种子的初步诊断，其他代理数或年数需要另行验证。自动运行入口按设计选取已通过检查的参数，未知设计不静默套用。

![600×12独立校准与保留的失败诊断](reliable-calibration/research-design-evidence.png)

## 网络与开放系统的条件参数

网络校准使用600代理、12年、该设计的新β={research['chosen_beta']:.4f}、训练种子901–916；九步二分的访问点和最终中点按训练误差选最佳值，再统一最终四位小数。模拟目标带噪声，不假定误差严格单调。32个验证种子3001–3032未参与选择。这里是保持网络比较基准的模型控制，不是新的独立实证偏好估计。预定验证标准为与同种子封闭基线的平均差不超过0.10个百分点，配对差的95%区间包含0。

| 衰减 | 最终留州参数 | 训练迁移率 | 验证迁移率 | 与封闭基线配对均值差（百分点） | 验证 |
|---|---:|---:|---:|---:|---|
{ntable}

开放系统目标直接取重建 PUMS 的外部来源份额 **{ext['external_origin_target']:.8%}**，即884486 / 1425981；精确数据口径保留波多黎各来源，区别于整体迁移率锚点的排除口径。取代旧0.62近似值，但不改变分类口径。共享与扩容模式分别八步二分，在访问点和最终中点中按训练误差选择，再统一最终四位小数。

| 容量模式 | 最终交换尝试率 | 训练接受外部迁入份额 | 验证接受外部迁入份额 | 验证95%模拟区间 | 验证 |
|---|---:|---:|---:|---|---|
{otable}

这两个模式的交换率不是现实人口迁移率；它们是使该模拟机制匹配外部来源构成的条件控制参数。预定验证标准：绝对偏差不超过1.5个百分点，95%模拟区间覆盖外部来源目标。网络与开放系统共 **{ext['unique_simulations']} 个不同校准/验证案例**；另外三个网络/开放系统案例重新执行最大差 **{ext['repeat_max_difference']}**。未通过对应验证的扩展候选保留在报告中，但不写入自动默认注册表。

## 原47行精度差异的修复验证

在单独的 `precision-fix-project/` 中，只将原Notebook单元67、69的二分最终参数送入模拟前统一四位小数；二分迭代保持完整精度。保持原发布IRS参数及β=3.925，实际重跑 **{precision['published_setting_rows']}行、{precision['unique_simulations']}个不同案例、{precision['numeric_metrics_checked']}项指标**，与旧缓存不匹配数从244降到 **{precision['mismatch_count']}**。

这是证明精度修复能保留原发布结果的对照实验，**不是新参数的政策效果验证**。修复副本还保留此前已验证的开放系统CLI常量加载修正。[源单元补丁](reliable-calibration/precision-fix.patch)与[逐项结果](reliable-calibration/precision-fix-report.json)可审查。

## 可复现文件与执行

- [新参数注册表](reliable-calibration/parameters.json)：完整精度IRS参数、四位标量、目的地效应、来源哈希、运行版本、明确未拟合的假设。
- [原始来源清单](reliable-calibration/input-source-manifest.json)：先前核验时保存的官方下载链接与哈希，需与重建协议和年龄口径一起解释。
- [参数对照CSV](reliable-calibration/parameter-comparison.csv)、[全部IRS拟合记录](reliable-calibration/irs-fit-report.json)
- [核心校准协议](reliable-calibration/beta-protocol.json)、[全部网格](reliable-calibration/beta-grid.csv)、[独立验证记录](reliable-calibration/beta-fit-report.json)
- [扩展参数验证](reliable-calibration/extension-fit-report.json)、[跨规模诊断](reliable-calibration/extended-scale-report.json)
- [600×12单独校准协议](reliable-calibration/research-design-protocol.json)、[拟合与新种子验证](reliable-calibration/research-design-fit-report.json)
- [诊断Notebook](calibration-validation.ipynb)、[执行HTML](calibration-validation.html)（执行完成后生成）
- [实际CLI样例验证](reliable-calibration/runner-verification-report.json)：基线、组合政策、网络、开放系统均不从模拟检查点读取结果。
- 完整项目可从本 PR 下载，或使用本次交付的完整项目 ZIP；此脚本也会另行生成本地校准包。

固定环境：Python3.10.18、numpy2.2.6、pandas2.3.3、scipy1.15.3、matplotlib3.10.6、joblib1.5.3；工作线程限制为1，多案例使用8进程。`Reproduce-Calibration.ps1` 重做确定性IRS拟合并核对已有检查点；加 `-Fresh` 会备份检查点并真实重跑所有案例。检查点包含输入指纹；数据或参数改变时拒绝混用旧结果。

单案例入口：

```powershell
.venv/Scripts/python.exe run_reliable_case.py --case reliable-calibration/examples/baseline.json --output reliable-calibration/example-result.json
```

运行入口默认读取新注册配置并记录参数文件SHA256。原 Notebook 模型机制原文保持不变，通过显式参数和已核验的原数据CSV载入。包不含虚拟环境和约270MB原始下载，包含模型源、已重建数值输入、来源清单、完整检查点和依赖版本；它是校准验证包，不是已更新全部政策结果的论文项目。

## 答辩时可以说明的结论

“我们将观察数据拟合、模拟目标校准和情景假设明确分开。路线参数通过出发州分组交叉验证选择正则化，当前模型的留州参数使用独立重建的ACS目标与独立模拟种子验证。最终参数数值约定、输入版本和随机种子均保存，重复运行得到相同结果。参数可靠性仍受八州宏观数据、先验和模型结构限制，不能解释成唯一真实个体偏好或已验证的因果政策效果。”
'''
    (OUT/'calibration-report.md').write_text(md.replace('(reliable-calibration/','(').replace('(calibration-validation.','(../results/calibration-validation.').replace('(reliable-calibration.zip)','(../results/reliable-calibration.zip)'),encoding='utf-8');(RESULTS/'reliable-calibration-report.md').write_text(md,encoding='utf-8')
    html=mistune.create_markdown(plugins=['table'])(md)
    style='body{max-width:1180px;margin:32px auto;padding:0 24px;font:16px/1.7 system-ui;color:#15333e}h1,h2{line-height:1.3}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #c9d8df;padding:9px;vertical-align:top;text-align:left}th{background:#eef5f6}a{color:#006e72}img{max-width:100%}pre{overflow:auto;background:#eef4f5;padding:14px}code{background:#eef4f5}'
    (RESULTS/'reliable-calibration-report.html').write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>新参数校准与复现验证</title><style>'+style+'</style><body>'+html+'</body></html>',encoding='utf-8')
    examples=OUT/'examples';examples.mkdir(exist_ok=True)
    cases={'baseline':{'seed':1901,'n_agents':1000,'years':20},'combined':{'seed':201,'n_agents':600,'years':12,'policy':'combined','intensity':1.,'interaction':'medium'},
        'network':{'seed':1901,'n_agents':600,'years':12,'network_decay':2.,'recalibrated_network':True},
        'open-scaled':{'seed':1901,'n_agents':600,'years':12,'capacity_mode':'scaled','policy':'baseline','intensity':0.}}
    for name,case in cases.items():(examples/(name+'.json')).write_text(json.dumps(case,indent=2),encoding='utf-8')
    # A diagnostic Notebook uses only this new calibration evidence, then runs a
    # real new-profile case; it never relabels original policy caches as new.
    nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('# 新参数：校准与独立验证\n本文件验证新参数，不包含旧发布配置的政策结论。'),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image\nROOT=Path.cwd()\nOUT=ROOT/'reliable-calibration'\nparameters=json.loads((OUT/'parameters.json').read_text(encoding='utf-8'))\ndisplay(pd.read_csv(OUT/'parameter-comparison.csv'))"),
        nbformat.v4.new_code_cell("display(Image(filename=str(OUT/'calibration-evidence.png')))\nbeta=json.loads((OUT/'beta-fit-report.json').read_text())\ndisplay(pd.DataFrame([{'profile':'original',**beta['validation_published']},{'profile':'new',**beta['validation_new']}]))\nassert beta['training_criterion_passed'] and beta['validation_criteria_passed']"),
        nbformat.v4.new_code_cell("from reliable_worker import run\ncase={'profile':'new','seed':1901,'n_agents':1000,'years':20,'beta_current_state':parameters['beta_current_state']}\nlive=run(case)\nrecords=[json.loads(line) for line in (OUT/'beta-live.jsonl').read_text().splitlines()]\nprevious=next(r['result'] for r in records if r['case']==case)\ndifference=max(abs(live[k]-previous[k]) for k in live)\nassert difference<1e-12\nprint('Actual model repeat maximum difference:',difference)\nprint('Live migration rate:',live['move_rate'])"),
        nbformat.v4.new_code_cell("precision=json.loads((OUT/'precision-fix-report.json').read_text())\nassert precision['passed'] and precision['mismatch_count']==0\nprint('Canonical precision verification:',precision['published_setting_rows'],'rows;',precision['numeric_metrics_checked'],'metrics; zero differences')"),
        nbformat.v4.new_markdown_cell('这些验证是当前模型与观察锚点的条件匹配，以及重复运行一致性。模拟区间不包括调查采样误差，也不是因果政策效果的置信区间。新参数尚未用于重跑全部政策分析。')])
    nb.metadata['kernelspec']={'name':'cits4403-310','display_name':'Calibration Python 3.10.18','language':'python'}
    nb.cells.insert(-2,nbformat.v4.new_code_cell("research=json.loads((OUT/'research-design-fit-report.json').read_text())\nassert research['training_criterion_passed'] and research['validation_criteria_passed']\ncase={'profile':'new','seed':3001,'n_agents':600,'years':12,'beta_current_state':parameters['beta_by_design']['600x12']}\nlive=run(case)\nrecords=[json.loads(line) for line in (OUT/'research-design-live.jsonl').read_text().splitlines()]\nprevious=next(r['result'] for r in records if r['case']==case)\ndifference=max(abs(live[k]-previous[k]) for k in live)\nassert difference<1e-12\nprint('600x12 actual repeat maximum difference:',difference)\ndisplay(pd.DataFrame([research['validation_new']]))"))
    nbformat.write(nb,OUT/'calibration-validation.ipynb')
    dependencies=['numpy','pandas','scipy','matplotlib','joblib','nbformat','nbclient','nbconvert','ipykernel','mistune']
    (OUT/'requirements-calibration.txt').write_text('\n'.join(f'{p}=={importlib.metadata.version(p)}' for p in dependencies)+'\n',encoding='utf-8')
    delivery=RESULTS/'reliable-calibration';delivery.mkdir(exist_ok=True)
    for name in ['calibration-evidence.png','research-design-evidence.png','parameters.json','input-source-manifest.json','parameter-comparison.csv','irs-fit-report.json','beta-protocol.json','beta-grid.csv','beta-fit-report.json','extension-fit-report.json','extended-scale-report.json','research-design-protocol.json','research-design-fit-report.json','precision-fix.patch','precision-fix-report.json','runner-verification-report.json']:
        if (OUT/name).exists():shutil.copy2(OUT/name,delivery/name)
    (delivery/'calibration-report.md').write_text((OUT/'calibration-report.md').read_text(encoding='utf-8').replace('../results/','../'),encoding='utf-8')
    banner=f'<aside id="reliable-followup" style="padding:18px;background:#e6f4f1;color:#15333e;border:1px solid #4b8b80"><strong>新参数校准已完成：</strong>1000×20留州参数{beta["chosen_beta"]:.4f}与600×12参数{research["chosen_beta"]:.4f}分别经过32个独立种子检查；IRS历史保留评估改善；最终参数精度统一后752行全部匹配旧发布控制。新参数政策结论尚未全量重跑；旧表确切生成历史仍有来源限制。<a href="reliable-calibration-report.html">查看新参数与验证报告</a>。</aside>'
    for filename in ['raw-rebuild-report.html','legacy-origin-report.html','audit-report.html']:
        path=RESULTS/filename
        if not path.exists():continue
        text=path.read_text(encoding='utf-8')
        if 'id="reliable-followup"' not in text:path.write_text(text.replace('<body>','<body>'+banner,1),encoding='utf-8')
    path=RESULTS/'index.html'
    if not path.exists():path.write_text('<!doctype html><meta charset=\"utf-8\"><main><h1>Calibration results</h1></main>',encoding='utf-8')
    text=path.read_text(encoding='utf-8')
    if 'id="reliable-followup"' not in text:path.write_text(text.replace('<main>','<main>'+banner,1),encoding='utf-8')
    scripts=['fit_reliable_irs.py','calibrate_reliable_beta.py','extend_scale_validation.py','calibrate_research_design.py','calibrate_reliable_extensions.py','verify_canonical_precision.py',
        'calibration_precision.py','reliable_worker.py','run_reliable_case.py','make_reliable_delivery.py','execute_calibration_notebook.py',
        'raw_model.py','full_simulation_rebuild.py','verify_calibration_inputs.py','verify_reliable_runner.py','Reproduce-Calibration.ps1']
    with zipfile.ZipFile(RESULTS/'reliable-calibration.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in scripts:
            if (ROOT/name).exists():archive.write(ROOT/name,name)
        for p in OUT.rglob('*'):
            if p.is_file() and p.relative_to(OUT).parts[0]!='precision-fix-project' and not p.name.endswith('.bak'):
                archive.write(p,'reliable-calibration/'+p.relative_to(OUT).as_posix())
        for folder in [ROOT/'deployment/master',ROOT/'download/CITS4403-GROUP-PROJECT-master']:
            for p in folder.rglob('*'):
                if p.is_file() and '__pycache__' not in p.parts:archive.write(p,p.relative_to(ROOT).as_posix())
        for folder in [ROOT/'raw-rebuild/rebuilt',ROOT/'results/master/tables']:
            for p in folder.glob('*.csv'):archive.write(p,p.relative_to(ROOT).as_posix())
        for name in ['state-inputs-reconstructed.csv','irs-routes-reconstructed.csv','kernel-with-legacy.json','calibration-report.json','source-manifest.json']:
            archive.write(ROOT/'raw-rebuild'/name,'raw-rebuild/'+name)
        for p in RESULTS.glob('calibration-validation.*'):archive.write(p,'results/'+p.name)
        for name in ['reliable-calibration-report.html','reliable-calibration-report.md']:
            archive.write(RESULTS/name,'results/'+name)
        # The HTML report refers to assets under results/reliable-calibration/.
        for name in ['calibration-evidence.png','research-design-evidence.png','parameters.json','input-source-manifest.json','parameter-comparison.csv','irs-fit-report.json','beta-protocol.json','beta-grid.csv','beta-fit-report.json','extension-fit-report.json','extended-scale-report.json','research-design-protocol.json','research-design-fit-report.json','precision-fix.patch','precision-fix-report.json','runner-verification-report.json']:
            if not (OUT/name).exists():continue
            archive.write(OUT/name,'results/reliable-calibration/'+name)
        archive.writestr('README-calibration.md','Use Python 3.10.18, create .venv and install reliable-calibration/requirements-calibration.txt. Run Reproduce-Calibration.ps1 -Fresh to recompute all calibration cases. Calibration report and examples are in reliable-calibration/. The research source and original policy caches are included only as source and control provenance; they remain old-profile outputs. New-fit policy results have not been regenerated. The original repository and historical files are unchanged.\n')
    (OUT/'delivery-status.json').write_text(json.dumps({'parameters_exported':True,'training_passed':beta['training_criterion_passed'],
        'independent_simulation_validation_passed':beta['validation_criteria_passed'],'precision_752_rows_passed':precision['passed'],
        'research_design_validation_passed':research['validation_criteria_passed'],
        'network_validation_by_decay':{str(r['decay']):r['validation_criteria_passed'] for r in ext['network']},
        'open_validation_by_capacity':{r['capacity_mode']:r['validation_criteria_passed'] for r in ext['open']},
        'new_policy_grid_regenerated':False,'calibration_command_writes_git_remote':False,'environment':environment},indent=2),encoding='utf-8')
    print('Parameters, uncertainty report, reproducible runner and package ready',flush=True)

if __name__=='__main__':main()
