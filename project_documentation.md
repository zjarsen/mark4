# Telegram Bot with ComfyUI Integration - Project Documentation

## Project Overview

This project is a **Telegram bot** that integrates with a **ComfyUI server** for AI-powered image processing. The bot accepts image uploads from users, queues them on a remote ComfyUI server for processing, monitors the processing progress, and returns the completed images to users.

**Primary Use Case**: Image processing workflow automation via Telegram interface.

---

## System Architecture

### High-Level Flow
```
User (Telegram) → Bot → ComfyUI Server → Processing → Bot → User (Telegram)
```

1. User interacts with bot through Telegram
2. Bot receives image and uploads to ComfyUI server
3. Bot queues the image processing task on ComfyUI
4. Bot monitors queue and processing status
5. Bot retrieves completed image and sends back to user
6. Bot automatically cleans up files after 5 minutes

---

## Core Components

### 1. Configuration (`telegram_bot.py` lines 10-27)

**Bot Token**:
- `BOT_TOKEN`: Telegram Bot API token for authentication
- Current token: `8119215433:AAGWetPqiUcwFPe7rbIa7DIa5LsRbM0HuQQ`

**ComfyUI Server**:
- `COMFYUI_SERVER`: Remote server URL (`http://20.196.153.126:8188`)
- `COMFYUI_UPLOAD_URL`: Endpoint for uploading images

**Storage Directories**:
- `USER_UPLOADS_DIR`: `~/mark4/user_uploads` - Stores original user-uploaded images
- `COMFYUI_RETRIEVE_DIR`: `~/mark4/comfyui_retrieve` - Stores processed images from ComfyUI

**State Management**:
- `user_states`: Tracks each user's current workflow state (waiting for image, processing, etc.)
- `user_queue_messages`: Stores message objects for queue position updates
- `cleanup_tasks`: Tracks async cleanup tasks for each user

---

## User Interaction Flow

### Menu System (`start()` and `handle_menu_selection()`)

**Menu Options**:
1. **"1. 图片脱衣"** - Image processing (implemented)
2. **"2. 图片转视频脱衣"** - Image-to-video processing (not yet implemented)
3. **"3. 查看队列"** - Check current queue status

**First-Time User Experience**:
- When a user first connects (`/start` command), they receive a "hello" message
- User state is initialized with `{'first_contact': True}`
- Menu keyboard is displayed with three options

**Menu Selection Handlers**:
- **Option 1**: Sets user state to `'waiting_for_image'` and prompts for image upload
- **Option 2**: Returns "此功能仍在开发中" (still under development)
- **Option 3**: Queries ComfyUI server for current queue size and reports total count

---

## Image Upload & Processing Workflow

### Phase 1: Image Upload (`handle_photo()` and `handle_document()`)

**Accepted Formats**:
- Photos (compressed by Telegram)
- Documents with extensions: `png`, `jpg`, `jpeg`, `webp`

**Upload Validation**:
1. Checks if user is in `'waiting_for_image'` state
2. Prevents duplicate uploads if already processing
3. Validates file format for documents
4. Implements 3-retry limit for invalid formats

**File Naming Convention**:
- Format: `{user_id}_{timestamp}.{extension}`
- Example: `6377164696_1759290746.jpg`
- Ensures unique filenames and traceability to user

**State Tracking**:
- Valid upload → `retry_count` reset to 0
- Invalid upload → `retry_count` incremented
- After 3 failed attempts → Reset state and show menu again

---

### Phase 2: ComfyUI Upload & Queueing (`upload_and_queue_image()`)

**Step-by-Step Process**:

1. **Upload Image to ComfyUI** (lines 186-194):
   - Uses `aiohttp` to POST image to `/upload/image` endpoint
   - Sends image as multipart form data
   - Filename preserved for ComfyUI reference

2. **Create and Queue Workflow** (lines 196-204):
   - Loads workflow JSON from `~/mark4/workflows/i2i_1.json`
   - Updates LoadImage node (node "44") with uploaded filename
   - Posts workflow to `/prompt` endpoint
   - Receives `prompt_id` for tracking

3. **Update User State** (lines 206-211):
   - Sets state to `'processing'`
   - Stores `prompt_id` and `filename` for tracking
   - Prevents new uploads until current one completes

