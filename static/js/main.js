// PC Configuration - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('PC Configuration System loaded');

    const fadeOutAndRemove = function(element, durationMs) {
        element.style.transition = `opacity ${durationMs / 1000}s`;
        element.style.opacity = '0';
        setTimeout(function() {
            element.remove();
        }, durationMs);
    };
    
    // Auto-hide flash messages after 5 seconds
    // Compatibility result blocks should stay visible until user changes parts.
    const alerts = document.querySelectorAll('.js-auto-hide-alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            fadeOutAndRemove(alert, 300);
        }, 5000);
    });
    
    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (e.defaultPrevented) return;
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner"></span> 处理中...';
            }
        });
    });
    
    // Price format helper
    const priceInputs = document.querySelectorAll('input[type="number"][data-type="price"]');
    priceInputs.forEach(function(input) {
        input.addEventListener('blur', function() {
            const value = parseFloat(this.value);
            if (!isNaN(value)) {
                this.value = value.toFixed(2);
            }
        });
    });
});

// Utility functions
function formatPrice(price) {
    return '¥' + parseFloat(price).toFixed(2);
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '1000';
    notification.style.minWidth = '300px';
    
    document.body.appendChild(notification);
    
    setTimeout(function() {
        notification.style.transition = 'opacity 0.3s';
        notification.style.opacity = '0';
        setTimeout(function() {
            notification.remove();
        }, 300);
    }, 3000);
}

// AJAX helper
async function ajaxRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                ...options.headers,
            },
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('AJAX request failed:', error);
        showNotification('请求失败，请稍后重试', 'error');
        throw error;
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showDialog(options = {}) {
    const {
        title = '提示',
        message = '',
        confirmText = '确定',
        cancelText = '取消',
        mode = 'confirm',
        defaultValue = '',
        placeholder = '',
    } = options;

    return new Promise((resolve) => {
        const overlay = document.createElement('div');
        overlay.className = 'pc-modal-overlay';
        const dialog = document.createElement('div');
        dialog.className = 'pc-modal';
        dialog.setAttribute('role', 'dialog');
        dialog.setAttribute('aria-modal', 'true');

        const titleEl = document.createElement('div');
        titleEl.className = 'pc-modal-title';
        titleEl.textContent = title;
        dialog.appendChild(titleEl);

        if (message) {
            const messageEl = document.createElement('div');
            messageEl.className = 'pc-modal-message';
            messageEl.textContent = message;
            dialog.appendChild(messageEl);
        }

        let inputEl = null;
        if (mode === 'prompt') {
            inputEl = document.createElement('input');
            inputEl.className = 'form-control pc-modal-input';
            inputEl.type = 'text';
            inputEl.value = defaultValue || '';
            inputEl.placeholder = placeholder || '';
            dialog.appendChild(inputEl);
        }

        const actions = document.createElement('div');
        actions.className = 'pc-modal-actions';

        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-outline';
        cancelBtn.textContent = cancelText;

        const confirmBtn = document.createElement('button');
        confirmBtn.type = 'button';
        confirmBtn.className = 'btn btn-primary';
        confirmBtn.textContent = confirmText;

        actions.appendChild(cancelBtn);
        actions.appendChild(confirmBtn);
        dialog.appendChild(actions);
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        const cleanup = () => {
            document.removeEventListener('keydown', onKeydown);
            overlay.remove();
        };
        const confirm = () => {
            const value = inputEl ? (inputEl.value || '').trim() : '';
            cleanup();
            resolve({ confirmed: true, value });
        };
        const cancel = () => {
            cleanup();
            resolve({ confirmed: false, value: '' });
        };
        const onKeydown = (event) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                cancel();
            } else if (event.key === 'Enter' && mode === 'prompt') {
                event.preventDefault();
                confirm();
            }
        };

        document.addEventListener('keydown', onKeydown);
        cancelBtn.addEventListener('click', cancel);
        confirmBtn.addEventListener('click', confirm);
        overlay.addEventListener('click', (event) => {
            if (event.target === overlay) cancel();
        });

        if (inputEl) {
            inputEl.focus();
            inputEl.setSelectionRange(0, inputEl.value.length);
        } else {
            confirmBtn.focus();
        }
    });
}

function promptDialog(title, defaultValue = '', message = '') {
    return showDialog({
        mode: 'prompt',
        title,
        message,
        confirmText: '保存',
        cancelText: '取消',
        defaultValue,
        placeholder: '请输入方案名称',
    });
}

function confirmDialog(title, message) {
    return showDialog({
        mode: 'confirm',
        title,
        message,
        confirmText: '确认',
        cancelText: '取消',
    });
}

// Export functions for global use
window.PCConfig = {
    formatPrice,
    showNotification,
    ajaxRequest,
    showDialog,
    promptDialog,
    confirmDialog,
};
