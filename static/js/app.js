// Institute Management System - Client Interactive Runtime

// Toast system
function showToast(message, type = 'info') {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.setAttribute('aria-live', 'polite');
    container.setAttribute('aria-atomic', 'true');
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'status');
  
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  toast.innerHTML = `<span style="font-weight: bold; margin-right: 6px;" aria-hidden="true">${icon}</span><span>${message}</span>`;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Modal controls
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    
    // Focus first focusable element inside modal
    const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length) {
      focusable[0].focus();
    }
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
}

// Close modal when clicking outside of modal card
document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
    e.target.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
});

// Escape key to close active modals & mobile sidebar
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.active').forEach(modal => {
      modal.classList.remove('active');
      modal.setAttribute('aria-hidden', 'true');
    });
    closeMobileSidebar();
    document.body.style.overflow = '';
  }
});

// Mobile Sidebar Drawer Navigation
function initMobileSidebar() {
  const toggleBtn = document.getElementById('mobile-menu-toggle');
  const sidebar = document.getElementById('app-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const closeBtn = document.getElementById('sidebar-close-btn');

  if (!toggleBtn || !sidebar) return;

  function openSidebar() {
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('active');
    toggleBtn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    toggleBtn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  toggleBtn.addEventListener('click', () => {
    if (sidebar.classList.contains('open')) {
      closeSidebar();
    } else {
      openSidebar();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener('click', closeSidebar);
  }

  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  // Close sidebar when clicking any navigation link on small screens
  sidebar.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 1024) {
        closeSidebar();
      }
    });
  });

  // Reset overflow and classes on viewport resize
  window.addEventListener('resize', () => {
    if (window.innerWidth > 1024 && sidebar.classList.contains('open')) {
      closeSidebar();
    }
  });
}

function closeMobileSidebar() {
  const sidebar = document.getElementById('app-sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const toggleBtn = document.getElementById('mobile-menu-toggle');
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
  }
}

// Button Loading State Helper
function setButtonLoading(button, isLoading, loadingText = 'Processing...') {
  if (!button) return;
  if (isLoading) {
    if (!button.dataset.originalHtml) {
      button.dataset.originalHtml = button.innerHTML;
    }
    button.classList.add('btn-loading');
    button.setAttribute('aria-busy', 'true');
    button.disabled = true;
    
    // Wrap text content in hideable wrapper if not already done
    button.innerHTML = `<span class="btn-text-content">${loadingText}</span>`;
  } else {
    button.classList.remove('btn-loading');
    button.removeAttribute('aria-busy');
    button.disabled = false;
    if (button.dataset.originalHtml) {
      button.innerHTML = button.dataset.originalHtml;
    }
  }
}

// Client-Side Form Validation & Submit Loading Engine
function initFormValidationAndLoading() {
  const forms = document.querySelectorAll('form');

  forms.forEach(form => {
    // Skip forms explicitly opting out
    if (form.getAttribute('data-no-validate') !== null) return;

    const inputs = form.querySelectorAll('input, select, textarea');

    // Real-time error clearance on user input
    inputs.forEach(input => {
      input.addEventListener('input', () => {
        if (input.classList.contains('is-invalid')) {
          validateSingleField(input);
        }
      });

      input.addEventListener('blur', () => {
        // Validate on blur if user interacted or field has content
        if (input.value.trim() !== '' || input.hasAttribute('required')) {
          validateSingleField(input);
        }
      });
    });

    // Handle form submit
    form.addEventListener('submit', (e) => {
      let isFormValid = true;
      let firstInvalidInput = null;

      inputs.forEach(input => {
        const isValid = validateSingleField(input);
        if (!isValid) {
          isFormValid = false;
          if (!firstInvalidInput) {
            firstInvalidInput = input;
          }
        }
      });

      if (!isFormValid) {
        e.preventDefault();
        showToast('Please correct the highlighted fields before submitting.', 'error');
        if (firstInvalidInput) {
          firstInvalidInput.focus();
        }
        return false;
      }

      // If valid and submitting to server, activate loading spinner
      const submitBtn = form.querySelector('button[type="submit"]') || form.querySelector('.btn-primary');
      if (submitBtn) {
        setButtonLoading(submitBtn, true);
      }
    });
  });
}

function validateSingleField(input) {
  // Ignore hidden, disabled, or non-submittable fields
  if (input.type === 'hidden' || input.disabled) return true;

  const value = input.value ? input.value.trim() : '';
  let errorMessage = '';

  // 1. Required check
  if (input.hasAttribute('required') && !value) {
    const label = getFieldLabel(input);
    errorMessage = `${label} is required.`;
  }
  // 2. Email format check
  else if (input.type === 'email' && value) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) {
      errorMessage = 'Please enter a valid email address.';
    }
  }
  // 3. Number range check
  else if (input.type === 'number' && value) {
    const num = parseFloat(value);
    if (input.hasAttribute('min') && num < parseFloat(input.getAttribute('min'))) {
      errorMessage = `Value must be at least ${input.getAttribute('min')}.`;
    } else if (input.hasAttribute('max') && num > parseFloat(input.getAttribute('max'))) {
      errorMessage = `Value must not exceed ${input.getAttribute('max')}.`;
    }
  }
  // 4. Pattern check
  else if (input.hasAttribute('pattern') && value) {
    const pattern = new RegExp(`^${input.getAttribute('pattern')}$`);
    if (!pattern.test(value)) {
      errorMessage = input.getAttribute('title') || 'Input does not match the required format.';
    }
  }

  // Render error or clear
  if (errorMessage) {
    setFieldError(input, errorMessage);
    return false;
  } else {
    clearFieldError(input);
    return true;
  }
}

function getFieldLabel(input) {
  const formGroup = input.closest('.form-group');
  if (formGroup) {
    const labelEl = formGroup.querySelector('label');
    if (labelEl) return labelEl.innerText.replace(/[*:]/g, '').trim();
  }
  return input.name || input.id || 'Field';
}

function setFieldError(input, message) {
  input.classList.add('is-invalid');
  input.classList.remove('is-valid');
  input.setAttribute('aria-invalid', 'true');

  const errorId = `error-${input.id || input.name || Math.random().toString(36).substring(2, 7)}`;
  input.setAttribute('aria-describedby', errorId);

  let errorEl = input.parentNode.querySelector('.form-error-inline');
  if (!errorEl) {
    errorEl = document.createElement('div');
    errorEl.className = 'form-error-inline';
    errorEl.id = errorId;
    input.parentNode.appendChild(errorEl);
  }
  errorEl.innerHTML = `<span aria-hidden="true">⚠️</span><span>${message}</span>`;
}

function clearFieldError(input) {
  input.classList.remove('is-invalid');
  input.removeAttribute('aria-invalid');
  input.removeAttribute('aria-describedby');

  const errorEl = input.parentNode.querySelector('.form-error-inline');
  if (errorEl) {
    errorEl.remove();
  }
}

// Global runtime initialization
document.addEventListener('DOMContentLoaded', () => {
  initMobileSidebar();
  initFormValidationAndLoading();
});

