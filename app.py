import html
import time
from io import BytesIO

import pandas as pd
import streamlit as st


# =============================
# 页面基础配置
# =============================
st.set_page_config(
    page_title="5G通信基建数智化交付系统",
    page_icon="📡",
    layout="wide",
)


# =============================
# 极简专业化样式
# =============================
st.markdown(
    """
    <style>
    .main-title {
        font-size: 30px;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .sub-title {
        color: #5f6b7a;
        font-size: 15px;
        margin-bottom: 22px;
    }
    .result-card {
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        padding: 22px 24px;
        background: #ffffff;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 10px 0 18px 0;
    }
    .metric-box {
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        padding: 12px 14px;
        background: #f8fafc;
    }
    .metric-label {
        color: #64748b;
        font-size: 13px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        margin-top: 2px;
    }
    div.stButton > button[kind="primary"] {
        background-color: #16a34a;
        border-color: #16a34a;
        color: #ffffff;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #15803d;
        border-color: #15803d;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================
# 模拟数据：未上传文件时用于演示
# =============================
def build_demo_dataframe() -> pd.DataFrame:
    """生成前序设计软件导出的基站设计元数据样例。"""
    return pd.DataFrame(
        [
            ["GD-GZ-5G-001", "宏站", "AAU5636", "BBU5900", 85, "市电直供"],
            ["GD-GZ-5G-002", "楼面站", "AAU5639", "BBU5900", 42, "交流配电箱"],
            ["GD-SZ-5G-017", "室分站", "pRRU5935", "BBU3910", 120, "弱电井取电"],
            ["GD-FS-5G-026", "微站", "AAU5339", "BBU5900", 28, "路灯杆取电"],
            ["GD-DG-5G-031", "宏站", "AAU5636", "BBU5900", 96, "市电直供"],
        ],
        columns=["站点编号", "站点类型", "AAU型号", "BBU型号", "线缆敷设距离", "取电方式"],
    )


# =============================
# 文件读取：支持 CSV 与 Excel
# =============================
def load_design_file(uploaded_file) -> pd.DataFrame:
    """读取上传的设计元数据表，并返回 DataFrame。"""
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):
        raw = uploaded_file.getvalue()
        try:
            return pd.read_csv(BytesIO(raw), encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(BytesIO(raw), encoding="gbk")

    return pd.read_excel(uploaded_file)


# =============================
# 报告导出：生成 Word 可打开的 HTML 文档
# =============================
def build_word_report(report_text: str, data: pd.DataFrame, mode: str) -> bytes:
    """
    生成可下载的 .doc 文件内容。
    为保持 Demo 极简，不引入 python-docx；Word/WPS 可直接打开 HTML 格式的 .doc 文件。
    """
    preview_table = data.head(5).to_html(index=False, escape=True, border=0)
    escaped_report = html.escape(report_text)

    document = f"""
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>5G通信基建数智化交付报告</title>
    <style>
        body {{
            font-family: "Microsoft YaHei", Arial, sans-serif;
            color: #1f2937;
            line-height: 1.6;
        }}
        h1 {{
            font-size: 22px;
            border-bottom: 2px solid #16a34a;
            padding-bottom: 8px;
        }}
        .meta {{
            color: #4b5563;
            margin-bottom: 16px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0 18px;
        }}
        th, td {{
            border: 1px solid #d1d5db;
            padding: 6px 8px;
            font-size: 12px;
        }}
        th {{
            background: #f3f4f6;
        }}
        pre {{
            white-space: pre-wrap;
            font-family: "Microsoft YaHei", Arial, sans-serif;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <h1>5G通信基建数智化交付报告</h1>
    <div class="meta">生成模式：{html.escape(mode)} | 数据记录数：{len(data)}</div>
    <h2>原始数据预览</h2>
    {preview_table}
    <h2>智能转化结果</h2>
    <pre>{escaped_report}</pre>
</body>
</html>
"""
    return document.encode("utf-8")


def show_download_toast() -> None:
    """下载按钮点击后的轻量反馈。"""
    st.toast("下载成功", icon="✅")


# =============================
# Mock LLM：模拟大模型生成专业施工文档
# =============================
def mock_llm_response(data: pd.DataFrame, mode: str) -> str:
    """
    根据基站设计元数据生成伪造的专业施工指令。
    当前阶段不调用真实 API，后续可在此函数内替换为 LLM SDK 请求。
    """
    row_count = len(data)
    cable_total = int(pd.to_numeric(data.get("线缆敷设距离", 0), errors="coerce").fillna(0).sum())
    site_types = "、".join(data.get("站点类型", pd.Series(dtype=str)).dropna().astype(str).unique())
    aau_models = "、".join(data.get("AAU型号", pd.Series(dtype=str)).dropna().astype(str).unique())
    bbu_models = "、".join(data.get("BBU型号", pd.Series(dtype=str)).dropna().astype(str).unique())

    # 物料估算采用通信工程常见经验规则，便于演示“设计数据 -> 交付指令”的转化逻辑。
    power_cable = cable_total + row_count * 8
    optical_cable = cable_total + row_count * 12
    grounding_cable = row_count * 18
    labels = row_count * 24
    cable_tray = max(1, round(cable_total * 0.35))

    bom_block = f"""
## 5G通信基建数智化交付指令报告

**生成模式：** {mode}  
**站点数量：** {row_count} 个  
**站点类型：** {site_types or "未识别"}  
**设备型号：** AAU：{aau_models or "未识别"}；BBU：{bbu_models or "未识别"}  

### 一、BOM 物料统计清单

| 序号 | 物料名称 | 推荐规格 | 估算数量 | 施工用途 |
|---:|---|---|---:|---|
| 1 | 室外电源线 | RVVZ 3x6mm² | {power_cable} 米 | AAU/BBU 供电接入 |
| 2 | 室外光缆 | GYTA-12B1 | {optical_cable} 米 | BBU 至 AAU 前传链路 |
| 3 | 保护接地线 | BVR 16mm² 黄绿双色 | {grounding_cable} 米 | 机柜、抱杆、AAU 接地 |
| 4 | 线缆标识牌 | 防水阻燃型 | {labels} 个 | 电源线、光缆、尾纤双端标识 |
| 5 | 镀锌桥架/线槽 | 100x50mm | {cable_tray} 米 | 楼面及弱电井线缆保护 |
| 6 | 防水胶泥与热缩套管 | 室外耐候型 | {row_count * 6} 套 | 馈线窗、穿墙孔洞封堵 |
"""

    guide_block = f"""
### 二、工序指导书

1. **进场复核**
   - 依据站点编号逐站核对设计图、设备型号、取电方式和路由长度。
   - 对楼面站、宏站需复测 AAU 挂高、抱杆垂直度及安装朝向，偏差超限时应回传设计复核。

2. **设备安装**
   - AAU 采用双螺母防松固定，安装完成后检查方位角、下倾角和端口防水帽。
   - BBU 上架前应确认机柜承重、空开容量、接地排余量和传输尾纤路由。

3. **线缆敷设**
   - 本批次设计线缆敷设距离合计约 **{cable_total} 米**，施工放缆应预留 3% 至 5% 工艺余量。
   - 电源线、光缆应分槽或分层敷设；无法分离时须增加阻燃隔板并做好交越标识。
   - 线缆转弯半径不得小于线缆外径的 10 倍，桥架内线缆填充率建议不超过 40%。

4. **上电与联调**
   - 上电前测量输入电压、接地电阻和空开容量，确认无短路、反接和松动端子。
   - 设备启动后检查 BBU-AAU 光链路、GPS/北斗同步、网管告警和小区激活状态。

### 三、安全注意事项

- 电力线与通信线交越时应保持安全净距，平行敷设距离不足时需采取隔离保护措施。
- 与强电管线交越的部位需设置明显警示标识，电力交越距离必须大于设计与现行规范规定值。
- 高处作业必须执行安全带高挂低用，楼面临边、洞口和爬梯区域需先防护后施工。
- 室外穿墙孔、馈线窗和设备端口应完成防水封堵，防止雨水倒灌造成设备故障。
- 所有接地点必须除锈、压接牢固并做防腐处理，接地电阻应满足站点验收要求。

### 四、交付验收要点

- 上传竣工照片：设备全景、铭牌、线缆路由、接地端子、空开标签和防水封堵点。
- 提交测试记录：光功率、驻波/链路状态、接地电阻、上电电压和网管无告警截图。
- 物料余量、设计变更和现场偏差需在交付单中闭环记录。
"""

    if mode == "生成BOM清单":
        return bom_block
    if mode == "生成工艺指导书":
        return "## 5G通信基建数智化交付指令报告\n\n" + guide_block
    return bom_block + "\n" + guide_block


# =============================
# 侧边栏：配置与控制台
# =============================
with st.sidebar:
    st.header("配置与控制台")

    uploaded_file = st.file_uploader(
        "上传基站设计元数据表",
        type=["xlsx", "csv"],
        help="支持前序设计软件导出的 Excel 或 CSV 结构化表格。",
    )

    mode = st.selectbox(
        "生成模式",
        ["生成BOM清单", "生成工艺指导书", "全量生成"],
        index=2,
    )

    start_button = st.button(
        "🚀 启动数智化指令转化",
        type="primary",
        use_container_width=True,
    )


# =============================
# 主区域：标题与数据源处理
# =============================
st.markdown('<div class="main-title">5G通信基建数智化交付系统 (Demo 版)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">读取设计元数据表，自动生成施工 BOM 与工序指导书。</div>',
    unsafe_allow_html=True,
)

try:
    df = load_design_file(uploaded_file) if uploaded_file else build_demo_dataframe()
except Exception as exc:
    st.error(f"文件读取失败，请检查表头、编码或文件格式。错误信息：{exc}")
    st.stop()


# =============================
# 主区域上方：原始数据透视
# =============================
st.subheader("原始数据透视")
if uploaded_file:
    st.caption(f"当前数据源：{uploaded_file.name}")
else:
    st.caption("当前数据源：系统内置模拟数据")

st.dataframe(df.head(5), use_container_width=True, hide_index=True)

st.markdown(
    f"""
    <div class="metric-strip">
        <div class="metric-box">
            <div class="metric-label">记录数</div>
            <div class="metric-value">{len(df)}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">字段数</div>
            <div class="metric-value">{len(df.columns)}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">生成模式</div>
            <div class="metric-value" style="font-size: 18px;">{mode}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================
# 主区域下方：智能转化结果
# =============================
st.subheader("智能转化结果")

if "ai_result" not in st.session_state:
    st.session_state.ai_result = ""

if start_button:
    progress = st.progress(0, text="正在调用规则引擎与AI模型校验安全规范...")

    # 模拟 2-3 秒处理过程，呈现真实系统的任务执行反馈。
    for value in range(0, 101, 10):
        time.sleep(0.22)
        progress.progress(value, text="正在调用规则引擎与AI模型校验安全规范...")

    st.session_state.ai_result = mock_llm_response(df, mode)
    st.success("数智化指令转化完成")

if st.session_state.ai_result:
    # 使用 Streamlit 原生边框容器作为结果卡片，避免自定义 HTML 影响 markdown 表格渲染。
    with st.container(border=True):
        st.markdown(st.session_state.ai_result)

    report_bytes = build_word_report(st.session_state.ai_result, df, mode)
    st.download_button(
        "一键下载转化报告 (Word)",
        data=report_bytes,
        file_name="5G通信基建数智化交付报告.doc",
        mime="application/msword",
        use_container_width=True,
        on_click=show_download_toast,
    )
else:
    st.info("请在左侧配置生成模式后，点击“启动数智化指令转化”。")


# =============================
# requirements.txt 依赖包列表
# streamlit
# pandas
# openpyxl
# =============================
