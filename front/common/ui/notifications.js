let notificationContainer = null;

function initContainer() {
  if (!notificationContainer) {
    notificationContainer = document.createElement('div');
    notificationContainer.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      display: flex;
      flex-direction: column;
      gap: 8px;
      pointer-events: none;
    `;
    document.body.appendChild(notificationContainer);
  }
}

function createToast(message, type) {
  initContainer();
  
  const toast = document.createElement('div');
  toast.style.cssText = `
    padding: 12px 16px;
    border-radius: 6px;
    color: white;
    font-size: 14px;
    font-weight: 500;
    max-width: 300px;
    word-wrap: break-word;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    pointer-events: auto;
    transform: translateX(100%);
    transition: transform 0.3s ease;
    ${type === 'success' ? 'background-color: #10b981;' : ''}
    ${type === 'error' ? 'background-color: #ef4444;' : ''}
    ${type === 'info' ? 'background-color: #3b82f6;' : ''}
  `;
  
  toast.textContent = message;
  notificationContainer.appendChild(toast);
  
  // 애니메이션을 위해 다음 프레임에서 스타일 적용
  requestAnimationFrame(() => {
    toast.style.transform = 'translateX(0)';
  });
  
  // 자동 제거
  setTimeout(() => {
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }, 3000);
  
  return toast;
}

function showNotification(message, type) {
  return createToast(message, type);
}

export function showSuccess(message) {
  return showNotification(message, 'success');
}

export function showError(message) {
  return showNotification(message, 'error');
}

export function showInfo(message) {
  return showNotification(message, 'info');
}

