# CHEMKIN 机理预处理模块

本目录包含 CHEMKIN 机理文件与 NASA-7 热力学数据的读取、结构化及热力学/动力学计算代码。主实现位于 `chemkin_mechanism.py`，示例输入为 `DataFile/grimech30.dat` 和 `DataFile/thermo30.dat`。

> **当前状态：开发中的预处理代码。** 文件解析、反应与辅助行归属、单位转换及压力依赖反应计算仍有未完成或待核验部分。本文区分“当前实现”和“预期用途”，不要把所有描述的能力都视为已通过完整验证。

## 目录内容

- `chemkin_mechanism.py`：元素/物种结构、单反应解析、CHEMKIN 标准化、机理和热力学数据读取、热力学与速率计算，以及预处理入口。
- `DataFile/grimech30.dat`：示例 CHEMKIN 反应机理。
- `DataFile/thermo30.dat`：NASA-7 热力学示例数据。
- `Mechanism_preprocessing/`：预处理结果的默认输出目录；运行入口会尝试写入 `species_check.csv` 和 `reactions_check.csv`。

## 运行方式

在项目环境中运行：

```bash
python chemkin_mechanism.py
```

程序会提示输入温度（K）和压力（Pa），直接回车时分别使用代码中的默认值 400 K 和 101325 Pa。输入文件和输出文件使用相对路径，具体解析位置取决于启动程序时的当前工作目录。

⚠️ **运行前检查入口的路径参数**：当前 `__main__` 调用 `MechanismPreprocessing` 时，`mechanism_file_path` 误传为 `therm_file_path`，导致机理读取路径指向 `DataFile/thermo30.dat`，而不是 `DataFile/grimech30.dat`。应确认调用使用：

```python
MechanismPreprocessing(
  t=temp,
  pressure=pressure,
  mechanism_file_path="DataFile/grimech30.dat",
  therm_file_path="DataFile/thermo30.dat",
).main()
```

另请确认运行目录中存在这两个输入文件。输出目录由 `Path.mkdir(..., exist_ok=True)` 创建。

## 主要类与职责

### `Element`

根据元素符号建立元素记录，并为代码中显式列出的元素提供原子质量。当前质量表只覆盖 H、C、O、N、F、HE、NE、AR；其他元素的 `Element` 实例可能没有 `mass` 属性，机理读取时会以 `None` 存入元素字典。

### `Species`

使用 NASA-7 系数，在给定温度下计算单个物种的标准熵 `S`、焓 `H` 和热容 `Cp`：

- 输入温度单位：K。
- `a_L`、`a_H`：低温和高温区各 7 个 NASA 系数。
- 输出单位：`H` 为 J/mol；`S`、`Cp` 为 J/(mol·K)。
- 温度区间选择：`T_l <= T < T_m` 使用低温系数；`T_m <= T <= T_h` 使用高温系数。

`Species` 是计算器对象；读取文件后长期保存的物种数据则是 `ChemkinStandardizer.species` 中的字典记录，两种表示不要混淆。

### `ChemkinReaction`

解析一条反应主行，当前保存：

- 主行阿伦尼乌斯参数 `A`、`N`、`E`；
- 原始反应表达式；
- 反应物/产物名称及计量系数列表；
- 辅助行解析所需的临时属性。

`extract_row_params()` 将反应物计量系数记为负数、产物记为正数，并尝试处理两侧同名物种的净抵消。独立的 `M` token 会被跳过并将 `type` 设为 `third_body`；`(+M)` 会在拆分前移除，但当前解析器不会仅凭 `(+M)` 设置类型。

**当前限制**：首字符系数解析只支持 1–9 的单字符整数，不支持多位数或小数；同名物种净抵消的实现有已知边界问题，可能影响净系数和反应级数。

### `ChemkinStandardizer`

负责读取并组织机理数据：

- `convert_to_standard()`：尝试大写化、跳过区块空行，并将反应行中的 ` = ` 替换为 `<=>`。
- `load_mechanism()`：读取元素、物种和反应，生成三个容器：
  - `elements`：元素符号到元素信息字典的映射；
  - `species`：物种名到物种信息字典的映射；
  - `reactions`：反应记录字典组成的列表。
- `load_therm()`：根据 NASA-7 固定列格式，为物种字典填入温度范围及 `a_L`、`a_H` 系数。

物种字典示例：

```python
{
    "H2": {
        "name": "H2",
        "elements": {"H": 2},
        "a_L": [...],
        "a_H": [...],
        "T_l": 200.0,
        "T_m": 1000.0,
        "T_h": 3500.0,
        "T": None,
        "H": None,
        "S": None,
        "Cp": None,
    }
}
```

反应记录示例：

