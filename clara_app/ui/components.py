import streamlit as st
import html
import pandas as pd
from clara_app.constants import RETRO_UI
from clara_app.services import storage

def render_chat_message(role, content):
    if role == "assistant":
        label = "Clara"
        label_class = "clara-label"
        avatar = "Clara Avatars/Simple Avatar/clara_avatar_helmet.jpeg"
    else:
        label = st.session_state.get("display_name") or "You"
        label_class = "user-label"
        avatar = "Clara Avatars/Simple Avatar/user_avatar_simple.png"

    if RETRO_UI:
        safe_text = html.escape(content).replace("\n", "<br/>")
        line_class = "clara" if role == "assistant" else "user"
        st.markdown(
            f"<div class=\"chat-line {line_class}\"><span class=\"name {label_class}\">{html.escape(label)}:</span><span class=\"msg\">{safe_text}</span></div>",
            unsafe_allow_html=True,
        )
        return

    with st.chat_message(role, avatar=avatar):
        # Never inject model/user text into HTML. Render content as safe Markdown.
        # safe_label = html.escape(label)
        # st.markdown(f"<span class=\"chat-name {label_class}\">{safe_label}</span>", unsafe_allow_html=True)
        # ^ Original code had this, but st.chat_message handles avatars nicely. 
        # However, to keep the "name above message" style with specific colors, we keep it.
        safe_label = html.escape(label)
        st.markdown(f"<span class=\"chat-name {label_class}\">{safe_label}</span>", unsafe_allow_html=True)
        st.markdown(content)

