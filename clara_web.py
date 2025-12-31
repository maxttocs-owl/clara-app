try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import random

from clara_app.constants import FREE_DAILY_MESSAGE_LIMIT, PLUS_DAILY_MESSAGE_LIMIT, BETA_ACCESS_KEY, FIREBASE_WEB_API_KEY
from clara_app.services import storage, llm, memory, auth
from clara_app.utils import helpers
from clara_app.ui import styles, components

from PIL import Image

# --- 1. SETUP & CONFIGURATION ---
try:
    favicon = Image.open("assets/clara_favicon.png")
except Exception:
    favicon = None

st.set_page_config(page_title="Clara Aster", page_icon=favicon, layout="centered")

# Initialize Firebase (The Memory & Security)
storage.initialize_firebase()

# Apply Styles
styles.apply_styles()

# Initialize Session State
if "username" not in st.session_state:
    st.session_state.username = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "display_name" not in st.session_state:
    st.session_state.display_name = None
if "beta_authenticated" not in st.session_state:
    st.session_state.beta_authenticated = False

# --- 1.1. BETA ACCESS GATE ---
if not st.session_state.beta_authenticated:
    st.title("Clara Aster™")
    with st.form("beta_gate_form"):
        key_input = st.text_input("Enter Early Access Key", type="password")
        submit_key = st.form_submit_button("Enter")
    
    if submit_key:
        if key_input == BETA_ACCESS_KEY:
            st.session_state.beta_authenticated = True
            st.rerun()
        else:
            st.error("Invalid Key.")
    st.stop()

# --- 1.5. PAGE ROUTING (Legal Content) ---
# If query params indicate a legal page, render it and stop execution.
if "page" in st.query_params:
    page = st.query_params["page"]
    if page == "terms":
         components.render_terms_page()
         st.stop()
    elif page == "legal":
         components.render_privacy_policy_page()
         st.stop()
    elif page == "account":
         components.render_account_page()
         st.stop()

# --- 2. THE WEB INTERFACE ---

# --- 2. THE WEB INTERFACE ---

# --- VIEW A: AUTHENTICATION SCREEN ---
if st.session_state.username is None:
    st.title("Clara")
    
    if FIREBASE_WEB_API_KEY:
        tab1, tab2 = st.tabs(["Log In", "New Account"])

        # --- LOG IN ---
        with tab1:
            with st.form("clara_login_form"):
                email_in = st.text_input("Email", placeholder="you@example.com")
                pass_in = st.text_input("Password", type="password", placeholder="••••••")
                submit_login = st.form_submit_button("Log In", type="primary")
            
            if submit_login:
                if not email_in or not pass_in:
                    st.error("Please enter both email and password.")
                else:
                    uid, user_email, err = auth.sign_in(email_in, pass_in)
                    if err:
                        st.error(err)
                    else:
                        # Success! Set up session
                        st.session_state.user_email = user_email
                        st.session_state.user_id = uid  # usage doc id
                        
                        # Core identity setup
                        storage.ensure_user_identity(uid, user_email)
                        
                        # Migration check (if they had a legacy email-doc-id that wasn't migrated yet)
                        # Note: The auth.sign_up logic forces UID to match legacy hash, so this should usually just work.
                        # But we double check ensuring the chat doc exists.
                        chat_id = uid
                        if not storage.chat_doc_exists(uid):
                             # Check for legacy hash ID
                             legacy_hash = helpers.email_to_user_id(user_email)
                             if storage.chat_doc_exists(legacy_hash):
                                 # We found their old data under the hash!
                                 # Since we are logging in with a UID that MIGHT match the hash (thanks to my auth.py fix),
                                 # this check is just a safeguard.
                                 if uid != legacy_hash:
                                     # This happens if they have a random UID from before the fix.
                                     # We should migrate or just use the hash as the chat_id.
                                     chat_id = legacy_hash
                        
                        st.session_state.username = chat_id
                        st.session_state.display_name = None # Will auto-fetch on rerun
                        st.rerun()

            # Simple password reset 
            with st.expander("Forgot password?"):
                with st.form("reset_form"):
                    reset_email = st.text_input("Account Email")
                    reset_submit = st.form_submit_button("Send Reset Link")
                if reset_submit and reset_email:
                    ok, msg = auth.send_password_reset(reset_email)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

        # --- SIGN UP ---
        with tab2:
            st.caption("Create a secure account to talk to Clara.")
            with st.form("clara_signup_form"):
                new_email = st.text_input("Email")
                new_pass = st.text_input("Password", type="password", help="At least 6 characters")
                confirm_pass = st.text_input("Confirm Password", type="password")
                submit_signup = st.form_submit_button("Create Account")
            
            if submit_signup:
                if not new_email or not new_pass:
                    st.error("Please fill in all fields.")
                elif new_pass != confirm_pass:
                    st.error("Passwords do not match.")
                elif len(new_pass) < 6:
                    st.error("Password should be at least 6 characters.")
                else:
                    # Create the user server-side
                    uid, err = auth.sign_up(new_email, new_pass)
                    if err:
                        st.error(err)
                    else:
                        st.success("Account created successfully! Logging you in...")
                        # Auto-login
                        uid, user_email, err = auth.sign_in(new_email, new_pass)
                        if not err:
                            st.session_state.user_email = user_email
                            st.session_state.user_id = uid
                            storage.ensure_user_identity(uid, user_email)
                            st.session_state.username = uid
                            st.session_state.display_name = None
                            st.rerun()
                        else:
                            st.info("Account created. Please switch to the Log In tab to sign in.")
    
    else:
        # --- FALLBACK: SIMPLE EMAIL LOGIN (DEV/LEGACY MODE) ---
        st.caption("Dev Mode active (missing `FIREBASE_WEB_API_KEY`). Using simple email login.")
        with st.form("clara_login_form"):
            username_input = st.text_input("Email", placeholder="Enter your email", label_visibility="collapsed")
            login_submitted = st.form_submit_button("Continue", type="primary")

        if login_submitted and username_input:
            email = helpers.normalize_email(username_input)
            user_id = helpers.email_to_user_id(email)

            st.session_state.user_email = email
            st.session_state.user_id = user_id or None

            # For fallback mode, we default to the legacy/simple email ID unless a migrated ID exists
            chat_id = user_id or email
            
            # Simple identity tracking
            if user_id:
                storage.ensure_user_identity(user_id, email)

            st.session_state.username = chat_id
            st.session_state.display_name = None
            st.rerun()

    components.render_footer()

