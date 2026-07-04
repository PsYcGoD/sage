# SAGE GUI Session Fix - STATUS

## ✅ COMPLETED (2026-07-04)

### 1. Session Storage Layer
- **File:** `src/sage/gui/session_manager.py` (NEW)
- **Status:** ✅ DONE & TESTED
- Multi-session architecture with UUID-based session IDs
- Sessions stored in `~/.sage/sessions.json`
- Test script confirms it works: 2 sessions created, messages saved

### 2. Sidebar UI Updates
- **File:** `src/sage/gui/widgets/floating_sidebar.py`
- **Status:** ✅ DONE
- Added "🕐 Scheduled" and "🔌 Plugins" menu items
- Updated `_create_chat_item` to support both old and new session formats
- Badge shows session count instead of run count

### 3. New Chat Behavior Fix
- **File:** `src/sage/gui/app.py` → `new_chat_with_folder_picker()`
- **Status:** ✅ DONE
- Now CREATES new session instead of clearing conversation
- Line 4052: Removed destructive `self.conversation_turns = []` persistence

### 4. SessionManager Integration
- **File:** `src/sage/gui/app.py` → `__init__()`
- **Status:** ✅ DONE
- Added `self.session_manager = SessionManager()`
- Added `self.current_session_id = None`

## 🚧 INCOMPLETE - BLOCKING GUI FROM WORKING

### 5. Load Sidebar from Sessions ⚠️ CRITICAL
- **File:** `src/sage/gui/app.py` → `_fetch_sidebar_data()`
- **Status:** ❌ HALF-DONE (still queries database)
- **Problem:** Line 3337-3484 still queries `runs` table from DB
- **Need:** Replace with `self.session_manager.get_all_projects()`
- **Impact:** Sidebar shows NOTHING because no database runs exist

### 6. Save Messages to Sessions ⚠️ CRITICAL
- **File:** `src/sage/gui/app.py` → `_remember_conversation_turn()`
- **Status:** ❌ NOT STARTED
- **Problem:** Line 2388 still saves to old `conversations.json`
- **Need:** Call `self.session_manager.add_message(project, session_id, role, text)`
- **Impact:** Messages not persisted to new session system

### 7. Session Switching ⚠️ CRITICAL
- **File:** `src/sage/gui/app.py` → `load_chat()`
- **Status:** ❌ NOT STARTED
- **Problem:** Clicking a session in sidebar does nothing
- **Need:** Load session messages, update `current_session_id`, restore to output
- **Impact:** Can't switch between sessions

### 8. Auto-create Session on Start
- **File:** `src/sage/gui/app.py` → `__init__()`  
- **Status:** ❌ NOT STARTED
- **Problem:** App starts with `current_session_id = None`
- **Need:** Call `session_manager.get_or_create_session(project)` after init
- **Impact:** First prompt fails because no session exists

## 🔧 EXACT FIXES NEEDED

### Fix #1: _fetch_sidebar_data() - Line 3331
```python
def _fetch_sidebar_data(self):
    """Fetch sidebar data from SessionManager"""
    try:
        projects = self.session_manager.get_all_projects()
        
        groups = []
        for project in projects:
            sessions = project.get("sessions", [])
            chats = []
            for session in sessions:
                chats.append({
                    "id": session.get("id"),
                    "title": session.get("title", "New Chat"),
                    "display_title": session.get("title", "New Chat"),
                    "relative_time": self._format_relative_time(session.get("updated_at", "")),
                    "pinned": session.get("pinned", False),
                    "unread": session.get("unread", False),
                })

            groups.append({
                "path": project.get("path"),
                "name": project.get("name"),
                "session_count": project.get("session_count", 0),
                "run_count": project.get("session_count", 0),  # Compat
                "sessions": chats,
                "chats": chats,  # Compat
            })

        current_dir = os.getcwd()
        if not any(g["path"] == current_dir for g in groups):
            groups.insert(0, {
                "path": current_dir,
                "name": os.path.basename(current_dir) or current_dir,
                "session_count": 0,
                "run_count": 0,
                "sessions": [],
                "chats": [],
            })

        groups.sort(key=lambda g: (g["path"] != current_dir, g.get("session_count", 0) == 0))
        self.after(0, lambda g=groups: self.sidebar.load_project_groups(g))

    except Exception as e:
        print(f"Sidebar Error: {e}")
```

### Fix #2: _remember_conversation_turn() - Line 2379
```python
def _remember_conversation_turn(self, role: str, text: str):
    """Keep recent chat context AND save to session."""
    text = (text or "").strip()
    if not text:
        return
    text = self._strip_low_value_output(text)
    if len(text) > 3500:
        text = text[:1700] + "\n[...]\n" + text[-1700:]
    
    # Old in-memory storage (keep for now)
    self.conversation_turns.append({"role": role, "text": text})
    self.conversation_turns = self.conversation_turns[-16:]
    
    # NEW: Save to SessionManager
    if self.current_session_id:
        self.session_manager.add_message(
            os.getcwd(),
            self.current_session_id,
            role,
            text
        )
```

### Fix #3: load_chat() - Add this method
```python
def load_chat(self, session_id: str):
    """Switch to a different session."""
    messages = self.session_manager.get_messages(os.getcwd(), session_id)
    self.current_session_id = session_id
    
    # Clear output and show session messages
    self.output_view.clear()
    for msg in messages:
        role = msg.get("role", "")
        text = msg.get("text", "")
        if role == "user":
            self.output_view.append_text(f"> {text}\n\n", "info")
        else:
            self.output_view.append_text(f"{text}\n\n", "assistant")
    
    # Mark as read
    self.session_manager.mark_unread(os.getcwd(), session_id, False)
    self.load_sidebar_data()
```

### Fix #4: Auto-create session - Line 262
```python
# After: self.after(700, lambda: self._load_saved_conversation(announce=True))
# Add:
self.current_session_id = self.session_manager.get_or_create_session(os.getcwd())
```

## 📊 TEST VERIFICATION

```bash
# 1. Test SessionManager works
python test_session_manager.py  # ✅ PASSED

# 2. Check sessions file
cat ~/.sage/sessions.json  # Shows 2 sessions created

# 3. Run GUI (will fail until fixes applied)
sage gui
```

## 🎯 NEXT STEPS

1. Apply Fix #1 to `_fetch_sidebar_data()`
2. Apply Fix #2 to `_remember_conversation_turn()`
3. Apply Fix #3 - add `load_chat()` method
4. Apply Fix #4 - auto-create session on start
5. Test: Create new chat → should appear in sidebar
6. Test: Switch between chats → should load messages
7. Test: Restart GUI → sessions should persist

## 🐛 KNOWN ISSUE

**Root cause of "chats disappearing":**
- Old code: Line 4052-4053 cleared `conversation_turns` AND persisted empty array
- This DESTROYED the only copy of chat history
- New system: Each "New Chat" creates a NEW session (keeps old ones)

Your screenshot shows the CORRECT behavior - multiple persistent sessions per project!
