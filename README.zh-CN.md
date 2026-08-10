# visio-mcp

在 Microsoft Visio 中绘制**电路原理图**的 MCP(Model Context Protocol)服务器,由 LLM 代理驱动。MIT 许可,100% 原创代码(不包含任何其他 Visio MCP 项目的代码)。

## 为什么做这个

用程序在 Visio 里画电路图,最常见的失败原因是:符号引脚坐标未知,导线落在符号旁边悬空。本服务器内置 **实测引脚几何数据**——经典 *Analog Circuit* stencil 的每个 master 都渲染成 240 DPI PNG 后逐像素定位引脚。`pin_point()` 把这些偏移量换算成页面绝对坐标,导线精确落在引脚上。

## 功能

- **实时 COM 引擎** —— 优先挂接已运行的 Visio(`GetActiveObject`),失败则启动新实例(`Dispatch`);自动应答模态对话框;所有 COM 调用在单工作线程上执行
- **stencil 锁绕行** —— stencil 被另一个 Visio 会话占用时(常见),自动打开临时副本
- **工具集**:文档、页面、stencil、master、形状(放置/连线/文字/节点/线宽/删除/查找/枚举)、导出(PNG/PDF/SVG/EMF 等)
- **实测引脚几何**:`Analog Circuit.vss` 的 NMOS1/PMOS1/Res1/Cap1/Ind2/balun/gnd/vdd,含旋转/翻转变体
- **内置模板** —— `stencils/` 随仓库附带 `Analog Circuit.vss`、`RFIC_lib.vss`、`RFsys_lib.vss`,开箱即可运行示例(第三方学术符号,来源见 `stencils/README.md`)
- **无头 Mock 引擎** —— 同一套工具层在无 Visio 环境下运行,测试套件可在 Linux CI 上跑
- **示例**:完整的两级差分 40 GHz LNA 原理图生成器

## 环境要求

| 要求 | 说明 |
|---|---|
| Windows 10/11 | 实时模式 |
| Microsoft Visio 2016+ | 任意版本 |
| Python 3.11+ | |
| `stencils/` | 随仓库附带(`Analog Circuit.vss`、`RFIC_lib.vss`、`RFsys_lib.vss`);用 `VISIO_MCP_STENCIL_DIRS` 指向该目录 |

## 安装

```bash
cd VISIO_MCP
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"

# 模板随仓库附带,把服务器指向它
export VISIO_MCP_STENCIL_DIRS="$PWD/stencils"
```

探测 Visio:

```bash
.venv\Scripts\python -m visio_mcp --check
```

## 作为 MCP 服务器运行(stdio)

```bash
.venv\Scripts\visio-mcp
```

### Claude Code 配置

```json
{
  "mcpServers": {
    "visio": {
      "command": "C:/path/to/your/stencils/VISIO_MCP/.venv/Scripts/python.exe",
      "args": ["-m", "visio_mcp"],
      "env": { "VISIO_MCP_STENCIL_DIRS": "C:/path/to/your/stencils" }
    }
  }
}
```

### Hermes Agent 配置

```yaml
mcp_servers:
  visio:
    command: "C:/path/to/your/stencils/VISIO_MCP/.venv/Scripts/python.exe"
    args: ["-m", "visio_mcp"]
    env:
      VISIO_MCP_STENCIL_DIRS: "C:/path/to/your/stencils"
```

## 环境变量

| 变量 | 默认值 | 含义 |
|---|---|---|
| `VISIO_MCP_STENCIL_DIRS` | (空) | `;` 分隔的 stencil 搜索目录 |
| `VISIO_MCP_VISIBLE` | `0` | 显示 Visio 窗口 |
| `VISIO_MCP_ATTACH` | `1` | 挂接已运行的 Visio 实例;`0` = 总是启动独立实例(更确定) |
| `VISIO_MCP_KEEP_ALIVE` | `0` | 退出时保留启动的 Visio 实例 |
| `VISIO_MCP_WIRE_WEIGHT` | `1.5 pt` | 导线默认线宽 |
| `VISIO_MCP_LABEL_FONT` | `Arial` | 标签默认字体 |
| `VISIO_MCP_LABEL_SIZE` | `10pt` | 标签默认字号 |
| `VISIO_MCP_DOT_STENCIL` | (空) | 节点圆点 stencil(如 RFIC_lib.vss) |
| `VISIO_MCP_DOT_MASTER` | `Point` | 节点圆点 master 名 |
| `VISIO_MCP_MOCK` | `0` | 强制使用无头 mock 引擎 |

## 绘制流程(代理工作流)

1. `new_document(16, 9.5)` —— 坐标单位英寸
2. `load_stencil("…/Analog Circuit.vss")` —— 拿到 stencil key
3. `drop_master(key, "NMOS1", x, y, flip_x=…)` 放置符号
4. `pin_point("NMOS1", x, y, "gate")` —— 精确引脚坐标
5. `draw_wire([...])` —— **先画线再放元件**(串联元件盖住线;用 `symbol_bounds` 避免线穿过器件)
6. ≥3 线节点 `add_junction`,命名用 `add_label`
7. `export_page("png", "out.png")` —— 渲染检查,迭代

## 实测引脚数据

`visio_mcp/data/pins_analog_circuit.json` —— 相对放置点(原点)的英寸偏移(y 向上坐标系),通过 PNG 渲染 + 像素分析测得;变体编码旋转(`angle`)与镜像(`flip_x`)。已用两级差分 LNA 示例验证(21 个连接点全部像素级连通)。

## 已知坑

- **重新生成时不要用 Visio 开着目标 .vsdx** —— SaveAs 会报"DOS 无效句柄"。先关文件或换新路径。
- **临时 stencil 副本必须放在原 stencil 旁边** —— %TEMP% 下的文件会被信任中心文件阻止设置拦截。
- **用户的交互式 Visio 会话不稳定时**(兼容模式 stencil、未保存文档等),设 `VISIO_MCP_ATTACH=0` 让服务器驱动独立实例。

## 目录结构

```
visio_mcp/
  engine.py        实时 COM 引擎(单工作线程,win32com 惰性导入)
  mock_engine.py   无头引擎(CI)
  server.py        FastMCP 应用 + 工具
  pins.py          实测几何辅助函数
  data/pins_analog_circuit.json
stencils/           随仓库附带的 Visio 模板(Analog Circuit / RFIC_lib / RFsys_lib)
examples/lna_two_stage.py   两级差分 LNA 原理图生成器
tests/                      单测(无头)
```

## 许可证

MIT —— 本项目的代码、实测引脚几何 JSON 和文档为作者原创。`stencils/` 中
附带的模板(`Analog Circuit.vss`、`RFIC_lib.vss`、`RFsys_lib.vss`)是
**第三方学术符号库**(最初创建于复旦大学),**不受**本项目 MIT 许可覆盖 ——
其来源与条款见 `stencils/README.md`。
