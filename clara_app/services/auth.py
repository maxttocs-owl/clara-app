import requests
import firebase_admin
from firebase_admin import auth
from clara_app.constants import FIREBASE_WEB_API_KEY
from clara_app.utils import helpers

def sign_up(email, password):
    """
    Create a new user in Firebase Auth.
    CRITICAL: To preserve Clara's history for existing users, we force the UID
    to match the legacy 'email_to_user_id' hash.
    
    Returns: (uid, None) on success, or (None, error_message) on failure.
    """
    if not email or not password:
        return None, "Email and password are required."
    
    # Generate the legacy ID
    legacy_uid = helpers.email_to_user_id(email)
    
    try:
        # Create user with specific UID to match legacy hash
        user = auth.create_user(
            uid=legacy_uid,
            email=email,
            password=password
        )
        return user.uid, None
    except firebase_admin.exceptions.FirebaseError as e:
        # Check for "email already exists"
        # The python SDK error object is a bit complex, but generally:
        err_msg = str(e)
        if "EMAIL_EXISTS" in err_msg or "email already exists" in err_msg.lower():
            return None, "This email is already registered. Try logging in."
        return None, f"Error creating account: {err_msg}"
    except Exception as e:
        return None, str(e)

def sign_in(email, password):
    """
    Authenticate utilizing the Firebase REST API.
    Returns: (uid, email, None) on success, or (None, None, error_message) on failure.
    """
    if not FIREBASE_WEB_API_KEY:
        return None, None, "system_error: Missing FIREBASE_WEB_API_KEY"

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    
    try:
        r = requests.post(url, json=payload)
        resp_data = r.json()
        
        if r.status_code == 200:
            local_id = resp_data.get("localId")
            return local_id, email, None
        else:
            error_details = resp_data.get("error", {}).get("message", "Unknown error")
            if "INVALID_PASSWORD" in error_details:
                return None, None, "Incorrect password."
            elif "EMAIL_NOT_FOUND" in error_details:
                return None, None, "No account found with this email."
            elif "USER_DISABLED" in error_details:
                return None, None, "This account has been disabled."
            else:
                return None, None, f"Login failed: {error_details}"
            
    except Exception as e:
        return None, None, f"Connection error: {str(e)}"

def send_password_reset(email):
    """
    Trigger a password reset email via Firebase REST API.
    Returns: (success_bool, message)
    """
    if not FIREBASE_WEB_API_KEY:
        return False, "Missing API Key"
        
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={FIREBASE_WEB_API_KEY}"
    payload = {
        "requestType": "PASSWORD_RESET",
        "email": email
    }
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            return True, "Reset email sent. Check your inbox."
        else:
            err = r.json().get("error", {}).get("message", "Unknown error")
            return False, f"Failed: {err}"
    except Exception as e:
        return False, f"Error: {str(e)}"
