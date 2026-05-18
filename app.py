import html
import hashlib
import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib import error, request

import pandas as pd
import streamlit as st


REQUIRED_COLUMNS = ["站点编号", "站点类型", "AAU型号", "BBU型号", "线缆敷设距离", "取电方式"]
DEFAULT_API_TIMEOUT = 180
DEFAULT_SAMPLE_ROWS = 30
RECENT_FILE_LIMIT = 10
CACHE_DIR = Path(__file__).resolve().parent / ".design_file_cache"
CACHE_INDEX_FILE = CACHE_DIR / "index.json"
REVIEW_REQUIRED_FIELDS = [
    "site_id",
    "site_name",
    "site_type",
    "cable_distance_m",
    "power_supply_mode",
    "fiber_core_count",
    "fiber_start",
    "fiber_end",
]
REVIEW_FIELD_ALIASES = {
    "site_id": ["site_id", "站点编号"],
    "site_name": ["site_name", "站点名称"],
    "site_type": ["site_type", "站点类型"],
    "cable_distance_m": ["cable_distance_m", "线缆敷设距离"],
    "power_supply_mode": ["power_supply_mode", "取电方式"],
    "fiber_core_count": ["fiber_core_count", "纤芯数量", "纤芯数"],
    "fiber_start": ["fiber_start", "纤芯起点", "光缆起点"],
    "fiber_end": ["fiber_end", "纤芯终点", "光缆终点"],
}


# =============================
# 页面基础配置
# =============================
st.set_page_config(
    page_title="5G通信基建数智化交付系统",
    page_icon="5G",
    layout="wide",
)


