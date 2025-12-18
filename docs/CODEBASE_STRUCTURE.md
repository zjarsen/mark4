# Codebase Structure - Current State

**Branch:** `restructure`
**Status:** Phase 4 Complete, Legacy Files Cleaned Up
**Last Updated:** December 2024

---

## 📊 Quick Stats

- **Total Python Files:** 74
- **New Architecture Code:** ~285KB
- **Legacy Code Remaining:** ~116KB (services/)
- **Empty Directories:** 6 (kept for future use)

---

## 🎯 Entry Points (Where Everything Starts)

### **telegram_bot.py** (1.5KB) - Main Bot Entry Point ✨ NEW
**What it does:** Starts the Telegram bot
**Uses:** `bot_application_v2.py` (new architecture)
**Status:** ✅ Fully migrated to new architecture
```bash
python telegram_bot.py
```

### **payment_webhook.py** (9.7KB) - Payment Webhook Server ✨ NEW
**What it does:** Separate Flask server that receives payment callbacks
**Uses:** New database + domain layers directly
**Status:** ✅ Fully migrated to new architecture
```bash
python payment_webhook.py
```

### **config.py** (5.0KB) - Configuration
**What it does:** Loads settings from `.env` file
**Contains:** API keys, database paths, server URLs
**Status:** ✅ Active (shared by all components)

---

## 📁 Core System (New Architecture)

### **core/** - Application Bootstrap & Dependency Injection

#### **core/bot_application_v2.py** (17.3KB) ✨ NEW
**What it does:** Main bot application using ServiceContainer
**Replaces:** Old `bot_application.py` (deleted)
**Key features:**
- Uses ServiceContainer for dependency injection
- Registers all Telegram handlers
- Manages bot lifecycle
- Backward compatible with legacy handlers

#### **core/service_container.py** (12.7KB) ✨ NEW
**What it does:** Initializes ALL services in correct order
**Think of it as:** Master control panel - wires everything together
**Initializes:**
1. Database layer (connection, repos)
2. Infrastructure (state, ComfyUI, notifications, files)
3. Domain services (credits, workflows)
4. Legacy compatibility (payment, queues)

#### **core/constants.py** (16.1KB)
**What it does:** All button labels, messages, and configuration constants
**Status:** ✅ Active (shared by all handlers)

**Status:** 🟢 **FULLY NEW ARCHITECTURE** - No legacy dependencies

---

## 💾 Database Layer (New Architecture)

### **database/** - Data Access with Transaction Safety

#### **database/connection.py** (5.7KB) ✨ NEW
**What it does:** Database connection pooling and transaction management
**Features:**
- Thread-safe connection pool
- Atomic transactions via context managers
- Automatic cleanup

#### **database/exceptions.py** (1.8KB) ✨ NEW
**What it does:** Specific database error types
**Replaces:** Generic `except Exception`
**Types:** `DatabaseError`, `IntegrityError`, `NotFoundError`, etc.

#### **database/models.py** (4.3KB) ✨ NEW
**What it does:** TypedDict definitions for data structures
**Models:** `User`, `Payment`, `Transaction`
**Benefit:** Type hints for IDE autocomplete

#### **database/repositories/** - Data Operations

All repositories use BaseRepository to eliminate boilerplate:

- **base.py** (4.8KB) ✨ NEW - Base repository with common CRUD operations
- **user_repo.py** (10.2KB) ✨ NEW - User operations (get, create, update credits)
- **payment_repo.py** (10.4KB) ✨ NEW - Payment records (create, get, update status)
- **transaction_repo.py** (7.6KB) ✨ NEW - Transaction history

#### **database/migrations/** - Database Updates

- **manager.py** (9.5KB) ✨ NEW - Migration tracking and execution

**Status:** 🟢 **FULLY NEW ARCHITECTURE** - Replaces old `database_service.py`

---

## 🎯 Domain Layer (Business Logic)

### **domain/credits/** - Credit System ✨ NEW

#### **domain/credits/service.py** (16.8KB)
**What it does:** Credit operations (add, deduct, check balance)
**Key features:**
- ⚠️ Atomic transactions (fixes race condition!)
- Free trial system (2-day reset)
- VIP status management
- Transaction history

#### **domain/credits/discount.py** (7.8KB)
**What it does:** Daily discount lucky draw system
**Tiers:**
- SSR (5%) - 50% off
- SR (15%) - 30% off
- R (30%) - 15% off
- C (50%) - 5% off

#### **domain/credits/exceptions.py** (1.0KB)
**What it does:** Credit-specific errors (InsufficientCredits, etc.)

**Replaces:** `services/credit_service.py` (deleted ✅)
**Replaces:** `services/discount_service.py` (deleted ✅)

---

