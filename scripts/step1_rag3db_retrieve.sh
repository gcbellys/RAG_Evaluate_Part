#!/usr/bin/env bash
set -euo pipefail

# 使用新的RAG_3DB系统进行检索，对指定报告ID范围执行检索，写入结构化缓存(JSONL)
# 用法：
#   bash scripts/step1_rag3db_retrieve.sh <start_id> <end_id> [top_k] [rag_db_type] [config_path] [--data-dir <data_dir>]
# 示例：
#   bash scripts/step1_rag3db_retrieve.sh 4000 4002 3 uniform config/config.yaml
#   bash scripts/step1_rag3db_retrieve.sh 17500 17600 3 report_context config/config_openai.yaml --data-dir diag_data_normalized

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

# 数据路径配置（支持 --data-dir 覆盖）
if [ "${DATA_DIR}" != "test_set" ]; then
    TEST_DIR="${DATA_DIR}"
else
    TEST_DIR="/home/duojiechen/Central_Data/Testset_0_43000-43508/diagnostic_results_normalized"
fi

# 根据数据库类型设置输出命名空间与目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${SCRIPT_DIR}/.."
case ${RAG_DB_TYPE} in
    uniform)
        NAMESPACE="uniform"
        ;;
    report_context)
        NAMESPACE="report_context"
        ;;
    sequential_block)
        NAMESPACE="sequential_block"
        ;;
esac

OUT_DIR="${BASE_DIR}/results/rag_output_${NAMESPACE}"
mkdir -p "${OUT_DIR}"

# 环境激活说明：此脚本假定已在 RAG_ws 环境中运行，避免子进程重复激活导致报错

echo "🚀 使用RAG_3DB系统进行检索"
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
        ;;
    report_context)
        echo "📋 使用Report Context数据库 - 报告级采样，保持完整报告上下文，43,000个SDU"
        ;;
    sequential_block)
        echo "📅 使用Sequential Block数据库 - 顺序采样，保持时间顺序，43,000个SDU"
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

for ((i=${START_ID}; i<=${END_ID}; i++)); do
    FILE="${TEST_DIR}/diagnostic_${i}.json"
    
    if [ ! -f "${FILE}" ]; then
        echo "⚠️  跳过：未找到文件 ${FILE}"
        continue
    fi
    
    echo "🔍 检索 diagnostic_${i}.json (${success_count}/${total_files})..."
    echo "   RAG数据库: ${RAG_DB_TYPE}"
    echo "   Top-K: ${TOP_K}"
    
    # 使用修复版的RAG_3DB适配器（传入数据库类型与输出目录）
    if python "${SCRIPT_DIR}/fixed_rag3db_search_adapter.py" \
        --file "${FILE}" \
        --rag_db_type "${RAG_DB_TYPE}" \
        --top_k "${TOP_K}" \
        --output_dir "${OUT_DIR}"; then
        
        success_count=$((success_count + 1))
        echo "   ✅ 检索成功"
    else
        echo "   ❌ 检索失败"
    fi
    
    echo ""
done

echo "🏁 RAG_3DB检索完成"
echo "📊 处理统计:"
echo "   成功处理: ${success_count}/${total_files} 个文件"
echo "   RAG数据库: ${RAG_DB_TYPE}"
echo "   缓存保存在: ${OUT_DIR}"

if [ ${success_count} -eq 0 ]; then
    echo "❌ 没有成功处理任何文件"
    exit 1
fi

echo "✅ 所有检索任务完成！"
