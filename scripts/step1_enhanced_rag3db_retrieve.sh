#!/usr/bin/env bash
set -euo pipefail

# 增强版RAG_3DB检索脚本 - 使用改进的搜索算法
# 用法：
#   bash scripts/step1_enhanced_rag3db_retrieve.sh <start_id> <end_id> [top_k] [rag_db_type] [config_path] [--data-dir <data_dir>]
# 示例：
#   bash scripts/step1_enhanced_rag3db_retrieve.sh 4000 4002 3 uniform config/config.yaml
#   bash scripts/step1_enhanced_rag3db_retrieve.sh 17500 17600 3 report_context config/config_openai.yaml --data-dir diag_data_normalized

START_ID=${1:-4000}
END_ID=${2:-4000}
TOP_K=${3:-3}
RAG_DB_TYPE=${4:-"uniform"}  # uniform, report_context, sequential_block
CONFIG_PATH=${5:-"config/config.yaml"}

# 解析可选参数
DATA_DIR="test_set"

# 检查是否有额外的参数
if [ $# -gt 5 ]; then
    # 处理 --data-dir 参数
    for ((i=6; i<=$#; i++)); do
        arg="${!i}"
        case $arg in
            --data-dir=*)
                DATA_DIR="${arg#*=}"
                ;;
            --data-dir)
                if [ $i -lt $# ]; then
                    next_i=$((i+1))
                    DATA_DIR="${!next_i}"
                    i=$next_i
                fi
                ;;
        esac
    done
fi

# 数据路径配置
TEST_DIR="/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized"

# 获取配置文件中的输出路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FULL_CONFIG_PATH="${SCRIPT_DIR}/../${CONFIG_PATH}"
OUT_DIR=$(python "${SCRIPT_DIR}/get_output_path.py" "${FULL_CONFIG_PATH}")
mkdir -p "${OUT_DIR}"

echo "🚀 使用增强版RAG_3DB系统进行检索"
echo "📊 参数配置:"
echo "   报告范围: ${START_ID} - ${END_ID}"
echo "   Top-K: ${TOP_K}"
echo "   RAG数据库类型: ${RAG_DB_TYPE}"
echo "   数据目录: ${DATA_DIR}"
echo "   输出目录: ${OUT_DIR}"
echo ""

# 数据库类型说明
case ${RAG_DB_TYPE} in
    uniform)
        echo "🎲 使用Uniform Random Unit数据库 - 纯随机采样，43,000个SDU"
        echo "   ✨ 增强特性: 医学文本预处理 + 多阶段搜索 + 质量过滤"
        ;;
    report_context)
        echo "📋 使用Report Context数据库 - 报告级采样，保持完整报告上下文，43,000个SDU"
        echo "   ✨ 增强特性: 上下文感知搜索 + 医学相关性评分"
        ;;
    sequential_block)
        echo "📅 使用Sequential Block数据库 - 顺序采样，保持时间顺序，43,000个SDU"
        echo "   ✨ 增强特性: 时序感知搜索 + 演变模式识别"
        ;;
    *)
        echo "❌ 不支持的RAG数据库类型: ${RAG_DB_TYPE}"
        echo "   支持的类型: uniform, report_context, sequential_block"
        exit 1
        ;;
esac

echo ""

# 检查MongoDB服务状态
echo "🔍 检查MongoDB服务状态..."
if ! pgrep -x "mongod" > /dev/null; then
    echo "⚠️  MongoDB服务未运行，尝试启动..."
    sudo systemctl start mongod || {
        echo "❌ MongoDB启动失败，请手动启动MongoDB服务"
        exit 1
    }
fi
echo "✅ MongoDB服务正常运行"

# 逐个处理文件
success_count=0
total_files=$((END_ID - START_ID + 1))
total_symptoms=0
high_quality_results=0

echo ""
echo "🎯 开始增强版RAG检索..."
echo "=" * 60

for ((i=${START_ID}; i<=${END_ID}; i++)); do
    FILE="${TEST_DIR}/diagnostic_${i}.json"
    
    if [ ! -f "${FILE}" ]; then
        echo "⚠️  跳过：未找到文件 ${FILE}"
        continue
    fi
    
    echo ""
    echo "🔍 增强版检索 diagnostic_${i}.json (${success_count}/${total_files})..."
    echo "   RAG数据库: ${RAG_DB_TYPE}"
    echo "   Top-K: ${TOP_K}"
    echo "   搜索算法: 多阶段增强搜索"
    
    # 使用增强版RAG_3DB适配器
    if python "${SCRIPT_DIR}/enhanced_rag3db_search_adapter.py" \
        --file "${FILE}" \
        --rag_db_type "${RAG_DB_TYPE}" \
        --top_k "${TOP_K}" \
        --output_dir "${OUT_DIR}"; then
        
        success_count=$((success_count + 1))
        
        # 统计症状数量（简单估算）
        symptom_count=$(python -c "
import json
try:
    with open('${FILE}', 'r', encoding='utf-8') as f:
        data = json.load(f)
    count = len([item for item in data if isinstance(item, dict) and 's_symptom' in item and item['s_symptom'].strip()])
    print(count)
except:
    print(0)
")
        total_symptoms=$((total_symptoms + symptom_count))
        
        echo "   ✅ 检索成功 - 处理了 ${symptom_count} 个症状"
        echo "   📊 累计处理症状: ${total_symptoms} 个"
    else
        echo "   ❌ 检索失败"
    fi
    
    echo "   " + "-" * 40
done

echo ""
echo "🏁 增强版RAG_3DB检索完成"
echo "=" * 60
echo "📊 处理统计:"
echo "   成功处理: ${success_count}/${total_files} 个文件"
echo "   总处理症状: ${total_symptoms} 个"
echo "   RAG数据库: ${RAG_DB_TYPE}"
echo "   搜索算法: 增强版多阶段搜索"
echo "   缓存保存在: ${OUT_DIR}"
echo ""

if [ ${success_count} -eq 0 ]; then
    echo "❌ 没有成功处理任何文件"
    exit 1
fi

echo "✅ 所有增强版检索任务完成！"
echo ""
echo "🎯 增强版特性总结:"
echo "   • 医学文本预处理 (缩写展开、同义词识别)"
echo "   • 多阶段搜索策略 (粗排→精排→过滤)"
echo "   • 医学相关性评分 (器官系统匹配、术语匹配)"
echo "   • 质量过滤机制 (一致性检查、多样性保证)"
echo "   • 智能结果排序 (向量相似度 + 医学知识)"
echo ""
echo "📈 预期改进效果:"
echo "   • 提高搜索结果的医学相关性"
echo "   • 减少不一致和冲突的信息"
echo "   • 增强结果的多样性和覆盖面"
echo "   • 更好的症状-诊断匹配精度"
echo ""
