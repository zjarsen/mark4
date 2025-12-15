# Queue Status Interface Refactoring

## Overview
Refactored queue manager architecture to use indexed dictionary structure for scalability, allowing multiple servers per workflow type in the future.

## Changes Made

### 1. WorkflowService - Indexed Queue Manager Structure

#### Before (workflow_service.py):
```python
self.image_queue_manager = ImageQueueManager(comfyui_service=image_comfyui)
self.video_queue_manager = VideoQueueManager(comfyui_service=video_douxiong_comfyui)
```

#### After (workflow_service.py:91-131):
```python
self.queue_managers = {
    'image': {
        'undress': ImageQueueManager(comfyui_service=image_comfyui),
        # Future: 'undress_2': ImageQueueManager(comfyui_service=image_comfyui_2),
    },
    'video': {
        'default': VideoQueueManager(comfyui_service=video_douxiong_comfyui),
        # Future: 'douxiong_2': VideoQueueManager(comfyui_service=video_douxiong_comfyui_2),
    }
}

# Convenience accessors (backward compatibility)
self.image_queue_manager = self.queue_managers['image']['undress']
self.video_queue_manager = self.queue_managers['video']['default']
```

### 2. New Helper Methods in WorkflowService

#### `get_queue_manager(workflow_type, server_key='default')` (Lines 108-122)
Get a specific queue manager by type and server key.

```python
manager = workflow_service.get_queue_manager('image', 'undress')
```

#### `get_all_queue_managers()` (Lines 124-131)
Get all queue managers for status reporting.

```python
all_managers = workflow_service.get_all_queue_managers()
# Returns: {'image': {'undress': manager}, 'video': {'default': manager}}
```

#### Updated `start_queue_managers()` (Lines 133-139)
Now iterates through all managers dynamically:

```python
for workflow_type, servers in self.queue_managers.items():
    for server_key, manager in servers.items():
        await manager.start()
```

#### Updated `stop_queue_managers()` (Lines 141-147)
Same dynamic iteration for stopping.

### 3. QueueService - Application Queue Status Method

#### New Method: `get_application_queue_status(workflow_service)` (Lines 54-90)

Returns comprehensive queue status across all managers:

```python
{
    'total_vip': 2,           # Total jobs in VIP queues
    'total_regular': 5,       # Total jobs in regular queues
    'total_processing': 2,    # Total jobs currently processing
    'total_queued': 7,        # Total jobs waiting in queues
    'total_jobs': 9,          # Total jobs (queued + processing)
    'managers': {
        'image': {
            'undress': {
                'vip_queue_size': 1,
                'regular_queue_size': 3,
                'processing': True,
                'total_queued': 4,
                'current_job_id': 'prompt_abc123'
            }
        },
        'video': {
            'default': {
                'vip_queue_size': 1,
                'regular_queue_size': 2,
                'processing': True,
                'total_queued': 3,
                'current_job_id': 'prompt_def456'
            }
        }
    }
}
```

### 4. Updated Check Queue Handler

#### File: `handlers/menu_handlers.py` (Lines 236-297)

**Before:**
- Showed total jobs in ComfyUI queue (multi-tenant, unreliable)
- No breakdown by workflow type
- No VIP/regular distinction

**After:**
- Shows application-layer queue status
- Breakdown by workflow type (image/video)
- Shows VIP vs regular queues
- Shows per-server status (ready for multiple servers)
- Chinese language display

**Example Output:**
```
📊 队列状态 (应用层)

🔸 总任务数: 9
   • VIP队列: 2
   • 普通队列: 5
   • 处理中: 2

🔹 图片队列:
   • 服务器 [undress]:
     VIP: 1, 普通: 3, 处理中: 是

🔹 视频队列:
   • 服务器 [default]:
     VIP: 1, 普通: 2, 处理中: 是

✅ 队列为空，可以立即处理您的请求！
```

## Benefits

### 1. Scalability
- **Easy to add more servers**: Just add entries to the dictionary
- **No code changes needed**: New servers automatically included in status reporting
- **Per-server load balancing**: Can route jobs to least busy server in the future

### 2. Better Visibility
- **Application queue**: Shows OUR queue, not ComfyUI's multi-tenant queue
- **VIP tracking**: Clear visibility into VIP priority usage
- **Per-type breakdown**: See image vs video workload separately

### 3. Future-Proof Architecture
- **Multiple servers per type**: Ready for horizontal scaling
- **Dynamic management**: Loop through all managers automatically
- **Backward compatible**: Old code still works via convenience accessors

## Future Enhancements

### Adding a New Server (Example)

```python
# In workflow_service.py __init__:
self.queue_managers = {
    'image': {
        'undress': ImageQueueManager(comfyui_service=image_comfyui),
        'undress_2': ImageQueueManager(comfyui_service=image_comfyui_2),  # NEW SERVER
    },
    'video': {
        'default': VideoQueueManager(comfyui_service=video_douxiong_comfyui),
        'douxiong_2': VideoQueueManager(comfyui_service=video_douxiong_comfyui_2),  # NEW SERVER
    }
}
```

That's it! The rest works automatically:
- `start_queue_managers()` will start it
- `get_application_queue_status()` will include it
- Queue status display will show it

### Load Balancing (Future)

```python
def get_least_busy_manager(self, workflow_type: str):
    """Get the queue manager with the smallest queue for this workflow type."""
    managers = self.queue_managers.get(workflow_type, {})

    least_busy = None
    min_size = float('inf')

    for server_key, manager in managers.items():
        status = manager.get_queue_status()
        total = status['total_queued']

        if total < min_size:
            min_size = total
            least_busy = manager

    return least_busy
```

Then in workflow submission:
```python
# Instead of: self.image_queue_manager.queue_job(job, is_vip)
# Use: manager = self.get_least_busy_manager('image')
#      await manager.queue_job(job, is_vip)
```

## Testing Checklist

- [ ] Bot starts successfully with indexed structure
- [ ] Check queue command shows correct status
- [ ] Status updates when jobs are queued
- [ ] Status updates when jobs complete
- [ ] Multiple servers show correctly (when added)
- [ ] Backward compatibility (old `self.image_queue_manager` still works)

## Migration Notes

- **Backward Compatible**: Existing code using `self.image_queue_manager` continues to work
- **No Database Changes**: This is purely in-memory restructuring
- **No API Changes**: External interfaces unchanged
- **Gradual Migration**: Can migrate to use `get_queue_manager()` over time

## File Changes Summary

1. **services/workflow_service.py**:
   - Lines 87-106: Indexed queue manager structure
   - Lines 108-122: `get_queue_manager()` method
   - Lines 124-131: `get_all_queue_managers()` method
   - Lines 133-147: Updated `start/stop_queue_managers()`

2. **services/queue_service.py**:
   - Lines 37-52: Deprecated `get_queue_total()` (kept for compatibility)
   - Lines 54-90: New `get_application_queue_status()` method

3. **handlers/menu_handlers.py**:
   - Lines 236-297: Updated `handle_check_queue()` with new status display

## Rollback Plan

If issues arise, the convenience accessors ensure backward compatibility:
```python
self.image_queue_manager  # Still works!
self.video_queue_manager  # Still works!
```

No rollback needed - old code continues to function while new code uses the indexed structure.
