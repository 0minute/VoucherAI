import { getBaseUrl, getToken } from './config.js';

class ApiError extends Error {
  constructor(message, status, serverError, ts) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.serverError = serverError;
    this.ts = ts;
  }
}

class ApiClient {
  async request(method, path, { json, formData, headers = {} } = {}) {
    const baseUrl = getBaseUrl();
    const token = getToken();
    
    if (!baseUrl) {
      throw new ApiError('BASE_URL이 설정되지 않았습니다', 0, null, new Date().toISOString());
    }

    const url = `${baseUrl}${path}`;
    const requestHeaders = { ...headers };

    // Authorization 헤더 자동 부착 (토큰이 있을 때만)
    if (token) {
      requestHeaders['Authorization'] = `Bearer ${token}`;
    }

    // JSON 바디일 때만 Content-Type 설정
    if (json) {
      requestHeaders['Content-Type'] = 'application/json; charset=utf-8';
    }
    // FormData일 때는 Content-Type을 설정하지 않음 (브라우저가 자동 설정)

    const requestOptions = {
      method,
      headers: requestHeaders
    };

    if (json) {
      requestOptions.body = JSON.stringify(json);
    } else if (formData) {
      requestOptions.body = formData;
    }

    const startTime = performance.now();
    
    try {
      const response = await fetch(url, requestOptions);
      const endTime = performance.now();
      
      console.debug(`API ${method} ${url} - ${response.status} (${Math.round(endTime - startTime)}ms)`);

      let responseData;
      try {
        responseData = await response.json();
      } catch (e) {
        responseData = { ok: false, error: 'Invalid JSON response', ts: new Date().toISOString() };
      }

      // HTTP status와 본문의 ok 모두 검사
      if (!response.ok || !responseData.ok) {
        const errorMessage = responseData.error || response.statusText || 'Unknown error';
        console.error('❌ API 에러 상세:', {
          url,
          method,
          status: response.status,
          statusText: response.statusText,
          responseData,
          requestBody: json || formData
        });
        throw new ApiError(
          errorMessage,
          response.status,
          responseData.error,
          responseData.ts || new Date().toISOString()
        );
      }

      return responseData;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      
      // 네트워크 에러 등
      throw new ApiError(
        error.message || 'Network error',
        0,
        null,
        new Date().toISOString()
      );
    }
  }

  async get(path, opts = {}) {
    return this.request('GET', path, opts);
  }

  async post(path, opts = {}) {
    return this.request('POST', path, opts);
  }

  async patch(path, opts = {}) {
    return this.request('PATCH', path, opts);
  }

  async delete(path, opts = {}) {
    return this.request('DELETE', path, opts);
  }
}

const apiClient = new ApiClient();
export default apiClient;
