#!/bin/bash
set -e

echo "============================================"
echo "  优品汇电商分析项目 - Docker 启动"
echo "============================================"

echo ""
echo "=== 等待 MySQL 就绪 ==="
# docker-compose 的 depends_on healthcheck 已保证 MySQL 可用
# 额外等待几秒确保 MySQL 完全初始化
sleep 5

echo "=== 步骤 1: 数据本地化转换（巴西数据 → 中国数据）==="
python scripts/rebrand_data.py

echo ""
echo "=== 步骤 2: 初始化 MySQL 数据库（导入转换后数据）==="
python scripts/init_mysql_db.py

echo ""
echo "=== 步骤 3: 运行分析 Pipeline ==="
python main.py --step all

echo ""
echo "============================================"
echo "  全部完成！"
echo "  结果文件位于: data/processed/"
echo "  图表文件位于: data/processed/plots/"
echo "============================================"
