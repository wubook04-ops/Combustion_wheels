# Rate File Plot

一个读取 Chemkin 速率文件（CSV / XLSX），按列名提取两列数据并绘制 X-Y 曲线的命令行小工具。

> **徽章建议补充**：本项目尚未作为独立仓库发布，没有可用的仓库 URL、CI 与发布流水线，因此暂不放置徽章。发布后建议补充 3–6 个来源有效的徽章（Python 版本、pandas、matplotlib、License）。

## 项目简介

`Rate_file_plot` 面向 Chemkin / 燃烧模拟导出的速率文件。程序以交互方式询问文件路径与列名，自动在表头中定位时间列与目标数据列，读取 CSV（`utf-8` / `gbk`）或 XLSX 文件，并用 matplotlib 绘制折线图。

程序由三个文件组成：

- `main.py`：交互入口，负责收集路径与列名，最多重试 3 次。
- `rate_file_plot.py`：`RateFilePlot` 类，负责判断扩展名、读取文件、调用列名识别并绘图。
- `find_column.py`：`FindColumn` 类，负责在 DataFrame 中匹配并确认列名。

## 功能特性

- 支持 `.csv` 与 `.xlsx` 两种输入格式；CSV 会依次尝试 `utf-8`、`gbk` 编码。
- 根据内置关键词表自动识别时间列、温度列、体积列、压力列。
- 自动识别失败时，列出全部可用列并提示手动输入列名。
- 交互式输入，单次运行只需提供文件路径与两个列类别。
- 文件不存在或加载失败时最多重试 3 次。
- 使用 pandas 读取数据、matplotlib 绘制图表，无额外业务依赖。

## 安装

### 环境要求

| 组件 | 已验证版本 | 说明 |
| --- | --- | --- |
| Python | 3.14.2 | 建议 3.11 及以上版本 |
| pandas | 3.0.6 | 读取 CSV / XLSX |
| matplotlib | 3.11.2 | 绘制折线图 |
| openpyxl | 未安装 | **读取 XLSX 必需**，需单独安装 |

> [!IMPORTANT]
> 当前验证环境中 `openpyxl` 未安装。未安装时读取 `.xlsx` 文件会失败；仅处理 CSV 时可以不装。

### 使用 conda

```bash
conda create -n rate-file-plot python=3.12 -y
conda activate rate-file-plot
conda install -c conda-forge pandas matplotlib openpyxl -y
```

### 使用 venv + pip

Windows PowerShell / cmd：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install pandas matplotlib openpyxl
```

Windows Git Bash：

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install pandas matplotlib openpyxl
```

> [!NOTE]
> 仓库当前没有 `requirements.txt`（**建议补充**）。如需固定依赖，可创建并提交：
>
> ```text
> pandas>=2.0
> matplotlib>=3.7
> openpyxl>=3.1
> ```

## 快速开始

进入项目目录并运行入口脚本：

```bash
cd E:/Python/mine/Rate_file_plot
python main.py
```

按提示依次输入文件路径与列名。示例使用仓库中真实存在的 `mine/CKSoln_solution_no_1_1.csv`：

```text
Please input the path of rate file: ../CKSoln_solution_no_1_1.csv
Please input the column name(s) to plot (e.g., TIME, TEMP, PRESSURE): TIME,TEMP
Reading CSV format file: ../CKSoln_solution_no_1_1.csv
Successfully read the file. Encoding: utf-8

Data shape: (行数, 列数)
Column names: ['Time_(sec)', ' Volume_(cm3)', ...]

Searching for time column...
Automatically identify the TIME column: ['Time_(sec)']
Time column confirmed as: Time_(sec)
Searching for temp column...
Automatically identify the TEMP column: ['Temperature_(K)']
Temp column confirmed as: Temperature_(K)
```

随后弹出 matplotlib 绘图窗口。关闭窗口后，终端输出：

```text
File format is correct, starting processing...
```

> [!NOTE]
> 上述终端输出为示意，`Data shape` 与列数取决于实际文件。绘图通过 `plt.show()` 完成，程序**不会保存图片文件**。

> [!IMPORTANT]
> `main.py` 使用同目录的 `rate_file_plot.py` 与 `find_column.py`，请在项目目录内运行，否则会出现 `ModuleNotFoundError`。

## 使用示例

### 示例 1：绝对路径

```text
Please input the path of rate file: E:\Python\mine\CKSoln_solution_no_1_1.csv
Please input the column name(s) to plot (e.g., TIME, TEMP, PRESSURE): TIME,TEMP
```

