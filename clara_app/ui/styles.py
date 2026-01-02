import streamlit as st

APP_STYLES = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Lato:ital,wght@0,300;0,400;0,700;1,400&family=Open+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* --- TYPOGRAPHY & LAYOUT --- */
body, .stMarkdown, .stButton, .stTextInput, .stChatInput {
    font-family: 'Open Sans', sans-serif;
}

/* Titles and Headings - Montserrat for a clean, versatile feel */
h1, h2, h3, .brand-title {
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 600;
    letter-spacing: -0.02em;
}

/* Chat typography - optimized for readability */
.chat-line {
    margin: 1.5rem 0;
    font-size: 0.95rem;
    line-height: 1.6;
}

@media (max-width: 600px) {
    .chat-line {
        font-size: 0.9rem;
    }
}

/* --- CHAT BUBBLES --- */
.chat-line .name {
    display: block;
    font-weight: 600;
    font-size: 0.72rem;
    margin-bottom: 0.3rem;
    opacity: 0.9;
    margin-left: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-family: 'Montserrat', sans-serif;
}

.chat-line .msg {
    display: inline-block;
    padding: 1rem 1.25rem;
    border-radius: 1.1rem;
    max-width: 85%;
    word-wrap: break-word;
    border: 1px solid rgba(255, 255, 255, 0.08); /* Subtle border for glassmorphism */
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(5px); }
    to { opacity: 1; transform: translateY(0); }
}

/* CLARA'S BUBBLE: Glass Teal */
.chat-line.clara .msg {
    background: rgba(15, 118, 110, 0.15); /* Semi-transparent Teal */
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    color: #ccfbf1; /* Teal 100 */
    border-bottom-left-radius: 0.3rem;
    font-family: 'Lato', sans-serif;
    font-weight: 400;
    font-size: 1.05rem; 
    line-height: 1.7;
}

.clara-label {
    color: #5eead4; /* Teal 300 */
}

/* USER'S BUBBLE: Glass Blue */
.chat-line.user .msg {
    background: rgba(30, 64, 175, 0.15); /* Semi-transparent Blue */
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    color: #dbeafe; /* Blue 100 */
    border-bottom-right-radius: 0.3rem;
    font-family: 'Open Sans', sans-serif;
    font-weight: 400;
}

.user-label {
    color: #93c5fd; /* Blue 300 */
}

/* --- SIDEBAR & UI --- */
[data-testid="stSidebar"] {
    border-right: 1px solid #1e293b; /* Slate border */
}

[data-testid="stSidebar"] * {
    font-size: 0.85rem;
    color: #cbd5e1; /* Slate 300 */
}

[data-testid="stSidebar"] .st-expander {
    border: none;
    background: transparent;
}

/* Data & Privacy sidebar text */
.privacy-text {
    font-size: 0.75rem;
    line-height: 1.5;
    color: #94a3b8;
}

.privacy-text h2,
.privacy-text h3,
.privacy-text strong {
    color: #e2e8f0;
    font-weight: 600;
}

/* --- BUTTONS --- */
/* Standardize buttons for a premium feel */
.stButton button, .stLinkButton a {
    border-radius: 0.5rem !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    font-weight: 500 !important;
}

/* Secondary Button Hover (Neutral) */
.stButton button[kind="secondary"]:hover {
    border-color: #64748b !important; /* Slate 500 */
    color: #f8fafc !important; /* Slate 50 */
    background: #334155 !important; /* Slate 700 */
}

/* Primary Button refinement */
.stButton button[kind="primary"], .stLinkButton a[data-testid="stLinkButton"] {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
}

/* Danger Zone delete buttons */
.danger-delete button {
    background-color: transparent !important;
    border: 1px solid #b91c1c !important;
    color: #f87171 !important;
    transition: all 0.2s ease;
}

.danger-delete button:hover {
    background-color: #7f1d1d !important;
    border-color: #ef4444 !important;
    color: white !important;
}

/* Footer / Disclaimer text */
.footer-text {
    font-size: 0.7rem;
    color: #64748b; /* Slate 500 */ 
    text-align: center;
    margin-top: 3rem;
    padding-bottom: 1rem;
}

.footer-text a {
    color: #94a3b8;
    text-decoration: none;
    transition: color 0.2s;
}

.footer-text a:hover {
    color: #cbd5e1;
}
</style>


"""

def apply_styles():
    st.markdown(APP_STYLES, unsafe_allow_html=True)