4. **Display Queue Information** (lines 213-226):
   - Fetches current queue position
   - Shows position and total queue size
   - Displays inline "刷新队列" (refresh queue) button
   - Stores message for later updates/deletion

5. **Start Background Monitoring** (line 229):
   - Creates async task to monitor processing
   - Non-blocking - bot continues handling other users

---

### Phase 3: Queue Management

#### Queue Position Tracking (`get_queue_position()`)

**Returns**: `(position, total_queue_size)`

**Logic**:
1. Queries `/queue` endpoint
2. Checks `queue_pending` array for prompt_id
3. If found in pending → Returns index + 1
4. Checks `queue_running` array
5. If currently running → Returns position 1
6. If not found → Returns 0 (completed or missing)
7. **Total Queue**: Sum of pending + running tasks

**Error Handling**: Returns `(-1, -1)` on failure

#### Queue Refresh Feature (`refresh_queue_callback()`)

**Trigger**: User clicks "刷新队列" inline button

**Process**:
1. Extracts `prompt_id` from callback data (`refresh_{prompt_id}`)
2. Fetches current queue position
3. Updates message with new position and total
4. If position > 0: Shows updated queue info with refresh button
5. If position = 0: Shows "处理中..." (processing)

---

### Phase 4: Processing Monitoring (`monitor_processing()`)

**Async Background Task** - Runs continuously until completion

**Polling Mechanism**:
- Checks every 5 seconds (`asyncio.sleep(5)`)
- Queries `/history/{prompt_id}` endpoint
- Non-blocking for other user operations

**Completion Detection**:
1. Checks if `prompt_id` exists in history response
2. Extracts output images from `outputs` field
3. Iterates through nodes to find image output
4. Retrieves first image in `images` array

**Image Retrieval** (lines 301-312):
1. Constructs URL: `/view?filename={image_filename}`
2. Downloads processed image
3. Saves to `COMFYUI_RETRIEVE_DIR`
4. Filename format: `{original_base_name}_complete.jpg`
5. Example: `6377164696_1759290746_complete.jpg`

**User Notification Sequence** (lines 314-334):
1. **Delete queue message** - Removes "您现在的排队为第X位" message
2. **Send processed image** - Photo sent first
3. **Send completion message** - "处理完成！请在5分钟内尽快储存"
4. **Schedule cleanup** - 5-minute timer starts
5. **Reset user state** - Clears processing state, user can upload again

**Design Rationale**: Image sent before text ensures user sees result immediately.

---

### Phase 5: Cleanup (`cleanup_after_timeout()`)

**Trigger**: 5 minutes after image delivery

**Cleanup Actions**:
1. Delete original upload from `user_uploads/`
2. Delete processed image from `comfyui_retrieve/`
3. Delete the image message from Telegram chat
4. Remove cleanup task reference from `cleanup_tasks` dict

**Purpose**:
- Saves storage space
- Protects user privacy
- Prevents long-term data retention

**Implementation**: Uses `asyncio.sleep(300)` for 5-minute delay

---

## Error Handling & Edge Cases

### Invalid Format Handling (`handle_invalid_format()`)

**Retry Logic**:
- Tracks attempts via `user_states[user_id]['retry_count']`
- Increments on each invalid upload
- After 3 attempts: Reset state and show menu

**User Feedback**:
- Attempts 1-2: "您发送的文件格式有误，请发送以下图片格式之一：'png', 'jpg', 'jpeg', 'webp'"
- Attempt 3: "您已尝试3次，请重新开始。" + Show menu

### Text Input During Image Wait (`handle_text_during_image_wait()`)

**Purpose**: Handles text messages when user should send image

**Exclusions**:
- Menu options are not treated as invalid
- List: `["1. 图片脱衣", "2. 图片转视频脱衣", "3. 查看队列"]`

**Behavior**:
- If user in `'waiting_for_image'` state
- Non-menu text triggers `handle_invalid_format()`

### Duplicate Upload Prevention

**Check** (lines 78-80, 113-115):
- If user already has state `'processing'`
- Returns message: "您上传的图片仍在队列中，请耐心等待"
- Prevents queue flooding

---

## ComfyUI Workflow Integration

### Workflow Loading (`create_comfyui_workflow()`)

**Workflow File**: `~/mark4/workflows/i2i_1.json`