### 示例 2：文件名放在项目目录内

把待绘制文件复制到 `Rate_file_plot` 目录后，直接输入文件名：

```text
Please input the path of rate file: CKSoln_solution_no_1_1.csv
Please input the column name(s) to plot (e.g., TIME, TEMP, PRESSURE): TIME,TEMP
```

### 示例 3：作为模块调用

```python
from rate_file_plot import RateFilePlot

plotter = RateFilePlot(
    filepath='../CKSoln_solution_no_1_1.csv',
    column_names='TIME,TEMP',
)
plotter.load_and_process_file()
```

`load_and_process_file()` 在读取成功并完成绘图后返回 `True`；文件不存在、格式不支持、读取失败或数据为空时返回 `False`。

<details>
<summary>完整处理流程（原始设计说明）</summary>

1. 读取用户给出的文件地址，分析文件类型；仅支持可读的 CSV / XLSX，否则提示重新输入。
2. 读取文件内容，成功后进入目标数据提取模块。
3. 以“时间-温度”为例：进入时间提取模块，寻找对应列名并提取列数据，再提取温度列数据。
4. 将两列数据绘制为 X-Y 轴，输出图片。

原始流程图：

```text
┌─────────────────────────────────────────────────────────┐
│                      程 序 启 动                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              步骤 1：获取文件路径                       │
│  用户输入要绘制的文件地址                               │
│  检查输入是否为空                                       │
│  ├── 为空 → 提示重新输入                                │
│  └── 非空 → 继续                                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              步骤 2：校验文件类型                       │
│  提取文件后缀名                                         │
│  判断是否为支持的格式                                   │
│  ├── 是 .csv 或 .xlsx → 继续                            │
│  └── 否 → 提示"不支持的文件格式，请重新输入"            │
│           └── 返回步骤 1                                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              步骤 3：读取文件内容                       │
│  根据文件类型选择读取方法                               │
│  ├── .csv  → pd.read_csv()，尝试多种编码                │
│  │   ├── 读取成功 → 继续                                │
│  │   └── 所有编码均失败 → 提示"无法解码文件" → 退出     │
│  └── .xlsx → pd.read_excel()                            │
│      ├── 读取成功 → 继续                                │
│      └── 读取失败 → 提示错误，退出程序                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              步骤 4：提取时间列数据                     │
│  调用 find_time_column() 自动识别时间列                 │
│  ├── 唯一匹配 → 自动确认                                │
│  ├── 多个匹配 → 列出候选，用户选择                      │
│  └── 无匹配   → 提示手动输入，并显示所有可用列          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              步骤 5：提取温度列数据                     │
│  提示用户输入要绘制的列名（如 T, TEMP）                 │
│  校验列名是否存在                                       │
│  ├── 存在 → 提取该列数据                                │
│  └── 不存在 → 提示重新输入                              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              步骤 6：验证数据有效性                     │
│  检查两列是否为空                                       │
│  ├── 任一为空 → 提示"没有数据可供提取"，退出            │
│  └── 均非空 → 继续                                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              步骤 7：绘制并输出图表                     │
│  时间列设为 X 轴，目标列设为 Y 轴                       │
│  创建画布并绘制折线图，设置标题与轴标签                 │
│  保存图片到本地文件，提示"图表生成成功"                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                      程 序 结 束                        │
└─────────────────────────────────────────────────────────┘
```

> [!NOTE]
> 上述为原始设计说明，完整原文见 [Readme.txt](Readme.txt)。当前实现中，步骤 4 与步骤 5 合并由 `FindColumn.find_columns()` 完成；`find_time_column()` 虽已定义，但主流程未调用。步骤 7 的“保存图片到本地文件”与“图表生成成功”在代码中并不存在，实际只调用 `plt.show()` 显示窗口。

</details>

## 配置说明

### 运行参数

程序没有命令行参数，也没有配置文件，以下参数通过源码或交互输入设置：