### **domain/workflows/** - Processing Logic ✨ NEW

#### **domain/workflows/base.py** (5.3KB)
**What it does:** Base classes for all workflow processors
**Defines:** `WorkflowProcessor` interface, `WorkflowResult` type

#### **domain/workflows/image/** - Image Processing

- **service.py** (12.1KB) - Image workflow orchestration
- **processors.py** (10.9KB) - Image processors:
  - `ImageUndressProcessor` (10 credits)
  - `PinkBraProcessor` (free, 5/day for non-VIP)

#### **domain/workflows/video/** - Video Processing

- **service.py** (11.8KB) - Video workflow orchestration
- **processors.py** (15.3KB) - Video processors:
  - `VideoStyleAProcessor` (douxiong, 30 credits)
  - `VideoStyleBProcessor` (liujing, 30 credits)
  - `VideoStyleCProcessor` (shejing, 30 credits)

**Replaces:** `services/workflow_service.py` (still exists for compatibility)

**Status:** 🟢 **FULLY NEW ARCHITECTURE**

---

## 🔌 Infrastructure Layer (External Services)

### **infrastructure/state/** - State Management ✨ NEW

#### **infrastructure/state/manager.py** (6.5KB)
**What it does:** Abstract state manager interface

#### **infrastructure/state/redis_impl.py** (12.7KB)
**What it does:** Redis-based state (persistent, scalable)
**For:** Production use

#### **infrastructure/state/memory_impl.py** (9.1KB)
**What it does:** In-memory state (fast, no dependencies)
**For:** Development and testing

**Replaces:** `core/state_manager.py` (deleted ✅)

---

### **infrastructure/comfyui/** - ComfyUI Integration ✨ NEW

#### **infrastructure/comfyui/client.py** (18.6KB)
**What it does:** Async ComfyUI API client
**Features:**
- Connection pooling (10 connections)
- Session reuse
- Exponential backoff retry
- Timeout handling

#### **infrastructure/comfyui/exceptions.py** (5.7KB)
**What it does:** ComfyUI-specific error types (8 types)

**Will Replace:** `services/comfyui_service.py` (in Phase 5)

---

### **infrastructure/notifications/** - Telegram Messaging ✨ NEW

#### **infrastructure/notifications/service.py** (15.3KB)
**What it does:** Sends messages to users via Telegram
**Features:**
- Message sending with error handling
- Button keyboards
- Return values for success/failure

**Replaces:** `services/notification_service.py` (deleted ✅)

---

### **infrastructure/files/** - File Management ✨ NEW

#### **infrastructure/files/service.py** (16.3KB)
**What it does:** File upload/download from Telegram
**Features:**
- Async downloads with retry
- Exponential backoff
- Old file cleanup
- Storage statistics

**Replaces:** `services/file_service.py` (deleted ✅)

**Status:** 🟢 **FULLY NEW ARCHITECTURE**

---

## 🎭 Handler Layer (User Interactions)

### **handlers/** - Telegram Command & Button Handlers

#### **handlers/command_handlers.py** (6.8KB)
**What it does:** Bot commands (/start, /help, /cancel, /broadcast)
**Status:** 🟡 Uses new services via bot_application_v2.py

#### **handlers/menu_handlers.py** (13.8KB)
**What it does:** Main menu selections (process image, check queue, etc.)
**Status:** 🟡 Uses legacy queue_service

#### **handlers/media_handlers.py** (7.9KB)
**What it does:** Handles when users upload photos
**Status:** 🟡 Uses legacy workflow_service

#### **handlers/callback_handlers.py** (13.3KB)
**What it does:** Inline button clicks (workflow selection, confirmations)
**Status:** 🟡 Uses legacy queue_service

#### **handlers/credit_handlers.py** (26.2KB)
**What it does:** Credit top-up and payment flows
**Status:** 🟡 Uses new credit_service, legacy payment_service

**Status:** 🟡 **PARTIALLY MIGRATED** - Use new services via dependency injection, but still expect legacy interfaces

---

## ⚠️ Legacy Services (Still Needed for Compatibility)

### **services/** - Old Service Layer (Being Phased Out)

These services are **only kept for backward compatibility** with handlers that haven't been fully migrated yet:

#### 🔴 **LEGACY - Will be removed in Phase 5:**

- **workflow_service.py** (64.8KB) - Monolithic workflow handler
  - **Used by:** `bot_application_v2.py` for handler compatibility
  - **Replaced by:** `domain/workflows/` (image + video services)
  - **Size:** 64.8KB (largest legacy file!)

- **comfyui_service.py** (11.8KB) - Old ComfyUI client
  - **Used by:** `workflow_service.py`, `bot_application_v2.py`
  - **Replaced by:** `infrastructure/comfyui/client.py`