```python
{
    "index": 0,
    "equation": "H2+O2<=>2OH",
    "reversibility": "reversible",
    "net_stoic": {"H2": -1, "O2": -1, "OH": 2},
    "rate_model": "elementary",
    "third_body": {"enabled": False, "efficiencies": {}},
    "arrhenius": {"A": ..., "N": ..., "E": ..., "E_unit": "cal/mol"},
    "low_pressure": {},
    "high_pressure": {},
    "broadening": {},
    "plog": [],
    "chebyshev": None,
    "duplicate": False,
    "reverse_arrhenius": None,
    "raw_aux_lines": [],
    "evaluations": [],
}
```

`evaluations` 用于保存不同温度/压力下的计算结果，例如 `delta_S_J_per_mol_K`、`delta_H_J_per_mol`、`Kp_dimensionless`、`Kc`、`kf`、`kr`。

### `ReactionThermoKinetics`

针对一条反应记录及给定温度，计算：

1. `cal_s_h()`：按净计量系数计算 `ΔS` 和 `ΔH`；
2. `cal_k_p()`：使用 `ln Kp = ΔS/R - ΔH/(RT)` 得到无量纲热力学平衡常数；
3. `cal_k_c()`：将 `Kp` 换算为基于 SI 浓度（mol/m³）的 `Kc`；
4. `cal_k_f()`：根据修正 Arrhenius 表达式计算正向速率常数；
5. `cal_k_r()`：按 `kr = kf/Kc` 计算逆向速率常数。

热力学求和要求物种的 `H`、`S` 已先按相同温度计算。推荐调用顺序为：

```python
calculator.cal_s_h()
calculator.cal_k_p()
calculator.cal_k_c()
calculator.cal_k_f()
calculator.cal_k_r()
```

## 辅助行与压力依赖反应

`parse_chemkin_aux_line()` 当前识别或处理：

- `LOW/`：低压极限 Arrhenius 参数；
- `HIGH/`：高压极限 Arrhenius 参数；
- `TROE/`：Troe 展宽参数；
- `SRI/`：解析 3 或 5 个参数；
- `DUPLICATE`、`REV/`：当前主要记录类型标记；
- 其他斜杠行：按第三体效率行解析物种名和效率。

`load_mechanism()` 会将辅助行信息并入当前反应记录，但这一逻辑仍在完善中。普通第三体效率应保存在：

```python
reaction_record["third_body"]["efficiencies"] = {
    "H2": 0.0,
    "CH4": 2.0,
    "AR": 0.63,
}
```

显式的零效率是有效数据，应保留；未列出的物种默认效率为 1。`TROE`/`SRI` 是 fall-off 展宽数据，不等同于普通第三体效率表。

**尚未完整实现或验证**：PLOG 与 CHEB 数据解析及速率计算；由 LOW、TROE/SRI、压力和有效第三体浓度共同计算完整 fall-off 速率；所有辅助行类型在同一反应记录上的稳定归属；重复反应和显式 REV 参数的完整数值处理。

## 单位约定与当前风险

- NASA-7 计算结果为 SI 热力学单位：`H` J/mol，`S`、`Cp` J/(mol·K)。
- CHEMKIN 默认活化能通常为 cal/mol；`cal_k_f()` 当前按默认值乘 4.184 转成 J/mol，与 `R=8.314 J/(mol·K)` 配套。机理文件中的 `UNITS` 声明尚未完整解析。
- `A` 的单位依赖反应级数及 CHEMKIN 浓度单位。当前 `cal_k_f()` 根据净计量字典的反应物负系数估算单位转换阶数；同名物种抵消、显式反应级数、普通第三体和 fall-off/LOW 参数都可能使估算不准确。
- 当前 `cal_k_f()` 对 fall-off 主行参数未完成压力修正；其结果可能只是高压极限速率，不能一概视为完整的压力相关速率常数。
- `Kc` 的单位随净气相计量变化；输出记录中的 `Kc_unit`、`kf_unit`、`kr_unit` 尚未自动推导。

## 输出

`MechanismPreprocessing.main()` 会读取机理与热力学数据、按指定温度计算物种热力学量和反应计算结果，并写出：

- `species_check.csv`：物种数据；
- `reactions_check.csv`：反应定义及 `evaluations` 计算结果。

CSV 适合人工检查；嵌套字典/列表会被序列化为单元格文本。如需供其他程序无损读取，建议额外输出 JSON。

## 当前已知限制

- `convert_to_standard()` 会将行内容大写；注释保留行为与“原样保留”的描述不完全一致。其输入输出同路径风险、编码和缺少 `END` 的处理也需谨慎。
- `load_mechanism()` / `load_therm()` 对区块标题、注释、END 标记及异常文件的边界处理仍需加强；输入应先确认符合预期 CHEMKIN/NASA-7 固定列格式。
- `parse_formula()` 对全大写物种名逐字符解析，不能可靠区分双字母元素（如 `AR`），也不完整支持括号、异构体后缀和复杂物种命名；元素组成结果需核验。
- 反应与辅助行识别以当前示例机理格式为目标，未覆盖全部 CHEMKIN 扩展关键字。
- 建议对实际使用的机理文件运行后核对元素/物种数、NASA 系数长度（每个温度区 7 个）、净计量数、辅助行参数和速率单位。
