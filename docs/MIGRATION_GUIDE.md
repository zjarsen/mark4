# Migration Guide: Old Architecture → New Architecture

This guide explains how to complete the migration from the old bot architecture to the new ServiceContainer-based architecture.

## Current Status

**Branch:** `restructure`
**Progress:** Phase 4 Part 2 (Integration) - In Progress

### What's Complete ✅

1. **Phase 1: Database Foundation** - All database layer refactored
2. **Phase 2: Domain Services** - Credit, Discount, Workflow services
3. **Phase 3: Infrastructure Layer** - State, ComfyUI, Notifications, Files
4. **Phase 4 Part 1: ServiceContainer** - Centralized dependency injection
5. **Phase 4 Part 2: BotApplication_v2** - New bot application created

### What's Pending ⏳

1. **Switch to bot_application_v2** - Update telegram_bot.py to use new version
2. **Test bot startup** - Verify initialization works
3. **Fix integration issues** - Address any runtime errors
4. **Migrate remaining handlers** - Update handlers to use new services directly
5. **Remove legacy services** - Clean up old service files

---

## Architecture Overview

### Old Architecture (Current)
```
telegram_bot.py
  └── BotApplication (core/bot_application.py)
       ├── Hardcoded service initialization
       ├── StateManager (in-memory only)
       ├── Old DatabaseService
       ├── Old CreditService
       └── Monolithic WorkflowService (1,580 lines)
```

### New Architecture (Target)
```
telegram_bot.py
  └── BotApplication (core/bot_application_v2.py)
       └── ServiceContainer (core/service_container.py)
            ├── Database Layer
            │   ├── DatabaseConnection (pool)
            │   └── Repositories (User, Transaction, Payment)
            ├── Infrastructure
            │   ├── StateManager (Redis/InMemory)
            │   ├── ComfyUIClient (pooled connections)
            │   ├── NotificationService
            │   └── FileService
            └── Domain Services
                ├── CreditService (atomic transactions)
                ├── DiscountService (random draw)
                ├── ImageWorkflowService
                └── VideoWorkflowService
```

---

## Step 1: Switch to BotApplication_v2

**File:** `telegram_bot.py`

**Current:**
```python
from core.bot_application import BotApplication
```

**New:**
```python
from core.bot_application_v2 import BotApplication
```

That's it! The interface is the same, so no other changes needed.

---

## Step 2: Test Bot Startup

```bash
cd /home/zj-ars/test_server/mark4
source venv/bin/activate
python telegram_bot.py
```

**Expected Output:**
```
==================================================
ServiceContainer Initialization Starting
==================================================
Initializing database layer...
✓ Database connection: data/mark4_bot.db
✓ Repositories: User, Transaction, Payment
✓ No pending migrations
Initializing infrastructure layer...
✓ State: RedisStateManager (redis://localhost:6379)
✓ ComfyUI clients: 4 servers
✓ Notifications: Telegram message service
✓ Files: Upload/download service
Initializing domain layer...
✓ Credits: CreditService with transaction safety
✓ Discounts: Random daily draw system
✓ Workflows: Deferred until queue managers ready
Initializing legacy services...
✓ Bot: Telegram Bot instance
✓ Payment provider: WeChatAlipay
✓ Payment service: Payment orchestration
✓ Payment timeout: Timeout tracking
✓ Queue managers: Image + 3 video styles
✓ Image workflow: Undress + Pink Bra
✓ Video workflow: 3 styles (A, B, C)
==================================================
ServiceContainer Initialization Complete
==================================================
Bot application initialized successfully
All handlers registered
```

---

## Step 3: Fix Common Issues

### Issue 1: Redis Connection Error

**Error:**
```
ConnectionError: Failed to connect to Redis
```

**Solution:**
1. Install Redis: `sudo apt install redis-server`
2. Start Redis: `sudo systemctl start redis`
3. Or use in-memory state: `BotApplication(config, use_redis=False)`

**Update bot_application_v2.py:**
```python
# For development without Redis:
self.container = ServiceContainer(config, use_redis=False)
```