#### 🟢 **ACTIVE - Will keep:**

- **payment_service.py** (12.4KB) - Payment orchestration
  - **Status:** Active (used by webhook and handlers)
  - **Note:** Uses new repositories via wrapper

- **payment_timeout_service.py** (5.8KB) - Payment timeout tracking
  - **Status:** Active (handles 3-minute payment timeouts)

- **queue_service.py** (5.7KB) - Queue management
  - **Status:** Active (temporary queue coordination)

- **queue_manager_base.py** (12.1KB) - Queue infrastructure
  - **Status:** Active (base class for queue managers)

- **image_queue_manager.py** (875B) - Image processing queue
  - **Status:** Active (manages image job queue)

- **video_queue_manager.py** (903B) - Video processing queue
  - **Status:** Active (manages video job queue)

#### ✅ **REMOVED (No longer exist):**

- ~~database_service.py~~ (28KB) → `database/` layer
- ~~credit_service.py~~ (24KB) → `domain/credits/service.py`
- ~~discount_service.py~~ (7.7KB) → `domain/credits/discount.py`
- ~~file_service.py~~ (11KB) → `infrastructure/files/service.py`
- ~~notification_service.py~~ (10KB) → `infrastructure/notifications/service.py`

**Status:** 🔴 **LEGACY** - 116KB remaining (77KB can be removed in Phase 5)

---

## 💳 Payment System

### **payments/** - Payment Gateway Integration

#### **payments/base_payment.py** (4.2KB)
**What it does:** Abstract payment provider interface
**Status:** ✅ Active

#### **payments/wechat_alipay_provider.py** (16.7KB)
**What it does:** WeChat/Alipay payment implementation
**Features:**
- Payment order creation
- Signature generation/verification
- Callback handling
**Status:** ✅ Active

**Status:** 🟢 **ACTIVE** - No migration needed

---

## 📢 Broadcast System

### **broadcast/** - Admin Broadcast Portal

#### **broadcast/app.py** (3.9KB)
**What it does:** Web interface for sending messages to all users
**Features:**
- Send messages to all users
- Filter by VIP/non-VIP
- Message preview
**Status:** ✅ Active (separate Flask app)

---

## 🛠️ Utilities

### **utils/** - Helper Functions

- **logger.py** (1.5KB) - Logging configuration
- **decorators.py** (3.2KB) - Function decorators
- **validators.py** (2.2KB) - Input validation

**Status:** ✅ Active (shared utilities)

---

## 📂 Storage Directories

### **user_uploads/** - Temporary User Files
**What it stores:** Images users upload
**Lifetime:** Automatically cleaned up after processing
**Think of it as:** Inbox for incoming files

### **comfyui_retrieve/** - Processed Results
**What it stores:** Processed images/videos from ComfyUI
**Lifetime:** Cleaned up after 5 minutes
**Think of it as:** Outbox for finished files

### **data/** - Database & Static Files
**Contains:**
- `mark4_bot.db` - SQLite database with all user data
- `static/` - Web assets for broadcast portal
- `templates/` - HTML templates for broadcast portal

### **workflows/** - ComfyUI Workflow JSON Files
**Contains:**
- `i2i_undress_final_v5.json` - Image undress workflow
- `i2i_bra_v5.json` - Pink bra workflow
- `i2v_undress_douxiong.json` - Video style A
- `i2v_undress_liujing.json` - Video style B
- `i2v_undress_shejing.json` - Video style C

### **logs/** - Application Logs
**Contains:** Bot activity logs for debugging

---

## 📚 Documentation

### **docs/** - Project Documentation

- **CODEBASE_STRUCTURE.md** - This file! Complete structure overview
- **FOLDER_GUIDE.md** - Simple explanations with analogies
- **MIGRATION_GUIDE.md** - How to switch to new architecture
- **RESTRUCTURE_SUMMARY.md** - Complete restructuring overview
- **EMPTY_DIRECTORIES_ANALYSIS.md** - Analysis of empty folders

---

## 🧪 Testing & Scripts

### **tests/** - Test Suite (Empty - For Future)
**Structure:**
- `tests/integration/` - End-to-end tests
- `tests/unit/database/` - Database tests

**Status:** 📝 Planned but not implemented

### **scripts/** - Admin Scripts (Empty - For Future)
**Purpose:** Maintenance scripts (backups, user management, cleanup)

**Status:** 📝 Planned but not implemented

### **test_imports.py** (3.6KB)
**What it does:** Verifies all imports work without starting the bot
**Usage:** `python3 test_imports.py`

---

## 🔮 Optional/Empty Directories

### **api/** - REST API (Empty)
**Purpose:** Would provide REST API for external integrations
**Status:** 📝 Optional feature, not currently needed

