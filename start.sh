#!/bin/bash
echo "============================================"
echo "  优品汇电商分析项目 - 一键启动"
echo "============================================"
echo ""

echo "[1/3] 检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo "错误: 未检测到 Docker，请先安装"
    echo "下载地址: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "[2/3] 构建并启动服务（首次约需 3-5 分钟）..."
echo ""
docker compose up --build

echo ""
echo "============================================"
echo "[3/3] 运行完成！"
echo "结果文件位于: data/processed/"
echo "图表文件位于: data/processed/plots/"
echo "============================================"
