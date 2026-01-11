/*
 * Contact Form Validation and Submission
 */

document.addEventListener('DOMContentLoaded', function() {
    initContactForm();
});

/**
 * Initialize Contact Form
 */
function initContactForm() {
    const form = document.getElementById('contact-form');
    if (!form) return;

    form.addEventListener('submit', handleFormSubmit);

    // Real-time validation on blur
    const inputs = form.querySelectorAll('input, textarea');
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateField(this);
        });

        input.addEventListener('input', function() {
            // Remove error styling while typing
            if (this.classList.contains('error')) {
                this.classList.remove('error');
            }
        });
    });
}

/**
 * Handle Form Submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const formMessage = document.getElementById('form-message');

    // Validate all fields
    if (!validateForm(form)) {
        showFormMessage('Please fix the errors above and try again.', 'error');
        return;
    }

    // Check honeypot (spam prevention)
    const honeypot = form.querySelector('input[name="website"]');
    if (honeypot && honeypot.value !== '') {
        // Likely a bot, silently reject
        showFormMessage('Thank you for your message!', 'success');
        form.reset();
        return;
    }

    // Get form data
    const formData = {
        name: form.querySelector('#name').value.trim(),
        email: form.querySelector('#email').value.trim(),
        subject: form.querySelector('#subject').value.trim(),
        message: form.querySelector('#message').value.trim(),
        timestamp: new Date().toISOString()
    };

    // Disable submit button
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Sending...';

    try {
        // TODO: Replace with actual form submission endpoint
        // For now, we'll simulate a successful submission
        await simulateFormSubmission(formData);

        // Success
        showFormMessage('Thank you for your message! I\'ll get back to you within 2-3 business days.', 'success');
        form.reset();

        // Log to console (for development)
        console.log('Form submission:', formData);

    } catch (error) {
        // Error
        showFormMessage('Sorry, there was an error sending your message. Please try again or contact me directly via email.', 'error');
        console.error('Form submission error:', error);

    } finally {
        // Re-enable submit button
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

/**
 * Validate Entire Form
 */
function validateForm(form) {
    let isValid = true;

    const name = form.querySelector('#name');
    const email = form.querySelector('#email');
    const subject = form.querySelector('#subject');
    const message = form.querySelector('#message');

    // Validate each field
    if (!validateField(name)) isValid = false;
    if (!validateField(email)) isValid = false;
    if (!validateField(subject)) isValid = false;
    if (!validateField(message)) isValid = false;

    return isValid;
}

/**
 * Validate Individual Field
 */
function validateField(field) {
    const value = field.value.trim();
    const fieldName = field.getAttribute('id');
    let isValid = true;
    let errorMessage = '';

    // Remove previous error
    removeFieldError(field);

    // Required field check
    if (!value) {
        errorMessage = 'This field is required';
        isValid = false;
    }
    // Email validation
    else if (fieldName === 'email') {
        if (!isValidEmail(value)) {
            errorMessage = 'Please enter a valid email address';
            isValid = false;
        }
    }
    // Name validation
    else if (fieldName === 'name') {
        if (value.length < 2) {
            errorMessage = 'Name must be at least 2 characters';
            isValid = false;
        }
        if (!/^[a-zA-Z\s'-]+$/.test(value)) {
            errorMessage = 'Name can only contain letters, spaces, hyphens, and apostrophes';
            isValid = false;
        }
    }
    // Subject validation
    else if (fieldName === 'subject') {
        if (value.length < 3) {
            errorMessage = 'Subject must be at least 3 characters';
            isValid = false;
        }
    }
    // Message validation
    else if (fieldName === 'message') {
        if (value.length < 10) {
            errorMessage = 'Message must be at least 10 characters';
            isValid = false;
        }
        if (value.length > 1000) {
            errorMessage = 'Message must be less than 1000 characters';
            isValid = false;
        }
    }

    if (!isValid) {
        showFieldError(field, errorMessage);
    }

    return isValid;
}

/**
 * Email Validation
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Show Field Error
 */
function showFieldError(field, message) {
    field.classList.add('error');
    field.style.borderColor = '#ef4444';

    // Create error message element
    let errorElement = field.parentElement.querySelector('.field-error');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'field-error';
        errorElement.style.color = '#ef4444';
        errorElement.style.fontSize = '0.875rem';
        errorElement.style.marginTop = '0.25rem';
        field.parentElement.appendChild(errorElement);
    }
    errorElement.textContent = message;
}

/**
 * Remove Field Error
 */
function removeFieldError(field) {
    field.classList.remove('error');
    field.style.borderColor = '';

    const errorElement = field.parentElement.querySelector('.field-error');
    if (errorElement) {
        errorElement.remove();
    }
}

/**
 * Show Form Message
 */
function showFormMessage(message, type) {
    const formMessage = document.getElementById('form-message');
    if (!formMessage) return;

    formMessage.textContent = message;
    formMessage.className = `form-message ${type}`;
    formMessage.style.display = 'block';

    // Scroll to message
    formMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Auto-hide success messages after 10 seconds
    if (type === 'success') {
        setTimeout(() => {
            formMessage.style.display = 'none';
        }, 10000);
    }
}

/**
 * Simulate Form Submission
 * TODO: Replace with actual backend endpoint
 */
function simulateFormSubmission(formData) {
    return new Promise((resolve, reject) => {
        // Simulate network delay
        setTimeout(() => {
            // Simulate 95% success rate
            if (Math.random() > 0.05) {
                resolve({ success: true });
            } else {
                reject(new Error('Simulated network error'));
            }
        }, 1000);
    });
}

/**
 * Actual Form Submission (to be implemented)
 * Example implementations:
 */

// Example 1: Using Formspree (free service)
async function submitToFormspree(formData) {
    const FORMSPREE_ENDPOINT = 'https://formspree.io/f/YOUR_FORM_ID';

    const response = await fetch(FORMSPREE_ENDPOINT, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    });

    if (!response.ok) {
        throw new Error('Form submission failed');
    }

    return await response.json();
}

// Example 2: Using your own backend
async function submitToBackend(formData) {
    const response = await fetch('/api/contact', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    });

    if (!response.ok) {
        throw new Error('Form submission failed');
    }

    return await response.json();
}

// Example 3: Using EmailJS (client-side email service)
async function submitWithEmailJS(formData) {
    // Requires EmailJS library
    // emailjs.send('YOUR_SERVICE_ID', 'YOUR_TEMPLATE_ID', formData)
    //     .then(response => { ... })
    //     .catch(error => { ... });
}

/**
 * Character Counter (optional enhancement)
 */
function addCharacterCounter(textareaId, maxLength) {
    const textarea = document.getElementById(textareaId);
    if (!textarea) return;

    const counter = document.createElement('div');
    counter.className = 'character-counter';
    counter.style.textAlign = 'right';
    counter.style.fontSize = '0.875rem';
    counter.style.color = 'var(--text-light)';
    counter.style.marginTop = '0.25rem';

    textarea.parentElement.appendChild(counter);

    function updateCounter() {
        const length = textarea.value.length;
        counter.textContent = `${length} / ${maxLength} characters`;

        if (length > maxLength) {
            counter.style.color = '#ef4444';
        } else if (length > maxLength * 0.9) {
            counter.style.color = '#f59e0b';
        } else {
            counter.style.color = 'var(--text-light)';
        }
    }

    textarea.addEventListener('input', updateCounter);
    updateCounter();
}

// Uncomment to add character counter to message field
// addCharacterCounter('message', 1000);