# --- VIEW C: THE CHAT INTERFACE ---
else:
    # 1. Simple header
    st.title("Clara")

    # 2. Plan & daily usage limits
    plan = storage.get_user_plan(st.session_state.username)
    today_str = datetime.date.today().isoformat()
    message_count_today = storage.get_daily_message_count(st.session_state.username, today_str)
    if plan == "plus":
        daily_limit = PLUS_DAILY_MESSAGE_LIMIT
    else:
        daily_limit = FREE_DAILY_MESSAGE_LIMIT
    over_limit = daily_limit is not None and message_count_today >= daily_limit

    # 3. Render Sidebar
    components.render_sidebar()

    # 4. Load Memory (If first load)
    if "messages" not in st.session_state or len(st.session_state.messages) == 0:
        st.session_state.messages = storage.get_chat_history(st.session_state.username)
    if "topic_counts" not in st.session_state:
        st.session_state.topic_counts = {}
    
    # Initialize the Chat Object with History for Gemini
    gemini_history = []
    # Add durable summary first (if available) so Clara has a compact memory across long chats
    summary_text = storage.get_chat_summary(st.session_state.username)
    if summary_text:
        gemini_history.append(
            {
                "role": "user",
                "parts": [
                    "[CONTEXT] Durable summary:\n" + summary_text
                ],
            }
        )
    if st.session_state.display_name:
        first_name = st.session_state.display_name.split()[0]
        gemini_history.append({"role": "user", "parts": [f"[CONTEXT] User name: {st.session_state.display_name}. Address the user as {first_name}."]})

    # If the user has written an explicit profile note, surface it as
    # durable context so Clara can tailor conversations more precisely.
    profile_note = storage.get_user_profile_note(st.session_state.username)
    if profile_note:
        gemini_history.append(
            {
                "role": "user",
                "parts": [
                    "[CONTEXT] Profile note:\n" + profile_note
                ],
            }
        )

    # Add lightweight time context so Clara can speak naturally about being in London
    try:
        london_now = helpers.get_london_now()
        london_str = london_now.strftime("%A, %H:%M")
        time_context = f"[CONTEXT] Time context: Right now it’s {london_str} in London."

        user_timezone = storage.get_user_timezone(st.session_state.username)
        if user_timezone:
            tz_key = user_timezone.strip()
            # Basic mapping from common city names to IANA timezone IDs
            city_to_tz = {
                "london": "Europe/London",
                "new york": "America/New_York",
                "nyc": "America/New_York",
                "los angeles": "America/Los_Angeles",
                "la": "America/Los_Angeles",
                "san francisco": "America/Los_Angeles",
                "chicago": "America/Chicago",
                "toronto": "America/Toronto",
                "paris": "Europe/Paris",
                "berlin": "Europe/Berlin",
                "tokyo": "Asia/Tokyo",
                "singapore": "Asia/Singapore",
                "sydney": "Australia/Sydney",
                "melbourne": "Australia/Melbourne",
            }
            tz_id = city_to_tz.get(tz_key.lower(), tz_key)
            try:
                user_now = datetime.datetime.now(ZoneInfo(tz_id))
                user_str = user_now.strftime("%A, %H:%M")
                time_context += f" The user’s local time is approximately {user_str} ({user_timezone})."
            except Exception:
                # If we can't interpret their input as a timezone, just note the place.
                time_context += f" The user has told you they are in {user_timezone}."

        gemini_history.append({"role": "user", "parts": [time_context]})
    except Exception:
        pass

    # Only send the most recent part of the conversation to keep context manageable
    recent_messages = st.session_state.messages[-50:]
    for msg in recent_messages:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
    
    # Get Model
    model = llm.get_model()
    try:
        chat_session = model.start_chat(history=gemini_history)
    except:
        chat_session = model.start_chat(history=[]) # Fallback if history error

    # 4. Optional search over this conversation
    search_query = st.text_input("Search this chat", "", placeholder="Type a word or phrase to search…")
    if search_query and st.session_state.messages:
        q = search_query.lower()
        matches = [
            (idx, m)
            for idx, m in enumerate(st.session_state.messages)
            if isinstance(m.get("content"), str) and q in m["content"].lower()
        ]
        with st.expander(f"Found {len(matches)} matching message(s)", expanded=True):
            if matches:
                for idx, m in matches:
                    speaker = "You" if m["role"] == "user" else "Clara"
                    snippet = m["content"]
                    if len(snippet) > 220:
                        snippet = snippet[:217] + "..."
                    st.markdown(f"**{speaker}** · `#{idx+1}`  \n{snippet}")
            else:
                st.caption("No matches in this chat yet.")

    # 5. Display Chat History
    for message in st.session_state.messages:
        components.render_chat_message(message["role"], message["content"])

    # 6. Simple chat input at the bottom, with limits
    if over_limit:
        st.warning(
            "You’ve reached today’s free message limit with the standard Clara experience.\n\n"
            "Clara Plus gives you more daily messages, richer long‑term memory, and room for more detailed answers "
            "when you actually want them.\n\n"
            "For now, reach out directly if you’d like Clara Plus turned on for your account."
        )
        st.chat_input("Talk to Clara...", disabled=True)
    elif True:
        # Capture chat input
        chat_val = st.chat_input("Talk to Clara...")
        
        # Capture button input (Quick Reply)
        # We show the button if the last message was from the assistant, 
        # giving the user an easy one-tap way to carry on.
        btn_val = None
        if st.session_state.messages and st.session_state.messages[-1]["role"] == "assistant":
            last_msg = st.session_state.messages[-1]["content"]
            if helpers.should_show_continue_button(last_msg):
                # Just a subtle button
                if st.button("Continue ➔", key=f"cont_{len(st.session_state.messages)}"):
                    btn_val = "Continue"

        # Prioritise chat input if both exist (rare), otherwise use button
        prompt = chat_val or btn_val
        
        if prompt:
            # A. Display User Message
            components.render_chat_message("user", prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            storage.append_chat_message(st.session_state.username, "user", prompt)
            storage.increment_daily_message_count(st.session_state.username, today_str, 1)

            # Anonymous topic classification (no raw text stored in metrics)
            try:
                topic = llm.classify_topic(prompt)
                st.session_state.topic_counts[topic] = st.session_state.topic_counts.get(topic, 0) + 1
                storage.log_ml_topic_metric(topic)
            except Exception:
                pass

            # Anonymous aggregate topic logging (no raw text or user IDs stored)
            try:
                topic = helpers.classify_conversation_topic(prompt)
                storage.log_topic_metric(topic)
            except Exception:
                pass

            # B. Get Clara's Response (with Clarity/Integrity Mirror)
            try:
                # 1. Emotional Analysis & Memory Retrieval
                memory_context = ""
                try:
                    # Async-like extraction (conceptually)
                    emotion_data = llm.extract_emotional_metadata(prompt)
                    
                    # Store current thought in vector DB (we do it before response so it's searchable in future immediate turns if needed, 
                    # but typically we'd do it after. Here we do it after response to correspond to the 'memory' of the interaction)
                    # Actually, for the Integrity Mirror, we want to know if *this* feeling matches *past* feelings.
                    
                    # a) Semantic Search (General context)
                    related_memories = memory.search_memories(st.session_state.username, prompt, n_results=3)
                    
                    # b) Pattern Search (Integrity Mirror)
                    pattern_memories = []
                    if emotion_data["weight"] >= 7:
                        pattern_memories = memory.search_patterns(st.session_state.username, emotion_data["tone"], n_results=3)
                    
                    # Combine & Deduplicate
                    all_memories = {}
                    for m in related_memories + pattern_memories:
                        all_memories[m["id"]] = m
                    
                    if all_memories:
                        memory_context = "\n[INTEGRITY MIRROR - RELEVANT MEMORIES]\n"
                        for m in all_memories.values():
                            memory_context += f"- ({m['metadata']['timestamp'][:10]}) {m['content']} [Tone: {m['metadata'].get('tone')}]\n"
                except Exception as e:
                    print(f"Memory error: {e}") 

                # 2. Add Context to Prompt (Hidden from user UI)
                final_prompt = prompt
                if memory_context:
                    # We prepend semantic context so Clara knows it immediately
                    final_prompt = f"{memory_context}\n\nUser: {prompt}"

                response = chat_session.send_message(final_prompt)
                clara_text = response.text or ""
                
                # 3. Store this interaction in long-term memory
                try:
                    memory.store_memory(
                        st.session_state.username, 
                        prompt, 
                        {
                            "tone": emotion_data["tone"], 
                            "weight": emotion_data["weight"],
                            "topic": topic if 'topic' in locals() else "General"
                        }
                    )
                except Exception:
                    pass


                # If the user explicitly asks for a full / detailed answer,
                # don't trim; otherwise, keep replies concise based on plan.
                if not helpers.user_wants_full_answer(prompt):
                    # Adjust answer length based on plan:
                    # free users get more concise replies, Clara Plus users get more room.
                    if plan == "plus":
                        max_chars = 1400
                    else:
                        max_chars = 700
                    clara_text = helpers.trim_response_for_conciseness(clara_text, max_chars=max_chars)

                components.render_chat_message("assistant", clara_text)
                st.session_state.messages.append({"role": "assistant", "content": clara_text})
                
                # D. SAVE TO DATABASE (Long-term Memory)
                storage.append_chat_message(st.session_state.username, "assistant", clara_text)

                # E. Occasionally refresh the long-term summary so Clara remembers enduring context
                try:
                    if len(st.session_state.messages) >= 20:
                        # Refresh every ~15 messages, with a bit of randomness to
                        # avoid unnecessary calls in very long chats.
                        if len(st.session_state.messages) % 15 == 0 and random.random() < 0.6:
                            # Summarise the recent conversation into a short, durable memory
                            recent_for_summary = st.session_state.messages[-60:]
                            convo_text = []
                            for m in recent_for_summary:
                                speaker = "User" if m["role"] == "user" else "Clara"
                                convo_text.append(f"{speaker}: {m['content']}")
                            summary_prompt = (
                                "Below is a conversation between the user and Clara.\n\n"
                                + "\n".join(convo_text)
                                + "\n\nWrite a durable memory summary of the user."
                            )
                            # Use concise summary model
                            summary_response = llm.get_summary_model().generate_content(summary_prompt)
                            summary_text = getattr(summary_response, "text", "").strip()
                            if summary_text:
                                storage.save_chat_summary(st.session_state.username, summary_text)
                except Exception:
                    pass

                # F. Refresh Logic
                # We force a rerun so that the "Continue" button disappears from its old spot
                # and reappears at the bottom of the new chat history if needed.
                st.rerun()
                
            except Exception as e:
                error_message = str(e)
                if "429" in error_message or "quota" in error_message.lower():
                    st.warning(
                        "Clara’s thinking is hitting the limits of the current plan for a moment.\n\n"
                        "Give it a little time and try again. If this keeps happening, check your Gemini API usage and billing."
                    )
                else:
                    st.error(f"Clara hit an unexpected error: {type(e).__name__}: {error_message}")
