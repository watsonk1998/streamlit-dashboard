import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any
import re
import os
import glob
from datetime import datetime

# --- Constants & Page Configuration ---
st.set_page_config(page_title="AI 评测审计控制台 (v7.0)", layout="wide")

# --- Custom CSS for High-Contrast, Zones, Visual Hierarchy & Print Optimization ---
st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #fcfcfd;
    }
    
    /* Print Optimization */
    @media print {
        section[data-testid="stSidebar"] {
            display: none !important;
        }
        .battle-card {
            page-break-inside: avoid !important;
            break-inside: avoid !important;
            border: 2px solid #000 !important;
            box-shadow: none !important;
        }
        .stMetric {
            page-break-inside: avoid !important;
        }
    }
    
    /* Header Title Badge */
    .case-badge {
        background-color: #2c3e50;
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.95em;
        display: inline-block;
        margin-bottom: 8px;
    }

    /* Question Text (High Contrast) */
    .question-title {
        font-size: 1.5em !important;
        font-weight: 800 !important;
        color: #000000 !important; /* Pure Black */
        margin-bottom: 12px;
        line-height: 1.4;
    }

    /* Truth Capsule (Primary - Green) */
    .truth-capsule {
        background-color: #d1fae5; /* Light Green */
        border-left: 5px solid #059669; /* Strong Green */
        padding: 12px;
        margin-bottom: 10px;
        border-radius: 4px;
        color: #064e3b; /* Dark Green Text */
        font-weight: 700;
        font-size: 1.1em;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }

    /* Unified Rule Capsule (Slate-100) */
    .rule-capsule {
        background-color: #f1f5f9; /* Slate-100 */
        border-left: 5px solid #64748b; /* Slate-500 */
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 24px;
        font-size: 0.95em;
        line-height: 1.6;
    }
    
    /* Battle Card Container */
    .battle-card {
        border: 1px solid #eef2f6;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 40px;
        background-color: #ffffff;
        box-shadow: 0 4px 25px rgba(0,0,0,0.06);
    }
    
    /* System Column Headers */
    .system-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid rgba(0,0,0,0.1);
        min-height: 42px;
    }
    
    .system-name {
        font-weight: 800;
        font-size: 1.1em;
        color: #1a202c;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Distinct System Zone Coloring */
    .sys-zone-0 { background-color: #edf5ff !important; border: 1px solid #c2e0ff !important; } /* Dify - Blue */
    .sys-zone-1 { background-color: #fcf0ff !important; border: 1px solid #f3d1ff !important; } /* FAST - Purple */
    .sys-zone-2 { background-color: #fff9e6 !important; border: 1px solid #ffe8a3 !important; } /* Pinming - Orange */
    
    /* Fatal Error Override */
    .fatal-zone {
        background-color: #fff1f0 !important;
        border: 2px solid #ef4444 !important;
    }

    /* Visual Badges */
    .badge {
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.85em;
        font-weight: 700;
    }
    .badge-perfect { background-color: #ecfdf5; color: #059669; border: 1px solid #10b981; }
    .badge-excellent { background-color: #f0fdf4; color: #16a34a; border: 1px solid #4ade80; }
    .badge-fail { background-color: #fef2f2; color: #dc2626; border: 1px solid #ef4444; }
    .badge-neutral { background-color: #eff6ff; color: #2563eb; border: 1px solid #60a5fa; }

    /* Summary Metric Enhancement */
    .metric-card {
        padding: 12px;
        border-radius: 8px;
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    /* Clean Expander */
    .stExpander { border: none !important; box-shadow: none !important; }
    
</style>
""", unsafe_allow_html=True)

# --- Data Models ---
@dataclass
class SystemResult:
    system_name: str
    score: float
    is_fatal: bool
    raw_response: str
    audit_reasoning: str
    fatal_reason: str = ""

@dataclass
class EvaluationCase:
    case_id: int
    question_text: str
    citation_rule: str
    ground_truth: str
    source_file: str
    results: List[SystemResult]

# --- Helper Logic ---
def format_markdown_to_html(text: str) -> str:
    """
    Simple converter to render basic Markdown within HTML blocks.
    1. Converts **text** to <strong>text</strong>
    2. Converts newlines to <br>
    """
    if not text: return ""
    # Bold: **text** -> <strong>text</strong>
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Newlines: \n -> <br>
    text = text.replace('\n', '<br>')
    return text

def get_latest_local_report() -> str:
    """Scan directory for the latest Evaluation_Report*.xlsx file."""
    files = glob.glob("Evaluation_Report*.xlsx")
    if not files:
        return None
    # Pick the newest by modification time
    latest_file = max(files, key=os.path.getmtime)
    return latest_file

# --- Backend Logic ---
@st.cache_data
def load_and_process_data(file_path_or_buffer) -> List[EvaluationCase]:
    try:
        if hasattr(file_path_or_buffer, 'name'):
            # It's an uploaded file buffer
            if file_path_or_buffer.name.endswith('.csv'):
                df = pd.read_csv(file_path_or_buffer)
            else:
                df = pd.read_excel(file_path_or_buffer)
        else:
            # It's a local file path
            if str(file_path_or_buffer).endswith('.csv'):
                df = pd.read_csv(file_path_or_buffer)
            else:
                df = pd.read_excel(file_path_or_buffer)
    except Exception as e:
        st.error(f"读取文件时出错: {e}")
        return []

    df = df.fillna({
        'CITATION_RULE': '无具体规则',
        'QUESTION': '未找到问题内容',
        'GROUND_TRUTH': '无标准内容参考',
        'S4_REASON': '',
        'AUDIT_REASONING': '暂无 AI 审计分析进度',
        'MODEL_OUTPUT': '[模型输出内容缺失]',
        'SOURCE_FILE': '未知数据源'
    })

    cases = []
    unique_systems = df['SYSTEM'].unique()
    
    for case_id, group in df.groupby('CASE_ID'):
        first_row = group.iloc[0]
        results = []
        for system in unique_systems:
            sys_row = group[group['SYSTEM'] == system]
            if not sys_row.empty:
                row = sys_row.iloc[0]
                results.append(SystemResult(
                    system_name=system,
                    score=float(row['TOTAL_SCORE']),
                    is_fatal=str(row['S4_FATAL']).upper() == 'YES',
                    raw_response=str(row['MODEL_OUTPUT']),
                    audit_reasoning=str(row['AUDIT_REASONING']),
                    fatal_reason=str(row.get('S4_REASON', ''))
                ))
            else:
                results.append(SystemResult(
                    system_name=system,
                    score=0.0,
                    is_fatal=False,
                    raw_response="[系统端缺失数据]",
                    audit_reasoning="N/A"
                ))
        
        cases.append(EvaluationCase(
            case_id=int(case_id),
            question_text=str(first_row['QUESTION']),
            citation_rule=str(first_row['CITATION_RULE']),
            ground_truth=str(first_row['GROUND_TRUTH']),
            source_file=str(first_row.get('SOURCE_FILE', '未知')),
            results=results
        ))
    
    return sorted(cases, key=lambda x: x.case_id)

# --- Component: Visual Badge ---
def get_badge_html(score, is_fatal):
    if is_fatal:
        return f'<span class="badge badge-fail">🚨 致命错误</span>'
    if score >= 100:
        return f'<span class="badge badge-perfect">💯 满分 ({int(score)})</span>'
    if score >= 90:
        return f'<span class="badge badge-excellent">🟢 优秀 ({int(score)})</span>'
    if score < 60:
        return f'<span class="badge badge-fail">⚠️ 不合格 ({int(score)})</span>'
    return f'<span class="badge badge-neutral">🔵 合格 ({int(score)})</span>'

# --- Renderer: Battle Card ---
def render_battle_card(case: EvaluationCase):
    st.markdown('<div class="battle-card">', unsafe_allow_html=True)
    
    st.markdown(f'<div class="case-badge">📝 题目 {case.case_id}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="question-title">{case.question_text}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="truth-capsule">✅ 标准答案：{case.ground_truth}</div>', unsafe_allow_html=True)
    
    # Unified Rule Capsule with Markdown formatting support
    formatted_rule = format_markdown_to_html(case.citation_rule)
    st.markdown(f"""
    <div class="rule-capsule">
        <div style="font-weight:800; margin-bottom:6px; color:#475569; font-size:0.9em;">📖 判定规则：</div>
        <div style="color:#1e293b;">{formatted_rule}</div>
    </div>
    """, unsafe_allow_html=True)
    
    cols = st.columns(len(case.results))
    for i, res in enumerate(case.results):
        with cols[i]:
            badge_html = get_badge_html(res.score, res.is_fatal)
            st.markdown(f"""
            <div class="system-header">
                <span class="system-name">{res.system_name}</span>
                {badge_html}
            </div>
            """, unsafe_allow_html=True)
            
            zone_class = f"sys-zone-{i % 3}" if not res.is_fatal else "fatal-zone"
            with st.container(height=480, border=True):
                st.markdown(f'<div class="{zone_class}" style="min-height:98%; padding:15px; border-radius:6px; color:#212529;">', unsafe_allow_html=True)
                if res.is_fatal:
                    st.error(f"致命缺陷：{res.fatal_reason if res.fatal_reason else '未明确原因'}")
                st.markdown(res.raw_response)
                st.markdown('</div>', unsafe_allow_html=True)
            
            with st.expander("🔻 详细审计意见"):
                st.markdown(f"**审计结论:**\n{res.audit_reasoning}")
                st.caption(f"数据源: {case.source_file}")

    st.markdown('</div>', unsafe_allow_html=True)

# --- Summary Component ---
def render_summary_section(cases: List[EvaluationCase]):
    if not cases: return
    
    st.markdown("### 📊 评测总览 (分系统详细统计)")
    all_res = []
    for c in cases:
        for r in c.results:
            all_res.append({'System': r.system_name, 'Score': r.score, 'Fatal': 1 if r.is_fatal else 0})
    
    res_df = pd.DataFrame(all_res)
    systems = res_df['System'].unique()
    
    cols = st.columns(len(systems))
    for i, sys in enumerate(systems):
        sys_data = res_df[res_df['System'] == sys]
        avg_score = sys_data['Score'].mean()
        fatal_count = sys_data['Fatal'].sum()
        theme_color = '#3b82f6' if i%3==0 else '#d946ef' if i%3==1 else '#fbbf24'
        
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card" style="border-top: 6px solid {theme_color};">
                <div style="font-weight:900; font-size:1.2em; color:#1e293b; margin-bottom:8px;">{sys}</div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div>
                        <div style="font-size:0.75em; color:#64748b; text-transform:uppercase;">平均得分</div>
                        <div style="font-size:1.8em; font-weight:900; color:{theme_color};">{avg_score:.1f}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.75em; color:#64748b; text-transform:uppercase;">致命错误</div>
                        <div style="font-size:1.3em; font-weight:800; color:#ef4444;">{int(fatal_count)} 例</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.divider()

# --- Main App ---
def main():
    st.title("🛡️ AI 评测审计控制台 (v7.0)")
    st.caption("Industrial Standard AI Audit & Comparison Console - Web Optimized")

    # Sidebar: Config & Filters
    with st.sidebar:
        st.header("⚙️ 配置与管理")
        uploaded_file = st.file_uploader("📂 上传新文件覆盖 (Upload New)", type=['csv', 'xlsx'])
        show_fatal = st.checkbox("🚨 过滤：仅查看致命错误案例", value=False)
        st.divider()
        st.info("💡 提示：系统将优先使用手动上传的文件。若未上传，则自动加载服务器端最新报告。")

    # Data Initialization Strategy
    data_source = None
    is_auto_loaded = False
    
    if uploaded_file is not None:
        data_source = uploaded_file
    else:
        # Check for local file
        latest_file = get_latest_local_report()
        if latest_file:
            data_source = latest_file
            is_auto_loaded = True
    
    if data_source:
        cases = load_and_process_data(data_source)
        if cases:
            # Welcome Banner for Stakeholders
            if is_auto_loaded:
                mtime = datetime.fromtimestamp(os.path.getmtime(data_source)).strftime('%Y-%m-%d %H:%M:%S')
                st.success(f"✅ 已自动加载服务器端报告：`{os.path.basename(data_source)}` (生成时间: {mtime})")
            
            # Rendering
            render_summary_section(cases)
            
            display_cases = [c for c in cases if any(r.is_fatal for r in c.results)] if show_fatal else cases
            st.write(f"当前视图：共展示 {len(display_cases)} / {len(cases)} 组用例")
            
            for case in display_cases:
                render_battle_card(case)
        else:
            st.error("数据加载失败，请检查报告格式。")
    else:
        # Empty State
        st.warning("⚠️ 未检测到服务器端报告，且未手动上传文件。")
        st.markdown("""
        ### 🏁 欢迎使用审计控制台
        请在左侧边栏上传您的评测数据：
        1. **上传文件**：支持 Excel (.xlsx) 或 CSV 格式。
        2. **自动加载**：若您在服务器目录存有 `Evaluation_Report*.xlsx`，控制台会自动呈现。
        """)

if __name__ == "__main__":
    main()
