# Reversi GUI Migration Plan (PySide6)

## 0. 核心目标
- **架构解耦**：保持原有 GUI-Protocol-Engine 架构，仅重写 `src/ui`。
- **视觉一致性**：1:1 复刻原有的深色调、现代感设计，优化棋子渲染效果。
- **稳定性提升**：利用 PySide6 成熟的事件循环处理引擎异步通信，彻底解决 Flet 的窗口关闭异常和 macOS 文件选择器问题。

## 1. 模块设计方案

### A. 主窗口 ([src/reversi/ui/app.py](src/reversi/ui/app.py))
- **基类**：`QMainWindow`。
- **布局**：使用 `QHBoxLayout` 作为主容器。左侧为固定宽度的 `Sidebar`，右侧为自适应缩放的 `BoardArea`。
- **消息队列**：通过 `qasync` 将引擎的 `ANALYSIS` / `BOARD` / `VALID_MOVES` 等异步消息转化为 Qt Signals 派发到各组件。

### B. 棋盘组件 ([src/reversi/ui/components/board.py](src/reversi/ui/components/board.py))
- **绘制核心**：实现一个 `BoardWidget`，重写 `resizeEvent` 以维持棋盘的正方形比例。
- **下子交互**：将鼠标点击坐标转换为棋盘代数坐标（如 "D4"）并向 `ProtocolInterface` 发送指令。
- **视觉层级**：
  1. **背景层**：深绿色网格。
  2. **提示层**：半透明小圆点（合法着法）和带有分数的辅助线。
  3. **棋子层**：使用 `QPainter.drawEllipse`，添加径向渐变（Radial Gradient）使棋子具有立体感。

### C. 设置与引擎对话框 ([src/reversi/ui/components/engine_dialog.py](src/reversi/ui/components/engine_dialog.py))
- **动态 UI**：利用 `src/reversi/engine/metadata.py`。遍历 `engine_registry`，根据参数类型（Int, Float, Bool, Enum）动态创建 `QSpinBox`, `QDoubleSpinBox`, `QCheckBox`, `QComboBox`。
- **联动**：切换引擎下拉框时，自动清空并重建下方配置表单。

### D. 游戏控制与日志 (Sidebar)
- **Scoreboard**：`QLabel` 组。
- **Log Area**：使用 `QPlainTextEdit`。设置 `setReadOnly(True)`，并实现 `append_log` 方法保持自动滚动。
- **Buttons**：`QPushButton`。Undo 功能需保留原有逻辑：连续发送两轮 `UNDO` 命令以适应人机模式。

## 2. 详细迁移步骤 (Implementation Steps)

### 第一阶段：脚手架 (Foundation)
1. 安装依赖：`pip install PySide6 qasync`。
2. 重命名旧 UI 代码，初始化新 `src/ui` 目录和 `__init__.py`。
3. 实现基础 `MainWindow` 和 `qasync` 启动脚本。

### 第二阶段：核心驱动 (Communication)
1. 在 `App` 类中实例化 `ProtocolInterface`。
2. 建立信号槽映射：
   - `on_board_update` -> `board_widget.update_state()`
   - `on_analysis_update` -> `board_widget.update_analysis()`
   - `on_engine_log` -> `log_widget.append()`

### 第三阶段：组件开发 (Components)
1. **棋盘系统**：实现格点坐标系映射、棋子绘制算法、响应式缩放。
2. **侧边栏**：按钮布局、玩家/引擎类型切换。
3. **对话框**：参数映射逻辑，确保 UI 修改能同步到 `EngineSpec`。

### 第四阶段：功能完善 (Features)
1. **回放工具条**：集成 `QTimer` 实现自动回放功能。
2. **持久化**：使用 `QFileDialog` 重写 Save/Load 交互。
3. **主题美化**：编写 `style.qss`。

## 3. 关键交互逻辑复刻
- **Undo/Pass**：UI 需根据 `VALID_MOVES` 消息动态禁用/启用按钮。
- **辅助分析**：当 Human 玩家模式下且启用 Analysis Assist 时，点击棋盘任何位置前，UI 需实时展示辅助引擎返回的权重（渲染在棋格角落）。
- **进程安全**：由于 Rust 引擎运行在独立进程，需确保 `MainWindow.closeEvent` 中调用引擎的 `stop()` 方法，防止僵尸进程。

## 4. 进一步的考虑

- 多线程/异步安全：Qt 的 UI 必须在主线程更新。虽然 qasync 简化了协程，但由于引擎回调可能产生在不同线程，建议所有 UI 更新都通过 pyqtSignal 转发。
- 主题定制：PySide6 很容易引入 QSS 文件。我们可以预留一个 themes.py，专门存放不同棋盘颜色方案的 QSS 片段。
- 性能优化：对于 8x8 棋盘，直接重绘全图性能足够；但如果考虑未来扩展到 19x19，可以使用 PySide6 的 `QGraphicsScene` 优化局部刷新。
