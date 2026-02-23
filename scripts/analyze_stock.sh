#!/bin/bash
# A股股票分析脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"

# 默认输出目录
OUTPUT_DIR="${2:-$HOME/Desktop}"
STOCK_CODE="$1"

if [ -z "$STOCK_CODE" ]; then
    echo "用法: $0 <股票代码> [输出目录]"
    echo "示例: $0 600519"
    echo "      $0 002471 ~/Desktop"
    exit 1
fi

echo "🔍 正在分析股票: $STOCK_CODE"

# 运行 Python 分析脚本
python3 "$SCRIPT_DIR/stock_analyzer.py" --code "$STOCK_CODE" --output "$OUTPUT_DIR"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 分析完成! 结果保存在: $OUTPUT_DIR/${STOCK_CODE}_analysis.json"
    
    # 读取结果并显示摘要
    if [ -f "$OUTPUT_DIR/${STOCK_CODE}_analysis.json" ]; then
        python3 -c "
import json
with open('$OUTPUT_DIR/${STOCK_CODE}_analysis.json', 'r') as f:
    data = json.load(f)
    
print('='*50)
print(f\"股票: {data.get('ts_code', '')}\")
print(f\"名称: {data.get('stock_info', {}).get('name', 'N/A')}\")
print('='*50)
print(f\"综合评分: {data['overall']['overall_score']}\")
print(f\"评级: {data['overall']['rating']}\")
print('-'*50)
print(f\"基本面: {data['fundamental']['score']} 分 ({data['fundamental'].get('comment', '')}\")
print(f\"技术面: {data['technical']['score']} 分 ({data['technical'].get('comment', '')}\")
print(f\"资讯面: {data['info']['score']} 分 ({data['info'].get('comment', '')}\")
print('='*50)
"
    fi
else
    echo "❌ 分析失败"
    exit 1
fi
