// ================================================== //
// Uploads Service - 파일 업로드 관련 API 호출
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

export const UploadsService = {
  /**
   * 개별 이미지 파일들 업로드
   * @param {string} workspaceName - 워크스페이스명
   * @param {File[]} files - 업로드할 파일 배열
   * @param {Object} options - 업로드 옵션
   * @param {number|null} options.ifMatchIndexVersion - 버전 매칭
   * @param {boolean} options.renameOnConflict - 충돌 시 이름 변경
   * @param {string|null} options.allowedExt - 허용 확장자 (".png,.jpg" 형태)
   * @returns {Promise<Object>} 업로드 결과
   */
  async uploadImages(workspaceName, files, options = {}) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);
    
    if (!files || !Array.isArray(files) || files.length === 0) {
      throw new Error('업로드할 파일이 필요합니다.');
    }

    const {
      ifMatchIndexVersion = null,
      renameOnConflict = true,
      allowedExt = null
    } = options;

    // FormData 생성
    const formData = new FormData();
    
    // 파일들 추가
    files.forEach(file => {
      formData.append('files', file);
    });
    
    // 옵션 파라미터들 추가
    if (ifMatchIndexVersion !== null) {
      formData.append('ifMatchIndexVersion', ifMatchIndexVersion.toString());
    }
    formData.append('renameOnConflict', renameOnConflict.toString());
    if (allowedExt !== null) {
      formData.append('allowedExt', allowedExt);
    }

    console.log('📤 이미지 파일 업로드 요청:', {
      workspaceName: validWorkspaceName,
      fileCount: files.length,
      fileNames: files.map(f => f.name),
      options
    });

    const response = await apiClient.post(`/workspaces/${encodeURIComponent(validWorkspaceName)}/uploads/images`, {
      formData
    });

    console.log('✅ 이미지 파일 업로드 완료:', response.data);
    return response.data;
  },

  /**
   * ZIP 파일 업로드
   * @param {string} workspaceName - 워크스페이스명
   * @param {File} file - ZIP 파일
   * @param {Object} options - 업로드 옵션
   * @param {boolean} options.preserveDirs - 디렉토리 구조 보존
   * @param {boolean} options.renameOnConflict - 충돌 시 이름 변경
   * @param {string|null} options.allowedExt - 허용 확장자
   * @param {boolean} options.rollbackOnFailure - 실패 시 롤백
   * @param {number|null} options.ifMatchIndexVersion - 버전 매칭
   * @returns {Promise<Object>} 업로드 결과
   */
  async uploadZip(workspaceName, file, options = {}) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);
    
    if (!file || !(file instanceof File)) {
      throw new Error('ZIP 파일이 필요합니다.');
    }

    if (!file.name.toLowerCase().endsWith('.zip')) {
      throw new Error('ZIP 파일만 업로드 가능합니다.');
    }

    const {
      preserveDirs = true,
      renameOnConflict = true,
      allowedExt = null,
      rollbackOnFailure = true,
      ifMatchIndexVersion = null
    } = options;

    // FormData 생성
    const formData = new FormData();
    formData.append('file', file);
    formData.append('preserveDirs', preserveDirs.toString());
    formData.append('renameOnConflict', renameOnConflict.toString());
    formData.append('rollbackOnFailure', rollbackOnFailure.toString());
    
    if (allowedExt !== null) {
      formData.append('allowedExt', allowedExt);
    }
    if (ifMatchIndexVersion !== null) {
      formData.append('ifMatchIndexVersion', ifMatchIndexVersion.toString());
    }

    console.log('📤 ZIP 파일 업로드 요청:', {
      workspaceName: validWorkspaceName,
      fileName: file.name,
      fileSize: file.size,
      options
    });

    const response = await apiClient.post(`/workspaces/${encodeURIComponent(validWorkspaceName)}/uploads/zip`, {
      formData
    });

    console.log('✅ ZIP 파일 업로드 완료:', response.data);
    return response.data;
  },

  /**
   * 업로드된 파일 목록 조회
   * @param {string} workspaceName - 워크스페이스명
   * @returns {Promise<Object>} 업로드된 파일 목록
   */
  async listUploaded(workspaceName) {
    const validWorkspaceName = validateWorkspaceName(workspaceName);

    console.log('🔍 업로드된 파일 목록 조회:', validWorkspaceName);

    const response = await apiClient.get(`/workspaces/${encodeURIComponent(validWorkspaceName)}/uploads`);

    console.log('✅ 업로드된 파일 목록:', response.data);
    return response.data;
  }
};

