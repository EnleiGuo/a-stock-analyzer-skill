#!/bin/bash

# =============================================================================
# A股深度分析系统 - Web 应用启动脚本
# 
# 用法:
#   ./start.sh              # 启动前后端
#   ./start.sh start        # 启动前后端
#   ./start.sh stop         # 停止前后端
#   ./start.sh restart      # 重启前后端
#   ./start.sh status       # 查看状态
#   ./start.sh logs         # 查看日志
#   ./start.sh frontend     # 仅启动前端
#   ./start.sh backend      # 仅启动后端
#   ./start.sh install      # 仅安装依赖
# =============================================================================

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$SCRIPT_DIR/api"
WEB_DIR="$SCRIPT_DIR/web"
PID_DIR="$SCRIPT_DIR/.pids"
LOG_DIR="$SCRIPT_DIR/logs"

FRONTEND_PORT=4661
BACKEND_PORT=4662

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 打印 Banner
print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           A股深度分析系统 - Web 应用管理器                ║"
    echo "║                                                           ║"
    echo "║   前端: http://localhost:${FRONTEND_PORT}                          ║"
    echo "║   后端: http://localhost:${BACKEND_PORT}                          ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 确保目录存在
ensure_dirs() {
    mkdir -p "$PID_DIR"
    mkdir -p "$LOG_DIR"
}

# 检测 Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        error "未找到 Python，请先安装 Python 3.10+"
        exit 1
    fi
    
    # 检查版本
    PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    info "Python 版本: $PY_VERSION"
}

# 检测 Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        error "未找到 Node.js，请先安装 Node.js 18+"
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        error "未找到 npm，请先安装 npm"
        exit 1
    fi
    
    NODE_VERSION=$(node -v)
    info "Node.js 版本: $NODE_VERSION"
}

# 安装后端依赖
install_backend_deps() {
    info "检查后端依赖..."
    
    cd "$API_DIR"
    
    # 检查是否需要安装
    if [ -f "requirements.txt" ]; then
        # 检查多个关键包是否已安装
        NEED_INSTALL=false
        for pkg in fastapi uvicorn nanoid pydantic; do
            if ! $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
                NEED_INSTALL=true
                break
            fi
        done
        
        if [ "$NEED_INSTALL" = true ]; then
            warn "正在安装后端依赖..."
            $PYTHON_CMD -m pip install -r requirements.txt -q
            success "后端依赖安装完成"
        else
            success "后端依赖已就绪"
        fi
    fi
    
    cd "$SCRIPT_DIR"
}

# 安装前端依赖
install_frontend_deps() {
    info "检查前端依赖..."
    
    cd "$WEB_DIR"
    
    # 检查 node_modules 是否存在
    if [ ! -d "node_modules" ]; then
        warn "正在安装前端依赖..."
        npm install --silent
        success "前端依赖安装完成"
    else
        # 检查是否需要更新
        if [ "package.json" -nt "node_modules" ]; then
            warn "检测到 package.json 更新，正在更新依赖..."
            npm install --silent
            success "前端依赖更新完成"
        else
            success "前端依赖已就绪"
        fi
    fi
    
    cd "$SCRIPT_DIR"
}

# 安装所有依赖
install_deps() {
    check_python
    check_node
    install_backend_deps
    install_frontend_deps
}

# 检查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口空闲
    fi
}

# 启动后端
start_backend() {
    info "启动后端服务..."
    
    if check_port $BACKEND_PORT; then
        warn "后端端口 $BACKEND_PORT 已被占用"
        return 1
    fi
    
    cd "$API_DIR"
    
    # 启动 uvicorn
    nohup $PYTHON_CMD -m uvicorn main:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --reload \
        > "$LOG_DIR/backend.log" 2>&1 &
    
    echo $! > "$PID_DIR/backend.pid"
    
    # 等待启动
    sleep 2
    
    if check_port $BACKEND_PORT; then
        success "后端服务已启动 (PID: $(cat "$PID_DIR/backend.pid"))"
        success "后端地址: http://localhost:$BACKEND_PORT"
    else
        error "后端启动失败，请查看日志: $LOG_DIR/backend.log"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
}

# 启动前端
start_frontend() {
    info "启动前端服务..."
    
    if check_port $FRONTEND_PORT; then
        warn "前端端口 $FRONTEND_PORT 已被占用"
        return 1
    fi
    
    cd "$WEB_DIR"
    
    # 启动 vite
    nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    
    echo $! > "$PID_DIR/frontend.pid"
    
    # 等待启动
    sleep 5  # Vite 需要更多启动时间
    
    if check_port $FRONTEND_PORT; then
        success "前端服务已启动 (PID: $(cat "$PID_DIR/frontend.pid"))"
        success "前端地址: http://localhost:$FRONTEND_PORT"
    else
        error "前端启动失败，请查看日志: $LOG_DIR/frontend.log"
        return 1
    fi
    
    cd "$SCRIPT_DIR"
}