# =============================
# 极简专业化样式
# =============================
st.markdown(
    """
    <style>
    :root {
        --ink: #111827;
        --muted: #6b7280;
        --line: #e5e7eb;
        --panel: #ffffff;
        --soft: #f8fafc;
        --accent: #2563eb;
        --accent-dark: #1d4ed8;
        --accent-soft: #eff6ff;
        --ok: #0f766e;
        --ok-soft: #f0fdfa;
    }
    .stApp {
        background: #f4f6f8;
        color: var(--ink);
    }
    [data-testid="stHeader"] {
        background: rgba(244, 246, 248, 0.9);
        backdrop-filter: blur(10px);
    }
    [data-testid="stToolbar"] {
        opacity: 0.35;
    }
    .block-container {
        max-width: 1240px;
        padding-top: 44px;
        padding-bottom: 48px;
    }
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    section[data-testid="stSidebar"] * {
        color: var(--ink);
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stCaption {
        color: #374151 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
        border: 1px dashed #cbd5e1;
        border-radius: 8px;
        padding: 10px;
        background: #f9fafb;
    }
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] textarea,
    section[data-testid="stSidebar"] select {
        color: var(--ink) !important;
    }
    section[data-testid="stSidebar"] [data-baseweb="select"] * {
        color: var(--ink) !important;
    }
    .sidebar-brand {
        border: 1px solid #e5e7eb;
        background: #ffffff;
        border-radius: 8px;
        padding: 14px 14px 13px;
        margin: 8px 0 18px;
        box-shadow: 0 1px 2px rgba(17, 24, 39, 0.03);
    }
    .brand-mark {
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background: linear-gradient(135deg, #111827 0%, #0f766e 100%);
        color: #ffffff;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 15px;
        font-weight: 800;
        margin-bottom: 10px;
    }
    .brand-title {
        color: #111827;
        font-size: 15px;
        font-weight: 800;
        line-height: 1.3;
    }
    .brand-sub {
        color: #6b7280;
        font-size: 12px;
        margin-top: 4px;
    }
    .hero-shell {
        border: 1px solid #e5e7eb;
        background: #ffffff;
        border-radius: 8px;
        padding: 24px 26px 22px;
        margin-bottom: 20px;
        box-shadow: 0 10px 28px rgba(17, 24, 39, 0.055);
    }
    .hero-topline {
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(250px, 360px);
        gap: 22px;
        align-items: start;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        border: 1px solid #99f6e4;
        background: var(--ok-soft);
        color: var(--ok);
        border-radius: 6px;
        padding: 5px 9px;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 12px;
    }
    .main-title {
        color: var(--ink);
        font-size: 32px;
        line-height: 1.15;
        font-weight: 800;
        margin-bottom: 10px;
        letter-spacing: 0;
    }
    .sub-title {
        color: var(--muted);
        font-size: 15px;
        margin-bottom: 0;
        max-width: 780px;
    }
    .hero-chip-row {
        display: grid;
        gap: 8px;
        margin-top: 2px;
    }
    .hero-chip {
        border: 1px solid #e5e7eb;
        background: #f8fafc;
        color: #374151;
        border-radius: 8px;
        padding: 9px 11px;
        font-size: 12px;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }
    .workflow-row {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-top: 22px;
    }
    .workflow-step {
        border: 1px solid #e5e7eb;
        border-top: 3px solid #94a3b8;
        border-radius: 8px;
        background: #f8fafc;
        padding: 12px 12px 11px;
    }
    .workflow-kicker {
        color: #2563eb;
        font-size: 11px;
        font-weight: 800;
        margin-bottom: 3px;
        text-transform: uppercase;
    }
    .workflow-title {
        color: #111827;
        font-size: 13px;
        font-weight: 750;
    }
    .section-card {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
        padding: 16px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
        margin-bottom: 16px;
    }
    .section-title {
        color: var(--ink);
        font-size: 16px;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .section-note {
        color: var(--muted);
        font-size: 13px;
        margin-bottom: 12px;
    }
    .result-card {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 22px 24px;
        background: var(--panel);
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
    }
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 0 0 22px 0;
    }
    .metric-box {
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 16px 17px;
        background: var(--panel);
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.04);
    }
    .metric-label {
        color: var(--muted);
        font-size: 13px;
    }
    .metric-value {
        color: var(--ink);
        font-size: 24px;
        font-weight: 700;
        margin-top: 4px;
        line-height: 1.2;
    }
    div.stButton > button[kind="primary"] {
        background-color: var(--accent);
        border-color: var(--accent);
        color: #ffffff;
        font-weight: 800;
        border-radius: 8px;
        min-height: 46px;
        box-shadow: 0 8px 16px rgba(37, 99, 235, 0.18);
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: var(--accent-dark);
        border-color: var(--accent-dark);
        color: #ffffff;
    }
    div.stDownloadButton > button {
        border-radius: 8px;
        min-height: 44px;
        font-weight: 800;
    }
    .report-hint {
        border-left: 4px solid var(--accent);
        background: #eff6ff;
        color: #1e3a8a;
        padding: 12px 14px;
        border-radius: 8px;
        margin: 10px 0 18px;
        font-size: 14px;
    }
    .phase-box {
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
        padding: 16px;
        margin: 12px 0;
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.04);
    }
    .phase-line {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        font-size: 14px;
        color: #334155;
    }
    .phase-percent {
        color: var(--accent);
        font-weight: 700;
    }
    .data-card {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
        padding: 18px;
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.04);
        min-height: 100%;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
        background: #ffffff;
    }
    div[data-testid="stAlert"] {
        border-radius: 8px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 8px;
        border-color: #e5e7eb;
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.035);
    }
    .report-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 6px 0 16px;
    }
    .report-module {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
        padding: 15px 16px;
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.035);
    }
    .report-module-label {
        color: #64748b;
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 7px;
    }
    .report-module-value {
        color: #111827;
        font-size: 20px;
        line-height: 1.25;
        font-weight: 800;
        overflow-wrap: anywhere;
    }
    .report-module-note {
        color: #64748b;
        font-size: 12px;
        line-height: 1.45;
        margin-top: 7px;
    }
    .acceptance-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        margin: 6px 0 16px;
    }
    .acceptance-item {
        border: 1px solid #e5e7eb;
        border-left: 3px solid #0f766e;
        border-radius: 8px;
        background: #ffffff;
        padding: 13px 14px;
    }
    .acceptance-title {
        color: #111827;
        font-size: 14px;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .acceptance-copy {
        color: #475569;
        font-size: 13px;
        line-height: 1.5;
    }
    .section-divider {
        color: #64748b;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
        margin: 4px 0 10px;
    }
    .taste-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        border: 1px solid rgba(226, 232, 240, 0.9);
        background: rgba(255, 255, 255, 0.82);
        backdrop-filter: blur(16px);
        border-radius: 999px;
        padding: 13px 18px 13px 20px;
        margin: 6px auto 22px;
        min-height: 52px;
        line-height: 1.4;
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.06);
    }
    .taste-nav-brand {
        color: #0f172a;
        font-size: 13px;
        font-weight: 850;
        letter-spacing: 0;
        line-height: 1.45;
    }
    .taste-nav-links {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 18px;
        color: #475569;
        font-size: 12px;
        font-weight: 750;
        line-height: 1.45;
    }
    .taste-hero {
        position: relative;
        overflow: hidden;
        border-radius: 14px;
        min-height: 430px;
        padding: 58px 46px 34px;
        margin-bottom: 18px;
        color: #ffffff;
        border: 1px solid rgba(15, 23, 42, 0.12);
        background:
            radial-gradient(circle at 18% 18%, rgba(15, 118, 110, 0.36), transparent 32%),
            radial-gradient(circle at 82% 68%, rgba(37, 99, 235, 0.26), transparent 30%),
            linear-gradient(135deg, #111827 0%, #172033 48%, #0f2f2c 100%);
        background-size: cover;
        background-position: center;
        box-shadow: 0 24px 70px rgba(15, 23, 42, 0.24);
    }
    .taste-hero::after {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background-image: linear-gradient(rgba(255,255,255,0.055) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px);
        background-size: 44px 44px;
        mask-image: linear-gradient(180deg, rgba(0,0,0,0.45), transparent 80%);
    }
    .taste-hero-inner {
        position: relative;
        z-index: 1;
        max-width: 1040px;
        margin: 0 auto;
        text-align: center;
    }
    .product-lockup {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        margin: 0 auto 24px;
        color: rgba(255,255,255,0.92);
    }
    .product-lockup-main {
        font-size: 18px;
        font-weight: 900;
        letter-spacing: 0.12em;
    }
    .product-lockup-line {
        width: 92px;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent);
    }
    .taste-hero-title {
        color: #ffffff;
        font-size: clamp(42px, 5.2vw, 74px);
        line-height: 1.04;
        font-weight: 900;
        letter-spacing: 0;
        margin: 0 auto 18px;
        max-width: 980px;
        text-wrap: balance;
    }
    .taste-hero-copy {
        display: block;
        max-width: 820px;
        margin: 0 auto;
        color: rgba(255, 255, 255, 0.82);
        font-size: 16px;
        line-height: 1.75;
        text-align: center !important;
        text-wrap: balance;
    }
    .hero-action-row {
        max-width: 540px;
        margin: 18px auto 34px;
        position: relative;
        z-index: 2;
        padding: 0;
        border: 0;
        background: transparent;
        box-shadow: none;
    }
    .hero-action-row div.stButton > button {
        border-radius: 999px;
        min-height: 44px;
        font-weight: 850;
    }
    .status-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 0 0 24px;
    }
    .status-cell {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
        padding: 13px 14px;
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.035);
    }
    .status-cell span {
        display: block;
        color: #64748b;
        font-size: 11px;
        font-weight: 800;
        margin-bottom: 5px;
        text-transform: uppercase;
    }
    .status-cell strong {
        color: #111827;
        font-size: 14px;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }
    .bento-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        grid-auto-flow: dense;
        gap: 12px;
        margin: 8px 0 26px;
    }
    .bento-card {
        position: relative;
        overflow: hidden;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        min-height: 156px;
        background: #ffffff;
        padding: 18px;
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.04);
        transition: transform 700ms ease, box-shadow 700ms ease;
    }
    .bento-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 18px 44px rgba(15, 23, 42, 0.10);
    }
    .bento-large { grid-column: span 2; grid-row: span 2; min-height: 324px; }
    .bento-wide { grid-column: span 2; }
    .bento-dark {
        color: #ffffff;
        background:
            radial-gradient(circle at 12% 16%, rgba(20, 184, 166, 0.30), transparent 34%),
            radial-gradient(circle at 86% 68%, rgba(148, 163, 184, 0.20), transparent 30%),
            linear-gradient(145deg, #111827 0%, #1f2937 58%, #0f766e 140%);
    }
    .bento-kicker {
        color: #2563eb;
        font-size: 11px;
        font-weight: 900;
        margin-bottom: 8px;
        text-transform: uppercase;
    }
    .bento-dark .bento-kicker { color: #99f6e4; }
    .bento-title {
        color: inherit;
        font-size: 22px;
        line-height: 1.12;
        font-weight: 900;
        max-width: 360px;
    }
    .bento-copy {
        color: #64748b;
        font-size: 13px;
        line-height: 1.65;
        margin-top: 12px;
        max-width: 420px;
    }
    .bento-dark .bento-copy { color: rgba(255,255,255,0.74); }
    .bento-number {
        position: absolute;
        right: 16px;
        bottom: 12px;
        color: rgba(15, 23, 42, 0.08);
        font-size: 56px;
        line-height: 1;
        font-weight: 950;
    }
    .result-stage {
        border: 1px solid #dbe3ea;
        border-radius: 16px;
        background:
            linear-gradient(180deg, rgba(255,255,255,0.94), rgba(248,250,252,0.96)),
            radial-gradient(circle at 12% 8%, rgba(15,118,110,0.10), transparent 32%);
        padding: 18px;
        box-shadow: 0 20px 42px rgba(15, 23, 42, 0.07);
    }
    .download-band {
        border: 1px solid #dbe3ea;
        border-radius: 14px;
        background: #ffffff;
        padding: 16px;
        margin-top: 14px;
        box-shadow: 0 1px 3px rgba(17, 24, 39, 0.04);
    }
    .download-title {
        color: #0f172a;
        font-size: 15px;
        font-weight: 900;
        margin-bottom: 4px;
    }
    .download-copy {
        color: #64748b;
        font-size: 13px;
        margin-bottom: 12px;
    }
    @media (max-width: 900px) {
        .main-title {
            font-size: 26px;
        }
        .hero-topline {
            grid-template-columns: 1fr;
        }
        .hero-shell {
            padding: 18px;
        }
        .workflow-row {
            grid-template-columns: 1fr;
        }
        .metric-strip {
            grid-template-columns: 1fr;
        }
        .report-grid,
        .acceptance-grid,
        .status-strip,
        .bento-grid {
            grid-template-columns: 1fr;
        }
        .taste-nav {
            border-radius: 12px;
            align-items: flex-start;
            flex-direction: column;
        }
        .taste-nav-links {
            flex-wrap: wrap;
            justify-content: flex-start;
        }
        .taste-hero {
            min-height: 360px;
            padding: 42px 20px 28px;
        }
        .taste-hero-title {
            font-size: 38px;
        }
        .bento-large,
        .bento-wide {
            grid-column: span 1;
            grid-row: span 1;
            min-height: 190px;
        }
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
            [
                "GD-GZ-5G-001",
                "广州天河宏站",
                "宏站",
                "AAU5636",
                "BBU5900",
                85,
                "市电直供",
                "GD-GZ-5G-001",
                "广州天河宏站",
                "macro",
                85,
                "市电",
                12,
                "ODF-A-01",
                "AAU-001",
            ],
            [
                "GD-GZ-5G-002",
                "广州越秀楼面站",
                "楼面站",
                "AAU5639",
                "BBU5900",
                42,
                "交流配电箱",
                "GD-GZ-5G-002",
                "广州越秀楼面站",
                "roof",
                42,
                "转供电",
                24,
                "ODF-A-02",
                "AAU-002",
            ],
            [
                "GD-SZ-5G-017",
                "深圳南山室分站",
                "室分站",
                "pRRU5935",
                "BBU3910",
                120,
                "弱电井取电",
                "GD-SZ-5G-017",
                "深圳南山室分站",
                "indoor",
                120,
                "转供电",
                24,
                "ODF-B-01",
                "pRRU-017",
            ],
            [
                "GD-FS-5G-026",
                "佛山禅城微站",
                "微站",
                "AAU5339",
                "BBU5900",
                28,
                "路灯杆取电",
                "GD-FS-5G-026",
                "佛山禅城微站",
                "micro",
                28,
                "市电",
                12,
                "ODF-C-01",
                "AAU-026",
            ],
            [
                "GD-DG-5G-031",
                "东莞松山湖宏站",
                "宏站",
                "AAU5636",
                "BBU5900",
                96,
                "市电直供",
                "GD-DG-5G-031",
                "东莞松山湖宏站",
                "macro",
                96,
                "市电",
                12,
                "ODF-D-01",
                "AAU-031",
            ],
        ],
        columns=[
            "站点编号",
            "站点名称",
            "站点类型",
            "AAU型号",
            "BBU型号",
            "线缆敷设距离",
            "取电方式",
            "site_id",
            "site_name",
            "site_type",
            "cable_distance_m",
            "power_supply_mode",
            "fiber_core_count",
            "fiber_start",
            "fiber_end",
        ],
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

    return pd.read_excel(BytesIO(uploaded_file.getvalue()))


class CachedDesignFile:
    """把缓存文件包装成与 Streamlit UploadedFile 兼容的轻量对象。"""

    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content

    def read(self, *args, **kwargs) -> bytes:
        return BytesIO(self._content).read(*args, **kwargs)

    def seek(self, position: int) -> int:
        return BytesIO(self._content).seek(position)


def load_recent_file_index() -> list[dict]:
    """读取最近上传文件缓存索引。"""
    if not CACHE_INDEX_FILE.exists():
        return []
    try:
        with CACHE_INDEX_FILE.open("r", encoding="utf-8") as file:
            index_data = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []
    return index_data if isinstance(index_data, list) else []


def save_recent_file_index(index_data: list[dict]) -> None:
    """保存最近上传文件缓存索引。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with CACHE_INDEX_FILE.open("w", encoding="utf-8") as file:
        json.dump(index_data[:RECENT_FILE_LIMIT], file, ensure_ascii=False, indent=2)


def cache_design_files(uploaded_files) -> list[dict]:
    """缓存本次上传文件，并保留最近 10 份。"""
    if not uploaded_files:
        return load_recent_file_index()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    index_data = load_recent_file_index()
    existing_by_key = {item.get("cache_key"): item for item in index_data}

    for uploaded_file in uploaded_files:
        content = uploaded_file.getvalue()
        digest = hashlib.sha256(content).hexdigest()[:16]
        suffix = Path(uploaded_file.name).suffix.lower() or ".dat"
        cache_key = f"{digest}{suffix}"
        cache_path = CACHE_DIR / cache_key
        cache_path.write_bytes(content)
        existing_by_key[cache_key] = {
            "cache_key": cache_key,
            "name": uploaded_file.name,
            "size": len(content),
            "cached_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    sorted_index = sorted(existing_by_key.values(), key=lambda item: item.get("cached_at", ""), reverse=True)
    trimmed_index = sorted_index[:RECENT_FILE_LIMIT]

    valid_keys = {item["cache_key"] for item in trimmed_index}
    for cached_file in CACHE_DIR.iterdir():
        if cached_file.is_file() and cached_file.name != CACHE_INDEX_FILE.name and cached_file.name not in valid_keys:
            cached_file.unlink(missing_ok=True)

    save_recent_file_index(trimmed_index)
    return trimmed_index


def load_cached_design_file(cache_item: dict) -> CachedDesignFile | None:
    """从缓存读取一份设计文件。"""
    cache_key = cache_item.get("cache_key")
    if not cache_key:
        return None
    cache_path = CACHE_DIR / cache_key
    if not cache_path.exists():
        return None
    return CachedDesignFile(cache_item.get("name", cache_key), cache_path.read_bytes())


def summarize_batch_files(files: list) -> pd.DataFrame:
    """对批量上传文件生成轻量处理概览。"""
    rows = []
    for file in files:
        try:
            batch_df = load_design_file(file)
            review_df, summary = run_design_review(batch_df)
            rows.append(
                {
                    "文件名": file.name,
                    "记录数": len(batch_df),
                    "总体结论": summary["conclusion"],
                    "错误": summary["error_count"],
                    "高风险": summary["warning_count"],
                    "提醒": summary["info_count"],
                    "正常": summary["normal_count"],
                    "状态": "可生成" if not summary["has_error"] else "需修改",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "文件名": getattr(file, "name", "未知文件"),
                    "记录数": 0,
                    "总体结论": "读取失败",
                    "错误": 1,
                    "高风险": 0,
                    "提醒": 0,
                    "正常": 0,
                    "状态": f"失败：{exc}",
                }
            )
    return pd.DataFrame(rows)


def attach_review_source(review_df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    """给审查明细追加来源文件，方便批量上传时定位问题。"""
    sourced_df = review_df.copy()
    if "source_file" not in sourced_df.columns:
        sourced_df.insert(0, "source_file", source_file)
    else:
        sourced_df["source_file"] = source_file
    return sourced_df


def build_batch_review_result(files: list) -> tuple[pd.DataFrame, dict]:
    """汇总批量上传文件的审查明细。"""
    review_frames = []
    total_rows = 0
    for file in files:
        source_file = getattr(file, "name", "未知文件")
        try:
            batch_df = load_design_file(file)
            file_review_df, _ = run_design_review(batch_df)
            total_rows += len(batch_df)
            review_frames.append(attach_review_source(file_review_df, source_file))
        except Exception as exc:
            review_frames.append(
                pd.DataFrame(
                    [
                        {
                            "source_file": source_file,
                            "check_item": "文件读取审查",
                            "level": "error",
                            "message": f"文件读取失败：{exc}",
                            "field": "-",
                            "row_index": "-",
                            "site_id": "-",
                            "suggestion": "检查文件格式、编码和表头后重新上传。",
                        }
                    ]
                )
            )

    if review_frames:
        batch_review_df = pd.concat(review_frames, ignore_index=True)
    else:
        batch_review_df = pd.DataFrame(
            columns=["source_file", "check_item", "level", "message", "field", "row_index", "site_id", "suggestion"]
        )
    return batch_review_df, build_review_summary(batch_review_df, total_rows)


# =============================
# 数据校验与规则引擎
# =============================
def validate_design_data(data: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """校验设计元数据表结构，并返回清洗后的 DataFrame。"""
    errors = []
    warnings = []
    cleaned = data.copy()

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in cleaned.columns]
    if missing_columns:
        errors.append("缺少必填字段：" + "、".join(missing_columns))
        return cleaned, errors, warnings

    cable_distance = pd.to_numeric(cleaned["线缆敷设距离"], errors="coerce")
    invalid_distance_count = int(cable_distance.isna().sum())
    negative_distance_count = int((cable_distance < 0).sum())

    if invalid_distance_count:
        warnings.append(f"有 {invalid_distance_count} 行线缆敷设距离无法识别，已按 0 米估算。")
    if negative_distance_count:
        warnings.append(f"有 {negative_distance_count} 行线缆敷设距离为负数，已按 0 米估算。")

    cleaned["线缆敷设距离"] = cable_distance.fillna(0).clip(lower=0)

    empty_site_count = int(cleaned["站点编号"].isna().sum())
    if empty_site_count:
        warnings.append(f"有 {empty_site_count} 行站点编号为空，建议补齐后再用于正式交付。")

    return cleaned, errors, warnings


def get_review_column(data: pd.DataFrame, canonical_field: str) -> str | None:
    """返回审查字段在当前表中的实际列名，兼容英文标准字段与中文演示字段。"""
    for candidate in REVIEW_FIELD_ALIASES.get(canonical_field, [canonical_field]):
        if candidate in data.columns:
            return candidate
    return None


def get_review_site_ids(data: pd.DataFrame) -> pd.Series:
    """取得审查明细中展示的站点编号。"""
    site_column = get_review_column(data, "site_id")
    if site_column:
        return data[site_column].fillna("").astype(str)
    return pd.Series([""] * len(data), index=data.index)


def format_review_scope(data: pd.DataFrame, mask: pd.Series) -> tuple[str, str]:
    """将问题涉及的行号和站点编号压缩成适合页面展示的文本。"""
    matched = data.loc[mask]
    row_indexes = "、".join(str(int(index) + 2) for index in matched.index[:20])
    site_ids = get_review_site_ids(data).loc[mask]
    site_text = "、".join(site_ids[site_ids != ""].drop_duplicates().head(20).tolist())
    return row_indexes or "-", site_text or "-"


def add_review_row(
    rows: list[dict],
    check_item: str,
    level: str,
    message: str,
    field: str,
    row_index: str = "-",
    site_id: str = "-",
    suggestion: str = "-",
) -> None:
    """追加一条标准格式审查结果。"""
    rows.append(
        {
            "check_item": check_item,
            "level": level,
            "message": message,
            "field": field,
            "row_index": row_index,
            "site_id": site_id,
            "suggestion": suggestion,
        }
    )


def run_design_review(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """执行赛道3轻量智能审查，返回审查明细和汇总结论。"""
    rows: list[dict] = []
    total_rows = len(data)
    site_ids = get_review_site_ids(data)

    for required_field in REVIEW_REQUIRED_FIELDS:
        actual_column = get_review_column(data, required_field)
        if not actual_column:
            add_review_row(
                rows,
                "字段完整性审查",
                "error",
                f"缺少必填字段 {required_field}。",
                required_field,
                suggestion="补充该字段后重新上传设计数据。",
            )
            continue

        empty_mask = data[actual_column].isna() | (data[actual_column].astype(str).str.strip() == "")
        if empty_mask.any():
            row_index, site_id = format_review_scope(data, empty_mask)
            add_review_row(
                rows,
                "字段完整性审查",
                "error",
                f"{required_field} 存在空值，共 {int(empty_mask.sum())} 行。",
                actual_column,
                row_index,
                site_id,
                "补齐空值，避免后续 BOM 与施工资料生成口径不完整。",
            )
        else:
            add_review_row(
                rows,
                "字段完整性审查",
                "normal",
                f"{required_field} 已提供且无空值。",
                actual_column,
                suggestion="保持当前字段口径。",
            )

    distance_column = get_review_column(data, "cable_distance_m")
    if distance_column:
        distance = pd.to_numeric(data[distance_column], errors="coerce")
        invalid_mask = distance.isna()
        non_positive_mask = distance.notna() & (distance <= 0)
        high_risk_mask = distance > 500
        attention_mask = distance.between(100, 500, inclusive="both")
        normal_mask = distance.gt(0) & distance.lt(100)

        if invalid_mask.any():
            row_index, site_id = format_review_scope(data, invalid_mask)
            add_review_row(rows, "线缆距离异常审查", "error", "线缆距离存在无法转换为数值的记录。", distance_column, row_index, site_id, "改为米制数值，例如 85。")
        if non_positive_mask.any():
            row_index, site_id = format_review_scope(data, non_positive_mask)
            add_review_row(rows, "线缆距离异常审查", "error", "线缆距离小于等于 0。", distance_column, row_index, site_id, "复核设计路由并填写大于 0 的敷设距离。")
        if high_risk_mask.any():
            row_index, site_id = format_review_scope(data, high_risk_mask)
            add_review_row(rows, "线缆距离异常审查", "warning", "线缆距离大于 500 米，属于高风险路由。", distance_column, row_index, site_id, "建议施工前复勘路由、桥架容量和中间牵引点。")
        if attention_mask.any():
            row_index, site_id = format_review_scope(data, attention_mask)
            add_review_row(rows, "线缆距离异常审查", "info", "线缆距离在 100 到 500 米之间，需关注放缆组织。", distance_column, row_index, site_id, "建议在施工任务单中提示路由复核和余量控制。")
        if normal_mask.any() and not (invalid_mask.any() or non_positive_mask.any() or high_risk_mask.any() or attention_mask.any()):
            add_review_row(rows, "线缆距离异常审查", "normal", "线缆距离均在 0 到 100 米正常区间。", distance_column, suggestion="可进入规则估算。")

    site_column = get_review_column(data, "site_id")
    if site_column:
        duplicated_mask = data[site_column].fillna("").astype(str).str.strip().duplicated(keep=False)
        duplicated_mask &= data[site_column].fillna("").astype(str).str.strip() != ""
        if duplicated_mask.any():
            row_index, site_id = format_review_scope(data, duplicated_mask)
            add_review_row(rows, "站点编号重复审查", "error", "存在重复站点编号。", site_column, row_index, site_id, "检查站点编号唯一性，避免施工资料串站。")
        else:
            add_review_row(rows, "站点编号重复审查", "normal", "站点编号未发现重复。", site_column, suggestion="保持唯一编号规则。")

    fiber_count_column = get_review_column(data, "fiber_core_count")
    if fiber_count_column:
        raw_fiber_count = data[fiber_count_column]
        fiber_count = pd.to_numeric(raw_fiber_count, errors="coerce")
        invalid_fiber_mask = fiber_count.isna() | (fiber_count % 1 != 0)
        non_positive_fiber_mask = fiber_count.notna() & (fiber_count <= 0)
        allocation_required_mask = fiber_count >= 24

        if invalid_fiber_mask.any():
            row_index, site_id = format_review_scope(data, invalid_fiber_mask)
            add_review_row(rows, "纤芯占用异常审查", "error", "纤芯数量不是有效整数。", fiber_count_column, row_index, site_id, "填写正整数纤芯数量。")
        if non_positive_fiber_mask.any():
            row_index, site_id = format_review_scope(data, non_positive_fiber_mask)
            add_review_row(rows, "纤芯占用异常审查", "error", "纤芯数量小于等于 0。", fiber_count_column, row_index, site_id, "复核光缆资源并填写大于 0 的纤芯数量。")
        if allocation_required_mask.any():
            row_index, site_id = format_review_scope(data, allocation_required_mask)
            add_review_row(rows, "纤芯占用异常审查", "info", "纤芯数量大于等于 24，需生成纤芯分配表。", fiber_count_column, row_index, site_id, "在施工资料中同步输出纤芯分配表。")
        if not (invalid_fiber_mask.any() or non_positive_fiber_mask.any() or allocation_required_mask.any()):
            add_review_row(rows, "纤芯占用异常审查", "normal", "纤芯数量为有效正整数。", fiber_count_column, suggestion="可进入纤芯资源分配。")

    fiber_start_column = get_review_column(data, "fiber_start")
    fiber_end_column = get_review_column(data, "fiber_end")
    fiber_core_column = next((column for column in ["fiber_core_id", "fiber_core_no"] if column in data.columns), None)
    if fiber_start_column and fiber_end_column and fiber_core_column:
        composite = (
            data[fiber_start_column].fillna("").astype(str).str.strip()
            + "->"
            + data[fiber_end_column].fillna("").astype(str).str.strip()
            + "::"
            + data[fiber_core_column].fillna("").astype(str).str.strip()
        )
        occupied_mask = composite.str.endswith("::") == False
        duplicate_fiber_mask = composite[occupied_mask].duplicated(keep=False).reindex(data.index, fill_value=False)
        if duplicate_fiber_mask.any():
            row_index, site_id = format_review_scope(data, duplicate_fiber_mask)
            add_review_row(rows, "纤芯占用异常审查", "error", "同一 fiber_start、fiber_end 下存在纤芯编号重复占用。", fiber_core_column, row_index, site_id, "调整纤芯编号，确保同一路由纤芯唯一。")
    elif fiber_start_column and fiber_end_column:
        add_review_row(rows, "纤芯占用异常审查", "info", "当前数据未提供 fiber_core_id 或 fiber_core_no，暂不检查纤芯编号重复占用。", "fiber_core_id/fiber_core_no", suggestion="如需精确审查纤芯占用，请补充纤芯编号字段。")

    power_column = get_review_column(data, "power_supply_mode")
    if power_column:
        power_values = data[power_column].fillna("").astype(str).str.strip()
        normalized_power = power_values.replace({"市电直供": "市电", "交流配电箱": "转供电", "弱电井取电": "转供电", "路灯杆取电": "临时取电"})
        temporary_mask = normalized_power == "临时取电"
        transfer_mask = normalized_power == "转供电"
        unknown_mask = ~normalized_power.isin(["市电", "转供电", "临时取电"]) & (normalized_power != "")
        normal_power_mask = normalized_power == "市电"

        if temporary_mask.any():
            row_index, site_id = format_review_scope(data, temporary_mask)
            add_review_row(rows, "取电方式施工风险审查", "warning", "存在临时取电，高风险。", power_column, row_index, site_id, "需专项审批或补充安全措施后再进入正式施工。")
        if transfer_mask.any():
            row_index, site_id = format_review_scope(data, transfer_mask)
            add_review_row(rows, "取电方式施工风险审查", "info", "存在转供电，中风险。", power_column, row_index, site_id, "补充用电确认、产权边界和施工协调记录。")
        if unknown_mask.any():
            row_index, site_id = format_review_scope(data, unknown_mask)
            add_review_row(rows, "取电方式施工风险审查", "info", "取电方式存在未知或不规范取值。", power_column, row_index, site_id, "建议统一为市电、转供电或临时取电。")
        if normal_power_mask.any() and not (temporary_mask.any() or transfer_mask.any() or unknown_mask.any()):
            add_review_row(rows, "取电方式施工风险审查", "normal", "取电方式均为市电。", power_column, suggestion="可进入施工资料生成。")

    resource_fields = [field for field in ["device_id", "port_id", "resource_id", "fiber_core_id"] if field in data.columns]
    if not resource_fields:
        add_review_row(rows, "资源配置冲突审查", "info", "当前数据未提供资源字段，暂不检查资源冲突。", "device_id/port_id/resource_id/fiber_core_id", suggestion="如需资源冲突审查，请补充设备、端口、资源或纤芯编号字段。")
    else:
        has_conflict = False
        for resource_field in resource_fields:
            values = data[resource_field].fillna("").astype(str).str.strip()
            duplicate_mask = values.duplicated(keep=False) & (values != "")
            if duplicate_mask.any():
                has_conflict = True
                row_index, site_id = format_review_scope(data, duplicate_mask)
                add_review_row(rows, "资源配置冲突审查", "error", f"{resource_field} 存在重复占用。", resource_field, row_index, site_id, "调整资源配置，确保同类资源唯一占用。")
        if not has_conflict:
            add_review_row(rows, "资源配置冲突审查", "normal", "已提供资源字段，未发现重复占用。", "、".join(resource_fields), suggestion="可进入施工资料生成。")

    review_df = pd.DataFrame(rows, columns=["check_item", "level", "message", "field", "row_index", "site_id", "suggestion"])
    summary = build_review_summary(review_df, total_rows)
    return review_df, summary


def build_review_summary(review_df: pd.DataFrame, total_rows: int) -> dict:
    """根据审查明细生成统计数据和总体结论。"""
    level_counts = review_df["level"].value_counts().to_dict() if not review_df.empty else {}
    error_count = int(level_counts.get("error", 0))
    warning_count = int(level_counts.get("warning", 0))
    info_count = int(level_counts.get("info", 0))
    normal_count = int(level_counts.get("normal", 0))

    if error_count:
        conclusion = "不通过，需要修改数据"
        status_level = "error"
    elif warning_count:
        conclusion = "存在高风险"
        status_level = "warning"
    elif info_count:
        conclusion = "存在提醒"
        status_level = "info"
    else:
        conclusion = "通过 / 低风险"
        status_level = "normal"

    return {
        "total_rows": int(total_rows),
        "error_count": error_count,
        "warning_count": warning_count,
        "info_count": info_count,
        "normal_count": normal_count,
        "conclusion": conclusion,
        "status_level": status_level,
        "has_error": error_count > 0,
    }


def render_review_result(review_df: pd.DataFrame, summary: dict) -> None:
    """渲染轻量智能审查结果。"""
    st.markdown(
        """
        <div class="section-title">轻量智能审查结果</div>
        <div class="section-note">融合赛道3的前置审查能力，在生成施工资料前检查字段、距离、纤芯、取电和资源冲突。</div>
        """,
        unsafe_allow_html=True,
    )

    status_message = f"总体审查结论：{summary['conclusion']}"
    if summary["status_level"] == "error":
        st.error(status_message)
        st.error("当前设计数据存在错误项，建议修改后重新上传。系统暂不建议直接生成施工资料。")
    elif summary["status_level"] == "warning":
        st.warning(status_message)
    elif summary["status_level"] == "info":
        st.info(status_message)
    else:
        st.success(status_message)

    metric_cols = st.columns(5)
    metric_cols[0].metric("总记录数", summary["total_rows"])
    metric_cols[1].metric("错误数量", summary["error_count"])
    metric_cols[2].metric("高风险数量", summary["warning_count"])
    metric_cols[3].metric("提醒数量", summary["info_count"])
    metric_cols[4].metric("正常数量", summary["normal_count"])

    if summary["error_count"]:
        st.error(f"需要优先处理 {summary['error_count']} 项错误。")
    if summary["warning_count"]:
        st.warning(f"存在 {summary['warning_count']} 项高风险，建议生成前复核。")
    if summary["info_count"]:
        st.info(f"存在 {summary['info_count']} 项提醒，可作为施工交底关注点。")
    if summary["normal_count"]:
        st.success(f"已有 {summary['normal_count']} 项检查正常。")

    level_labels = {"error": "错误", "warning": "高风险", "info": "提醒", "normal": "正常"}
    level_order = {"错误": 0, "高风险": 1, "提醒": 2, "正常": 3}

    def render_review_table(filtered_df: pd.DataFrame) -> None:
        display_df = filtered_df.copy()
        display_df["level"] = display_df["level"].map(level_labels).fillna(display_df["level"])
        sort_columns = ["level"]
        if "source_file" in display_df.columns:
            sort_columns = ["source_file", "level"]
        display_df = display_df.sort_values(
            by=sort_columns,
            key=lambda series: series.map(level_order).fillna(9) if series.name == "level" else series,
        )
        display_df = display_df.rename(
            columns={
                "source_file": "文件来源",
                "check_item": "审查项",
                "level": "风险等级",
                "message": "问题描述",
                "field": "涉及字段",
                "row_index": "涉及行号",
                "site_id": "站点编号",
                "suggestion": "修改建议",
            }
        )

        def color_rows(row):
            color_map = {
                "错误": "background-color: #fee2e2; color: #7f1d1d;",
                "高风险": "background-color: #fef3c7; color: #78350f;",
                "提醒": "background-color: #dbeafe; color: #1e3a8a;",
                "正常": "background-color: #dcfce7; color: #14532d;",
            }
            return [color_map.get(row["风险等级"], "") for _ in row]

        st.dataframe(
            display_df.style.apply(color_rows, axis=1),
            use_container_width=True,
            hide_index=True,
        )

    all_tab, error_tab, warning_tab, info_tab, normal_tab = st.tabs(["全部明细", "错误项", "高风险项", "提醒项", "正常项"])
    review_tab_configs = [
        (all_tab, review_df, "当前没有审查明细。"),
        (error_tab, review_df[review_df["level"] == "error"], "当前没有错误项。"),
        (warning_tab, review_df[review_df["level"] == "warning"], "当前没有高风险项。"),
        (info_tab, review_df[review_df["level"] == "info"], "当前没有提醒项。"),
        (normal_tab, review_df[review_df["level"] == "normal"], "当前没有正常项记录。"),
    ]
    for review_tab, filtered_df, empty_message in review_tab_configs:
        with review_tab:
            if filtered_df.empty:
                st.info(empty_message)
            else:
                render_review_table(filtered_df)


def estimate_bom(data: pd.DataFrame) -> dict[str, int]:
    """根据通信工程经验规则估算关键物料数量。"""
    row_count = len(data)
    if "线缆敷设距离" in data.columns:
        cable_distance = pd.to_numeric(data["线缆敷设距离"], errors="coerce").fillna(0).clip(lower=0)
    else:
        cable_distance = pd.Series([0] * row_count)
    cable_total = int(cable_distance.sum())

    return {
        "site_count": row_count,
        "cable_total": cable_total,
        "power_cable": cable_total + row_count * 8,
        "optical_cable": cable_total + row_count * 12,
        "grounding_cable": row_count * 18,
        "labels": row_count * 24,
        "cable_tray": max(1, round(cable_total * 0.35)),
        "waterproof_kits": row_count * 6,
    }


def join_unique(data: pd.DataFrame, column: str) -> str:
    """拼接某列去重后的非空值。"""
    if column not in data.columns:
        return ""
    return "、".join(data[column].dropna().astype(str).unique())


def value_counts_dict(data: pd.DataFrame, column: str, limit: int = 12) -> dict[str, int]:
    """返回适合放入 LLM 上下文的字段分布。"""
    if column not in data.columns:
        return {}
    counts = data[column].fillna("未填写").astype(str).value_counts().head(limit)
    return {str(key): int(value) for key, value in counts.items()}


def build_engineering_summary(data: pd.DataFrame, sample_rows: int) -> dict:
    """将大型设计表压缩为工程摘要，避免把整表塞给大模型导致超时。"""
    bom = estimate_bom(data)
    cable_distance = pd.to_numeric(data.get("线缆敷设距离", pd.Series(dtype=float)), errors="coerce").fillna(0)
    sample_columns = [column for column in REQUIRED_COLUMNS if column in data.columns]
    long_distance_sites = []

    if "站点编号" in data.columns and "线缆敷设距离" in data.columns:
        top_rows = data.assign(线缆敷设距离=cable_distance).nlargest(min(10, len(data)), "线缆敷设距离")
        long_distance_sites = top_rows[["站点编号", "站点类型", "线缆敷设距离"]].to_dict("records")

    return {
        "record_count": int(len(data)),
        "bom_estimate": bom,
        "site_type_distribution": value_counts_dict(data, "站点类型"),
        "aau_model_distribution": value_counts_dict(data, "AAU型号"),
        "bbu_model_distribution": value_counts_dict(data, "BBU型号"),
        "power_source_distribution": value_counts_dict(data, "取电方式"),
        "cable_distance": {
            "total_m": int(cable_distance.sum()),
            "max_m": int(cable_distance.max()) if len(cable_distance) else 0,
            "avg_m": round(float(cable_distance.mean()), 2) if len(cable_distance) else 0,
            "long_distance_sites": long_distance_sites,
        },
        "sample_rows": data[sample_columns].head(sample_rows).to_dict("records") if sample_columns else [],
    }


def build_llm_context(data: pd.DataFrame, sample_rows: int) -> str:
    """生成面向外接 API 的紧凑上下文。"""
    summary = build_engineering_summary(data, sample_rows)
    return json.dumps(summary, ensure_ascii=False, indent=2)


def build_report_tables(data: pd.DataFrame, mode: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """构造页面、Word 和 Excel 复用的结构化报告表格。"""
    bom = estimate_bom(data)
    site_types = join_unique(data, "站点类型") or "未识别"
    aau_models = join_unique(data, "AAU型号") or "未识别"
    bbu_models = join_unique(data, "BBU型号") or "未识别"
    power_sources = join_unique(data, "取电方式") or "未识别"
    avg_cable = round(bom["cable_total"] / bom["site_count"], 1) if bom["site_count"] else 0
    terminal_lugs = bom["site_count"] * 10
    firestop_kits = bom["site_count"] * 4
    cable_ties = max(100, bom["cable_total"] * 2)

    overview_table = pd.DataFrame(
        [
            ["生成模式", mode],
            ["站点数量", f"{bom['site_count']} 个"],
            ["站点类型", site_types],
            ["AAU 型号", aau_models],
            ["BBU 型号", bbu_models],
            ["取电方式", power_sources],
            ["线缆路由", f"合计约 {bom['cable_total']} 米，平均约 {avg_cable} 米/站"],
            ["交付范围", "AAU/BBU 安装、前传光缆、电源接入、接地、防水封堵、基础联调"],
            ["风险重点", "电力交越安全净距、高处作业、防水封堵、隔离保护、接地闭环"],
        ],
        columns=["项目", "结论"],
    )

    bom_table = pd.DataFrame(
        [
            ["室外电源线", "RVVZ 3x6mm²", bom["power_cable"], "米", "AAU/BBU 供电接入"],
            ["室外光缆", "GYTA-12B1", bom["optical_cable"], "米", "BBU 至 AAU 前传链路"],
            ["保护接地线", "BVR 16mm² 黄绿双色", bom["grounding_cable"], "米", "机柜、抱杆、AAU 接地"],
            ["线缆标识牌", "防水阻燃型", bom["labels"], "个", "电源线、光缆、尾纤双端标识"],
            ["镀锌桥架/线槽", "100x50mm", bom["cable_tray"], "米", "楼面及弱电井线缆保护"],
            ["防水胶泥与热缩套管", "室外耐候型", bom["waterproof_kits"], "套", "馈线窗、穿墙孔洞封堵"],
            ["铜鼻子/冷压端子", "与电源线线径匹配", terminal_lugs, "个", "电源线端接压接"],
            ["防火封堵材料", "阻燃泥/防火包", firestop_kits, "套", "竖井、穿墙、机房孔洞封堵"],
            ["尼龙扎带/不锈钢扎带", "室外耐候型", cable_ties, "根", "线缆绑扎与路由整理"],
        ],
        columns=["物料名称", "推荐规格", "估算数量", "单位", "施工用途"],
    )

    acceptance_table = pd.DataFrame(
        [
            ["设备安装", "设备位置、朝向、挂高、紧固、防水、铭牌照片齐全。"],
            ["线缆工艺", "路由整齐、绑扎间距一致、转弯半径合规、标签双端一致。"],
            ["电源接入", "空开容量、输入电压、端子压接、线缆颜色和极性复核通过。"],
            ["接地系统", "接地线规格、接地点防腐、接地电阻测试记录齐全。"],
            ["光链路", "收发光功率、端口对应关系、链路状态截图齐全。"],
            ["资料闭环", "竣工图、变更记录、测试记录、隐蔽工程照片和整改记录归档。"],
        ],
        columns=["验收项", "交付要求"],
    )

    return overview_table, bom_table, acceptance_table


def build_fiber_allocation_table(data: pd.DataFrame, max_rows: int = 2000) -> pd.DataFrame:
    """根据设计数据生成纤芯分配表。"""
    site_column = get_review_column(data, "site_id")
    site_name_column = get_review_column(data, "site_name")
    fiber_start_column = get_review_column(data, "fiber_start")
    fiber_end_column = get_review_column(data, "fiber_end")
    fiber_count_column = get_review_column(data, "fiber_core_count")
    fiber_core_column = next((column for column in ["fiber_core_id", "fiber_core_no"] if column in data.columns), None)

    rows = []
    for index, record in data.iterrows():
        site_id = str(record.get(site_column, record.get("站点编号", ""))) if site_column or "站点编号" in data.columns else ""
        site_name = str(record.get(site_name_column, record.get("站点名称", ""))) if site_name_column or "站点名称" in data.columns else ""
        fiber_start = str(record.get(fiber_start_column, "")) if fiber_start_column else ""
        fiber_end = str(record.get(fiber_end_column, "")) if fiber_end_column else ""
        raw_count = record.get(fiber_count_column, 0) if fiber_count_column else 0
        fiber_count = pd.to_numeric(pd.Series([raw_count]), errors="coerce").fillna(0).iloc[0]

        if fiber_core_column and str(record.get(fiber_core_column, "")).strip():
            core_values = [str(record.get(fiber_core_column)).strip()]
        else:
            core_values = [str(core_no) for core_no in range(1, int(fiber_count) + 1)] if fiber_count > 0 and float(fiber_count).is_integer() else []

        for core_value in core_values:
            rows.append(
                {
                    "站点编号": site_id or "-",
                    "站点名称": site_name or "-",
                    "纤芯起点": fiber_start or "-",
                    "纤芯终点": fiber_end or "-",
                    "纤芯编号": core_value,
                    "占用状态": "规划占用",
                    "来源行号": int(index) + 2,
                }
            )
            if len(rows) >= max_rows:
                break
        if len(rows) >= max_rows:
            break

    if not rows:
        return pd.DataFrame(
            [{"站点编号": "-", "站点名称": "-", "纤芯起点": "-", "纤芯终点": "-", "纤芯编号": "-", "占用状态": "未提供纤芯数据", "来源行号": "-"}]
        )
    return pd.DataFrame(rows)


def markdown_to_html_fragment(markdown_text: str) -> str:
    """把生成报告中的常见 Markdown 表格/段落转成 Word 可识别的 HTML。"""
    lines = markdown_text.splitlines()
    fragments = []
    index = 0
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            fragments.append("</ul>")
            in_list = False

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            close_list()
            index += 1
            continue

        if line.startswith("|") and line.endswith("|"):
            close_list()
            table_rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                current = lines[index].strip()
                cells = [html.escape(cell.strip()) for cell in current.strip("|").split("|")]
                if not all(cell.replace("-", "").replace(":", "").strip() == "" for cell in cells):
                    table_rows.append(cells)
                index += 1
            if table_rows:
                header = table_rows[0]
                body_rows = table_rows[1:]
                fragments.append("<table><thead><tr>" + "".join(f"<th>{cell}</th>" for cell in header) + "</tr></thead><tbody>")
                for row in body_rows:
                    fragments.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
                fragments.append("</tbody></table>")
            continue

        close_list()
        if line.startswith("### "):
            fragments.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            fragments.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            in_list = True
            fragments.append("<ul>")
            while index < len(lines) and lines[index].strip().startswith("- "):
                fragments.append(f"<li>{html.escape(lines[index].strip()[2:])}</li>")
                index += 1
            continue
        else:
            fragments.append(f"<p>{html.escape(line)}</p>")
        index += 1

    close_list()
    return "\n".join(fragments)


# =============================
# 报告导出：生成 Word 可打开的 HTML 文档
# =============================
def build_word_report(report_text: str, data: pd.DataFrame, mode: str) -> bytes:
    """
    生成可下载的 .doc 文件内容。
    为保持 Demo 极简，不引入 python-docx；Word/WPS 可直接打开 HTML 格式的 .doc 文件。
    """
    overview_table, bom_table, acceptance_table = build_report_tables(data, mode)
    preview_table = data.head(5).to_html(index=False, escape=True, border=0)
    overview_html = overview_table.to_html(index=False, escape=True, border=0)
    bom_html = bom_table.to_html(index=False, escape=True, border=0)
    acceptance_html = acceptance_table.to_html(index=False, escape=True, border=0)
    report_html = markdown_to_html_fragment(report_text)

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
            font-size: 24px;
            border-bottom: 2px solid #0f766e;
            padding-bottom: 8px;
        }}
        h2 {{
            font-size: 18px;
            margin-top: 22px;
        }}
        h3 {{
            font-size: 15px;
            margin-top: 18px;
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
            border: 1px solid #cbd5e1;
            padding: 7px 9px;
            font-size: 12px;
        }}
        th {{
            background: #f1f5f9;
            color: #0f172a;
        }}
        p, li {{
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <h1>5G通信基建数智化交付报告</h1>
    <div class="meta">生成模式：{html.escape(mode)} | 数据记录数：{len(data)}</div>
    <h2>工程概况</h2>
    {overview_html}
    <h2>BOM 物料统计清单</h2>
    {bom_html}
    <h2>质量验收与交付资料</h2>
    {acceptance_html}
    <h2>原始数据预览</h2>
    {preview_table}
    <h2>完整智能转化结果</h2>
    {report_html}
</body>
</html>
"""
    return document.encode("utf-8")


def build_excel_report(report_text: str, data: pd.DataFrame, mode: str) -> bytes:
    """生成可下载的 Excel 交付工作簿。"""
    overview_table, bom_table, acceptance_table = build_report_tables(data, mode)
    fiber_table = build_fiber_allocation_table(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        overview_table.to_excel(writer, sheet_name="工程概况", index=False)
        bom_table.to_excel(writer, sheet_name="BOM物料清单", index=False)
        acceptance_table.to_excel(writer, sheet_name="质量验收", index=False)
        fiber_table.to_excel(writer, sheet_name="纤芯分配表", index=False)
        data.to_excel(writer, sheet_name="原始设计数据", index=False)
        pd.DataFrame({"报告正文": report_text.splitlines()}).to_excel(writer, sheet_name="完整报告", index=False)

        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            for column_cells in worksheet.columns:
                max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 3, 12), 42)

    output.seek(0)
    return output.getvalue()


def show_download_toast() -> None:
    """下载按钮点击后的轻量反馈。"""
    st.toast("下载成功")


def render_phase(placeholder, percent: int, title: str, detail: str) -> None:
    """渲染数字化处理阶段。"""
    placeholder.markdown(
        f"""
        <div class="phase-box">
            <div class="phase-line">
                <strong>{html.escape(title)}</strong>
                <span class="phase-percent">{percent}%</span>
            </div>
            <div style="margin-top: 6px; color: #64748b; font-size: 13px;">{html.escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report_dashboard(data: pd.DataFrame, mode: str, report_text: str) -> None:
    """按 Taste Skill 的 dashboards 风格渲染结构化报告预览。"""
    bom = estimate_bom(data)
    overview_table, bom_table, acceptance_table = build_report_tables(data, mode)
    fiber_table = build_fiber_allocation_table(data)
    site_types = join_unique(data, "站点类型") or "未识别"
    aau_models = join_unique(data, "AAU型号") or "未识别"
    bbu_models = join_unique(data, "BBU型号") or "未识别"
    power_sources = join_unique(data, "取电方式") or "未识别"
    avg_cable = round(bom["cable_total"] / bom["site_count"], 1) if bom["site_count"] else 0
    acceptance_items = list(acceptance_table.itertuples(index=False, name=None))

    overview_tab, bom_tab, acceptance_tab, fiber_tab, full_tab = st.tabs(["工程概况", "BOM", "质量验收", "纤芯分配表", "完整报告"])

    with overview_tab:
        st.caption("工程概况总览")
        metric_cols = st.columns(3)
        metric_cols[0].metric("站点数量", f"{bom['site_count']} 个", site_types)
        metric_cols[1].metric("线缆路由", f"{bom['cable_total']} m", f"平均 {avg_cable} m/站")
        metric_cols[2].metric("生成模式", mode, "与左侧控制台同步")

        detail_cols = st.columns(3)
        with detail_cols[0]:
            with st.container(border=True):
                st.markdown("**设备型号**")
                st.write(f"AAU：{aau_models}")
                st.write(f"BBU：{bbu_models}")
        with detail_cols[1]:
            with st.container(border=True):
                st.markdown("**取电方式**")
                st.write(power_sources)
                st.caption("重点复核空开容量、产权边界和接地条件。")
        with detail_cols[2]:
            with st.container(border=True):
                st.markdown("**风险重点**")
                st.write("电力交越、高处作业、防水封堵、隔离保护、接地闭环。")

        st.info("规则引擎以全量设计表为计算口径，工程概况直接来自当前上传数据或内置模拟数据。")
        st.dataframe(overview_table, use_container_width=True, hide_index=True)

    with bom_tab:
        st.caption("BOM 物料估算")
        bom_kpis = st.columns(4)
        bom_kpis[0].metric("电源线", f"{bom['power_cable']} m")
        bom_kpis[1].metric("光缆", f"{bom['optical_cable']} m")
        bom_kpis[2].metric("标签", f"{bom['labels']} 个")
        bom_kpis[3].metric("防水套件", f"{bom['waterproof_kits']} 套")
        st.dataframe(bom_table, use_container_width=True, hide_index=True)
        st.caption("BOM 为 Demo 经验规则估算，用于演示物料核对流程，不作为真实采购依据。")

    with acceptance_tab:
        st.caption("质量验收清单")
        left_col, right_col = st.columns(2)
        for index, (title, copy) in enumerate(acceptance_items):
            target_col = left_col if index % 2 == 0 else right_col
            with target_col:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.write(copy)

    with fiber_tab:
        st.caption("纤芯分配表")
        st.dataframe(fiber_table, use_container_width=True, hide_index=True)
        if len(fiber_table) >= 2000:
            st.warning("纤芯分配表已截断展示前 2000 行，完整工程建议拆分站点或导出后分批核对。")
        else:
            st.info("纤芯分配表基于 fiber_start、fiber_end、fiber_core_count 或现有 fiber_core_id/fiber_core_no 自动生成。")

    with full_tab:
        st.markdown(report_text)


# =============================
# Mock LLM：模拟大模型生成专业施工文档
# =============================
def mock_llm_response(data: pd.DataFrame, mode: str) -> str:
    """
    根据基站设计元数据生成伪造的专业施工指令。
    当前阶段不调用真实 API，后续可在此函数内替换为 LLM SDK 请求。
    """
    bom = estimate_bom(data)
    site_types = join_unique(data, "站点类型")
    aau_models = join_unique(data, "AAU型号")
    bbu_models = join_unique(data, "BBU型号")
    power_sources = join_unique(data, "取电方式")
    avg_cable = round(bom["cable_total"] / bom["site_count"], 1) if bom["site_count"] else 0
    terminal_lugs = bom["site_count"] * 10
    firestop_kits = bom["site_count"] * 4
    cable_ties = max(100, bom["cable_total"] * 2)
    long_route_note = "存在长距离放缆场景，建议增加中间牵引点、复核桥架余量并预留光功率测试窗口。" if avg_cable >= 80 else "线缆平均路由较短，重点控制端口防水、标签一致性和现场余量管理。"
    power_note = "涉及弱电井或路灯杆取电时，需提前确认产权边界、计量方式、空开容量和接地条件。" if any(keyword in power_sources for keyword in ["弱电井", "路灯", "交流配电箱"]) else "以市电直供为主，需重点复核进线空开容量、接地排余量和停送电审批。"

    overview_block = f"""
## 5G通信基建数智化交付指令报告

**文档性质：** Demo 版自动生成交付建议，适用于施工准备、物料核对和现场技术交底  
**生成模式：** {mode}  
**站点数量：** {bom["site_count"]} 个  
**站点类型：** {site_types or "未识别"}  
**设备型号：** AAU：{aau_models or "未识别"}；BBU：{bbu_models or "未识别"}  
**取电方式：** {power_sources or "未识别"}  
**线缆路由：** 合计约 {bom["cable_total"]} 米，平均约 {avg_cable} 米/站  

### 一、工程概况与规则引擎结论

| 项目 | 结论 |
|---|---|
| 交付范围 | AAU/BBU 安装、前传光缆、电源接入、接地、防水封堵、基础联调 |
| 规则口径 | 线缆敷设距离按设计表汇总，电源线与光缆按站点预留工艺余量估算 |
| 重点风险 | 电力交越安全净距、楼面临边高处作业、弱电井/路灯杆取电边界、端口防水 |
| 现场建议 | {long_route_note} |
| 取电建议 | {power_note} |
"""

    bom_block = f"""
### 二、BOM 物料统计清单

| 序号 | 物料名称 | 推荐规格 | 估算数量 | 施工用途 |
|---:|---|---|---:|---|
| 1 | 室外电源线 | RVVZ 3x6mm² | {bom["power_cable"]} 米 | AAU/BBU 供电接入 |
| 2 | 室外光缆 | GYTA-12B1 | {bom["optical_cable"]} 米 | BBU 至 AAU 前传链路 |
| 3 | 保护接地线 | BVR 16mm² 黄绿双色 | {bom["grounding_cable"]} 米 | 机柜、抱杆、AAU 接地 |
| 4 | 线缆标识牌 | 防水阻燃型 | {bom["labels"]} 个 | 电源线、光缆、尾纤双端标识 |
| 5 | 镀锌桥架/线槽 | 100x50mm | {bom["cable_tray"]} 米 | 楼面及弱电井线缆保护 |
| 6 | 防水胶泥与热缩套管 | 室外耐候型 | {bom["waterproof_kits"]} 套 | 馈线窗、穿墙孔洞封堵 |
| 7 | 铜鼻子/冷压端子 | 与电源线线径匹配 | {terminal_lugs} 个 | 电源线端接压接 |
| 8 | 防火封堵材料 | 阻燃泥/防火包 | {firestop_kits} 套 | 竖井、穿墙、机房孔洞封堵 |
| 9 | 尼龙扎带/不锈钢扎带 | 室外耐候型 | {cable_ties} 根 | 线缆绑扎与路由整理 |

**物料复核要求：**

- 到货后按站点编号分包核对，重点核对 AAU/BBU 型号、光模块、尾纤规格和电源线线径。
- 电源类材料应提供阻燃等级、合格证和批次记录；室外材料需满足耐候、防水和抗紫外要求。
- 现场若发生路由变更，应同步更新线缆长度、桥架数量、标签数量和竣工图。
"""

    guide_block = f"""
### 三、工序指导书

1. **进场复核**
   - 依据站点编号逐站核对设计图、设备型号、取电方式和路由长度。
   - 对楼面站、宏站需复测 AAU 挂高、抱杆垂直度、安装朝向、方位角和机械下倾角。
   - 对室分站需核对弱电井、走线架、机柜位置、传输资源和供电空开容量。

2. **设备安装**
   - AAU 采用双螺母防松固定，安装完成后检查方位角、下倾角和端口防水帽。
   - BBU 上架前应确认机柜承重、空开容量、接地排余量、传输尾纤路由和散热空间。
   - 室外设备安装后需完成螺栓复紧、端口防水、铭牌拍照和安装位置复核。

3. **线缆敷设**
   - 本批次设计线缆敷设距离合计约 **{bom["cable_total"]} 米**，施工放缆应预留 3% 至 5% 工艺余量。
   - 电源线、光缆应分槽或分层敷设；无法分离时须增加阻燃隔板并做好交越标识。
   - 线缆转弯半径不得小于线缆外径的 10 倍，桥架内线缆填充率建议不超过 40%。
   - 光缆两端应挂永久性标签，标签内容应包含站点编号、起止端口、方向和施工日期。

4. **供电与接地**
   - 上电前测量输入电压、接地电阻和空开容量，确认无短路、反接、虚接和松动端子。
   - 电源线端接必须压接牢固，线鼻子规格与线径匹配，端子处不得露铜。
   - 所有设备保护地应接入站点接地排，接地点除锈后做防腐处理。

5. **开通联调**
   - 设备启动后检查 BBU-AAU 光链路、GPS/北斗同步、网管告警和小区激活状态。
   - 光链路需记录收发光功率，异常时优先排查尾纤极性、光模块规格、端口配置和弯折半径。
   - 联调完成后导出网管无告警截图、基础参数截图和测试记录。

### 四、安全注意事项

- 电力线与通信线交越时应保持安全净距，平行敷设距离不足时需采取隔离保护措施。
- 与强电管线交越的部位需设置明显警示标识，电力交越距离必须大于设计与现行规范规定值。
- 高处作业必须执行安全带高挂低用，楼面临边、洞口和爬梯区域需先防护后施工。
- 室外穿墙孔、馈线窗和设备端口应完成防水封堵，防止雨水倒灌造成设备故障。
- 所有接地点必须除锈、压接牢固并做防腐处理，接地电阻应满足站点验收要求。
- 涉及停送电、配电箱开盖、弱电井作业和夜间施工时，必须执行审批、监护和复核制度。

### 五、质量验收与交付资料

| 验收项 | 交付要求 |
|---|---|
| 设备安装 | 设备位置、朝向、挂高、紧固、防水、铭牌照片齐全 |
| 线缆工艺 | 路由整齐、绑扎间距一致、转弯半径合规、标签双端一致 |
| 电源接入 | 空开容量、输入电压、端子压接、线缆颜色和极性复核通过 |
| 接地系统 | 接地线规格、接地点防腐、接地电阻测试记录齐全 |
| 光链路 | 收发光功率、端口对应关系、链路状态截图齐全 |
| 资料闭环 | 竣工图、变更记录、测试记录、隐蔽工程照片和问题整改记录归档 |

### 六、风险闭环建议

- 对线缆路由超过平均值较多的站点，建议施工前二次踏勘，确认桥架、竖井和穿墙孔容量。
- 对取电方式存在产权或计量边界的站点，建议先完成业主确认和停送电审批，再安排设备上电。
- 对楼面站和宏站，建议把临边防护、吊装路径、天气条件和人员资质作为开工前检查项。
- 对室分站，建议重点核查弱电井空间、消防封堵恢复和物业施工窗口。
"""

    if mode == "生成BOM清单":
        return overview_block + "\n" + bom_block
    if mode == "生成工艺指导书":
        return overview_block + "\n" + guide_block
    return overview_block + "\n" + bom_block + "\n" + guide_block


def call_llm_api(
    data: pd.DataFrame,
    mode: str,
    api_url: str,
    model: str,
    api_key: str,
    timeout_seconds: int,
    sample_rows: int,
) -> str:
    """调用 OpenAI 兼容的 Chat Completions 接口生成交付文档。"""
    llm_context = build_llm_context(data, sample_rows)
    prompt = f"""
你是一名通信基建工程交付专家。请基于下方工程摘要，生成一份专业、可交付的中文施工文档。

生成模式：{mode}

工程摘要 JSON：
{llm_context}

输出要求：
1. 使用 Markdown。
2. 必须包含工程概况、BOM 物料统计表、工序指导书、安全注意事项、质量验收标准、风险闭环建议。
3. BOM 数量必须优先采用工程摘要 JSON 中的 bom_estimate，不要自行改写数量。
4. 语言要像真实通信施工交付文件，避免营销化表达。
5. 如涉及电力线与通信线交越，必须提示安全净距、隔离保护、警示标识和复核记录。
6. 对大路由、弱电井取电、楼面站/宏站高处作业、端口防水分别给出具体执行建议。
"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你负责把通信设计元数据转化为施工 BOM 和工序指导书。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    api_request = request.Request(
        api_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(api_request, timeout=timeout_seconds) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("大模型 API 返回内容不是有效 JSON。") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise RuntimeError(
            f"大模型 API 在 {timeout_seconds} 秒内未返回结果。建议提高超时时间、减少样本行数，或切换为本地 Mock 先生成交付初稿。"
        ) from exc
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"大模型 API 返回错误：HTTP {exc.code} {detail[:300]}") from exc
    except error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise RuntimeError(
                f"大模型 API 在 {timeout_seconds} 秒内未返回结果。建议提高超时时间、减少样本行数，或切换为本地 Mock 先生成交付初稿。"
            ) from exc
        raise RuntimeError(f"无法连接大模型 API：{exc.reason}") from exc

    try:
        return response_data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("大模型 API 返回格式不符合 Chat Completions 兼容结构。") from exc


# =============================
# 侧边栏：配置与控制台
# =============================
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-mark">5G</div>
            <div class="brand-title">云筑交付中枢</div>
            <div class="brand-sub">设计表 · BOM · 交付文档</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("可折叠控制台")

    with st.expander("数据接入", expanded=True):
        uploaded_files = st.file_uploader(
            "上传基站设计元数据表",
            type=["xlsx", "csv"],
            accept_multiple_files=True,
            help="支持前序设计软件导出的 Excel 或 CSV 结构化表格。",
        )
        recent_files = cache_design_files(uploaded_files)
        uploaded_file_names = [file.name for file in uploaded_files] if uploaded_files else []
        recent_file_labels = [f"{item['name']} · {item.get('cached_at', '')}" for item in recent_files]
        source_options = ["使用内置演示数据"] + [f"本次上传：{name}" for name in uploaded_file_names] + [f"最近文件：{label}" for label in recent_file_labels]
        selected_source = st.selectbox("当前处理文件", source_options, index=1 if uploaded_file_names else 0)
        st.caption("支持一次上传多份文件；系统会缓存最近 10 份，重新打开后可继续查看。")

    with st.expander("生成设置", expanded=True):
        mode = st.selectbox(
            "生成模式",
            ["生成BOM清单", "生成工艺指导书", "全量生成"],
            index=2,
        )
        llm_engine = st.selectbox(
            "AI 引擎",
            ["本地Mock（无需密钥）", "真实大模型API（OpenAI兼容）"],
        )

    with st.expander("真实 API 配置", expanded=False):
        api_url = st.text_input(
            "API 地址",
            value=os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions"),
            help="填写兼容 Chat Completions 的接口地址。",
        )
        model_name = st.text_input(
            "模型名称",
            value=os.getenv("LLM_MODEL", "gpt-4.1-mini"),
            help="示例：gpt-4.1-mini，或你所使用平台提供的模型名称。",
        )
        api_key = st.text_input(
            "API Key",
            value=os.getenv("LLM_API_KEY", ""),
            type="password",
        )
        api_timeout = st.number_input(
            "API 超时时间（秒）",
            min_value=30,
            max_value=600,
            value=int(os.getenv("LLM_TIMEOUT", DEFAULT_API_TIMEOUT)),
            step=30,
            help="大型工程文件建议设置为 180-300 秒。",
        )
        sample_rows = st.number_input(
            "送入模型的样本行数",
            min_value=5,
            max_value=200,
            value=int(os.getenv("LLM_SAMPLE_ROWS", DEFAULT_SAMPLE_ROWS)),
            step=5,
            help="系统会把全量数据压缩为工程摘要，只附带少量样本行给模型参考。",
        )
        fallback_to_mock = st.checkbox(
            "API 失败时自动生成本地工程报告",
            value=True,
            help="开启后，API 超时或网络异常时不会中断流程，会自动使用规则引擎生成交付报告。",
        )

    with st.expander("执行", expanded=True):
        start_button = st.button(
            "启动数智化指令转化",
            type="primary",
            use_container_width=True,
        )


uploaded_file = None
if selected_source.startswith("本次上传："):
    selected_name = selected_source.replace("本次上传：", "", 1)
    uploaded_file = next((file for file in uploaded_files if file.name == selected_name), None)
elif selected_source.startswith("最近文件："):
    selected_label = selected_source.replace("最近文件：", "", 1)
    selected_cache = next((item for item in recent_files if selected_label.startswith(item["name"])), None)
    uploaded_file = load_cached_design_file(selected_cache) if selected_cache else None

try:
    df = load_design_file(uploaded_file) if uploaded_file else build_demo_dataframe()
except Exception as exc:
    st.error(f"文件读取失败，请检查表头、编码或文件格式。错误信息：{exc}")
    st.stop()

clean_df, validation_errors, validation_warnings = validate_design_data(df)
work_df = clean_df if not validation_errors else df
data_source_label = uploaded_file.name if uploaded_file else "系统内置模拟数据"
review_df, review_summary = run_design_review(df)
review_df = attach_review_source(review_df, data_source_label)
batch_summary_df = summarize_batch_files(uploaded_files) if uploaded_files and len(uploaded_files) > 1 else pd.DataFrame()
batch_review_df, batch_review_summary = (
    build_batch_review_result(uploaded_files) if uploaded_files and len(uploaded_files) > 1 else (pd.DataFrame(), {})
)
display_review_df = batch_review_df if not batch_review_df.empty else review_df
display_review_summary = batch_review_summary if batch_review_summary else review_summary


# =============================
# 主区域：导航、Hero 与工作台入口
# =============================
st.markdown(
    f"""
    <div class="taste-nav">
        <div class="taste-nav-brand">云筑交付中枢</div>
        <div class="taste-nav-links">
            <span>设计接入</span>
            <span>规则估算</span>
            <span>智能成稿</span>
            <span>交付导出</span>
        </div>
    </div>
    <section class="taste-hero">
        <div class="taste-hero-inner">
            <div class="product-lockup">
                <div class="product-lockup-main">云筑交付中枢</div>
                <div class="product-lockup-line"></div>
            </div>
            <h1 class="taste-hero-title">把设计元数据转成可交付施工报告</h1>
            <p class="taste-hero-copy">
                面向通信基建交付演示：从 Excel/CSV 基站清单进入，经过数据校验、BOM 规则估算、AI 文档生成，最终输出可下载的 Word 交付文件。
            </p>
        </div>
    </section>
    <div class="status-strip">
        <div class="status-cell"><span>数据来源</span><strong>{html.escape(data_source_label)}</strong></div>
        <div class="status-cell"><span>生成模式</span><strong>{html.escape(mode)}</strong></div>
        <div class="status-cell"><span>智能引擎</span><strong>{html.escape(llm_engine)}</strong></div>
    </div>
    <div class="bento-grid">
        <div class="bento-card bento-large bento-dark">
            <div class="bento-kicker">交付流水线</div>
            <div class="bento-title">结构化设计表进入统一交付流水线</div>
            <div class="bento-copy">上传 Excel 或 CSV 后，系统立即校验必填字段、路由长度和站点记录，为后续 BOM 与施工文档生成建立可信输入。</div>
        </div>
        <div class="bento-card">
            <div class="bento-kicker">规则引擎</div>
            <div class="bento-title">BOM 估算</div>
            <div class="bento-copy">电源线、光缆、接地、标签、防水套件按全量数据估算。</div>
            <div class="bento-number">01</div>
        </div>
        <div class="bento-card">
            <div class="bento-kicker">质量门禁</div>
            <div class="bento-title">数据校验</div>
            <div class="bento-copy">缺列、异常距离、空站点编号以清晰状态反馈给操作员。</div>
            <div class="bento-number">02</div>
        </div>
        <div class="bento-card bento-wide">
            <div class="bento-kicker">智能成稿</div>
            <div class="bento-title">摘要化上下文，避免整表直塞模型</div>
            <div class="bento-copy">大型文件先压缩为工程摘要和样本行，再调用 OpenAI 兼容接口，超时可回退本地规则报告。</div>
            <div class="bento-number">03</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="hero-action-row"></div>', unsafe_allow_html=True)
hero_col_a, hero_col_b = st.columns([1, 1], gap="medium")
with hero_col_a:
    view_workbench_button = st.button("查看工程工作台", use_container_width=True)
with hero_col_b:
    hero_generate_button = st.button("生成交付报告", type="primary", use_container_width=True)

if view_workbench_button:
    st.session_state.show_workbench_hint = True
    st.toast("已定位到工程工作台")

if not batch_summary_df.empty:
    st.markdown(
        """
        <div class="section-title">批量文件处理概览</div>
        <div class="section-note">当前批次所有上传文件均已读取并完成轻量审查，可在左侧切换单个文件查看详情。</div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(batch_summary_df, use_container_width=True, hide_index=True)

if recent_files:
    recent_preview_df = pd.DataFrame(recent_files)[["name", "size", "cached_at"]].rename(
        columns={"name": "文件名", "size": "文件大小(Byte)", "cached_at": "缓存时间"}
    )
    with st.expander("最近 10 份文件缓存", expanded=False):
        st.dataframe(recent_preview_df, use_container_width=True, hide_index=True)


# =============================
# 主区域上方：原始数据透视与校验
# =============================
st.markdown('<div id="workbench"></div>', unsafe_allow_html=True)
if st.session_state.get("show_workbench_hint"):
    st.info("工程工作台已展开：可在下方查看数据预览、质量校验、规则指标和智能转换结果。")

preview_col, quality_col = st.columns([1.65, 1], gap="large")

with preview_col:
    with st.container(border=True):
        st.markdown(
            """
            <div class="section-title">原始数据透视</div>
            <div class="section-note">展示前 5 行设计元数据，用于快速确认表头、站点类型和设备型号。</div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(df.head(5), use_container_width=True, hide_index=True)

with quality_col:
    with st.container(border=True):
        st.markdown(
            """
            <div class="section-title">数据质量校验</div>
            <div class="section-note">生成前先检查必填字段、线缆距离和站点编号完整性。</div>
            """,
            unsafe_allow_html=True,
        )
        if validation_errors:
            for validation_error in validation_errors:
                st.error(validation_error)
        elif validation_warnings:
            for validation_warning in validation_warnings:
                st.warning(validation_warning)
        else:
            st.success("数据结构校验通过，可用于生成交付指令。")

if not batch_review_df.empty:
    st.caption("当前为批量上传文件的汇总审查明细；“文件来源”列用于定位每条问题来自哪一张图纸。")
render_review_result(display_review_df, display_review_summary)
if display_review_summary["has_error"]:
    st.warning("当前结果仅供预览，不建议作为正式交付材料。请先修正审查错误项，再生成施工资料。")

if llm_engine.startswith("真实") and len(work_df) > sample_rows:
    st.markdown(
        f"""
        <div class="report-hint">
            大文件处理策略：当前共有 {len(work_df)} 行记录，系统会先生成全量工程摘要，再仅附带 {sample_rows} 行样本给外接 API，降低超时和上下文溢出风险。
        </div>
        """,
        unsafe_allow_html=True,
    )

summary_bom = estimate_bom(work_df)
st.markdown(
    """
    <div class="section-title">规则指标总览</div>
    <div class="section-note">基于全量数据计算的交付规模指标，用于判断本次任务复杂度。</div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    f"""
    <div class="metric-strip">
        <div class="metric-box">
            <div class="metric-label">记录数</div>
            <div class="metric-value">{len(work_df)}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">线缆总长</div>
            <div class="metric-value">{summary_bom["cable_total"]} m</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">字段数</div>
            <div class="metric-value">{len(work_df.columns)}</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">生成模式</div>
            <div class="metric-value" style="font-size: 18px;">{html.escape(mode)}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================
# 主区域下方：智能转化结果
# =============================
st.markdown(
    """
    <div class="section-title">智能转化结果</div>
    <div class="section-note">生成过程会显示阶段百分比，完成后可预览报告并下载 Word 文件。</div>
    """,
    unsafe_allow_html=True,
)

if "ai_result" not in st.session_state:
    st.session_state.ai_result = ""

if start_button or hero_generate_button:
    if validation_errors:
        st.error("当前数据缺少必填字段，请修正后再启动转化。")
        st.stop()
    if display_review_summary["has_error"]:
        st.error("轻量智能审查未通过：当前设计数据存在错误项，系统暂不建议生成正式施工资料。请修改数据后重新上传。")
        st.stop()

    if llm_engine.startswith("真实") and (not api_url or not model_name or not api_key):
        st.error("真实大模型 API 模式需要填写 API 地址、模型名称和 API Key。")
        st.stop()

    progress = st.progress(0, text="0% 准备启动数智化转化任务")
    phase_placeholder = st.empty()

    render_phase(phase_placeholder, 15, "数据结构校验", "正在核对必填字段、线缆距离和站点记录完整性。")
    progress.progress(15, text="15% 数据结构校验完成")
    time.sleep(0.25)

    bom_preview = estimate_bom(work_df)
    render_phase(
        phase_placeholder,
        35,
        "规则引擎估算",
        f"已完成 {bom_preview['site_count']} 个站点、{bom_preview['cable_total']} 米线缆的物料规则估算。",
    )
    progress.progress(35, text="35% 规则引擎完成 BOM 估算")
    time.sleep(0.25)

    render_phase(phase_placeholder, 55, "AI上下文压缩", "正在把大型工程表压缩为站点分布、设备分布、取电方式、长路由风险和样本行。")
    progress.progress(55, text="55% 工程摘要已生成，准备调用 AI 引擎")
    time.sleep(0.25)

    if llm_engine.startswith("真实"):
        render_phase(
            phase_placeholder,
            60,
            "AI生成中",
            f"正在等待外接 API 返回，最长等待 {api_timeout} 秒。大文件已按摘要+{sample_rows}行样本送入模型。",
        )
        progress.progress(60, text=f"60% AI生成中，已等待 0 秒 / {api_timeout} 秒")

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                call_llm_api,
                work_df,
                mode,
                api_url,
                model_name,
                api_key,
                int(api_timeout),
                int(sample_rows),
            )
            start_time = time.time()
            while not future.done():
                elapsed = int(time.time() - start_time)
                percent = min(94, 60 + int((elapsed / max(int(api_timeout), 1)) * 34))
                render_phase(
                    phase_placeholder,
                    percent,
                    "AI生成中",
                    f"外接 API 正在处理工程摘要，已等待 {elapsed} 秒 / {api_timeout} 秒。页面仍在运行，请勿重复点击。",
                )
                progress.progress(percent, text=f"{percent}% AI生成中，已等待 {elapsed} 秒 / {api_timeout} 秒")
                time.sleep(0.5)

            try:
                st.session_state.ai_result = future.result()
            except Exception as exc:
                if fallback_to_mock:
                    st.warning(f"{exc} 已自动切回本地规则引擎报告，避免本次任务中断。")
                    st.session_state.ai_result = mock_llm_response(work_df, mode)
                else:
                    st.error(str(exc))
                    render_phase(phase_placeholder, 100, "任务中断", "外接 API 未在预期时间内返回，已停止生成。")
                    progress.progress(100, text="100% 任务中断")
                    st.stop()
    else:
        for percent in (70, 82, 94):
            render_phase(phase_placeholder, percent, "本地报告生成", "正在根据规则引擎结果生成工程交付指令报告。")
            progress.progress(percent, text=f"{percent}% 本地工程报告生成中")
            time.sleep(0.25)
        st.session_state.ai_result = mock_llm_response(work_df, mode)

    render_phase(phase_placeholder, 100, "报告封装完成", "已完成报告正文生成，可在下方预览并下载 Word 文件。")
    progress.progress(100, text="100% 数智化指令转化完成")
    st.success("数智化指令转化完成")

if st.session_state.ai_result:
    st.markdown('<div class="result-stage">', unsafe_allow_html=True)
    render_report_dashboard(work_df, mode, st.session_state.ai_result)
    st.markdown("</div>", unsafe_allow_html=True)

    report_bytes = build_word_report(st.session_state.ai_result, work_df, mode)
    excel_bytes = build_excel_report(st.session_state.ai_result, work_df, mode)
    st.markdown(
        """
        <div class="download-band">
            <div class="download-title">交付文件下载</div>
            <div class="download-copy">Word 用于施工交底与归档，Excel 用于物料复核、数据流转和二次编辑。</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    download_col_a, download_col_b = st.columns(2)
    with download_col_a:
        st.download_button(
            "下载 Word 交付报告",
            data=report_bytes,
            file_name="5G通信基建数智化交付报告.doc",
            mime="application/msword",
            use_container_width=True,
            on_click=show_download_toast,
        )
    with download_col_b:
        st.download_button(
            "下载 Excel 交付清单",
            data=excel_bytes,
            file_name="5G通信基建数智化交付清单.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            on_click=show_download_toast,
        )
else:
    st.markdown(
        """
        <div class="report-hint">
            当前展示的是基于现有数据的演示预览。点击左侧“启动数智化指令转化”后，会生成正式报告正文并开放 Word 下载。
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="result-stage">', unsafe_allow_html=True)
    render_report_dashboard(work_df, mode, mock_llm_response(work_df, mode))
    st.markdown("</div>", unsafe_allow_html=True)


# =============================
# requirements.txt 依赖包列表
# streamlit
# pandas
# openpyxl
# =============================
