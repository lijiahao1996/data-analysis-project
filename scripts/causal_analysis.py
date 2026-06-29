# -*- coding: utf-8 -*-
"""
物流因果分析模块
核心方法：倾向得分匹配 (Propensity Score Matching, PSM)
研究问题：物流延迟是否因果性地降低了用户复购概率？
"""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from scipy.spatial import KDTree
import yaml

warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class CausalAnalyzer:
    """PSM 因果推断分析器"""

    def __init__(self, config: dict):
        self.config = config
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_dir = self.project_root / 'data' / 'processed'
        self.plot_dir = self.data_dir / 'plots'
        self.plot_dir.mkdir(parents=True, exist_ok=True)

        # PSM 参数
        psm_cfg = config.get('psm', {})
        self.caliper = psm_cfg.get('caliper', 0.05)
        self.bootstrap_n = psm_cfg.get('bootstrap_n', 100)

        # 结果存储
        self.results = {}

    def run(self):
        """执行完整 PSM 分析流程"""
        print("=" * 60)
        print("物流时效对复购的因果效应分析 (PSM)")
        print("=" * 60)

        # Step 1: 数据准备
        df = self._prepare_data()

        # Step 2: 描述性分析
        self._descriptive_analysis(df)

        # Step 3: 倾向得分估计
        df = self._estimate_propensity_score(df)

        # Step 4: 匹配
        matched_df = self._perform_matching(df)

        # Step 5: 平衡性检验
        self._balance_check(df, matched_df)

        # Step 6: ATT 估计
        self._estimate_att(matched_df)

        # Step 7: 敏感性分析
        self._sensitivity_analysis(matched_df)

        # Step 8: 业务 ROI 量化
        self._business_roi(df, matched_df)

        # 保存结果
        output_path = self.data_dir / 'causal_results.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n分析结果已保存至: {output_path}")

        return self.results

    def _prepare_data(self) -> pd.DataFrame:
        """Step 1: 数据准备 - 定义处理组/对照组/协变量"""
        print("\n[Step 1] 数据准备...")

        df = pd.read_parquet(self.data_dir / 'user_features.parquet')
        print(f"  原始用户数: {len(df)}")

        # 定义处理变量：是否经历过物流延迟
        df['treatment'] = (df['delayed_order_ratio'] > 0).astype(int)

        # 定义结果变量：是否复购
        df['is_repeat_purchaser'] = (df['total_orders'] > 1).astype(int)

        # 协变量编码
        covariates = ['total_spend', 'avg_review_score']
        categorical_cols = ['main_category', 'customer_state', 'main_payment_type']

        for col in categorical_cols:
            if col in df.columns:
                le = LabelEncoder()
                df[f'{col}_encoded'] = le.fit_transform(df[col].astype(str))
                covariates.append(f'{col}_encoded')

        # 去除缺失值
        all_cols = covariates + ['treatment', 'is_repeat_purchaser']
        df_clean = df.dropna(subset=all_cols).copy()
        print(f"  清洗后用户数: {len(df_clean)}")
        print(f"  处理组(延迟用户): {df_clean['treatment'].sum()}")
        print(f"  对照组(未延迟用户): {(df_clean['treatment'] == 0).sum()}")

        self.covariates = covariates
        self.results['sample_size'] = {
            'total': len(df_clean),
            'treatment': int(df_clean['treatment'].sum()),
            'control': int((df_clean['treatment'] == 0).sum())
        }

        return df_clean

    def _descriptive_analysis(self, df: pd.DataFrame):
        """Step 2: 描述性分析"""
        print("\n[Step 2] 描述性分析...")

        # 处理组 vs 对照组复购率
        repurchase_by_group = df.groupby('treatment')['is_repeat_purchaser'].mean()
        print(f"  对照组(未延迟)复购率: {repurchase_by_group.get(0, 0):.4f}")
        print(f"  处理组(延迟)复购率: {repurchase_by_group.get(1, 0):.4f}")
        print(f"  朴素差异: {repurchase_by_group.get(1, 0) - repurchase_by_group.get(0, 0):.4f}")

        self.results['descriptive'] = {
            'control_repurchase_rate': float(repurchase_by_group.get(0, 0)),
            'treatment_repurchase_rate': float(repurchase_by_group.get(1, 0)),
            'naive_difference': float(repurchase_by_group.get(1, 0) - repurchase_by_group.get(0, 0))
        }

        # 可视化
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 复购率对比柱状图
        groups = ['未延迟(对照组)', '有延迟(处理组)']
        rates = [repurchase_by_group.get(0, 0), repurchase_by_group.get(1, 0)]
        axes[0].bar(groups, rates, color=['#2ecc71', '#e74c3c'], alpha=0.8)
        axes[0].set_ylabel('复购率')
        axes[0].set_title('处理组 vs 对照组 复购率对比')
        for i, v in enumerate(rates):
            axes[0].text(i, v + 0.005, f'{v:.3f}', ha='center', fontsize=12)

        # 按延迟程度分组复购率
        if 'avg_delay_days' in df.columns:
            bins = [-np.inf, 0, 3, 7, np.inf]
            labels = ['准时', '轻微延迟\n(1-3天)', '中度延迟\n(3-7天)', '严重延迟\n(>7天)']
            df['delay_group'] = pd.cut(df['avg_delay_days'], bins=bins, labels=labels)
            delay_rates = df.groupby('delay_group', observed=False)['is_repeat_purchaser'].mean()
            axes[1].bar(delay_rates.index, delay_rates.values, color=['#2ecc71', '#f39c12', '#e67e22', '#e74c3c'], alpha=0.8)
            axes[1].set_ylabel('复购率')
            axes[1].set_title('不同延迟程度的复购率')
            for i, v in enumerate(delay_rates.values):
                axes[1].text(i, v + 0.005, f'{v:.3f}', ha='center', fontsize=10)
        else:
            axes[1].text(0.5, 0.5, '无延迟天数数据', ha='center', va='center', transform=axes[1].transAxes)

        plt.tight_layout()
        plt.savefig(self.plot_dir / 'causal_descriptive.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  描述性分析图表已保存")

    def _estimate_propensity_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 3: 倾向得分估计"""
        print("\n[Step 3] 倾向得分估计...")

        X = df[self.covariates].values
        y = df['treatment'].values

        # Logistic Regression 估计倾向得分
        lr = LogisticRegression(max_iter=1000, random_state=42)
        lr.fit(X, y)
        df = df.copy()
        df['propensity_score'] = lr.predict_proba(X)[:, 1]

        # Positivity 检查
        ps = df['propensity_score']
        positivity_ratio = ((ps > 0.1) & (ps < 0.9)).mean()
        print(f"  倾向得分 positivity (0.1 < PS < 0.9): {positivity_ratio:.4f}")

        self.results['propensity_score'] = {
            'positivity_ratio': float(positivity_ratio),
            'mean_treatment': float(df.loc[df['treatment'] == 1, 'propensity_score'].mean()),
            'mean_control': float(df.loc[df['treatment'] == 0, 'propensity_score'].mean())
        }

        # 倾向得分分布图
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(df.loc[df['treatment'] == 0, 'propensity_score'], bins=50,
                alpha=0.6, label='对照组(未延迟)', color='#2ecc71', density=True)
        ax.hist(df.loc[df['treatment'] == 1, 'propensity_score'], bins=50,
                alpha=0.6, label='处理组(延迟)', color='#e74c3c', density=True)
        ax.set_xlabel('倾向得分 (Propensity Score)')
        ax.set_ylabel('密度')
        ax.set_title('倾向得分分布: 处理组 vs 对照组')
        ax.legend()
        plt.tight_layout()
        plt.savefig(self.plot_dir / 'propensity_score_dist.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  倾向得分分布图已保存")

        return df

    def _perform_matching(self, df: pd.DataFrame) -> pd.DataFrame:
        """Step 4: 最近邻匹配 1:1"""
        print("\n[Step 4] 倾向得分匹配...")

        treatment_df = df[df['treatment'] == 1].copy()
        control_df = df[df['treatment'] == 0].copy()

        caliper = self.caliper

        # 使用 KDTree 进行最近邻匹配
        control_ps = control_df['propensity_score'].values.reshape(-1, 1)
        tree = KDTree(control_ps)

        matched_treatment_idx = []
        matched_control_idx = []
        used_control = set()

        treatment_ps = treatment_df['propensity_score'].values
        treatment_indices = treatment_df.index.tolist()
        control_indices = control_df.index.tolist()

        for i, ps_val in enumerate(treatment_ps):
            dist, idx = tree.query([ps_val], k=min(10, len(control_ps)))
            # 找到距离在 caliper 内且未被使用的最近邻
            for d, j in zip(dist[0] if len(dist.shape) > 1 else dist,
                           idx[0] if len(idx.shape) > 1 else idx):
                if d <= caliper and j not in used_control:
                    matched_treatment_idx.append(treatment_indices[i])
                    matched_control_idx.append(control_indices[j])
                    used_control.add(j)
                    break

        match_rate = len(matched_treatment_idx) / len(treatment_df)
        print(f"  Caliper = {caliper}, 匹配率: {match_rate:.4f}")

        # 如果匹配率 < 50%，自动放宽 caliper
        if match_rate < 0.5:
            caliper = 0.1
            print(f"  匹配率过低，放宽 caliper 至 {caliper}")
            matched_treatment_idx = []
            matched_control_idx = []
            used_control = set()

            for i, ps_val in enumerate(treatment_ps):
                dist, idx = tree.query([ps_val], k=min(10, len(control_ps)))
                for d, j in zip(dist[0] if len(dist.shape) > 1 else dist,
                               idx[0] if len(idx.shape) > 1 else idx):
                    if d <= caliper and j not in used_control:
                        matched_treatment_idx.append(treatment_indices[i])
                        matched_control_idx.append(control_indices[j])
                        used_control.add(j)
                        break

            match_rate = len(matched_treatment_idx) / len(treatment_df)
            print(f"  放宽后匹配率: {match_rate:.4f}")

        # 构建匹配后数据集
        matched_t = df.loc[matched_treatment_idx].copy()
        matched_t['match_group'] = 'treatment'
        matched_c = df.loc[matched_control_idx].copy()
        matched_c['match_group'] = 'control'
        matched_df = pd.concat([matched_t, matched_c], ignore_index=True)

        print(f"  匹配成功对数: {len(matched_treatment_idx)}")

        self.results['matching'] = {
            'caliper': caliper,
            'match_rate': float(match_rate),
            'matched_pairs': len(matched_treatment_idx)
        }

        return matched_df

    def _balance_check(self, df_before: pd.DataFrame, df_after: pd.DataFrame):
        """Step 5: 平衡性检验 (SMD + Love Plot)"""
        print("\n[Step 5] 平衡性检验...")

        smd_before = {}
        smd_after = {}

        for cov in self.covariates:
            # 匹配前 SMD
            t_before = df_before.loc[df_before['treatment'] == 1, cov]
            c_before = df_before.loc[df_before['treatment'] == 0, cov]
            pooled_std = np.sqrt((t_before.var() + c_before.var()) / 2)
            if pooled_std > 0:
                smd_before[cov] = abs(t_before.mean() - c_before.mean()) / pooled_std
            else:
                smd_before[cov] = 0

            # 匹配后 SMD
            t_after = df_after.loc[df_after['match_group'] == 'treatment', cov]
            c_after = df_after.loc[df_after['match_group'] == 'control', cov]
            pooled_std_after = np.sqrt((t_after.var() + c_after.var()) / 2)
            if pooled_std_after > 0:
                smd_after[cov] = abs(t_after.mean() - c_after.mean()) / pooled_std_after
            else:
                smd_after[cov] = 0

        # 输出平衡性结果
        print(f"  {'协变量':<25} {'匹配前SMD':<12} {'匹配后SMD':<12} {'平衡?'}")
        print("  " + "-" * 60)
        for cov in self.covariates:
            balanced = "Y" if smd_after[cov] < 0.1 else "N"
            print(f"  {cov:<25} {smd_before[cov]:<12.4f} {smd_after[cov]:<12.4f} {balanced}")

        self.results['balance_check'] = {
            'smd_before': {k: float(v) for k, v in smd_before.items()},
            'smd_after': {k: float(v) for k, v in smd_after.items()},
            'all_balanced': all(v < 0.1 for v in smd_after.values())
        }

        # Love Plot
        fig, ax = plt.subplots(figsize=(10, 6))
        y_pos = np.arange(len(self.covariates))
        before_vals = [smd_before[c] for c in self.covariates]
        after_vals = [smd_after[c] for c in self.covariates]

        ax.barh(y_pos - 0.2, before_vals, 0.4, label='匹配前', color='#e74c3c', alpha=0.7)
        ax.barh(y_pos + 0.2, after_vals, 0.4, label='匹配后', color='#2ecc71', alpha=0.7)
        ax.axvline(x=0.1, color='black', linestyle='--', label='平衡阈值(0.1)')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(self.covariates)
        ax.set_xlabel('标准化均值差 (SMD)')
        ax.set_title('Love Plot: 匹配前后协变量平衡性')
        ax.legend()
        plt.tight_layout()
        plt.savefig(self.plot_dir / 'love_plot.png', dpi=150, bbox_inches='tight')
        plt.close()
        print("  Love Plot 已保存")

    def _estimate_att(self, matched_df: pd.DataFrame):
        """Step 6: ATT 估计 + Bootstrap 置信区间"""
        print("\n[Step 6] ATT 估计...")

        treatment_outcome = matched_df.loc[matched_df['match_group'] == 'treatment', 'is_repeat_purchaser']
        control_outcome = matched_df.loc[matched_df['match_group'] == 'control', 'is_repeat_purchaser']

        att = treatment_outcome.mean() - control_outcome.mean()
        print(f"  ATT (处理组平均处理效应): {att:.4f}")

        # Bootstrap 置信区间
        np.random.seed(42)
        bootstrap_atts = []
        n_pairs = len(treatment_outcome)

        for _ in range(self.bootstrap_n):
            # 有放回重采样
            idx = np.random.choice(n_pairs, size=n_pairs, replace=True)
            t_sample = treatment_outcome.iloc[idx].mean()
            c_sample = control_outcome.iloc[idx].mean()
            bootstrap_atts.append(t_sample - c_sample)

        ci_lower = np.percentile(bootstrap_atts, 2.5)
        ci_upper = np.percentile(bootstrap_atts, 97.5)

        print(f"  95% CI: [{ci_lower:.4f}, {ci_upper:.4f}]")
        print(f"  结论: 物流延迟使复购概率{'降低' if att < 0 else '提高'} {abs(att)*100:.2f} 个百分点")

        self.results['att'] = {
            'att': float(att),
            'ci_lower': float(ci_lower),
            'ci_upper': float(ci_upper),
            'treatment_mean': float(treatment_outcome.mean()),
            'control_mean': float(control_outcome.mean()),
            'conclusion': f"物流延迟使复购概率{'降低' if att < 0 else '提高'} {abs(att)*100:.2f} 个百分点 (95% CI: [{ci_lower:.4f}, {ci_upper:.4f}])"
        }

    def _sensitivity_analysis(self, matched_df: pd.DataFrame):
        """Step 7: Rosenbaum bounds 敏感性分析（简化版）"""
        print("\n[Step 7] 敏感性分析 (Rosenbaum Bounds)...")

        treatment_outcome = matched_df.loc[matched_df['match_group'] == 'treatment', 'is_repeat_purchaser'].values
        control_outcome = matched_df.loc[matched_df['match_group'] == 'control', 'is_repeat_purchaser'].values

        n_pairs = min(len(treatment_outcome), len(control_outcome))
        # 计算配对差异
        diffs = treatment_outcome[:n_pairs] - control_outcome[:n_pairs]
        n_discordant = np.sum(diffs != 0)
        n_positive = np.sum(diffs > 0)

        gamma_values = [1.0, 1.25, 1.5, 2.0]
        sensitivity_results = []

        print(f"  {'Gamma':<10} {'p值上界':<15} {'结论'}")
        print("  " + "-" * 50)

        for gamma in gamma_values:
            # 简化的 Rosenbaum bounds
            # 在 Gamma 偏差下，处理组被分配到处理的概率上界
            p_upper = gamma / (1 + gamma)
            # 期望正差异数的上界
            expected_positive = n_discordant * p_upper
            # 标准差
            std = np.sqrt(n_discordant * p_upper * (1 - p_upper))

            if std > 0:
                # z 统计量
                z = (n_positive - expected_positive) / std
                # 单侧 p 值上界
                from scipy.stats import norm
                p_value = 1 - norm.cdf(z)
            else:
                p_value = 0.5

            significant = "显著" if p_value < 0.05 else "不显著"
            sensitivity_results.append({
                'gamma': gamma,
                'p_upper_bound': float(p_value),
                'significant': p_value < 0.05
            })
            print(f"  {gamma:<10} {p_value:<15.4f} {significant}")

        # 判断结果稳健性
        gamma_15_result = next((r for r in sensitivity_results if r['gamma'] == 1.5), None)
        if gamma_15_result and not gamma_15_result['significant']:
            robustness = "结果对未观测混淆因素敏感，需谨慎解读"
        else:
            robustness = "结果在 Gamma=1.5 水平下仍显著，具有较好的稳健性"
        print(f"\n  稳健性判断: {robustness}")

        self.results['sensitivity'] = {
            'rosenbaum_bounds': sensitivity_results,
            'robustness_conclusion': robustness
        }

    def _business_roi(self, df: pd.DataFrame, matched_df: pd.DataFrame):
        """Step 8: 业务 ROI 量化"""
        print("\n[Step 8] 业务 ROI 量化...")

        att = self.results['att']['att']
        n_delayed_users = int(df['treatment'].sum())
        avg_customer_value = float(df['total_spend'].mean())

        # 假设物流优化可减少不同比例的延迟率
        optimization_scenarios = [0.3, 0.5, 0.7]  # 减少30%/50%/70%延迟

        roi_table = []
        print(f"  当前延迟用户数: {n_delayed_users}")
        print(f"  ATT (因果效应): {att:.4f}")
        print(f"  平均客户价值: ¥{avg_customer_value:.2f}")
        print(f"\n  {'优化比例':<12} {'挽回用户数':<12} {'增量收入(¥)':<15}")
        print("  " + "-" * 45)

        for ratio in optimization_scenarios:
            rescued_users = int(n_delayed_users * abs(att) * ratio)
            incremental_revenue = rescued_users * avg_customer_value
            roi_table.append({
                'optimization_ratio': ratio,
                'rescued_users': rescued_users,
                'incremental_revenue': float(incremental_revenue)
            })
            print(f"  {ratio*100:.0f}%{'':<9} {rescued_users:<12} ¥{incremental_revenue:,.2f}")

        self.results['roi'] = {
            'delayed_users': n_delayed_users,
            'avg_customer_value': avg_customer_value,
            'att_effect': float(att),
            'scenarios': roi_table
        }


if __name__ == "__main__":
    # 加载配置
    config_path = Path(__file__).resolve().parent.parent / 'config.yaml'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        # 默认配置
        config = {
            'psm': {
                'caliper': 0.05,
                'bootstrap_n': 100
            }
        }

    analyzer = CausalAnalyzer(config)
    results = analyzer.run()