# 停止后端
stop_backend() {
    info "停止后端服务..."
    
    if [ -f "$PID_DIR/backend.pid" ]; then
        PID=$(cat "$PID_DIR/backend.pid")
        if kill -0 $PID 2>/dev/null; then
            kill $PID 2>/dev/null || true
            sleep 1
            # 强制杀死
            kill -9 $PID 2>/dev/null || true
        fi
        rm -f "$PID_DIR/backend.pid"
    fi
    
    # 确保端口释放
    if check_port $BACKEND_PORT; then
        PID=$(lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t 2>/dev/null)
        if [ -n "$PID" ]; then
            kill -9 $PID 2>/dev/null || true
        fi
    fi
    
    success "后端服务已停止"
}

# 停止前端
stop_frontend() {
    info "停止前端服务..."
    
    if [ -f "$PID_DIR/frontend.pid" ]; then
        PID=$(cat "$PID_DIR/frontend.pid")
        if kill -0 $PID 2>/dev/null; then
            kill $PID 2>/dev/null || true
            sleep 1
            kill -9 $PID 2>/dev/null || true
        fi
        rm -f "$PID_DIR/frontend.pid"
    fi
    
    # 确保端口释放
    if check_port $FRONTEND_PORT; then
        PID=$(lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t 2>/dev/null)
        if [ -n "$PID" ]; then
            kill -9 $PID 2>/dev/null || true
        fi
    fi
    
    success "前端服务已停止"
}

# 启动所有服务
start_all() {
    print_banner
    ensure_dirs
    install_deps
    
    echo ""
    start_backend
    start_frontend
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  所有服务已启动！${NC}"
    echo -e "${GREEN}  前端: ${CYAN}http://localhost:$FRONTEND_PORT${NC}"
    echo -e "${GREEN}  后端: ${CYAN}http://localhost:$BACKEND_PORT${NC}"
    echo -e "${GREEN}  日志: ${CYAN}$LOG_DIR/${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
}

# 停止所有服务
stop_all() {
    print_banner
    stop_frontend
    stop_backend
    echo ""
    success "所有服务已停止"
}

# 重启所有服务
restart_all() {
    stop_all
    echo ""
    sleep 2
    start_all
}

# 查看状态
show_status() {
    print_banner
    
    echo -e "${BLUE}服务状态:${NC}"
    echo ""
    
    # 后端状态
    if check_port $BACKEND_PORT; then
        PID=$(lsof -Pi :$BACKEND_PORT -sTCP:LISTEN -t 2>/dev/null || echo "未知")
        echo -e "  后端 (端口 $BACKEND_PORT): ${GREEN}运行中${NC} (PID: $PID)"
    else
        echo -e "  后端 (端口 $BACKEND_PORT): ${RED}已停止${NC}"
    fi
    
    # 前端状态
    if check_port $FRONTEND_PORT; then
        PID=$(lsof -Pi :$FRONTEND_PORT -sTCP:LISTEN -t 2>/dev/null || echo "未知")
        echo -e "  前端 (端口 $FRONTEND_PORT): ${GREEN}运行中${NC} (PID: $PID)"
    else
        echo -e "  前端 (端口 $FRONTEND_PORT): ${RED}已停止${NC}"
    fi
    
    echo ""
}

# 查看日志
show_logs() {
    echo -e "${BLUE}选择要查看的日志:${NC}"
    echo "  1) 后端日志"
    echo "  2) 前端日志"
    echo "  3) 同时查看（分屏）"
    echo ""
    read -p "请选择 [1-3]: " choice
    
    case $choice in
        1)
            tail -f "$LOG_DIR/backend.log"
            ;;
        2)
            tail -f "$LOG_DIR/frontend.log"
            ;;
        3)
            tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
            ;;
        *)
            error "无效选择"
            ;;
    esac
}

# 显示帮助
show_help() {
    print_banner
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动前后端服务 (默认)"
    echo "  stop        停止前后端服务"
    echo "  restart     重启前后端服务"
    echo "  status      查看服务状态"
    echo "  logs        查看服务日志"
    echo "  frontend    仅启动前端"
    echo "  backend     仅启动后端"
    echo "  install     仅安装依赖"
    echo "  help        显示此帮助信息"
    echo ""
}

# 主函数
main() {
    case "${1:-start}" in
        start)
            start_all
            ;;
        stop)
            stop_all
            ;;
        restart)
            restart_all
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        frontend)
            ensure_dirs
            check_node
            install_frontend_deps
            start_frontend
            ;;
        backend)
            ensure_dirs
            check_python
            install_backend_deps
            start_backend
            ;;
        install)
            install_deps
            success "依赖安装完成"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行
main "$@"