### Issue 2: Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'redis'
```

**Solution:**
```bash
pip install redis[asyncio]
```

### Issue 3: State Manager Method Differences

**Error:**
```
AttributeError: 'RedisStateManager' object has no attribute 'get_state'
```

**Problem:** StateManager methods are now async!

**Old (Synchronous):**
```python
state = state_manager.get_state(user_id)
```

**New (Async):**
```python
state = await state_manager.get_state(user_id)
```

**Fix:** Add `await` to all state_manager calls in handlers.

---

## Step 4: Migrate Handlers (Gradually)

Handlers currently use legacy services. Migrate them gradually:

### Example: command_handlers.py

**Before:**
```python
# Uses old CreditService
balance = credit_service.get_balance(user_id)
```

**After:**
```python
# Uses new CreditService (same interface!)
balance = await credit_service.get_balance(user_id)
```

**Note:** Most methods are now async, so add `await`.

### Handler Migration Checklist

- [ ] **command_handlers.py** - Uses: state_manager, credit_service
- [ ] **menu_handlers.py** - Uses: state_manager, notification_service, queue_service
- [ ] **media_handlers.py** - Uses: state_manager, file_service, workflow_service
- [ ] **callback_handlers.py** - Uses: state_manager, queue_service
- [ ] **credit_handlers.py** - Uses: credit_service, payment_service, discount_service

---

## Step 5: Remove Legacy Services

Once all handlers are migrated, remove old service files:

```bash
# Backup first!
mkdir old_services_backup
mv services/database_service.py old_services_backup/
mv services/credit_service.py old_services_backup/
mv services/discount_service.py old_services_backup/
mv services/file_service.py old_services_backup/
mv services/notification_service.py old_services_backup/
mv services/comfyui_service.py old_services_backup/
mv services/workflow_service.py old_services_backup/
```

**Keep these (still needed):**
- `services/payment_service.py` - Payment orchestration
- `services/payment_timeout_service.py` - Timeout tracking
- `services/queue_service.py` - Queue management (temporary)
- `services/image_queue_manager.py` - Image queue
- `services/video_queue_manager.py` - Video queue

---

## Step 6: Environment Configuration

### Required Environment Variables

**Existing (keep these):**
```env
BOT_TOKEN=your_token_here
DATABASE_PATH=data/mark4_bot.db
COMFYUI_IMAGE_UNDRESS_SERVER=http://...
COMFYUI_VIDEO_DOUXIONG_SERVER=http://...
COMFYUI_VIDEO_LIUJING_SERVER=http://...
COMFYUI_VIDEO_SHEJING_SERVER=http://...
```

**New (add these):**
```env
# Redis configuration (optional, defaults to localhost)
REDIS_URL=redis://localhost:6379
```

---

## Testing Strategy

### 1. Unit Tests (Todo)
Create tests for new services:
- `test_credit_service.py` - Test atomic transactions
- `test_discount_service.py` - Test random draw
- `test_workflow_services.py` - Test workflow orchestration

### 2. Integration Tests
Test bot functionality end-to-end:
1. Start bot
2. Send `/start` command
3. Upload image
4. Check queue status
5. Complete workflow
6. Verify credits deducted

### 3. Production Rollout
1. Test on staging environment first
2. Monitor Redis connection
3. Check logs for errors
4. Verify state persistence across restarts

---

## Rollback Plan

If issues occur after deployment:

```bash
# Revert to old architecture
git checkout main

# Or cherry-pick specific fixes
git cherry-pick <commit-hash>
```

**Files to restore:**
- `core/bot_application.py` (old version)
- `telegram_bot.py` (import old BotApplication)

---

## Benefits of New Architecture

### Performance
- ✅ Connection pooling (database + ComfyUI)
- ✅ Async/await throughout
- ✅ Redis session reuse

### Reliability
- ✅ Atomic credit transactions (no race conditions)
- ✅ State persists across restarts
- ✅ Better error handling (specific exceptions)

### Maintainability
- ✅ Clear dependency injection
- ✅ Smaller, focused services
- ✅ Easier to test (swap implementations)

### Scalability
- ✅ Horizontal scaling (Redis state)
- ✅ Multiple bot instances supported
- ✅ Better resource management

---

## Next Steps

1. **Immediate:** Switch to `bot_application_v2` and test
2. **Short-term:** Migrate handlers to use new services
3. **Long-term:** Remove all legacy services
4. **Future:** Add comprehensive test suite

---

## Questions?

Check existing documentation:
- `docs/ARCHITECTURE.md` - System design
- `database/README.md` - Database layer docs
- `domain/README.md` - Domain services docs
- `infrastructure/README.md` - Infrastructure docs

Or review commit history:
```bash
git log --oneline restructure
```
