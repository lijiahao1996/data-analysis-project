#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
优品汇电商经营分析 Pipeline 主入口
用法: python main.py --step [clean|feature|churn|model|causal|review|business|all]
"""

import argparse
import sys
import logging
from pathlib import Path
import yaml
import time

BASE_DIR = Path(__file__).parent

# 配置日志
def setup_logging(config):
    """配置日志系统"""
    log_dir = BASE_DIR / config.get('output', {}).get('logs_dir', 'logs')
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, config.get('logging', {}).get('level', 'INFO')),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'pipeline.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger(__name__)


def load_config() -> dict:
    """加载配置文件"""
    config_path = BASE_DIR / "config.yaml"
    if not config_path.exists():
        print(f"错误: 配置文件不存在 {config_path}")
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class Pipeline:
    """分析 Pipeline 主类"""

    def __init__(self, config: dict):
        self.config = config
        from utils.db_connector import get_engine
        self.engine = get_engine(config)
        self.processed_dir = BASE_DIR / config['data']['processed_dir']
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def step_clean(self):
        """Step 1: 数据清洗"""
        logger.info("=" * 60)
        logger.info("Step 1: 数据清洗")
        logger.info("=" * 60)
        from utils.data_cleaner import DataCleaner
        cleaner = DataCleaner(self.config, engine=self.engine)
        cleaner.run()
        logger.info("  数据清洗完成")

    def step_feature(self):
        """Step 2: 特征工程"""
        logger.info("=" * 60)
        logger.info("Step 2: 特征工程")
        logger.info("=" * 60)
        from utils.feature_builder import FeatureBuilder
        builder = FeatureBuilder(self.config, engine=self.engine)
        builder.run()
        logger.info("  特征工程完成")

    def step_churn(self):
        """Step 3: 流失标签构建"""
        logger.info("=" * 60)
        logger.info("Step 3: 流失标签构建 (P75x2规则)")
        logger.info("=" * 60)
        from scripts.churn_label_builder import ChurnLabelBuilder
        builder = ChurnLabelBuilder(self.config)
        builder.run()
        logger.info("  流失标签构建完成")

    def step_model(self):
        """Step 4: 流失预测建模"""
        logger.info("=" * 60)
        logger.info("Step 4: 多模型流失预测")
        logger.info("=" * 60)
        from utils.model_trainer import ModelTrainer
        trainer = ModelTrainer(self.config)
        trainer.run()
        logger.info("  模型训练完成")

    def step_causal(self):
        """Step 5: 因果推断分析"""
        logger.info("=" * 60)
        logger.info("Step 5: 物流因果分析 (PSM)")
        logger.info("=" * 60)
        from scripts.causal_analysis import CausalAnalyzer
        analyzer = CausalAnalyzer(self.config)
        analyzer.run()
        logger.info("  因果分析完成")

    def step_review(self):
        """Step 6: 评论分析"""
        logger.info("=" * 60)
        logger.info("Step 6: 评论评分维度分析")
        logger.info("=" * 60)
        from scripts.review_analysis import ReviewAnalyzer
        analyzer = ReviewAnalyzer(self.config, engine=self.engine)
        analyzer.run()
        logger.info("  评论分析完成")

    def step_business(self):
        """Step 7: 经营分析"""
        logger.info("=" * 60)
        logger.info("Step 7: 经营分析与KPI计算")
        logger.info("=" * 60)
        from scripts.business_analysis import BusinessAnalyzer
        analyzer = BusinessAnalyzer(self.config, engine=self.engine)
        analyzer.run()
        logger.info("  经营分析完成")

    def run_all(self):
        """执行完整 Pipeline"""
        start_time = time.time()
        logger.info("[启动] 开始完整分析 Pipeline")
        logger.info(f"项目: {self.config['project']['name']}")
        logger.info(f"数据库: MySQL - {self.config['database']['host']}:{self.config['database']['port']}/{self.config['database']['database']}")

        self.step_clean()
        self.step_feature()
        self.step_churn()
        self.step_model()
        self.step_causal()
        self.step_review()
        self.step_business()

        elapsed = time.time() - start_time
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Pipeline 全部完成! 耗时: {elapsed:.1f} 秒")
        logger.info(f"{'=' * 50}")


def main():
    parser = argparse.ArgumentParser(
        description="优品汇电商经营分析 Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --step all        # 运行全流程
  python main.py --step clean      # 仅数据清洗
  python main.py --step feature    # 仅特征工程
  python main.py --step churn      # 仅流失标签
  python main.py --step model      # 仅模型训练
  python main.py --step causal     # 仅因果分析
  python main.py --step review     # 仅评论分析
  python main.py --step business   # 仅经营分析
        """
    )
    parser.add_argument(
        "--step",
        choices=["clean", "feature", "churn", "model", "causal", "review", "business", "all"],
        default="all",
        help="执行的步骤 (默认: all)"
    )

    args = parser.parse_args()
    config = load_config()
    setup_logging(config)

    # 检查数据库连接
    try:
        from utils.db_connector import get_engine
        from sqlalchemy import text
        engine = get_engine(config)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"无法连接 MySQL 数据库: {e}")
        logger.error("请确认 MySQL 已启动，且数据库 olist_ecommerce 已创建。")
        logger.error("若数据尚未导入，请先运行: python scripts/init_mysql_db.py")
        sys.exit(1)

    pipeline = Pipeline(config)

    if args.step == "all":
        pipeline.run_all()
    else:
        step_method = getattr(pipeline, f"step_{args.step}")
        step_method()


if __name__ == "__main__":
    main()
