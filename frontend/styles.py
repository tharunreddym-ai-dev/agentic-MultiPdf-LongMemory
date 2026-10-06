import streamlit as st

PALETTES = {
    "dark": {
        "bg": "#14161B",
        "bg_secondary": "#1A1D24",
        "surface": "#242832",
        "border": "#2E323C",
        "text": "#ECECE9",
        "text_muted": "#92969F",
        "accent": "#D9A441",
        "accent_text": "#14161B",
        "danger": "#C15C50",
    },
    "light": {
        "bg": "#F5F6F8",
        "bg_secondary": "#ECEEF1",
        "surface": "#FFFFFF",
        "border": "#D9DCE2",
        "text": "#1D2027",
        "text_muted": "#5B5F6B",
        "accent": "#B9832A",
        "accent_text": "#FFFFFF",
        "danger": "#B23B2E",
    },
}


def inject_css(dark_mode: bool):
    p = PALETTES["dark"] if dark_mode else PALETTES["light"]

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

        .stApp, .stApp p, .stApp span, .stApp div, .stApp li, .stApp label,
        .stApp button, .stApp input, .stApp textarea {{
            font-family: 'IBM Plex Sans', sans-serif;
        }}

        /* Leave Streamlit's own icon glyphs alone */
        [data-testid="stIconMaterial"], .material-symbols-outlined,
        .material-symbols-rounded {{
            font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
                         'Material Icons' !important;
        }}

        .stApp {{
            background-color: {p['bg']} !important;
            color: {p['text']} !important;
        }}

        [data-testid="stSidebar"], [data-testid="stSidebarContent"] {{
            background-color: {p['bg_secondary']} !important;
            border-right: 1px solid {p['border']};
        }}

        [data-testid="stSidebar"] * {{
            color: {p['text']} !important;
        }}

        .stMarkdown, .stMarkdown p, .stMarkdown li, .stCaption, label {{
            color: {p['text']} !important;
        }}

        .brand-title, .app-title {{
            font-family: 'Fraunces', serif;
            font-weight: 600;
            font-size: 1.5rem;
            color: {p['text']} !important;
            line-height: 1.2;
            margin: 0.1rem 0 0.15rem 0;
        }}

        .brand-tagline {{
            font-size: 0.8rem;
            color: {p['text_muted']} !important;
            margin-bottom: 1.1rem;
        }}

        .set-subtitle {{
            font-size: 0.92rem;
            color: {p['text_muted']} !important;
            margin: 0 0 1rem 0;
        }}

        /* Buttons */
        .stButton > button, button[kind] {{
            border-radius: 6px !important;
            border: 1px solid {p['border']} !important;
            font-weight: 500 !important;
            transition: border-color 0.12s ease, background-color 0.12s ease;
        }}

        button[kind="secondary"] {{
            background-color: transparent !important;
            color: {p['text']} !important;
        }}

        button[kind="primary"] {{
            background-color: {p['accent']} !important;
            color: {p['accent_text']} !important;
            border: 1px solid {p['accent']} !important;
        }}

        [data-testid="stSidebar"] .stButton > button {{
            text-align: left;
            justify-content: flex-start;
        }}

        [data-testid="stSidebar"] button[kind="secondary"]:hover {{
            border-color: {p['accent']} !important;
        }}

        /* Document cards */
        .doc-card {{
            border-left: 3px solid {p['accent']};
            background-color: {p['surface']};
            border-radius: 4px;
            padding: 0.6rem 0.8rem;
            margin-bottom: 0.55rem;
        }}

        .doc-card .doc-name {{
            font-weight: 500;
            font-size: 0.88rem;
            color: {p['text']};
            word-break: break-word;
        }}

        .doc-card .doc-meta {{
            font-size: 0.76rem;
            color: {p['text_muted']};
            margin-top: 0.15rem;
        }}

        /* Chunk-capacity gauge */
        .gauge-label {{
            font-size: 0.78rem;
            color: {p['text_muted']};
            margin-bottom: 0.3rem;
        }}

        .gauge-track {{
            width: 100%;
            height: 6px;
            background-color: {p['border']};
            border-radius: 3px;
            margin-bottom: 1rem;
            overflow: hidden;
        }}

        .gauge-fill {{
            height: 100%;
            background-color: {p['accent']};
        }}

        .gauge-fill.full {{
            background-color: {p['danger']};
        }}

        /* File uploader */
        [data-testid="stFileUploaderDropzone"], .stFileUploader section {{
            background-color: {p['surface']} !important;
            border: 1px dashed {p['border']} !important;
        }}

        /* Chat */
        [data-testid="stChatMessage"] {{
            background-color: {p['surface']} !important;
            border: 1px solid {p['border']};
            border-radius: 8px;
        }}

        [data-testid="stChatInput"] textarea {{
            background-color: {p['surface']} !important;
            color: {p['text']} !important;
        }}

        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: {p['border']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