| 配置项 | 位置 | 默认值 | 说明 |
| --- | --- | --- | --- |
| 支持的文件扩展名 | `RateFilePlot.load_and_process_file()` | `csv`、`xlsx` | 其他扩展名直接返回 `False` |
| CSV 编码尝试顺序 | `rate_file_plot.py` | `utf-8` → `gbk` | 依次尝试，均失败则报告无法解码 |
| 列名输入数量 | `FindColumn.preprocess_column_name()` | 2 | 必须恰好两个，顺序即 X、Y |
| 列类别 | `FindColumn.keywords` | `time`、`temp`、`volume`、`pressure` | 首词必须是这四个之一，否则触发 `KeyError` |
| 最大重试次数 | `main.py` | 3 | 文件不存在或加载失败时计数 |
| 图片输出方式 | `RateFilePlot.plot_x_y()` | `plt.show()` | 仅显示，不保存文件 |
| 时间列自动识别 | `FindColumn.find_time_column()` | 未启用 | 主流程不调用该方法 |

### 列名关键词

匹配方式为：先对表头做 `strip()`，再与下表做**精确、区分大小写**的成员判断。

| 类别 | 可匹配的列名 |
| --- | --- |
| `time` | `time_s`、`Time_(sec)`、`time`、`Time`、`时间`、`t`、`second` |
| `temp` | `Temperature_(K)`、`T`、`temp`、`温度` |
| `volume` | `Volume_(cm3)` |
| `pressure` | `Pressure_(atm)`、`Pressure_(pa)`、`Pressure_(kpa)` |

> [!WARNING]
> `find_column.py` 中 `volume` 类别的另外两条 `' Volume_(dm3)'`、`' Volume_(m3)'` 带前导空格，而待匹配的列名会先被 `strip()`，因此这两条实际无法命中。若需要支持，应去掉源码中的前导空格。

> [!NOTE]
> 交互输入的是**列类别**（如 `TIME,TEMP`），不是完整列名（如 `Time_(sec),Temperature_(K)`）。输入完整列名会因不在类别表中而抛出 `KeyError`。

### 已知限制

- 不支持 `.xls`，仅支持 `.csv` 与 `.xlsx`。
- 只尝试 `utf-8`、`gbk` 两种编码，其他编码会报告无法解码。
- 输入不是恰好两个列类别时，`preprocess_column_name()` 会重新询问，但新输入不会被重新按逗号切分，后续会按字符遍历，建议一次性输入正确。
- 列名匹配区分大小写，且不做模糊匹配。
- 绘图后不保存文件，需要落盘时请自行改用 `plt.savefig()`。
- 无命令行参数、无配置文件、无测试。

## 项目结构

```text
Rate_file_plot/
├── main.py            # 交互入口：收集路径与列名，最多重试 3 次
├── rate_file_plot.py  # RateFilePlot：格式判断、文件读取、取列、绘图
├── find_column.py     # FindColumn：列名匹配与确认
├── README.md          # 本文档
├── Readme.txt         # 原始说明文档（保留）
└── __pycache__/       # Python 自动生成的字节码缓存
```

## 贡献指南

当前仓库没有 `CONTRIBUTING.md`（**建议补充**）。提交改动时请遵循以下约定：

1. Fork 仓库并新建分支，分支名说明改动范围，例如 `fix/volume-keywords`。
2. 保持三个模块的职责边界：交互逻辑放 `main.py`，读取与绘图放 `rate_file_plot.py`，列名匹配放 `find_column.py`。
3. 修改列名关键词时，同步更新本文档的“列名关键词”表格。
4. 提交前至少手动跑通一次 CSV 示例（`TIME,TEMP`）与一次 XLSX 示例。
5. 在 Pull Request 中说明改动原因、验证方式与影响范围。

> [!NOTE]
> 项目尚无自动化测试（**建议补充**）。引入测试时，建议为 `FindColumn.find_columns()` 的自动识别、多候选、无匹配三条分支各写一个用例。

## 许可证

本项目当前**未声明开源许可证**（**建议补充** `LICENSE` 文件，例如 MIT）。在补充许可证之前，默认保留所有权利，他人不得直接复制、修改或分发。

## 附录：建议补充清单

- [ ] `requirements.txt` 或 `pyproject.toml`，固定依赖版本。
- [ ] `LICENSE` 文件，并在本节补充具体许可证名称与链接。
- [ ] 独立仓库地址与 3–6 个来源有效的徽章。
- [ ] `CONTRIBUTING.md` 与 `CHANGELOG.md`。
- [ ] 列名关键词的单元测试。
- [ ] 可选的 `plt.savefig()` 输出，替代仅 `plt.show()`。
- [ ] 可选的命令行参数（`argparse`），避免纯交互输入。
- [ ] `assets/` 目录下的示例截图，使用 `./assets/xxx.png` 相对路径引用。
