/**
 * Jal Sarovar - Main JavaScript
 * Interactive features and utilities
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap tooltips are used
    initializeTooltips();

    // Auto-dismiss alerts after 5 seconds
    autoDismissAlerts();

    // Form validation
    initializeFormValidation();

    // Confirmation dialogs for delete actions
    initializeDeleteConfirmations();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(
        document.querySelectorAll('[data-bs-toggle="tooltip"]')
    );
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Auto-dismiss alert messages after 5 seconds
 */
function autoDismissAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

/**
 * Initialize delete confirmations
 */
function initializeDeleteConfirmations() {
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            const message = button.getAttribute('data-confirm-message') ||
                          'Are you sure you want to delete this item? This action cannot be undone.';
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });
}

/**
 * Show loading spinner overlay
 */
function showLoadingSpinner() {
    const spinner = document.querySelector('.spinner-overlay');
    if (spinner) {
        spinner.classList.add('active');
    }
}

/**
 * Hide loading spinner overlay
 */
function hideLoadingSpinner() {
    const spinner = document.querySelector('.spinner-overlay');
    if (spinner) {
        spinner.classList.remove('active');
    }
}

/**
 * Format date for display
 */
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

/**
 * Format number with commas
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showNotification('Copied to clipboard!', 'success');
    }, function(err) {
        showNotification('Failed to copy', 'error');
    });
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
    const alertClass = type === 'error' ? 'danger' : type;
    const alertHtml = `
        <div class="alert alert-${alertClass} alert-dismissible fade show position-fixed top-0 end-0 m-3"
             role="alert" style="z-index: 9999;">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', alertHtml);

    // Auto-dismiss after 3 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        if (alerts.length > 0) {
            const lastAlert = alerts[alerts.length - 1];
            const bsAlert = new bootstrap.Alert(lastAlert);
            bsAlert.close();
        }
    }, 3000);
}

/**
 * AJAX helper function
 */
function makeAjaxRequest(url, method = 'GET', data = null) {
    showLoadingSpinner();

    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    return fetch(url, options)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .finally(() => {
            hideLoadingSpinner();
        });
}

// Export functions for global use
window.JalSarovar = {
    showLoadingSpinner,
    hideLoadingSpinner,
    formatDate,
    formatNumber,
    copyToClipboard,
    showNotification,
    makeAjaxRequest
};
