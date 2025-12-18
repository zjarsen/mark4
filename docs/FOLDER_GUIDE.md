# Folder Guide - Simple Explanations

This guide explains what each folder does in simple terms.

---

## 📁 Core Folders (Your Bot's Brain)

### `core/` - Bot Startup & Configuration
**What it does:** Starts your bot and wires everything together
**Contains:**
- `bot_application_v2.py` - Main bot starter (NEW, uses ServiceContainer)
- `bot_application.py` - Old bot starter (backup)
- `service_container.py` - Connects all services together
- `state_manager.py` - Old state tracker (being replaced)
- `constants.py` - All text messages and button labels

**Think of it as:** The ignition system of a car - starts everything and makes sure all parts work together

---

### `config.py` + `.env` - Settings
**What it does:** Stores all your bot's settings (API keys, server URLs, etc.)
**Contains:**
- Bot token
- ComfyUI server addresses
- Payment gateway settings
- File paths

**Think of it as:** Your bot's settings menu - all the configuration in one place

---

## 📊 Database Layer (Where Data Lives)

### `database/` - All Database Operations
**What it does:** Saves and retrieves data (users, credits, transactions)
**Contains:**
- `connection.py` - Connects to database
- `repositories/` - Functions to read/write data
  - `user_repo.py` - User operations (get user, update credits, etc.)
  - `transaction_repo.py` - Transaction history
  - `payment_repo.py` - Payment records
- `migrations/` - Database updates/changes
- `models.py` - Data structure definitions
- `exceptions.py` - Database error types

**Think of it as:** A filing cabinet - organized storage for all your data

---

### `data/` - Actual Database Files
**What it does:** Contains the actual SQLite database file
**Contains:**
- `mark4_bot.db` - Your actual database with all user data

**Think of it as:** The physical filing cabinet where papers are stored

---

## 🎯 Domain Layer (Business Logic)

### `domain/` - Core Business Rules
**What it does:** Contains all your business logic (credits, workflows, etc.)

#### `domain/credits/` - Credit System
**What it does:** Handles user credits (adding, removing, checking balance)
**Contains:**
- `service.py` - Credit operations (deduct credits, add credits, etc.)
- `discount.py` - Daily discount system (random draw for discounts)
- `exceptions.py` - Credit-related errors

**Think of it as:** Your bot's wallet system - manages virtual currency

#### `domain/workflows/` - Processing Workflows
**What it does:** Handles image/video processing logic

**`domain/workflows/image/`** - Image Processing
- `service.py` - Image workflow orchestration
- `processors.py` - Image processing implementations
  - Undress processor (10 credits)
  - Pink bra processor (free, 5/day)

**`domain/workflows/video/`** - Video Processing
- `service.py` - Video workflow orchestration
- `processors.py` - Video processing implementations
  - Style A (douxiong) - 30 credits
  - Style B (liujing) - 30 credits
  - Style C (shejing) - 30 credits

**Think of it as:** Your bot's kitchen - recipes (workflows) for making different dishes (processed images/videos)

---

## 🔌 Infrastructure Layer (External Services)

### `infrastructure/` - External Integrations
**What it does:** Talks to external services (Redis, ComfyUI, Telegram, files)

#### `infrastructure/state/` - State Management
**What it does:** Remembers what users are doing
**Contains:**
- `manager.py` - Base state interface
- `redis_impl.py` - Redis state (persistent, survives restarts)
- `memory_impl.py` - In-memory state (for testing, lost on restart)

**Think of it as:** Short-term memory - remembers what you're currently doing

#### `infrastructure/comfyui/` - ComfyUI Integration
**What it does:** Sends images to ComfyUI for processing
**Contains:**
- `client.py` - Communicates with ComfyUI servers
- `exceptions.py` - ComfyUI error types

**Think of it as:** The delivery service - sends work to ComfyUI and gets results back

#### `infrastructure/notifications/` - Telegram Messages
**What it does:** Sends messages to users via Telegram
**Contains:**
- `service.py` - Message sending functions

**Think of it as:** Your bot's voice - how it talks to users

#### `infrastructure/files/` - File Management
**What it does:** Downloads from Telegram, saves files, deletes old files
**Contains:**
- `service.py` - File upload/download operations

**Think of it as:** File manager - handles all file operations

---

## 🎭 Handler Layer (User Interactions)

### `handlers/` - Responds to User Actions
**What it does:** Handles what happens when users click buttons or send messages
**Contains:**
- `command_handlers.py` - Commands like /start, /help, /cancel
- `menu_handlers.py` - Main menu selections
- `media_handlers.py` - When users upload photos
- `callback_handlers.py` - When users click inline buttons
- `credit_handlers.py` - Credit top-up and payment flows

**Think of it as:** Customer service reps - each one handles different types of requests

---

## 💳 Payment System

### `payments/` - Payment Processing
**What it does:** Handles payment gateway integration
**Contains:**
- `wechat_alipay_provider.py` - WeChat/Alipay payment integration

**Think of it as:** Cashier - processes payments

### `payment_webhook.py` - Payment Callbacks
**What it does:** Receives notifications when payments complete
**Contains:** Webhook server for payment confirmations

**Think of it as:** Receipt scanner - confirms payments went through

---

## 🛠️ Services Layer (Legacy)

### `services/` - Old Services (Being Phased Out)
**What it does:** Old service implementations (some still in use)
**Contains:**
- `payment_service.py` - Payment orchestration
- `payment_timeout_service.py` - Payment timeout tracking
- `queue_service.py` - Queue management (temporary)
- `image_queue_manager.py` - Image processing queue
- `video_queue_manager.py` - Video processing queue
- Old services being replaced:
  - `database_service.py` → replaced by `database/` layer
  - `credit_service.py` → replaced by `domain/credits/`
  - `workflow_service.py` → replaced by `domain/workflows/`