**Subdirectories (all empty):**
- `api/handlers/` - Request handlers
- `api/middleware/` - Auth, CORS, rate limiting
- `api/responses/` - Response formatters

---

## 📊 Architecture Flow

### **How a User Request Flows Through the System:**

```
1. User sends photo
   ↓
2. handlers/media_handlers.py receives it
   ↓
3. infrastructure/files/service.py downloads it
   ↓
4. domain/credits/service.py checks balance
   ↓
5. infrastructure/comfyui/client.py sends to ComfyUI
   ↓
6. domain/workflows/image/service.py orchestrates processing
   ↓
7. domain/credits/service.py deducts credits (atomic!)
   ↓
8. infrastructure/notifications/service.py sends result
   ↓
9. infrastructure/files/service.py cleans up
```

**All data operations go through:** `database/repositories/`
**All state tracking goes through:** `infrastructure/state/`

---

## 🎨 Architecture Layers (Clean Separation)

```
┌─────────────────────────────────────────────┐
│  Entry Points (telegram_bot.py, webhook)   │
├─────────────────────────────────────────────┤
│  Handlers (command, menu, media, callback)  │ ← 🟡 Uses legacy via DI
├─────────────────────────────────────────────┤
│  Core (bot_application_v2, container)       │ ← ✨ NEW
├─────────────────────────────────────────────┤
│  Domain (credits, workflows)                │ ← ✨ NEW
├─────────────────────────────────────────────┤
│  Infrastructure (state, comfyui, files)     │ ← ✨ NEW
├─────────────────────────────────────────────┤
│  Database (connection, repositories)        │ ← ✨ NEW
├─────────────────────────────────────────────┤
│  Services (legacy compatibility layer)      │ ← 🔴 LEGACY (116KB)
└─────────────────────────────────────────────┘
```

---

## 📈 Migration Progress

### ✅ **Phase 4 Complete (80% Done)**

**Migrated (New Architecture):**
- ✅ Database layer (connection, repositories, migrations)
- ✅ Domain layer (credits, workflows with processors)
- ✅ Infrastructure layer (state, ComfyUI, notifications, files)
- ✅ Core layer (ServiceContainer, BotApplication_v2)
- ✅ Entry points (telegram_bot.py uses v2, payment_webhook.py migrated)

**Removed (Deleted Legacy Code):**
- ✅ `core/bot_application.py` (20KB)
- ✅ `core/state_manager.py` (8.5KB)
- ✅ `services/database_service.py` (28KB)
- ✅ `services/credit_service.py` (24KB)
- ✅ `services/discount_service.py` (7.7KB)
- ✅ `services/file_service.py` (11KB)
- ✅ `services/notification_service.py` (10KB)
- **Total removed:** 7 files, ~110KB

### ⏳ **Phase 5 Pending (20% Remaining)**

**To Migrate:**
- [ ] Handlers to use new services directly (not via legacy wrappers)
- [ ] Remove `services/workflow_service.py` (64.8KB)
- [ ] Remove `services/comfyui_service.py` (11.8KB)

**To Keep:**
- ✅ `services/payment_service.py` (active)
- ✅ `services/payment_timeout_service.py` (active)
- ✅ `services/queue_*.py` (active)

---

## 🎯 Key Takeaways

### **Most Important Files:**

1. **telegram_bot.py** - Entry point (starts bot)
2. **core/service_container.py** - Wires everything together
3. **core/bot_application_v2.py** - Main bot application
4. **database/repositories/** - All data operations
5. **domain/credits/service.py** - Credit system
6. **domain/workflows/** - Processing logic
7. **infrastructure/** - External service integrations
8. **handlers/** - User interaction handling

### **Legacy Code Still in Use:**

**services/** directory (116KB total):
- 🔴 77KB can be removed in Phase 5 (workflow_service.py, comfyui_service.py)
- 🟢 39KB stays (payment, queue management)

### **Architecture Status:**

- 🟢 **NEW:** 285KB of clean, maintainable code
- 🔴 **LEGACY:** 116KB remaining (67% can be removed)
- ✅ **DELETED:** 110KB of duplicated legacy code

---

## 🚀 Quick Reference

### **Start the bot:**
```bash
python telegram_bot.py
```

### **Start payment webhook:**
```bash
python payment_webhook.py
```

### **Start broadcast portal:**
```bash
cd broadcast && python app.py
```

### **Test imports:**
```bash
python3 test_imports.py
```

### **Check structure:**
```bash
tree -L 2 -I 'venv|__pycache__|*.pyc|.git'
```

---

**Last Updated:** December 2024
**Current Branch:** `restructure`
**Next Step:** Phase 5 - Handler migration and final legacy cleanup
