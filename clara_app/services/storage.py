import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
from clara_app.constants import FREE_DAILY_MESSAGE_LIMIT, PLUS_DAILY_MESSAGE_LIMIT, FORCE_PLAN, FIREBASE_SERVICE_ACCOUNT, FIREBASE_CREDENTIALS_PATH
from clara_app.utils.helpers import normalize_email

# @st.cache_resource # Removed to prevent stale client issues after long uptime
def get_db():
    if not firebase_admin._apps:

        try:
            if FIREBASE_SERVICE_ACCOUNT:
                cred = credentials.Certificate(dict(FIREBASE_SERVICE_ACCOUNT))
            else:
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"Error loading Firebase: {e}")
            return None

    try:
        return firestore.client()
    except Exception:
        return None

# initialize_firebase is deprecated in favor of cached get_db, but kept for compatibility if needed elsewhere
def initialize_firebase():
    return get_db()

# --- DB Helpers ---

def _get_chat_doc(username):
    db = get_db()
    if db is None:
        return None
    return db.collection("chats").document(username)

def _get_user_doc(user_id: str):
    db = get_db()
    if db is None:
        return None
    return db.collection("users").document(user_id)

def ensure_user_identity(user_id: str, email: str):
    """
    Keep a stable user document keyed by user_id, storing the login email separately.
    """
    doc_ref = _get_user_doc(user_id)
    if doc_ref is None:
        return
    try:
        existing = doc_ref.get()
        payload = {
            "email": normalize_email(email),
            "updatedAt": datetime.datetime.now(datetime.timezone.utc),
        }
        if not existing.exists:
            payload["createdAt"] = firestore.SERVER_TIMESTAMP
        doc_ref.set(payload, merge=True)
    except Exception:
        pass

def chat_doc_exists(chat_id: str) -> bool:
    doc_ref = _get_chat_doc(chat_id)
    if doc_ref is None:
        return False
    try:
        doc = doc_ref.get()
        return bool(doc.exists)
    except Exception:
        return False

def _daily_usage_doc(username, date_str: str):
    db = get_db()
    if db is None:
        return None
    return db.collection("usage").document(username).collection("daily").document(date_str)

def migrate_legacy_chat_doc(*, legacy_chat_id: str, new_chat_id: str, email: str, max_messages: int = 250) -> bool:
    """
    Best-effort migration from legacy chat doc ids (email) to stable ids (hash).
    Copies core fields and a bounded number of recent messages.
    """
    db = get_db()
    if db is None:
        return False
    if not legacy_chat_id or not new_chat_id or legacy_chat_id == new_chat_id:
        return False

    legacy_ref = _get_chat_doc(legacy_chat_id)
    new_ref = _get_chat_doc(new_chat_id)
    if legacy_ref is None or new_ref is None:
        return False

    try:
        legacy_doc = legacy_ref.get()
        if not legacy_doc.exists:
            return False
        if new_ref.get().exists:
            return True

        legacy_data = legacy_doc.to_dict() or {}
        new_ref.set(
            {
                "profile": legacy_data.get("profile", {}) or {},
                "summary": legacy_data.get("summary", "") or "",
                "clearedAt": legacy_data.get("clearedAt"),
                "usage": legacy_data.get("usage", {}) or {},
                "chatMeta": {
                    "migratedFrom": legacy_chat_id,
                    "migratedAt": datetime.datetime.now(datetime.timezone.utc),
                    "email": normalize_email(email),
                },
            },
            merge=True,
        )

        # Prefer migrating from the legacy messages subcollection if present.
        migrated_any = False
        try:
            q = legacy_ref.collection("messages").order_by("ts", direction=firestore.Query.DESCENDING).limit(max_messages)
            docs = q.get()
            if docs:
                batch = db.batch()
                # Reverse so timestamps remain ascending when written.
                for d in reversed(docs):
                    data = d.to_dict() or {}
                    role = data.get("role")
                    content = data.get("content")
                    ts = data.get("ts")
                    if role not in ("user", "assistant") or not isinstance(content, str):
                        continue
                    target = new_ref.collection("messages").document()
                    batch.set(
                        target,
                        {
                            "role": role,
                            "content": content,
                            "ts": ts or datetime.datetime.now(datetime.timezone.utc),
                        },
                    )
                batch.commit()
                migrated_any = True
        except Exception:
            migrated_any = False

        # If there was no messages subcollection, migrate from the legacy `messages` array.
        if not migrated_any:
            legacy_messages = legacy_data.get("messages", []) or []
            if isinstance(legacy_messages, list) and legacy_messages:
                recent = legacy_messages[-max_messages:]
                base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=len(recent) + 1)
                batch = db.batch()
                for i, m in enumerate(recent):
                    role = (m or {}).get("role")
                    content = (m or {}).get("content")
                    if role not in ("user", "assistant") or not isinstance(content, str):
                        continue
                    target = new_ref.collection("messages").document()
                    batch.set(target, {"role": role, "content": content, "ts": base + datetime.timedelta(seconds=i + 1)})
                batch.commit()

        # Leave legacy chat doc intact, but mark it for diagnostics.
        legacy_ref.set({"chatMeta": {"migratedTo": new_chat_id}}, merge=True)

        # Best-effort: carry over today's usage counter so limits behave consistently.
        try:
            today_str = datetime.date.today().isoformat()
            legacy_usage = _daily_usage_doc(legacy_chat_id, today_str)
            new_usage = _daily_usage_doc(new_chat_id, today_str)
            if legacy_usage is not None and new_usage is not None:
                legacy_usage_doc = legacy_usage.get()
                if legacy_usage_doc.exists and not new_usage.get().exists:
                    new_usage.set(legacy_usage_doc.to_dict() or {}, merge=True)
        except Exception:
            pass

        return True
    except Exception:
        return False