**JSON Structure**:
```json
{
  "44": {
    "inputs": {
      "image": "placeholder.jpg"
    }
  },
  // ... other nodes
}
```

**Dynamic Update**:
- Node "44" is the LoadImage node
- `workflow["44"]["inputs"]["image"]` is updated with uploaded filename
- Ensures ComfyUI loads the correct user image

**Design Note**: Node IDs are static in ComfyUI workflow JSON. "44" must match the LoadImage node ID in the actual workflow.

---

## State Management Design

### User State Structure

**States**:
1. **First Contact**: `{'first_contact': True}`
2. **Waiting for Image**: `{'state': 'waiting_for_image', 'retry_count': 0}`
3. **Processing**: `{'state': 'processing', 'prompt_id': '...', 'filename': '...'}`
4. **Reset/Empty**: `{}`

**State Transitions**:
```
Start → First Contact → Menu Selection → Waiting for Image →
Processing → Cleanup → Reset → (back to Menu)
```

**Thread Safety**: Python's GIL ensures dictionary operations are thread-safe for simple updates.

---

## Handler Registration (`main()`)

**Order of Registration** (lines 408-413):
1. `/start` command
2. Menu selection (regex filter)
3. Photo messages
4. Document messages
5. Callback queries (button clicks)
6. All other text messages

**Filter Hierarchy**:
- Most specific filters first (commands, regex)
- Media filters (PHOTO, Document)
- Catch-all text filter last

**Regex Pattern**: `r"^(1\. 图片脱衣|2\. 图片转视频脱衣|3\. 查看队列)$"`
- Raw string to avoid escape sequence warnings
- Exact match for menu options

---

## Async Architecture

### Background Tasks

**Task Creation**:
- `asyncio.create_task()` for non-blocking execution
- Monitor processing: Runs per user
- Cleanup tasks: Scheduled deletions

**Concurrency**:
- Bot handles multiple users simultaneously
- Each user has independent state and tasks
- No blocking operations in main event loop

### Session Management

**aiohttp ClientSession**:
- Created per request batch
- Used with `async with` for proper cleanup
- Separate sessions for upload, queue checks, monitoring

---

## Key Design Decisions

### 1. Why Node "44" for LoadImage?
- ComfyUI workflows are JSON-based with fixed node IDs
- Node "44" is the LoadImage node in the specific workflow (`i2i_1.json`)
- This must match the actual workflow configuration

### 2. Why 5-Minute Cleanup?
- Balance between user convenience and storage management
- Gives users time to save images manually
- Prevents indefinite storage accumulation

### 3. Why Delete Queue Message?
- Clean user experience
- Reduces chat clutter
- Position info no longer relevant after completion

### 4. Why Send Image Before Text?
- Users see results immediately
- Image is the primary deliverable
- Text message can be ignored if user already saved image

### 5. Why Track Retry Count?
- Prevents infinite retry loops
- Guides user back to menu after repeated failures
- Better UX than immediate rejection

### 6. Why Separate Photo and Document Handlers?
- Telegram treats them differently
- Photos are compressed, documents preserve quality
- Different API methods required

---

## Future Development Notes

### Option 2: Image-to-Video
- Currently returns "此功能仍在开发中"
- Would require different ComfyUI workflow
- Likely similar structure to Option 1 but with video output handling

### Potential Improvements
1. **Webhook Mode**: Replace polling with webhooks for better performance
2. **User Analytics**: Track usage patterns, processing times
3. **Multi-Workflow Support**: Allow users to select different processing styles
4. **Progress Bar**: Show percentage completion during processing
5. **Error Recovery**: Auto-retry failed uploads
6. **Admin Commands**: Queue management, server status
7. **Payment Integration**: Premium features, usage limits
8. **Batch Processing**: Upload multiple images at once

---

## File Structure

```
mark4/
├── telegram_bot.py          # Main bot application
├── venv/                    # Python virtual environment
├── user_uploads/            # Temporary storage for user uploads
├── comfyui_retrieve/        # Temporary storage for processed images
├── workflows/
│   ├── i2i_1.json          # ComfyUI workflow definition
│   └── flux_dev_checkpoint_example.json:Zone.Identifier
└── project_documentation.md # This file
```

---

## Dependencies

