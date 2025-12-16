// Broadcast Portal JavaScript
// This file contains shared JavaScript functions for the broadcast portal

// Check if message should be reused from history (via sessionStorage)
document.addEventListener('DOMContentLoaded', function() {
    const reuseData = sessionStorage.getItem('reuseMessage');
    if (reuseData) {
        try {
            const data = JSON.parse(reuseData);

            // Set message content
            if (document.getElementById('messageText')) {
                document.getElementById('messageText').value = data.message;
            }

            // Set parse mode
            if (data.parse_mode && window.setParseMode) {
                window.setParseMode(data.parse_mode);
            }

            // Set buttons
            if (data.buttons && window.buttons !== undefined) {
                window.buttons = data.buttons;
                if (window.renderButtons) {
                    window.renderButtons();
                }
                if (window.updatePreview) {
                    window.updatePreview();
                }
            }

            // Clear sessionStorage
            sessionStorage.removeItem('reuseMessage');

            // Show notification
            showNotification('消息已从历史记录加载', 'success');
        } catch (e) {
            console.error('Error loading reused message:', e);
        }
    }
});

// Utility function to show notifications
function showNotification(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alertDiv);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 5000);
}

// Format date for display
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('已复制到剪贴板', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('复制失败', 'danger');
    });
}

// Confirm action with custom message
function confirmAction(message) {
    return confirm(message);
}

// Debounce function for input events
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Validate URL format
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Log to console with timestamp
function log(message, level = 'info') {
    const timestamp = new Date().toISOString();
    console[level](`[${timestamp}] ${message}`);
}

// Export functions for use in other scripts
if (typeof window !== 'undefined') {
    window.broadcastUtils = {
        showNotification,
        formatDate,
        copyToClipboard,
        confirmAction,
        debounce,
        isValidUrl,
        escapeHtml,
        log
    };
}