def get_cleared_at(username):
    doc_ref = _get_chat_doc(username)
    if doc_ref is None:
        return None
    try:
        doc = doc_ref.get()
        if not doc.exists:
            return None
        return (doc.to_dict() or {}).get("clearedAt")
    except Exception:
        return None

def append_chat_message(username, role: str, content: str):
    """Append a single message to Firestore as its own document."""
    db = get_db()
    if db is None:
        return
    if not username or role not in ("user", "assistant"):
        return
    if not isinstance(content, str) or not content.strip():
        return

    doc_ref = _get_chat_doc(username)
    if doc_ref is None:
        return

    try:
        msg_ref = doc_ref.collection("messages").document()
        msg_ref.set(
            {
                "role": role,
                "content": content,
                "ts": datetime.datetime.now(datetime.timezone.utc),
            }
        )
    except Exception:
        # Persistence should never break the main chat flow
        pass

def clear_chat_history(username):
    """
    "Clear memory" without deleting docs: mark a cutoff timestamp and clear the durable summary.
    Message queries only return items newer than clearedAt.
    """
    doc_ref = _get_chat_doc(username)
    if doc_ref is None:
        return
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        doc_ref.set(
            {
                "clearedAt": now,
                "summary": "",
                # Keep legacy field small if it exists from earlier versions
                "messages": [],
            },
            merge=True,
        )
    except Exception:
        pass

def _maybe_migrate_legacy_messages(username, legacy_messages):
    """
    One-time migration: if there are no message docs yet, copy the legacy `messages` array
    into `chats/{username}/messages/*` so we can stop rewriting a single large document.
    """
    db = get_db()
    if db is None:
        return
    if not legacy_messages:
        return

    doc_ref = _get_chat_doc(username)
    if doc_ref is None:
        return

    try:
        # If any message docs exist, don't migrate.
        existing = doc_ref.collection("messages").limit(1).get()
        if existing:
            return

        # Write in a batch with increasing timestamps to preserve ordering.
        batch = db.batch()
        base = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=len(legacy_messages) + 1)
        for i, m in enumerate(legacy_messages):
            role = m.get("role")
            content = m.get("content")
            if role not in ("user", "assistant") or not isinstance(content, str):
                continue
            msg_ref = doc_ref.collection("messages").document()
            batch.set(
                msg_ref,
                {
                    "role": role,
                    "content": content,
                    "ts": base + datetime.timedelta(seconds=i + 1),
                },
            )
        batch.commit()

        # Clear legacy array so it stops growing / inflating reads.
        doc_ref.set({"messages": [], "chatMeta": {"legacyMigrated": True}}, merge=True)
    except Exception:
        pass

