import apiClient from '../apiClient.js';

function validateWorkspaceName(name) {
  if (!name || typeof name !== 'string') {
    throw new Error('워크스페이스 이름이 필요합니다');
  }
  
  const trimmed = name.trim();
  if (trimmed.length === 0) {
    throw new Error('워크스페이스 이름은 비어있을 수 없습니다');
  }
  
  if (trimmed.length > 128) {
    throw new Error('워크스페이스 이름은 128자를 초과할 수 없습니다');
  }
  
  return trimmed;
}

export const WorkspacesService = {
  async create(workspaceName, periodStart, periodEnd) {
    const validName = validateWorkspaceName(workspaceName);
    
    const response = await apiClient.post('/workspaces', {
      json: {
        workspaceName: validName,
        periodStart,
        periodEnd
      }
    });
    
    return response.data;
  },

  async remove(workspaceName) {
    const validName = validateWorkspaceName(workspaceName);
    
    const response = await apiClient.delete(`/workspaces/${encodeURIComponent(validName)}`);
    return response.data;
  },

  async list() {
    const response = await apiClient.get('/workspaces');
    return response.data.workspaces; // 백엔드에서 { workspaces: [...] } 형태로 반환
  },

  async rename(oldName, newName, includeArchived = false) {
    const validOldName = validateWorkspaceName(oldName);
    const validNewName = validateWorkspaceName(newName);
    
    // URL 경로에서 특수 문자 처리를 위해 더 안전한 인코딩 사용
    const encodedOldName = encodeURIComponent(validOldName);
    console.log('🔍 URL 인코딩 확인:', {
      original: validOldName,
      encoded: encodedOldName
    });
    
    const response = await apiClient.patch(`/workspaces/${encodedOldName}`, {
      json: {
        newName: validNewName,
        includeArchived
      }
    });
    
    return response.data;
  },

  async updatePeriod(workspaceName, periodStart, periodEnd) {
    const validName = validateWorkspaceName(workspaceName);
    
    const response = await apiClient.patch(`/workspaces/${encodeURIComponent(validName)}/period`, {
      json: {
        periodStart,
        periodEnd
      }
    });
    
    return response.data;
  }
};