**Required Python Packages**:
- `python-telegram-bot`: Telegram Bot API wrapper
- `aiohttp`: Async HTTP client for ComfyUI communication
- `asyncio`: Built-in async/await support

**External Services**:
- Telegram Bot API
- ComfyUI Server (remote at `20.196.153.126:8188`)

---

## Security Considerations

### Current Implementation
- Bot token is hardcoded (should use environment variables)
- No user authentication beyond Telegram
- No rate limiting implemented
- File cleanup after 5 minutes (privacy-conscious)

### Recommendations for Production
1. Move sensitive config to environment variables
2. Implement rate limiting per user
3. Add admin whitelist
4. Enable logging for monitoring
5. Add error reporting/alerting
6. Use HTTPS for ComfyUI if possible
7. Validate/sanitize file uploads
8. Implement user quotas

---

## Troubleshooting

### Common Issues

**"Conflict: terminated by other getUpdates request"**:
- Another bot instance is running with same token
- Solution: Kill other processes, wait 1-2 minutes for Telegram timeout

**Queue Position Not Updating**:
- ComfyUI server may be down
- Check `/queue` endpoint accessibility
- Verify network connectivity

**Images Not Retrieved**:
- Check `/history/{prompt_id}` response structure
- Verify node IDs match workflow
- Ensure ComfyUI server can write to output directory

**Cleanup Not Working**:
- Verify file paths exist
- Check file permissions
- Ensure cleanup tasks aren't being cancelled prematurely

---

## API Endpoints Used

### ComfyUI Server Endpoints

**POST `/upload/image`**:
- Upload user image to server
- Multipart form data with image file
- Returns: `{...}` (upload confirmation)

**POST `/prompt`**:
- Queue workflow for processing
- JSON body: `{"prompt": <workflow_json>}`
- Returns: `{"prompt_id": "..."}`

**GET `/queue`**:
- Get current queue status
- Returns: `{"queue_pending": [...], "queue_running": [...]}`

**GET `/history/{prompt_id}`**:
- Check if processing completed
- Returns: `{prompt_id: {"outputs": {...}}}`

**GET `/view?filename={filename}`**:
- Download processed image
- Returns: Binary image data

---

## Testing Checklist

### User Flows to Test
- [ ] First-time user flow (/start → hello → menu)
- [ ] Image upload (photo compressed)
- [ ] Image upload (document uncompressed)
- [ ] Invalid format handling (3 retries)
- [ ] Queue position display
- [ ] Queue refresh button
- [ ] Check queue status (Option 3)
- [ ] Processing completion
- [ ] Image delivery order (image then text)
- [ ] 5-minute cleanup
- [ ] Duplicate upload prevention
- [ ] Multiple concurrent users

### Error Cases to Test
- [ ] ComfyUI server down
- [ ] Invalid workflow JSON
- [ ] Missing node "44" in workflow
- [ ] Network timeout
- [ ] File write permission errors
- [ ] Telegram API rate limits

---

## Changelog

### Recent Updates

**2025-10-01**:
- Added Option 3: "查看队列" to check current queue size
- Modified queue display to show total queue size
- Changed image delivery order (image sent before text)
- Fixed regex escape sequence warning in handler registration

**Initial Version**:
- Basic image upload and processing
- Queue position tracking with refresh button
- Auto-cleanup after 5 minutes
- Retry logic for invalid uploads

---

## Contact & Maintenance

**For Future Claude Code Sessions**:
- All core functionality is in `telegram_bot.py`
- Workflow configuration in `workflows/i2i_1.json`
- State is in-memory (resets on bot restart)
- No database required for current implementation

**Key Files to Preserve**:
- `telegram_bot.py` - Main bot code
- `workflows/i2i_1.json` - ComfyUI workflow
- `project_documentation.md` - This documentation

---

## Summary for Quick Onboarding

This is a **Telegram bot for AI image processing**. Users upload images via Telegram, the bot forwards them to a remote ComfyUI server for processing, monitors the queue, and returns processed images. Files are automatically cleaned up after 5 minutes. The bot uses async Python with python-telegram-bot and aiohttp. State is managed in memory. Three menu options: process images, video processing (TODO), and check queue status. Main file: `telegram_bot.py`. ComfyUI workflow: `workflows/i2i_1.json` with LoadImage on node "44".
