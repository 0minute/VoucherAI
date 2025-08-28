/**
 * API 설정 페이지 JavaScript
 * config.js와 apiClient.js를 사용하여 API 설정 관리
 */

import { getBaseUrl, setBaseUrl, getToken, setToken } from '../common/config.js';
import apiClient from '../common/apiClient.js';
import { showSuccess, showError, showInfo } from '../common/ui/notifications.js';

class SettingsAPIManager {
  constructor() {
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.loadCurrentSettings();
    console.log('⚙️ Settings API Manager initialized');
  }

  setupEventListeners() {
    // 저장 버튼
    const saveBtn = document.getElementById('saveBtn');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => this.saveSettings());
    }

    // ping 버튼
    const pingBtn = document.getElementById('pingBtn');
    if (pingBtn) {
      pingBtn.addEventListener('click', () => this.testConnection());
    }

    // Enter 키 지원
    const baseUrlInput = document.getElementById('baseUrlInput');
    const tokenInput = document.getElementById('tokenInput');
    
    [baseUrlInput, tokenInput].forEach(input => {
      if (input) {
        input.addEventListener('keydown', (e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            this.saveSettings();
          }
        });
      }
    });
  }

  loadCurrentSettings() {
    const baseUrlInput = document.getElementById('baseUrlInput');
    const tokenInput = document.getElementById('tokenInput');

    if (baseUrlInput) {
      baseUrlInput.value = getBaseUrl();
    }

    if (tokenInput) {
      tokenInput.value = getToken();
    }

    console.log('📋 현재 설정 로드 완료');
  }

  saveSettings() {
    const baseUrlInput = document.getElementById('baseUrlInput');
    const tokenInput = document.getElementById('tokenInput');

    if (!baseUrlInput || !tokenInput) {
      showError('설정 입력 필드를 찾을 수 없습니다.');
      return;
    }

    const baseUrl = baseUrlInput.value.trim();
    const token = tokenInput.value.trim();

    // BASE_URL과 TOKEN 저장
    setBaseUrl(baseUrl);
    setToken(token);

    showSuccess('API 설정이 저장되었습니다.');
    console.log('✅ API 설정 저장 완료:', { baseUrl: baseUrl || '(비어있음)', hasToken: !!token });
  }

  async testConnection() {
    const baseUrl = getBaseUrl();
    
    if (!baseUrl) {
      showError('BASE_URL을 먼저 설정해주세요.');
      return;
    }

    const pingBtn = document.getElementById('pingBtn');
    if (pingBtn) {
      pingBtn.disabled = true;
      pingBtn.textContent = '연결 테스트 중...';
    }

    try {
      console.log('🔄 API 연결 테스트 중...', baseUrl);
      
      // /ping 대신 /workspaces 엔드포인트 사용
      const response = await apiClient.get('/workspaces');
      
      console.log('✅ API 연결 테스트 성공:', response);
      showSuccess(`API 연결 성공! (워크스페이스 ${response.workspaces?.length || 0}개 발견)`);
      
    } catch (error) {
      console.error('❌ API 연결 테스트 실패:', error);
      let errorMessage = 'API 연결 실패';
      
      if (error.status) {
        errorMessage += ` (HTTP ${error.status})`;
      }
      
      if (error.message) {
        errorMessage += `: ${error.message}`;
      }
      
      showError(errorMessage);
      
    } finally {
      if (pingBtn) {
        pingBtn.disabled = false;
        pingBtn.textContent = '연결 테스트';
      }
    }
  }
}

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', () => {
  window.settingsAPIManager = new SettingsAPIManager();
});