def get_chat_history(username, limit: int = 60):
    """Load recent conversation from Firestore (subcollection-first, legacy fallback)."""
    db = get_db()
    if db is None:
        return []
    if not username:
        return []

    doc_ref = _get_chat_doc(username)
    if doc_ref is None:
        return []

    cleared_at = get_cleared_at(username)
    try:
        q = doc_ref.collection("messages")
        if cleared_at:
            q = q.where("ts", ">", cleared_at)
        docs = q.order_by("ts", direction=firestore.Query.DESCENDING).limit(limit).get()
        if docs:
            items = []
            for d in reversed(docs):
                data = d.to_dict() or {}
                role = data.get("role")
                content = data.get("content")
                if role in ("user", "assistant") and isinstance(content, str):
                    items.append({"role": role, "content": content})
            return items
    except Exception as e:
        # If query fails, fall back to legacy field
        print(f"Error fetching chat history (Query): {e}")
        pass

    # Legacy fallback: read `messages` array from the chat doc (older versions)
    try:
        doc = doc_ref.get()
        if not doc.exists:
            return []
        legacy = (doc.to_dict() or {}).get("messages", []) or []
        if isinstance(legacy, list) and legacy:
            _maybe_migrate_legacy_messages(username, legacy)
            # Apply clearedAt cutoff locally for legacy messages (no ts field there)
            if cleared_at:
                return []
            return legacy[-limit:]
    except Exception:
        pass

    return []

def log_topic_metric(topic: str):
    """
    Increment an anonymous aggregate counter for the given topic.
    No user identifiers or raw message text are stored in this document.
    """
    db = get_db()
    if db is None: return
    if not topic:
        topic = "other"
    try:
        metrics_ref = db.collection("metrics").document("topics")
        metrics_ref.set({topic: firestore.Increment(1)}, merge=True)
    except Exception:
        pass

def log_ml_topic_metric(topic: str):
    """
    Increment an anonymous aggregate counter for the ML-based topic labels.
    Uses a separate document so it doesn't conflict with the heuristic logger.
    """
    db = get_db()
    if db is None:
        return
    if not topic:
        topic = "Other"
    try:
        metrics_ref = db.collection("metrics").document("topics_ml")
        metrics_ref.set({topic: firestore.Increment(1)}, merge=True)
    except Exception:
        pass

def get_chat_summary(username):
    """Load a short, durable summary of the chat from Firestore"""
    db = get_db()
    if db is None: return ""
    doc_ref = db.collection("chats").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return ""
    return doc.to_dict().get("summary", "") or ""

def save_chat_summary(username, summary):
    """Save/update the short summary for this user"""
    db = get_db()
    if db is None: return
    doc_ref = db.collection("chats").document(username)
    doc_ref.set({"summary": summary}, merge=True)

def get_user_name(username):
    db = get_db()
    if db is None: return None
    doc_ref = db.collection("chats").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return None
    profile = doc.to_dict().get("profile", {})
    name = profile.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else None

def save_user_name(username, name):
    db = get_db()
    if db is None: return
    doc_ref = db.collection("chats").document(username)
    doc_ref.set({"profile": {"name": name}}, merge=True)

def get_user_timezone(username):
    """Return the user's preferred timezone / city string."""
    db = get_db()
    if db is None: return None
    doc_ref = db.collection("chats").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return None
    profile = doc.to_dict().get("profile", {})
    tz = profile.get("timezone")
    return tz.strip() if isinstance(tz, str) and tz.strip() else None

def save_user_timezone(username, timezone_str):
    """Persist the user's preferred timezone string on their profile."""
    db = get_db()
    if db is None: return
    doc_ref = db.collection("chats").document(username)
    doc_ref.set({"profile": {"timezone": timezone_str}}, merge=True)

def get_user_profile_note(username):
    """Short, free-text note the user shares about themselves."""
    db = get_db()
    if db is None: return ""
    doc_ref = db.collection("chats").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return ""
    profile = doc.to_dict().get("profile", {})
    note = profile.get("profileNote") or ""
    return note.strip()

def save_user_profile_note(username, note):
    """Persist the user's optional profile note."""
    db = get_db()
    if db is None: return
    clean = (note or "").strip()
    doc_ref = db.collection("chats").document(username)
    doc_ref.set({"profile": {"profileNote": clean}}, merge=True)

