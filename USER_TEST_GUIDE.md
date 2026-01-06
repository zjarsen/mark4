# 🧪 User Test Guide - What to Test Yourself

## 🚨 CRITICAL TESTS (Must Do)

These features were **BROKEN** before the refactoring. Test them to confirm they work now.

---

### ✅ Test 1: Bot Startup

**What was broken**: Bot crashed immediately with `ImportError: cannot import name 'MENU_OPTION_IMAGE'`

**How to test**:
```bash
# Stop bot if running
# Start bot
python3 -m bot
```

**Expected**:
- ✅ Bot starts successfully
- ✅ Console shows "Bot started" or similar
- ❌ NO "ImportError" messages

---

### ✅ Test 2: Check Balance (Balance Button)

**What was broken**: Clicking balance button crashed with `cannot import name 'TRANSACTION_ITEM_TEMPLATE'`

**How to test**:
1. Open bot in Telegram
2. Send `/start`
3. Click **"💰 我的积分"** button (or "4. 📊 積分餘額")

**Expected**:
- ✅ Shows your credit balance
- ✅ Shows total spent
- ✅ Shows transaction history (if any)
- ✅ No crash

**What you'll see**:
```
💰 我的积分

当前余额：100 积分
累计消费：50 积分

📋 服务价格：
• 图片脱衣：10 积分
...
```

---

### ✅ Test 3: Image Processing Menu

**What was broken**: Clicking image processing crashed with `cannot import name 'IMAGE_STYLE_BRA_BUTTON'`

**How to test**:
1. Open bot
2. Send `/start`
3. Click **"1. 📸 圖片脫衣"** (Image Processing)

**Expected**:
- ✅ Shows style selection menu
- ✅ Shows 2 buttons:
  - "🎁 粉色蕾丝内衣"
  - "脱到精光"
- ✅ Shows "🏠 返回主菜单" button
- ✅ No crash

---

### ✅ Test 4: Video Processing Menu

**What was broken**: Clicking video processing crashed with `cannot import name 'VIDEO_STYLE_SELECTION_MESSAGE'`

**How to test**:
1. Open bot
2. Send `/start`
3. Click **"2. 🎬 圖片→視頻脫衣"** (Video Processing)

**Expected**:
- ✅ Shows style selection menu
- ✅ Shows 3 buttons:
  - "脱衣+抖胸（30积分）"
  - "脱衣+下体流精（30积分）"
  - "脱衣+ 吃吊喝精（30积分）"
- ✅ Shows "🏠 返回主菜单" button
- ✅ No crash

---

### ✅ Test 5: Image Style Selection

**What was broken**: After clicking a style, bot crashed with `cannot import name 'WORKFLOW_NAME_IMAGE_BRA'`

**How to test**:
1. Click "1. 📸 圖片脫衣"
2. Click **any style** (e.g., "🎁 粉色蕾丝内衣")

**Expected**:
- ✅ Bot shows: "已选择 [style name]"
- ✅ Bot asks you to send a photo
- ✅ Shows image requirements
- ✅ No crash

---

### ✅ Test 6: Video Style Selection

**What was broken**: After clicking video style, bot crashed with `cannot import name 'WORKFLOW_NAME_VIDEO_A'`

**How to test**:
1. Click "2. 🎬 圖片→視頻脫衣"
2. Click **any style** (e.g., "脱衣+抖胸")

**Expected**:
- ✅ Bot shows: "已选择 [style name]"
- ✅ Bot asks you to send an image
- ✅ Shows image requirements
- ✅ No crash

---

### ✅ Test 7: Send Photo for Processing

**What was broken**: Queue status messages crashed with `cannot import name 'PROCESSING_IN_PROGRESS'`

**How to test**:
1. Select any image style
2. Send **any photo** to the bot

**Expected**:
- ✅ Bot shows credit confirmation
- ✅ After confirm, shows queue position OR processing status
- ✅ Eventually sends you the processed image
- ✅ No crash at any step

---

### ✅ Test 8: Top-up Credits Menu

**What was broken**: Package buttons had wrong text

**How to test**:
1. Click "💰 我的积分"
2. Scroll down, you should see top-up buttons

**Expected**:
- ✅ Shows 4 packages:
  - ¥11 = 30积分
  - ¥32 = 120积分
  - ¥54 = 250积分
  - ¥108 = 600积分
- ✅ Each button is clickable
- ✅ No crash

---

### ✅ Test 9: Back Button in Payment

**What was broken**: Back button didn't work

**How to test**:
1. Click any top-up package
2. Click **"⬅️ 返回"** (Back button)

**Expected**:
- ✅ Takes you back to package selection
- ✅ Shows the 4 packages again
- ✅ Button actually works now

---

### ✅ Test 10: Check Queue

**What was broken**: Queue messages crashed with `cannot import name 'QUEUE_STATUS_TEMPLATE'`

**How to test**:
1. Send `/start`
2. Click **"5. 查看當前隊列"** (Check Queue)

**Expected**:
- ✅ Shows current queue status
- ✅ Shows total jobs in queue
- ✅ No crash

---

## 🎯 QUICK 5-MINUTE TEST

Just run through this checklist:

```
□ Start bot - no ImportError?
□ Click "💰 我的积分" - shows balance?
□ Click "1. 📸 圖片脫衣" - shows styles?
□ Click "2. 🎬 圖片→視頻脫衣" - shows styles?
□ Click a style - asks for photo?
□ Send a photo - processes it?
□ Click "5. 查看當前隊列" - shows queue?
```

If all ✅ = **Refactoring successful!**

---

## 🐛 What to Report If Something Breaks

If you find ANY error:

1. **Copy the error from console/logs**:
   ```bash
   tail -100 logs/mark4_bot.log
   ```

2. **Tell me**:
   - What you clicked
   - What happened
   - The error message (if any)

Example:
```
I clicked "1. 📸 圖片脫衣" and got error:
"ImportError: cannot import name 'SOME_CONSTANT'"
```

---

## ✅ EXPECTED RESULT

After all tests:
- **0 ImportErrors** anywhere
- **All menus work** properly
- **All buttons work** properly
- **Image/video processing works** end-to-end

---

## 📝 Notes

- The bot may show Chinese or Traditional Chinese depending on your language setting
- All functionality should work the same
- If payment gateways have issues, that's NOT related to refactoring (those are external services)

**Bottom line**: If the bot doesn't crash with ImportError, we're good! ✅
