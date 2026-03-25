// PC Configuration - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('PC Configuration System loaded');
    
    // Auto-hide flash messages after 5 seconds
    // Compatibility result blocks should stay visible until user changes parts.
    const alerts = document.querySelectorAll('.js-auto-hide-alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            alert.style.transition = 'opacity 0.3s';
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.remove();
            }, 300);
        }, 5000);
    });
    
    // Form validation enhancement
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
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

// Export functions for global use
window.PCConfig = {
    formatPrice,
    showNotification,
    ajaxRequest,
};