def get_user_plan(username) -> str:
    """
    Load the user's plan ("free" or "plus") from the chat doc.
    Plan is relatively static; daily usage is tracked separately.
    """
    if FORCE_PLAN:
        return FORCE_PLAN
    plan = "free"
    db = get_db()
    if db is None:
        return plan
    doc_ref = _get_chat_doc(username)
    if doc_ref is None:
        return plan
    try:
        doc = doc_ref.get()
        if not doc.exists:
            return plan
        data = doc.to_dict() or {}
        usage = data.get("usage", {}) or {}
        stored_plan = usage.get("plan")
        if isinstance(stored_plan, str) and stored_plan.strip():
            return stored_plan.strip().lower()
    except Exception:
        pass
    return plan

def get_daily_message_count(username, date_str: str) -> int:
    db = get_db()
    if db is None:
        return 0
    ref = _daily_usage_doc(username, date_str)
    if ref is None:
        return 0
    try:
        doc = ref.get()
        if not doc.exists:
            return 0
        data = doc.to_dict() or {}
        return int(data.get("count") or 0)
    except Exception:
        return 0

def increment_daily_message_count(username, date_str: str, amount: int = 1):
    """
    Atomically increment a per-day counter in Firestore:
    usage/{username}/daily/{YYYY-MM-DD}.count
    """
    db = get_db()
    if db is None:
        return
    ref = _daily_usage_doc(username, date_str)
    if ref is None:
        return
    try:
        ref.set(
            {
                "count": firestore.Increment(int(amount)),
                "updatedAt": datetime.datetime.now(datetime.timezone.utc),
            },
            merge=True,
        )
    except Exception:
        pass

def _delete_all_docs_in_collection(collection_ref, batch_size: int = 250) -> None:
    """
    Best-effort deletion of every document in a collection.
    Firestore does not cascade delete subcollections when parent docs are deleted,
    so account deletion must explicitly remove subcollection documents too.
    """
    db = get_db()
    if db is None or collection_ref is None:
        return
    try:
        batch_size = int(batch_size)
    except Exception:
        batch_size = 250
    if batch_size <= 0:
        batch_size = 250

    while True:
        try:
            docs = collection_ref.limit(batch_size).get()
        except Exception:
            return
        if not docs:
            return
        try:
            batch = db.batch()
            for d in docs:
                batch.delete(d.reference)
            batch.commit()
        except Exception:
            for d in docs:
                try:
                    d.reference.delete()
                except Exception:
                    pass
        if len(docs) < batch_size:
            return

def delete_user_account(username: str, user_id: str | None):
    """
    Permanently delete the core documents for this account:
    - chats/{username}
    - users/{user_id} (if provided)
    - usage/{username}
    Subcollections (like messages) are deleted so data is actually removed.
    """
    db = get_db()
    if db is None:
        return
    try:
        if username:
            try:
                chat_ref = db.collection("chats").document(username)
                _delete_all_docs_in_collection(chat_ref.collection("messages"))
                chat_ref.delete()
            except Exception:
                pass
            try:
                usage_ref = db.collection("usage").document(username)
                _delete_all_docs_in_collection(usage_ref.collection("daily"))
                usage_ref.delete()
            except Exception:
                pass
        if user_id:
            try:
                db.collection("users").document(user_id).delete()
            except Exception:
                pass
    except Exception:
        # Account deletion should never crash the app
        pass

def delete_entire_account(username: str, user_id: str | None):
    """
    Nuclear option: permanently delete all records of this user.
    1. chats/{username} -> Contains history, profile, and name.
    2. usage/{username}  -> Contains daily limits.
    3. users/{user_id}   -> Contains the sensitive PII (email).
    """
    db = get_db()
    if db is None:
        return

    # 1. Delete Chat & Profile
    if username:
        try:
            chat_ref = db.collection("chats").document(username)
            _delete_all_docs_in_collection(chat_ref.collection("messages"))
            chat_ref.delete()
        except Exception:
            pass

    # 2. Delete Usage Stats
    if username:
        try:
            usage_ref = db.collection("usage").document(username)
            _delete_all_docs_in_collection(usage_ref.collection("daily"))
            usage_ref.delete()
        except Exception:
            pass

    # 3. Delete Identity (The Email Record)
    if user_id:
        try:
            db.collection("users").document(user_id).delete()
        except Exception:
            pass