**Think of it as:** Old tools that still work but being replaced with better ones

---

## 📝 Utility & Support

### `utils/` - Helper Functions
**What it does:** Common utilities used everywhere
**Contains:**
- `logger.py` - Logging setup

**Think of it as:** Toolbox - small helpful tools

### `workflows/` - ComfyUI Workflow JSON Files
**What it does:** Contains workflow configuration files for ComfyUI
**Contains:**
- `i2i_undress_final_v5.json` - Image undress workflow
- `i2i_bra_v5.json` - Pink bra workflow
- `i2v_undress_douxiong.json` - Video style A
- `i2v_undress_liujing.json` - Video style B
- `i2v_undress_shejing.json` - Video style C

**Think of it as:** Recipe cards for ComfyUI - instructions on how to process images/videos

---

## 📂 Storage Folders

### `user_uploads/` - User Uploaded Files
**What it does:** Temporarily stores images users upload
**Contains:** User photos (automatically cleaned up)

**Think of it as:** Inbox - temporary storage for incoming files

### `comfyui_retrieve/` - Processed Results
**What it does:** Stores processed images/videos from ComfyUI
**Contains:** Output files (automatically cleaned up after 5 minutes)

**Think of it as:** Outbox - temporary storage for finished files

---

## 📚 Documentation & Tools

### `docs/` - Documentation
**What it does:** All project documentation
**Contains:**
- `MIGRATION_GUIDE.md` - How to switch to new architecture
- `RESTRUCTURE_SUMMARY.md` - Complete project overview
- `EMPTY_DIRECTORIES_ANALYSIS.md` - Empty folder analysis
- `FOLDER_GUIDE.md` - This file!

**Think of it as:** Instruction manuals

### `logs/` - Log Files
**What it does:** Stores bot activity logs
**Contains:** Log files for debugging

**Think of it as:** Activity journal - records everything that happens

### `broadcast/` - Broadcast System
**What it does:** Sends messages to multiple users
**Contains:** Broadcast functionality for announcements

**Think of it as:** Announcement system - send messages to many users at once

---

## 🧪 Testing & Scripts (Empty, For Future)

### `tests/` - Tests (Not Implemented Yet)
**What it does:** Will contain automated tests
**Folders:**
- `integration/` - End-to-end tests
- `unit/database/` - Database tests

**Think of it as:** Quality control - checks everything works correctly

### `scripts/` - Admin Scripts (Empty)
**What it does:** Will contain maintenance scripts
**Future use:** Database backups, user management, cleanup

**Think of it as:** Admin tools - one-off maintenance tasks

---

## 🔮 Optional Features (Empty)

### `api/` - REST API (Not Implemented)
**What it does:** Would provide REST API for external integrations
**Status:** Optional feature, not needed for current bot

**Think of it as:** Side door - alternative way to access bot features (not currently used)

---

## 🗑️ Generated/Temporary

### `venv/` - Python Virtual Environment
**What it does:** Contains Python packages and dependencies
**Don't touch!** - Managed by pip

### `__pycache__/` - Python Cache
**What it does:** Python's temporary compiled files
**Don't touch!** - Automatically managed

### `.git/` - Git Repository
**What it does:** Version control history
**Don't touch!** - Managed by git

---

## 📋 Quick Reference

**Core Bot Functionality:**
```
telegram_bot.py          → Start here (main entry point)
├── core/                → Bot startup & wiring
├── handlers/            → User interactions
├── domain/              → Business logic (credits, workflows)
├── infrastructure/      → External services (ComfyUI, Telegram, files)
└── database/            → Data storage
```

**Data & Configuration:**
```
config.py + .env         → Settings
data/mark4_bot.db        → Database
workflows/               → ComfyUI recipes
```

**Supporting:**
```
payments/                → Payment processing
services/                → Legacy services (being phased out)
utils/                   → Helper functions
logs/                    → Activity logs
broadcast/               → Announcements
```

**Storage:**
```
user_uploads/            → User photos (temporary)
comfyui_retrieve/        → Processed files (temporary)
```

**Future/Optional:**
```
tests/                   → For tests (add later)
scripts/                 → For admin tools (add later)
api/                     → For REST API (optional)
docs/                    → Documentation
```

---

## 🎯 Main Flow (How It All Works Together)

1. **User sends photo** → `handlers/media_handlers.py`
2. **Download photo** → `infrastructure/files/service.py`
3. **Check credits** → `domain/credits/service.py`
4. **Send to ComfyUI** → `infrastructure/comfyui/client.py`
5. **Wait for result** → `domain/workflows/image/service.py`
6. **Deduct credits** → `domain/credits/service.py`
7. **Send result** → `infrastructure/notifications/service.py`
8. **Clean up** → `infrastructure/files/service.py`

All data operations go through → `database/repositories/`
All state tracking goes through → `infrastructure/state/`

---

## 💡 Key Takeaways

**Most Important Folders:**
1. `core/` - Starts everything
2. `handlers/` - Responds to users
3. `domain/` - Business rules
4. `infrastructure/` - External services
5. `database/` - Data storage

**Configuration:**
- `config.py` + `.env` - All settings

**Data:**
- `data/mark4_bot.db` - Your database

**Everything Else:**
- Supporting files, documentation, or future features

---

*This guide is meant to help you understand the project structure at a glance!*
