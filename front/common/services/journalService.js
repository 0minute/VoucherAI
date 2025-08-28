// ================================================== //
// Journal Service - 분개 관련 API 호출
// ================================================== //

import apiClient from '../apiClient.js';

/**
 * 워크스페이스명 검증
 */
function validateWorkspaceName(name) {
  if (!name || typeof name !== 'string') {
    throw new Error('워크스페이스명이 필요합니다.');
  }
  
  const trimmed = name.trim();
  if (trimmed.length === 0) {
    throw new Error('워크스페이스명은 공백일 수 없습니다.');
  }
  
  if (trimmed.length > 128) {
    throw new Error('워크스페이스명은 128자를 초과할 수 없습니다.');
  }
  
  return trimmed;
}

export const JournalService = {
  /**
   * OCR + 분개 생성 파이프라인 실행
   * @param {string} workspaceName - 워크스페이스명
   * @returns {Promise<Object>} OCR 및 분개 생성 결과
   */
  async generateJournal(workspaceName) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);

    console.log('🔄 OCR + 분개 생성 파이프라인 시작:', validWorkspaceName);

    const response = await apiClient.post(`/workspaces/${encodeURIComponent(validWorkspaceName)}/pipeline/ocr-journal`);

    console.log('✅ OCR + 분개 생성 완료:', response.data);
    return response.data;
  },

  /**
   * 분개 초안 조회
   * @param {string} workspaceName - 워크스페이스명
   * @returns {Promise<Object>} 분개 초안 데이터
   */
  async getJournalDrafts(workspaceName) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);

    console.log('🔍 분개 초안 조회:', validWorkspaceName);

    const response = await apiClient.get(`/workspaces/${encodeURIComponent(validWorkspaceName)}/journal-drafts`);

    console.log('✅ 분개 초안 조회 완료:', response.data);
    return response.data;
  },

  /**
   * 특정 파일의 바우처 데이터 조회
   * @param {string} workspaceName - 워크스페이스명
   * @param {string} fileId - 파일 ID
   * @returns {Promise<Object>} 바우처 데이터
   */
  async getVoucherData(workspaceName, fileId) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);
    
    if (!fileId) {
      throw new Error('파일 ID가 필요합니다.');
    }

    console.log('🔍 바우처 데이터 조회:', { workspaceName: validWorkspaceName, fileId });

    const response = await apiClient.get(`/workspaces/${encodeURIComponent(validWorkspaceName)}/voucher-data/${encodeURIComponent(fileId)}`);

    console.log('✅ 바우처 데이터 조회 완료:', response.data);
    return response.data;
  },

  /**
   * 특정 파일의 바우처 데이터 수정
   * @param {string} workspaceName - 워크스페이스명
   * @param {string} fileId - 파일 ID
   * @param {Object} edits - 수정할 데이터
   * @returns {Promise<Object>} 수정 결과
   */
  async updateVoucherData(workspaceName, fileId, edits) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);
    
    if (!fileId) {
      throw new Error('파일 ID가 필요합니다.');
    }

    if (!edits || typeof edits !== 'object') {
      throw new Error('수정할 데이터가 필요합니다.');
    }

    console.log('🔄 바우처 데이터 수정:', { workspaceName: validWorkspaceName, fileId, edits });

    const response = await apiClient.patch(`/workspaces/${encodeURIComponent(validWorkspaceName)}/voucher-data/${encodeURIComponent(fileId)}`, {
      json: { edits }
    });

    console.log('✅ 바우처 데이터 수정 완료:', response.data);
    return response.data;
  },

  /**
   * 시각화 이미지 경로 조회
   * @param {string} workspaceName - 워크스페이스명
   * @param {string} fileId - 파일 ID
   * @returns {Promise<Object>} 시각화 이미지 정보
   */
  async getVisualizationImage(workspaceName, fileId) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);
    
    if (!fileId) {
      throw new Error('파일 ID가 필요합니다.');
    }

    console.log('🔍 시각화 이미지 조회:', { workspaceName: validWorkspaceName, fileId });

    const response = await apiClient.get(`/workspaces/${encodeURIComponent(validWorkspaceName)}/visualizations/${encodeURIComponent(fileId)}`);

    console.log('✅ 시각화 이미지 조회 완료:', response.data);
    return response.data;
  },

  /**
   * 분개 데이터 기반 분개 재생성
   * @param {string} workspaceName - 워크스페이스명
   * @returns {Promise<Object>} 재생성된 분개 데이터
   */
  async refreshJournal(workspaceName) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);

    console.log('🔄 분개 재생성:', validWorkspaceName);

    const response = await apiClient.post(`/workspaces/${encodeURIComponent(validWorkspaceName)}/journal/refresh`);

    console.log('✅ 분개 재생성 완료:', response.data);
    return response.data;
  },

  /**
   * 분개 아카이브
   * @param {string} workspaceName - 워크스페이스명
   * @returns {Promise<Object>} 아카이브 결과
   */
  async archiveJournal(workspaceName) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);

    console.log('🔄 분개 아카이브:', validWorkspaceName);

    const response = await apiClient.post(`/workspaces/${encodeURIComponent(validWorkspaceName)}/journal/archive`);

    console.log('✅ 분개 아카이브 완료:', response.data);
    return response.data;
  }
};

