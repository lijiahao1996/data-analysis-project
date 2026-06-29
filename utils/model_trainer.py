# -*- coding: utf-8 -*-
"""
多模型流失预测训练器
支持 Logistic Regression / Random Forest / XGBoost 三模型对比训练
包含 SMOTE 过采样、交叉验证、特征重要性分析、可视化输出
"""

import logging
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from imblearn.over_sampling import SMOTE
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelTrainer:
    """多模型流失预测训练器"""

    def __init__(self, config: dict):
        """
        Parameters
        ----------
        config : dict
            配置字典，需包含:
            - model.random_state: 随机种子
            - model.test_size: 测试集比例（默认0.2）
        """
        self.config = config
        self.random_state = config.get('model', {}).get('random_state', 42)
        self.test_size = config.get('model', {}).get('test_size', 0.2)
        self.models = {}
        self.results = {}
        self.best_model = None
        self.best_model_name = None
        self.feature_names = None
        self.label_encoders = {}

    def run(self):
        """执行完整的模型训练流程"""
        logger.info("=" * 60)
        logger.info("开始多模型流失预测训练流程")
        logger.info("=" * 60)

        # Step 1: 加载数据
        df = self._load_data()

        # Step 2-3: 特征工程
        X, y = self._feature_engineering(df)

        # Step 4: 划分训练/测试集
        X_train, X_test, y_train, y_test = self._split_data(X, y)

        # Step 5: SMOTE 过采样
        X_train_resampled, y_train_resampled = self._apply_smote(X_train, y_train)

        # Step 6: 定义模型
        self._define_models(y_train)

        # Step 7: 交叉验证
        cv_results = self._cross_validate(X_train_resampled, y_train_resampled)

        # Step 8: 测试集评估
        test_results = self._evaluate_on_test(X_train_resampled, y_train_resampled, X_test, y_test)

        # Step 9: 特征重要性
        feature_importances = self._get_feature_importances(X_train_resampled, y_train_resampled)

        # Step 10: 选择最优模型
        self._select_best_model(test_results)

        # Step 11: 保存最优模型
        self._save_best_model()

        # Step 12: 保存对比结果
        self._save_comparison_results(cv_results, test_results)

        # Step 13: 生成可视化
        self._generate_visualizations(test_results, feature_importances)

        logger.info("=" * 60)
        logger.info(f"训练流程完成！最优模型: {self.best_model_name}")
        logger.info("=" * 60)

        return self.results

    def _load_data(self) -> pd.DataFrame:
        """Step 1: 读取用户特征数据"""
        data_path = BASE_DIR / 'data' / 'processed' / 'user_features.parquet'
        logger.info(f"正在加载数据: {data_path}")

        df = pd.read_parquet(data_path)
        logger.info(f"数据加载完成，形状: {df.shape}")
        logger.info(f"流失用户占比: {df['is_churned'].mean():.2%}")
        return df

    def _feature_engineering(self, df: pd.DataFrame):
        """Step 2-3: 特征选择与编码"""
        logger.info("开始特征工程...")

        # 排除不参与建模的列
        exclude_cols = []

        # 排除 ID 列（包含 id, customer 等关键字的列）
        id_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['id', 'customer_unique'])]
        exclude_cols.extend(id_cols)

        # 排除日期列
        date_cols = [c for c in df.columns if df[c].dtype == 'datetime64[ns]' or 'date' in c.lower()]
        exclude_cols.extend(date_cols)

        # 排除目标变量
        target_col = 'is_churned'
        exclude_cols.append(target_col)

        # 排除分类标签列（如 rfm_segment 等非特征的衍生标签）
        label_cols = [c for c in df.columns if any(kw in c.lower() for kw in ['segment', 'label', 'cluster', 'group'])]
        exclude_cols.extend(label_cols)

        exclude_cols = list(set(exclude_cols))
        feature_cols = [c for c in df.columns if c not in exclude_cols]

        logger.info(f"排除列 ({len(exclude_cols)}): {exclude_cols}")
        logger.info(f"特征列 ({len(feature_cols)}): {feature_cols[:10]}...")

        X = df[feature_cols].copy()
        y = df[target_col].copy()

        # 处理分类特征：LabelEncoder
        cat_cols = X.select_dtypes(include=['object', 'category']).columns.tolist()
        logger.info(f"分类特征: {cat_cols}")

        for col in cat_cols:
            le = LabelEncoder()
            X[col] = X[col].fillna('unknown')
            X[col] = le.fit_transform(X[col].astype(str))
            self.label_encoders[col] = le

        # 填充缺失值
        X = X.fillna(0)

        self.feature_names = X.columns.tolist()
        logger.info(f"最终特征数量: {len(self.feature_names)}")

        return X, y

    def _split_data(self, X, y):
        """Step 4: 分层划分训练/测试集"""
        logger.info(f"划分数据集 (test_size={self.test_size})")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.test_size,
            stratify=y,
            random_state=self.random_state
        )

        logger.info(f"训练集: {X_train.shape[0]} 样本, 流失率: {y_train.mean():.2%}")
        logger.info(f"测试集: {X_test.shape[0]} 样本, 流失率: {y_test.mean():.2%}")

        return X_train, X_test, y_train, y_test

    def _apply_smote(self, X_train, y_train):
        """Step 5: SMOTE 过采样处理类别不平衡（仅训练集）"""
        logger.info("应用 SMOTE 过采样...")

        smote = SMOTE(random_state=self.random_state)
        X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

        logger.info(f"SMOTE 前: {len(y_train)} 样本 (正: {y_train.sum()}, 负: {(~y_train.astype(bool)).sum()})")
        logger.info(f"SMOTE 后: {len(y_resampled)} 样本 (正: {y_resampled.sum()}, 负: {(~y_resampled.astype(bool)).sum()})")

        return X_resampled, y_resampled

    def _define_models(self, y_train):
        """Step 6: 定义三个候选模型"""
        # 自动计算正负样本权重比（用于 XGBoost）
        neg_count = (y_train == 0).sum()
        pos_count = (y_train == 1).sum()
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0

        self.models = {
            'Logistic Regression': LogisticRegression(
                C=1.0,
                max_iter=1000,
                class_weight='balanced',
                random_state=self.random_state
            ),
            'Random Forest': RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                class_weight='balanced',
                n_jobs=-1,
                random_state=self.random_state
            ),
            'XGBoost': XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                scale_pos_weight=scale_pos_weight,
                random_state=self.random_state,
                use_label_encoder=False,
                eval_metric='logloss'
            )
        }

        logger.info(f"已定义 {len(self.models)} 个模型")
        logger.info(f"XGBoost scale_pos_weight = {scale_pos_weight:.2f}")

    def _cross_validate(self, X_train, y_train) -> dict:
        """Step 7: 5折分层交叉验证"""
        logger.info("开始 5 折分层交叉验证...")

        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        cv_results = {}

        scoring_metrics = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']

        for name, model in self.models.items():
            logger.info(f"\n{'─' * 40}")
            logger.info(f"交叉验证: {name}")
            model_scores = {}

            for metric in scoring_metrics:
                scores = cross_val_score(
                    model, X_train, y_train,
                    cv=skf, scoring=metric, n_jobs=-1
                )
                model_scores[metric] = {
                    'mean': scores.mean(),
                    'std': scores.std()
                }
                logger.info(f"  {metric}: {scores.mean():.4f} (+/- {scores.std():.4f})")

            cv_results[name] = model_scores

        return cv_results

    def _evaluate_on_test(self, X_train, y_train, X_test, y_test) -> dict:
        """Step 8: 在测试集上生成详细评估报告"""
        logger.info("\n开始测试集评估...")

        test_results = {}

        for name, model in self.models.items():
            logger.info(f"\n{'─' * 40}")
            logger.info(f"测试集评估: {name}")

            # 训练模型
            model.fit(X_train, y_train)

            # 预测
            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]

            # 计算指标
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred),
                'recall': recall_score(y_test, y_pred),
                'f1': f1_score(y_test, y_pred),
                'auc_roc': roc_auc_score(y_test, y_prob)
            }

            # 分类报告
            report = classification_report(y_test, y_pred, output_dict=True)

            # 混淆矩阵
            cm = confusion_matrix(y_test, y_pred)

            # ROC 曲线数据
            fpr, tpr, thresholds = roc_curve(y_test, y_prob)

            test_results[name] = {
                'metrics': metrics,
                'report': report,
                'confusion_matrix': cm,
                'roc_curve': {'fpr': fpr, 'tpr': tpr},
                'y_pred': y_pred,
                'y_prob': y_prob
            }

            logger.info(f"  Accuracy:  {metrics['accuracy']:.4f}")
            logger.info(f"  Precision: {metrics['precision']:.4f}")
            logger.info(f"  Recall:    {metrics['recall']:.4f}")
            logger.info(f"  F1:        {metrics['f1']:.4f}")
            logger.info(f"  AUC-ROC:   {metrics['auc_roc']:.4f}")

        return test_results

    def _get_feature_importances(self, X_train, y_train) -> dict:
        """Step 9: 获取各模型特征重要性"""
        logger.info("\n计算特征重要性...")

        feature_importances = {}

        for name, model in self.models.items():
            if name == 'Logistic Regression':
                # LR: 标准化系数绝对值
                importances = np.abs(model.coef_[0])
            elif name == 'Random Forest':
                importances = model.feature_importances_
            elif name == 'XGBoost':
                importances = model.feature_importances_
            else:
                continue

            fi_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': importances
            }).sort_values('importance', ascending=False)

            feature_importances[name] = fi_df
            logger.info(f"\n{name} Top 5 特征:")
            for _, row in fi_df.head(5).iterrows():
                logger.info(f"  {row['feature']}: {row['importance']:.4f}")

        return feature_importances

    def _select_best_model(self, test_results: dict):
        """Step 10: 按 AUC-ROC 选择最优模型"""
        logger.info("\n选择最优模型（按 AUC-ROC）...")

        auc_scores = {
            name: result['metrics']['auc_roc']
            for name, result in test_results.items()
        }

        self.best_model_name = max(auc_scores, key=auc_scores.get)
        self.best_model = self.models[self.best_model_name]

        logger.info(f"各模型 AUC-ROC:")
        for name, score in sorted(auc_scores.items(), key=lambda x: x[1], reverse=True):
            marker = " ★ BEST" if name == self.best_model_name else ""
            logger.info(f"  {name}: {score:.4f}{marker}")

    def _save_best_model(self):
        """Step 11: 保存最优模型"""
        models_dir = BASE_DIR / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)

        model_path = models_dir / 'best_churn_model.pkl'
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': self.best_model,
                'model_name': self.best_model_name,
                'feature_names': self.feature_names,
                'label_encoders': self.label_encoders
            }, f)

        logger.info(f"最优模型已保存: {model_path}")

    def _save_comparison_results(self, cv_results: dict, test_results: dict):
        """Step 12: 保存模型对比结果到 CSV"""
        rows = []
        for name in self.models.keys():
            row = {'model': name}
            # 交叉验证结果
            for metric, scores in cv_results[name].items():
                row[f'cv_{metric}_mean'] = scores['mean']
                row[f'cv_{metric}_std'] = scores['std']
            # 测试集结果
            for metric, value in test_results[name]['metrics'].items():
                row[f'test_{metric}'] = value
            rows.append(row)

        comparison_df = pd.DataFrame(rows)
        output_path = BASE_DIR / 'data' / 'processed' / 'model_comparison.csv'
        output_path.parent.mkdir(parents=True, exist_ok=True)
        comparison_df.to_csv(output_path, index=False, encoding='utf-8-sig')

        logger.info(f"模型对比结果已保存: {output_path}")

    def _generate_visualizations(self, test_results: dict, feature_importances: dict):
        """Step 13: 生成所有可视化图表"""
        plots_dir = BASE_DIR / 'data' / 'processed' / 'plots'
        plots_dir.mkdir(parents=True, exist_ok=True)

        self._plot_roc_comparison(test_results, plots_dir)
        self._plot_feature_importance(feature_importances, plots_dir)
        self._plot_confusion_matrices(test_results, plots_dir)

        logger.info("所有可视化图表生成完成")

    def _plot_roc_comparison(self, test_results: dict, plots_dir: Path):
        """ROC 曲线对比图"""
        fig, ax = plt.subplots(figsize=(10, 8))

        colors = ['#2196F3', '#4CAF50', '#FF5722']
        for (name, result), color in zip(test_results.items(), colors):
            fpr = result['roc_curve']['fpr']
            tpr = result['roc_curve']['tpr']
            auc_score = result['metrics']['auc_roc']
            ax.plot(fpr, tpr, color=color, lw=2,
                    label=f'{name} (AUC={auc_score:.4f})')

        ax.plot([0, 1], [0, 1], 'k--', lw=1, label='随机基线')
        ax.set_xlabel('假阳性率 (FPR)', fontsize=12)
        ax.set_ylabel('真阳性率 (TPR)', fontsize=12)
        ax.set_title('ROC 曲线对比 - 流失预测模型', fontsize=14)
        ax.legend(loc='lower right', fontsize=11)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        save_path = plots_dir / 'roc_comparison.png'
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"ROC 曲线已保存: {save_path}")

    def _plot_feature_importance(self, feature_importances: dict, plots_dir: Path):
        """特征重要性 Top15 对比图"""
        fig, axes = plt.subplots(1, 3, figsize=(20, 8))

        for ax, (name, fi_df) in zip(axes, feature_importances.items()):
            top15 = fi_df.head(15)
            sns.barplot(data=top15, x='importance', y='feature', ax=ax, palette='viridis')
            ax.set_title(f'{name}\n特征重要性 Top15', fontsize=12)
            ax.set_xlabel('重要性', fontsize=10)
            ax.set_ylabel('')

        plt.suptitle('各模型特征重要性对比', fontsize=14, y=1.02)
        plt.tight_layout()
        save_path = plots_dir / 'feature_importance.png'
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"特征重要性图已保存: {save_path}")

    def _plot_confusion_matrices(self, test_results: dict, plots_dir: Path):
        """混淆矩阵可视化"""
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))

        for ax, (name, result) in zip(axes, test_results.items()):
            cm = result['confusion_matrix']
            sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                        xticklabels=['未流失', '已流失'],
                        yticklabels=['未流失', '已流失'])
            ax.set_title(f'{name}\n混淆矩阵', fontsize=12)
            ax.set_xlabel('预测标签', fontsize=10)
            ax.set_ylabel('真实标签', fontsize=10)

        plt.suptitle('各模型混淆矩阵对比', fontsize=14)
        plt.tight_layout()
        save_path = plots_dir / 'confusion_matrix.png'
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        logger.info(f"混淆矩阵图已保存: {save_path}")


if __name__ == "__main__":
    # 默认配置
    default_config = {
        'model': {
            'random_state': 42,
            'test_size': 0.2
        }
    }

    trainer = ModelTrainer(config=default_config)
    trainer.run()
