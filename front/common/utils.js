// ================================================== //
// Voucher AI - 공통 유틸리티 함수들
// ================================================== //

// ================================================== //
// 유틸리티 함수들
// ================================================== //
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

// ================================================== //
// 토스트 알림 관리자
// ================================================== //
class ToastManager {
  constructor() {
    this.container = this.getOrCreateContainer();
  }

  getOrCreateContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  show(type, title, message, duration = 5000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconMap = {
      success: 'fa-check-circle',
      error: 'fa-exclamation-circle',
      warning: 'fa-exclamation-triangle',
      info: 'fa-info-circle'
    };
    
    toast.innerHTML = `
      <div class="toast-content">
        <div class="toast-icon">
          <i class="fas ${iconMap[type] || iconMap.info}"></i>
        </div>
        <div class="toast-message">
          <div class="toast-title">${title}</div>
          <div class="toast-description">${message}</div>
        </div>
      </div>
    `;

    this.container.appendChild(toast);

    // 자동 제거
    setTimeout(() => {
      toast.style.animation = 'toastSlideOut 0.3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    }, duration);

    // 클릭으로 제거
    toast.addEventListener('click', () => {
      toast.style.animation = 'toastSlideOut 0.3s ease forwards';
      setTimeout(() => toast.remove(), 300);
    });
  }
}

// 전역 토스트 인스턴스
window.toast = new ToastManager();

// ================================================== //
// 모달 유틸리티
// ================================================== //
class ModalManager {
  static show(modal) {
    if (!modal) return;
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    ModalManager.trapFocus(modal);
  }

  static hide(modal) {
    if (!modal) return;
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    modal._cleanupFocusTrap?.();
  }

  static trapFocus(modal) {
    const focusableElements = modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleKeyDown = (e) => {
      if (e.key === 'Tab') {
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            lastElement.focus();
            e.preventDefault();
          }
        } else {
          if (document.activeElement === lastElement) {
            firstElement.focus();
            e.preventDefault();
          }
        }
      }
    };

    modal.addEventListener('keydown', handleKeyDown);
    
    // 정리 함수를 모달 객체에 저장
    modal._cleanupFocusTrap = () => {
      modal.removeEventListener('keydown', handleKeyDown);
    };
  }
}

window.ModalManager = ModalManager;

// ================================================== //
// 네비게이션 관리자
// ================================================== //
class NavigationManager {
  static handleNavigation(href) {
    if (href === '#logout') {
      if (confirm('정말 로그아웃하시겠습니까?')) {
        console.log('🚪 Logging out...');
        window.toast.show('info', '로그아웃', '로그아웃되었습니다.');
      }
      return;
    }

    // 페이지 이동
    const page = href.replace('#', '');
    if (page === 'dashboard') {
      window.location.href = '/dashboard/dashboard.html';
    } else if (page === 'workspace') {
      window.location.href = '/workspace/workspace.html';
    }
  }

  static updateActiveNavLink(currentPage) {
    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.remove('active');
      const href = link.getAttribute('href');
      if (href === `#${currentPage}`) {
        link.classList.add('active');
      }
    });
  }

  static setupNavigation() {
    // 네비게이션 링크 이벤트 리스너
    document.querySelectorAll('.nav-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const href = link.getAttribute('href');
        NavigationManager.handleNavigation(href);
      });
    });

    // 키보드 이벤트 (ESC로 모달 닫기)
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const visibleModal = document.querySelector('.modal[aria-hidden="false"]');
        if (visibleModal) {
          ModalManager.hide(visibleModal);
        }
      }
    });
  }
}

window.NavigationManager = NavigationManager;

// ================================================== //
// API 유틸리티
// ================================================== //
class ApiClient {
  static async get(url) {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('API GET 오류:', error);
      throw error;
    }
  }

  static async post(url, data) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('API POST 오류:', error);
      throw error;
    }
  }

  static async delete(url) {
    try {
      const response = await fetch(url, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.status === 204 ? null : await response.json();
    } catch (error) {
      console.error('API DELETE 오류:', error);
      throw error;
    }
  }
}

window.ApiClient = ApiClient;

// ================================================== //
// DOM 초기화
// ================================================== //
document.addEventListener('DOMContentLoaded', () => {
  // 네비게이션 초기화
  NavigationManager.setupNavigation();
  
  console.log('🚀 Common utilities initialized');
});