def render_footer():
    """Renders the copyright and terms of use disclaimer."""
    st.markdown(
        """
        <div class="footer-text">
            Clara Aster™ is a trademark of ASTR, LLC. © 2025 ASTR, LLC.
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_terms_page():
    st.title("Terms of Use")
    st.markdown("*Last updated: December 2025*")
    st.write(
        """
        **1. Acceptance of Terms**
        By accessing and using the Clara Aster ("the Service"), you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by these terms, you are not authorized to use or access the Service.

        **2. Access and Use License**
        Subject to your compliance with these Terms, Clara Aster grants you a limited, non-exclusive, non-transferable, and revocable license to access and use the Service for your personal, non-commercial use. 
        
        **Restrictions:** You agree that you will not:
        - Modify, copy, distribute, transmit, display, perform, reproduce, publish, license, create derivative works from, transfer, or sell any information, software, or services obtained from the Clara Aster.
        - Reverse engineer, decompile, or disassemble any aspect of the Service to access the source code or underlying algorithms.
        - Use the Service to scrape data or build a competitive product.

        **3. Intellectual Property Rights**
        The Service and its original content, features, and functionality (including but not limited to all information, software, code, text, displays, and images) are owned by Clara Aster and are protected by international copyright, trademark, patent, trade secret, and other intellectual property or proprietary rights laws.

        **4. Disclaimer of Warranties**
        The Service is provided on an "AS IS" and "AS AVAILABLE" basis. Clara Aster makes no warranties, expressed or implied, regarding the accuracy, reliability, or completeness of the content provided by the Service. 
        
        **AI Disclaimer:** The Service utilizes artificial intelligence to generate responses. As an AI Persona, these responses may occasionally be inaccurate. You should not rely on this Digital Presence for professional (medical, legal, financial) advice.

        **5. Limitation of Liability**
        In no event shall Clara Aster, its developers, or suppliers be liable for any damages (including, without limitation, damages for loss of data or profit, or due to business interruption) arising out of the use or inability to use the Service, even if Clara Aster has been notified orally or in writing of the possibility of such damage.

        **6. Termination**
        We may terminate or suspend access to our Service immediately, without prior notice or liability, for any reason whatsoever, including without limitation if you breach the Terms.
        """
    )
    if st.button("← Back to App"):
        st.query_params.clear()
        st.rerun()

    render_footer()

def render_privacy_policy_page():
    """Renders the consolidated privacy policy page (Gemini-style)."""
    st.title("Privacy Policy")
    st.markdown(
        """
        At **Clara Aster**, we prioritize your privacy and trust. This policy outlines what data we collect, why we use it, and how you can control it.

        ### 1. Information We Collect
        We collect data to provide the service and improve your experience.
        *   **Conversations:** The messages you send and receive are stored to maintain context and history.
        *   **Account Information:** Basic details like your preferred name, city, and timezone (if provided).
        *   **Usage Logs:** Anonymous counters (e.g., number of messages sent) to monitor system stability.

        ---

        ### 2. How We Use Information
        *   **To Provide the Service:** We process your input to generate responses and maintain your conversational history.
        *   **Safety & Security:** We process content to detect and prevent harmful or illegal activity in line with our safety guidelines.
        *   **AI Processing:** Content is processed by Google's Gemini API to generate responses. By using this service, you acknowledge that data handling is subject to Google's API data usage policies.

        ---

        ### 3. Your Privacy Controls
        You have full control over your data.
        *   **Clear Chat:** You can instantly wipe the active conversation from Clara's short-term memory using the "Clear Chat" button in Settings.
        *   **Delete Account:** You can permanently delete your entire account, including all history and profile data, via the "Manage Account & Data" page. This action is irreversible.

        ---

        ### 4. Keeping You Safe
        *   **Age Requirement:** This service is intended for users **18+**.
        *   **Nature of Presence:** Clara is an AI Persona, not a human. She is not a replacement for professional medical, legal, or financial advice.
        *   **Crisis Resources:** If you are in crisis, please call **911** or **988** (US) immediately.

        ---

        ### 5. Contact Us
        *   **Privacy Inquiries:** For questions regarding your data, please contact **privacy@claraaster.com**

        ---


        ---

        """
    )
    if st.button("← Back to App"):
        st.query_params.clear()
        st.rerun()

    render_footer()


@st.dialog("Edit Profile")
def edit_profile_dialog():
    st.write("Update your details below to help Clara understand you better.")
    
    # 1. Profile Note
    current_note = storage.get_user_profile_note(st.session_state.username)
    new_note = st.text_area(
        "About You",
        value=current_note,
        height=140,
        placeholder="Is there anything specific about your world—like your career, family, health, or personal goals—that would help me understand you better?",
        help="Shared context for Clara to keep in mind."
    )
    
    # 2. Timezone / City
    current_timezone = storage.get_user_timezone(st.session_state.username) or ""
    new_timezone = st.text_input(
        "City / Time Zone",
        value=current_timezone,
        placeholder="e.g. London, New York"
    )
    
    if st.button("Save Changes", type="primary"):
        if new_note != current_note:
            storage.save_user_profile_note(st.session_state.username, new_note)
        
        if new_timezone != current_timezone:
            storage.save_user_timezone(st.session_state.username, new_timezone.strip())
            
        st.success("Profile updated!")
        st.rerun()

def render_sidebar():
    # --- Sidebar: Profile, Settings, Info, Danger Zone ---
    with st.sidebar:
        st.sidebar.title("Clara")
        # 1. Profile at the top
        with st.expander("Profile", expanded=False):
            # Read-only view
            note = storage.get_user_profile_note(st.session_state.username)
            tz = storage.get_user_timezone(st.session_state.username)
            
            if note:
                st.caption("About You")
                st.info(note)
            else:
                st.info("Tell Clara about yourself...")

            if tz:
                st.caption("Location")
                st.markdown(f"**{tz}**")
            
            st.write("") # Spacer
            if st.button("Edit Profile", use_container_width=True):
                edit_profile_dialog()

        # 2. Settings
        with st.expander("Settings", expanded=False):
            if st.button("Clear Chat", type="secondary"):
                st.session_state.messages = []
                storage.clear_chat_history(st.session_state.username)
                st.rerun()

            if st.button("Change name", type="secondary"):
                st.session_state.display_name = ""
                st.rerun()

            if st.button("Sign out", type="secondary"):
                st.session_state.username = None
                st.session_state.user_id = None
                st.session_state.user_email = None
                st.session_state.display_name = None
                st.session_state.messages = []
                st.rerun()

            st.markdown("---")

            # Feedback
            st.info("Have feedback? Email us at **feedback@claraaster.com**")

            st.markdown("---")
            if st.button("Manage Account & Data", use_container_width=True):
                st.query_params["page"] = "account"
                st.rerun()

        # 3. Privacy & Terms
        with st.expander("Privacy & Terms"):
            st.markdown(
                """
                **Safety & Control**

                **Nature of Presence**  
                Clara is an AI Persona and a Digital Presence—a witness to patterns and a partner in thought. She is not a professional service (doctor, therapist, or lawyer).

                **In a Crisis**
                <div style="color: #FF4B4B; font-weight: bold;">
                If you are in crisis, call 911 or call/text 988 immediately (US).
                </div>
                """,
                unsafe_allow_html=True,
            )
            
            st.markdown("---")
            
            # Legal page navigation
            if st.button("Privacy Policy", key="sidebar_legal", use_container_width=True):
                st.query_params["page"] = "legal"
                st.rerun()
            
            if st.button("Terms of Use", key="sidebar_terms", use_container_width=True):
                st.query_params["page"] = "terms"
                st.rerun()

        # Anonymous Topic Logger – lightweight admin-style view for this session
        # Hidden for production/immersion.
        # if "topic_counts" in st.session_state and st.session_state.topic_counts:
        #     with st.expander("Anonymous topics (this session)", expanded=False):
        #         counts = st.session_state.topic_counts
        #         data = pd.DataFrame(
        #             {"topic": list(counts.keys()), "count": list(counts.values())}
        #         ).set_index("topic")
        #         st.bar_chart(data)

        # Standard Footer
        st.sidebar.caption("Clara Aster™ is a trademark of ASTR, LLC. © 2025 ASTR, LLC.")

def render_account_page():
    st.markdown("## Account & Data Management")
    st.markdown("Manage your data and account status. Use these controls to clear history, reset your profile, or delete your account permanently.")
    st.markdown("---")

    # 1. Clear Chat
    st.subheader("1. Clear Chat (The Blank Page)")
    st.markdown(
        """
        - **What it does:** Wipes your current conversation window and Clara's "short-term" memory of the discussion.
        - **Best for:** Starting a new topic without Clara being influenced by the previous conversation context.
        - **Data Status:** Old messages are effectively hidden/archived (marked with a timestamp), but Clara's *Summary* of who you are and what you talked about in that session is erased.
        """
    )
    if st.button("Clear Chat", type="secondary"):
        st.session_state.messages = []
        storage.clear_chat_history(st.session_state.username)
        # We don't rerun here to let the toast show or just clear state, but actually button reloads anyway in streamlit effectively
        st.success("Chat context cleared.")
        # If we want to return to main, we could, but let's stay here.
    
    st.markdown("---")

    # 2. Account Reset
    st.subheader("2. Account Reset (Factory Reset)")
    st.markdown(
        """
        - **What it does:** Wipes all personalization, including your chosen name, profile notes, city/timezone, and *all* chat history.
        - **Best for:** When you want to start fresh as a "new user" but keep your existing login credentials.
        - **Data Status:** Permanently deletes your profile data and conversation logs. You return to "Day 1" of the experience.
        """
    )
    
    if st.button("Reset Account", type="primary"):
        st.session_state.confirm_reset_page = True
        st.session_state.confirm_delete_account_page = False

    if st.session_state.get("confirm_reset_page"):
        st.warning("⚠️ **Warning:** This action will permanently delete your profile information and chat history. This process cannot be undone.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm Reset", key="page_confirm_reset_yes"):
                storage.delete_user_account(st.session_state.username, st.session_state.user_id)
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()
        with col2:
            if st.button("Cancel", key="page_confirm_reset_cancel"):
                st.session_state.confirm_reset_page = False
                st.rerun()

    st.markdown("---")

    # 3. Delete Account
    st.subheader("3. Delete Account (The Shredder)")
    st.markdown(
        """
        - **What it does:** The nuclear option. It removes everything associated with you from the system.
        - **Best for:** Permanently leaving the platform.
        - **Data Status:** Deletes your profile, all history, usage stats, and your authentication record. If you wanted to return, you would have to create a completely new account.
        """
    )

    st.markdown('<div class="danger-delete">', unsafe_allow_html=True)
    if st.button("Delete Account", type="primary"):
        st.session_state.confirm_delete_account_page = True
        st.session_state.confirm_reset_page = False

    if st.session_state.get("confirm_delete_account_page"):
        st.error("🛑 **Danger:** Are you sure you want to delete your account? All data, including your history and settings, will be permanently removed from our systems.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Permanently Delete Account", key="page_confirm_delete_account_yes"):
                storage.delete_entire_account(st.session_state.username, st.session_state.user_id)
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()
        with col2:
            if st.button("Cancel", key="page_confirm_delete_account_cancel"):
                st.session_state.confirm_delete_account_page = False
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("← Back to App"):
        st.query_params.clear()
        st.rerun()

    render_footer()
