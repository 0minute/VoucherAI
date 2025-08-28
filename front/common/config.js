/**
 * API 설정 관리 (BASE_URL, TOKEN)
 * settings 화면에서 이 함수들을 사용하여 API 설정을 저장/로드합니다.
 */

export function getBaseUrl() {
  try {
    const baseUrl = localStorage.getItem('BASE_URL') || '';
    // 설정되지 않았다면 기본값 사용
    if (!baseUrl.trim()) {
      return 'http://localhost:8000';
    }
    return baseUrl.trim();
  } catch (e) {
    console.warn('localStorage 읽기 실패 (BASE_URL):', e);
    return 'http://localhost:8000';
  }
}

export function setBaseUrl(baseUrl) {
  try {
    const trimmed = (baseUrl || '').trim();
    localStorage.setItem('BASE_URL', trimmed);
  } catch (e) {
    console.warn('localStorage 저장 실패 (BASE_URL):', e);
  }
}

export function getToken() {
  try {
    const token = localStorage.getItem('TOKEN') || '';
    return token.trim();
  } catch (e) {
    console.warn('localStorage 읽기 실패 (TOKEN):', e);
    return '';
  }
}

export function setToken(token) {
  try {
    const trimmed = (token || '').trim();
    localStorage.setItem('TOKEN', trimmed);
  } catch (e) {
    console.warn('localStorage 저장 실패 (TOKEN):', e);
  }
}

