// ================================================== //
// Workspace Manager - 파일 업로드 및 분개 생성
// ================================================== //

import { JournalService } from '../common/services/journalService.js';
import { showSuccess, showError, showInfo } from '../common/ui/notifications.js';
import { getBaseUrl } from '../common/config.js';

class WorkspaceManager {
  constructor() {
    this.isMobile = window.innerWidth <= 768;
    this.fileRows = new Map(); // file ID -> fileRow object
    this.projects = new Map(); // project ID -> project object
    this.selectedFiles = new Set(); // selected file IDs
    this.fileCounter = 0;
    this.uploadQueue = new Map(); // file ID -> upload promise
    
    // 임시 선택된 파일들
    this.tempSelectedFiles = null;
    this.tempSelectedZip = null;
    
    this.init();
  }

// ================================================== //
// API 설정
// ================================================== //
setupAPI() {
  this.apiBaseURL = ''; // FastAPI는 같은 도메인
  this.apiHeaders = {
    'Content-Type': 'application/json'
  };
}

getWorkspaceNameFromURL() {
  const urlParams = new URLSearchParams(window.location.search);
  const workspaceTitle = urlParams.get('title');
  return workspaceTitle || 'default';
}

  init() {
    this.setupAPI();
    this.setupEventListeners();
    this.setupScrollSpy();
    this.setupUploadHandlers();
    this.setupTableHandlers();
    this.setupModalHandlers();
    this.loadProjects();
    
    // URL 파라미터에서 Workspace 정보 가져오기
    this.loadWorkspaceFromURL();
    
    this.updateEmptyState();
    this.updateUploadPreview(); // 초기 업로드 미리보기 설정
    
    // 기존 업로드된 파일들 로드
    this.loadUploadedFiles();
    
    console.log('🚀 Workspace Manager initialized');
  }

  // ================================================== //
  // 기본 이벤트 리스너 설정
  // ================================================== //
  setupEventListeners() {
    // 사이드바 링크 (Workspace)
    document.querySelectorAll('.workspace-sidebar .sidebar-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const href = link.getAttribute('href');
        this.handleSidebarNavigation(href, link);
      });
    });

    // 분개 생성 버튼
    const btnGenerateJournal = document.getElementById('btn-generate-journal');
    if (btnGenerateJournal) {
      btnGenerateJournal.addEventListener('click', () => {
        this.generateJournal();
      });
    }

    // 윈도우 리사이즈
    window.addEventListener('resize', debounce(() => {
      this.isMobile = window.innerWidth <= 768;
      this.handleResize();
    }, 250));
  }

  // ================================================== //
  // 업로드 핸들러 설정
  // ================================================== //
  setupUploadHandlers() {
    const uploadBox = document.querySelector('[data-testid="upload-dropzone"]');
    const fileInput = document.getElementById('file-input');
    const zipInput = document.getElementById('zip-input');
    const btnUploadImages = document.getElementById('btn-upload-images');
    const btnUploadZip = document.getElementById('btn-upload-zip');

    if (!uploadBox || !fileInput) return;

    // 업로드 박스 클릭/키보드
    uploadBox.addEventListener('click', () => fileInput.click());
    uploadBox.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        fileInput.click();
      }
    });

      // 버튼 클릭 - 실제 업로드 처리
  btnUploadImages?.addEventListener('click', () => {
    if (this.tempSelectedFiles && this.tempSelectedFiles.length > 0) {
      this.handleFileSelect(this.tempSelectedFiles);
      this.tempSelectedFiles = null;
      this.updateUploadPreview();
    } else {
      fileInput.click();
    }
  });
  
  btnUploadZip?.addEventListener('click', () => {
    if (this.tempSelectedZip) {
      this.handleZipSelect([this.tempSelectedZip]);
      this.tempSelectedZip = null;
      this.updateUploadPreview();
    } else {
      zipInput.click();
    }
  });

      // 파일 선택 - 선택된 파일을 임시 저장만 하고 테이블에는 추가하지 않음
  fileInput.addEventListener('change', (e) => {
    this.tempSelectedFiles = Array.from(e.target.files);
    this.updateUploadPreview();
    e.target.value = ''; // 리셋
  });

  zipInput?.addEventListener('change', (e) => {
    this.tempSelectedZip = e.target.files[0];
    this.updateUploadPreview();
    e.target.value = ''; // 리셋
  });

    // 드래그 앤 드롭
    uploadBox.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadBox.classList.add('drag-over');
    });

    uploadBox.addEventListener('dragleave', (e) => {
      e.preventDefault();
      if (!uploadBox.contains(e.relatedTarget)) {
        uploadBox.classList.remove('drag-over');
      }
    });

      uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('drag-over');
    
    const files = Array.from(e.dataTransfer.files);
    this.tempSelectedFiles = files;
    this.updateUploadPreview();
  });

    console.log('📁 Upload handlers initialized');
  }

  // ================================================== //
  // 테이블 핸들러 설정
  // ================================================== //
  setupTableHandlers() {
    // 전체 선택 체크박스
    const selectAll = document.getElementById('select-all');
    if (selectAll) {
      selectAll.addEventListener('change', (e) => {
        this.handleSelectAll(e.target.checked);
      });
    }

    // 일괄 수정 버튼
    const bulkProjectBtn = document.getElementById('btn-bulk-project');
    if (bulkProjectBtn) {
      bulkProjectBtn.addEventListener('click', () => {
        this.openBulkProjectModal();
      });
    }
  }

  // ================================================== //
  // 모달 핸들러 설정
  // ================================================== //
  setupModalHandlers() {
    const modal = document.getElementById('modal-bulk-project');
    const bulkCancel = document.getElementById('bulk-cancel');
    const bulkConfirm = document.getElementById('bulk-confirm');
    const modalClose = modal?.querySelector('.modal-close');
    const backdrop = modal?.querySelector('.modal-backdrop');
    const projectSelect = document.getElementById('bulk-project-select');

    // 모달 닫기
    [bulkCancel, modalClose, backdrop].forEach(el => {
      el?.addEventListener('click', () => this.closeBulkProjectModal());
    });

    // 확인 버튼
    bulkConfirm?.addEventListener('click', () => this.confirmBulkProject());

    // 프로젝트 선택 변경
    projectSelect?.addEventListener('change', (e) => {
      const confirmBtn = document.getElementById('bulk-confirm');
      if (confirmBtn) {
        confirmBtn.disabled = !e.target.value;
      }
    });
  }

  // ================================================== //
  // 파일 처리
  // ================================================== //
  async handleFileSelect(files) {
    const validFiles = files.filter(file => this.validateFile(file));
    
    if (validFiles.length === 0) return;
  
    // 중복 방지 (name + size 해시)
    const uniqueFiles = validFiles.filter(file => {
      const hash = this.getFileHash(file);
      return !Array.from(this.fileRows.values()).some(row => row.hash === hash);
    });
  
    if (uniqueFiles.length === 0) {
      window.toast?.show('warning', '중복 파일', '선택한 파일들이 이미 업로드되어 있습니다.');
      return;
    }
  
    try {
      // FormData 생성
      const formData = new FormData();
      uniqueFiles.forEach(file => {
        formData.append('files', file);
      });
      
      const workspaceName = this.getWorkspaceNameFromURL();
      
      // 임시 파일 행들 먼저 생성 (업로드 상태 표시용)
      const tempFileRows = [];
      uniqueFiles.forEach(file => {
        const fileRow = this.createFileRow(file);
        fileRow.status = 'uploading';
        this.fillEmptyRow(fileRow);
        this.updateRowStatus(fileRow.id, 'uploading', '업로드 중...');
        tempFileRows.push(fileRow);
      });
  
      // 실제 API 호출
      const baseUrl = getBaseUrl();
      const response = await fetch(`${baseUrl}/workspaces/${encodeURIComponent(workspaceName)}/uploads/images`, {
        method: 'POST',
        body: formData
      });
  
      if (!response.ok) {
        throw new Error(`업로드 실패: ${response.statusText}`);
      }
  
      const result = await response.json();
      
      if (result.ok && result.data?.fsResult?.copied) {
        // 성공한 파일들 상태 업데이트
        const copiedFiles = result.data.fsResult.copied;
        tempFileRows.forEach((fileRow, index) => {
          if (copiedFiles[index]) {
            fileRow.status = 'completed';
            fileRow.serverId = copiedFiles[index];
            this.updateRowStatus(fileRow.id, 'completed', '업로드 완료');
          }
        });
  
        window.toast?.show('success', '업로드 완료', `${copiedFiles.length}개 파일이 업로드되었습니다.`);
        
        // 업로드 완료 후 파일 목록 새로고침
        await this.loadUploadedFiles();
      } else {
        throw new Error(result.error || '업로드 실패');
      }
  
    } catch (error) {
      console.error('업로드 실패:', error);
      window.toast?.show('error', '업로드 실패', error.message);
      
      // 실패한 파일들은 테이블에서 제거
      uniqueFiles.forEach(file => {
        const hash = this.getFileHash(file);
        const failedRow = Array.from(this.fileRows.values()).find(row => row.hash === hash);
        if (failedRow) {
          this.deleteFile(failedRow.id);
        }
      });
    }
  
    this.updateEmptyState();
  }

  async handleZipSelect(files) {
    if (files.length === 0) return;
    
    const zipFile = files[0];
    if (!zipFile.name.toLowerCase().endsWith('.zip')) {
      return;
    }
  
    try {
      // 임시 ZIP 표시 행 생성
      const zipRow = this.createFileRow(zipFile);
      zipRow.name = `📦 ${zipFile.name} (압축 해제 중...)`;
      zipRow.status = 'processing';
      this.fillEmptyRow(zipRow);
      this.updateRowStatus(zipRow.id, 'processing', '압축 해제 중...');
  
      const formData = new FormData();
      formData.append('file', zipFile);
      
      const workspaceName = this.getWorkspaceNameFromURL();
      
      const baseUrl = getBaseUrl();
      const response = await fetch(`${baseUrl}/workspaces/${encodeURIComponent(workspaceName)}/uploads/zip`, {
        method: 'POST',
        body: formData
      });
  
      if (!response.ok) {
        throw new Error(`ZIP 업로드 실패: ${response.statusText}`);
      }
  
      const result = await response.json();
      
      if (result.ok && result.data?.fsResult?.copied_rel) {
        // ZIP 행 제거
        this.deleteFile(zipRow.id);
        
        // 압축 해제된 파일들을 테이블에 추가
        const extractedFiles = result.data.fsResult.copied_rel;
        extractedFiles.forEach((filePath) => {
          const fileName = filePath.split('/').pop();
          const mockFile = new File([''], fileName, { type: 'image/jpeg' });
          
          const fileRow = this.createFileRow(mockFile);
          fileRow.serverId = filePath;
          fileRow.status = 'completed';
          
          this.fillEmptyRow(fileRow);
          this.updateRowStatus(fileRow.id, 'completed', '압축 해제 완료');
        });
  
        window.toast?.show('success', 'ZIP 업로드 완료', 
          `${extractedFiles.length}개 파일이 압축 해제되었습니다.`);
        
        // 업로드 완료 후 파일 목록 새로고침
        await this.loadUploadedFiles();
      } else {
        throw new Error(result.error || 'ZIP 처리 실패');
      }
  
    } catch (error) {
      console.error('ZIP 처리 실패:', error);
      window.toast?.show('error', 'ZIP 처리 실패', error.message);
    }
  
    this.updateEmptyState();
  }

  validateFile(file) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];

    if (file.size > maxSize) {
      return false;
    }

    if (!allowedTypes.includes(file.type)) {
      return false;
    }

    return true;
  }

  getFileHash(file) {
    return `${file.name}_${file.size}`;
  }

  createFileRow(file) {
    const id = `file_${++this.fileCounter}`;
    return {
      id,
      name: file.name,
      size: file.size,
      projectId: null,
      status: 'pending',
      selected: false,
      hash: this.getFileHash(file),
      file
    };
  }

  // ================================================== //
  // 테이블 관리
  // ================================================== //
  fillEmptyRow(fileRow) {
    this.fileRows.set(fileRow.id, fileRow);
    
    // 빈 행을 찾아서 채우기
    const emptyRow = document.querySelector('.empty-row');
    if (emptyRow) {
      this.convertEmptyRowToFileRow(emptyRow, fileRow);
    } else {
      // 빈 행이 없으면 새로운 행을 생성
      this.createNewFileRow(fileRow);
    }
  }

  convertEmptyRowToFileRow(emptyRow, fileRow) {
    // 빈 행을 일반 행으로 변경
    emptyRow.classList.remove('empty-row');
    emptyRow.dataset.fileId = fileRow.id;
    emptyRow.innerHTML = this.getTableRowHTML(fileRow);
    this.attachRowEventListeners(emptyRow, fileRow);
  }

  createNewFileRow(fileRow) {
    const tbody = document.getElementById('file-rows');
    if (!tbody) return;

    // 새로운 행 생성
    const newRow = document.createElement('tr');
    newRow.dataset.fileId = fileRow.id;
    newRow.innerHTML = this.getTableRowHTML(fileRow);
    
    // tbody에 추가
    tbody.appendChild(newRow);
    
    // 이벤트 리스너 연결
    this.attachRowEventListeners(newRow, fileRow);
  }

  getTableRowHTML(fileRow) {
    const projectOptions = Array.from(this.projects.values())
      .map(p => `<option value="${p.id}" ${p.id === fileRow.projectId ? 'selected' : ''}>${p.name}</option>`)
      .join('');

    const rowNumber = Array.from(this.fileRows.keys()).indexOf(fileRow.id) + 1;

    return `
      <td>
        <input type="checkbox" class="row-checkbox" ${fileRow.selected ? 'checked' : ''} 
               aria-label="${fileRow.name} 선택" />
      </td>
      <td>${rowNumber}</td>
      <td>
        <span class="file-name" title="${fileRow.name}">${fileRow.name}</span>
      </td>
      <td>
        <select class="project-select">
          <option value="">N/A</option>
          ${projectOptions}
        </select>
      </td>
      <td class="status-cell">
        ${this.getStatusHTML(fileRow.status, 'pending')}
      </td>
      <td class="delete-cell">
        <svg class="delete-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 6H5H21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M8 6V4C8 3.46957 8.21071 2.96086 8.58579 2.58579C8.96086 2.21071 9.46957 2 10 2H14C14.5304 2 15.0391 2.21071 15.4142 2.58579C15.7893 2.96086 16 3.46957 16 4V6M19 6V20C19 20.5304 18.7893 21.0391 18.4142 21.4142C18.0391 21.7893 17.5304 22 17 22H7C6.46957 22 5.96086 21.7893 5.58579 21.4142C5.21071 21.0391 5 20.5304 5 20V6H19Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M10 11V17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M14 11V17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </td>
    `;
  }

  attachRowEventListeners(row, fileRow) {
    // 체크박스
    const checkbox = row.querySelector('.row-checkbox');
    checkbox?.addEventListener('change', (e) => {
      fileRow.selected = e.target.checked;
      if (e.target.checked) {
        this.selectedFiles.add(fileRow.id);
      } else {
        this.selectedFiles.delete(fileRow.id);
      }
      this.updateSelectionState();
    });

    // 프로젝트 선택
    const projectSelect = row.querySelector('.project-select');
    projectSelect?.addEventListener('change', (e) => {
      fileRow.projectId = e.target.value || null;
    });

    // 삭제 아이콘
    const deleteIcon = row.querySelector('.delete-icon');
    deleteIcon?.addEventListener('click', () => {
      this.deleteFile(fileRow.id);
    });
  }

  deleteFile(fileId) {
    const fileRow = this.fileRows.get(fileId);
    if (!fileRow) return;

    const row = document.querySelector(`tr[data-file-id="${fileId}"]`);
    if (row) {
      // 행을 완전히 제거
      row.remove();
      
      this.fileRows.delete(fileId);
      this.selectedFiles.delete(fileId);
      this.uploadQueue.delete(fileId);
      
      this.updateSelectionState();
      this.renumberFiles();
    }
  }



  renumberFiles() {
    // 모든 파일 행 넘버링
    const fileRows = document.querySelectorAll('#file-rows tr[data-file-id]');
    fileRows.forEach((row, index) => {
      const numberCell = row.children[1];
      if (numberCell) {
        numberCell.textContent = index + 1;
      }
    });
  }

  // ================================================== //
  // 선택 관리
  // ================================================== //
  handleSelectAll(checked) {
    this.fileRows.forEach(fileRow => {
      fileRow.selected = checked;
      if (checked) {
        this.selectedFiles.add(fileRow.id);
      } else {
        this.selectedFiles.delete(fileRow.id);
      }
    });

    // DOM 업데이트
    document.querySelectorAll('.row-checkbox').forEach(checkbox => {
      checkbox.checked = checked;
    });

    this.updateSelectionState();
  }

  updateSelectionState() {
    const selectedCount = this.selectedFiles.size;
    const totalCount = this.fileRows.size;
    
    // 선택 카운트 업데이트
    const selectedCountEl = document.getElementById('selected-count');
    if (selectedCountEl) {
      selectedCountEl.textContent = `${selectedCount}개 선택됨`;
    }

    // 전체 선택 체크박스 상태 및 활성화
    const selectAll = document.getElementById('select-all');
    if (selectAll) {
      selectAll.disabled = totalCount === 0;
      selectAll.checked = selectedCount === totalCount && totalCount > 0;
      selectAll.indeterminate = selectedCount > 0 && selectedCount < totalCount;
    }

    // 일괄 수정 버튼 활성화
    const bulkBtn = document.getElementById('btn-bulk-project');
    if (bulkBtn) {
      bulkBtn.disabled = selectedCount === 0;
    }
  }

  updateEmptyState() {
    // 테이블은 항상 표시
    const tableContainer = document.querySelector('.table-container');
    if (tableContainer) {
      tableContainer.removeAttribute('hidden');
    }
  }

    // 업로드 미리보기 업데이트
  updateUploadPreview() {
    const uploadBox = document.querySelector('[data-testid="upload-dropzone"]');
    if (!uploadBox) return;

    if (this.tempSelectedFiles && this.tempSelectedFiles.length > 0) {
      // 파일이 선택된 경우: 기존 요소들을 숨기고 파일 목록만 표시
      this.hideInitialUploadElements(uploadBox);
      this.showFilePreview(uploadBox, this.tempSelectedFiles);
      
    } else if (this.tempSelectedZip) {
      // ZIP 파일이 선택된 경우: 기존 요소들을 숨기고 ZIP 파일 정보만 표시
      this.hideInitialUploadElements(uploadBox);
      this.showZipPreview(uploadBox, this.tempSelectedZip);
      
    } else {
      // 기본 상태: 모든 초기 요소들을 다시 표시
      this.showInitialUploadElements(uploadBox);
    }
  }

  // 초기 업로드 요소들을 숨기기
  hideInitialUploadElements(uploadBox) {
    const uploadIcon = uploadBox.querySelector('.upload-icon');
    const uploadMent = uploadBox.querySelector('.upload-ment');
    const uploadInstructions = uploadBox.querySelector('.upload-instructions');
    
    if (uploadIcon) uploadIcon.style.display = 'none';
    if (uploadMent) uploadMent.style.display = 'none';
    if (uploadInstructions) uploadInstructions.style.display = 'none';
  }

  // 초기 업로드 요소들을 다시 표시
  showInitialUploadElements(uploadBox) {
    const uploadIcon = uploadBox.querySelector('.upload-icon');
    const uploadMent = uploadBox.querySelector('.upload-ment');
    const uploadInstructions = uploadBox.querySelector('.upload-instructions');
    
    if (uploadIcon) uploadIcon.style.display = 'block';
    if (uploadMent) uploadMent.style.display = 'block';
    if (uploadInstructions) uploadInstructions.style.display = 'block';
    
    // 기존 파일 미리보기 제거
    const existingPreview = uploadBox.querySelector('.upload-preview-container');
    if (existingPreview) {
      existingPreview.remove();
    }
  }

  // 파일 미리보기 표시
  showFilePreview(uploadBox, files) {
    // 기존 파일 미리보기 제거
    const existingPreview = uploadBox.querySelector('.upload-preview-container');
    if (existingPreview) {
      existingPreview.remove();
    }

    const previewContainer = document.createElement('div');
    previewContainer.className = 'upload-preview-container';
    
    previewContainer.innerHTML = `
      <div class="upload-preview-header">
        ${files.length}개 파일 선택됨
      </div>
      <div class="upload-preview-files">
        ${files.map((file, index) => `
          <div class="upload-preview-file-item">
            <span class="upload-preview-file-name">${index + 1}. ${file.name}</span>
          </div>
        `).join('')}
      </div>
    `;
    
    uploadBox.appendChild(previewContainer);
  }

  // ZIP 파일 미리보기 표시
  showZipPreview(uploadBox, zipFile) {
    // 기존 파일 미리보기 제거
    const existingPreview = uploadBox.querySelector('.upload-preview-container');
    if (existingPreview) {
      existingPreview.remove();
    }

    const previewContainer = document.createElement('div');
    previewContainer.className = 'upload-preview-container';
    
    previewContainer.innerHTML = `
      <div class="upload-preview-header">
        ZIP 파일 선택됨
      </div>
      <div class="upload-preview-files">
        <span class="upload-preview-file-name">${zipFile.name}</span>
      </div>
      <div class="upload-preview-instruction">
        아래 <strong>ZIP 파일 업로드</strong> 버튼을 클릭하세요
      </div>
    `;
    
    uploadBox.appendChild(previewContainer);
  }

  // ================================================== //
// 상태 관리
// ================================================== //
updateRowStatus(fileId, status, message = '') {
  const row = document.querySelector(`tr[data-file-id="${fileId}"]`);
  if (!row) return;
  
  const statusCell = row.querySelector('.status-cell');
  if (statusCell) {
    statusCell.innerHTML = this.getStatusHTML(status, message);
  }
}

getStatusHTML(status, message) {
  const statusConfig = {
    'pending': { icon: '⏳', text: '대기 중', class: 'status-pending' },
    'uploading': { icon: '📤', text: '업로드 중', class: 'status-uploading' },
    'processing': { icon: '🔄', text: message || '처리 중', class: 'status-processing' },
    'completed': { icon: '✅', text: '완료', class: 'status-completed' },
    'failed': { icon: '❌', text: message || '실패', class: 'status-failed' }
  };
  
  const config = statusConfig[status] || statusConfig.pending;
  return `<span class="${config.class}">${config.icon} ${config.text}</span>`;
}

  // ================================================== //
  // 프로젝트 관리
  // ================================================== //
  async loadProjects() {
    try {
      // 실제 구현에서는 GET /projects API 호출
      const mockProjects = [
        { id: 'proj_1', name: '루미 (HUNTRIX)' },
        { id: 'proj_2', name: '미라 (HUNTRIX)' },
        { id: 'proj_3', name: '조이 (HUNTRIX)' },
        { id: 'proj_4', name: '진우 (SajaBoys)' },
        { id: 'proj_5', name: '베이비 (SajaBoys)' },
        { id: 'proj_6', name: '미스터리 (SajaBoys)' },
        { id: 'proj_7', name: '로맨스 (SajaBoys)' },
        { id: 'proj_8', name: '애비 (SajaBoys)' },
        { id: 'proj_9', name: 'HUNTRIX 유닛 프로젝트' },
        { id: 'proj_10', name: 'SajaBoys 유닛 프로젝트' }
      ];

      // 상태에 저장
      mockProjects.forEach(project => {
        this.projects.set(project.id, project);
      });

      // 모달 셀렉트 박스 업데이트
      this.updateModalProjectOptions();
      
      console.log('📋 Projects loaded:', mockProjects.length);
      
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  }

  updateModalProjectOptions() {
    const select = document.getElementById('bulk-project-select');
    if (!select) return;

    select.innerHTML = `
      <option value="">N/A</option>
      ${Array.from(this.projects.values())
        .map(p => `<option value="${p.id}">${p.name}</option>`)
        .join('')}
    `;
  }

  // ================================================== //
  // 일괄 수정 모달
  // ================================================== //
  openBulkProjectModal() {
    const selectedCount = this.selectedFiles.size;
    if (selectedCount === 0) {
      return;
    }

    const modal = document.getElementById('modal-bulk-project');
    const countSpan = document.getElementById('bulk-selected-count');
    const confirmBtn = document.getElementById('bulk-confirm');
    const projectSelect = document.getElementById('bulk-project-select');

    if (countSpan) countSpan.textContent = selectedCount;
    if (confirmBtn) confirmBtn.disabled = true;
    if (projectSelect) projectSelect.value = '';

    window.ModalManager.show(modal);
    
    // 포커스를 select로 이동
    setTimeout(() => projectSelect?.focus(), 100);
  }

  closeBulkProjectModal() {
    const modal = document.getElementById('modal-bulk-project');
    window.ModalManager.hide(modal);
    
    // 포커스를 트리거 버튼으로 복귀
    setTimeout(() => {
      document.getElementById('btn-bulk-project')?.focus();
    }, 100);
  }

  async confirmBulkProject() {
    const projectSelect = document.getElementById('bulk-project-select');
    const selectedProjectId = projectSelect?.value;
    
    if (!selectedProjectId) return;
  
    try {
      const workspaceName = this.getWorkspaceNameFromURL();
      
      // 선택된 파일들의 매핑 객체 생성
      const mapping = {};
      this.selectedFiles.forEach(fileId => {
        const fileRow = this.fileRows.get(fileId);
        if (fileRow && fileRow.serverId) {
          mapping[fileRow.serverId] = selectedProjectId;
        }
      });
  
      const baseUrl = getBaseUrl();
      const response = await fetch(`${baseUrl}/workspaces/${encodeURIComponent(workspaceName)}/uploads/projects`, {
        method: 'PATCH',
        headers: this.apiHeaders,
        body: JSON.stringify({ mapping })
      });
  
      if (!response.ok) {
        throw new Error(`프로젝트 설정 실패: ${response.statusText}`);
      }
  
      const result = await response.json();
      
      if (result.ok) {
        // UI 업데이트
        const selectedProject = this.projects.get(selectedProjectId);
        let updatedCount = 0;
        
        this.selectedFiles.forEach(fileId => {
          const fileRow = this.fileRows.get(fileId);
          if (fileRow) {
            fileRow.projectId = selectedProjectId;
            
            const row = document.querySelector(`tr[data-file-id="${fileId}"]`);
            const projectSelectInRow = row?.querySelector('.project-select');
            if (projectSelectInRow) {
              projectSelectInRow.value = selectedProjectId;
            }
            
            updatedCount++;
          }
        });
  
        window.toast?.show('success', '프로젝트 설정 완료', 
          `${updatedCount}개 파일의 프로젝트가 "${selectedProject.name}"으로 설정되었습니다.`);
      } else {
        throw new Error(result.error || '프로젝트 설정 실패');
      }
  
    } catch (error) {
      console.error('프로젝트 설정 실패:', error);
      window.toast?.show('error', '프로젝트 설정 실패', error.message);
    }
  
    this.closeBulkProjectModal();
  }

  // ================================================== //
  // 사이드바 네비게이션
  // ================================================== //
  handleSidebarNavigation(href, clickedLink) {
    document.querySelectorAll('.workspace-sidebar .sidebar-link').forEach(link => {
      link.classList.remove('active');
    });
    clickedLink.classList.add('active');

    const targetSection = document.querySelector(href);
    if (targetSection) {
      targetSection.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    } 
  }

  setupScrollSpy() {
    const sections = document.querySelectorAll('.content-section');
    const sidebarLinks = document.querySelectorAll('.sidebar-link');

    const observerOptions = {
      root: null,
      rootMargin: '-20% 0px -70% 0px',
      threshold: 0
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const sectionId = entry.target.id;
          
          sidebarLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${sectionId}`) {
              link.classList.add('active');
            }
          });
        }
      });
    }, observerOptions);

    sections.forEach(section => {
      observer.observe(section);
    });
  }

  handleResize() {
    // 모바일에서 사이드바 처리
    if (this.isMobile) {
      const sidebar = document.querySelector('.workspace-sidebar');
      if (sidebar) {
        sidebar.style.display = 'none';
      }
    }
  }

  // ================================================== //
  // URL 파라미터에서 Workspace 정보 로드
  // ================================================== //
  loadWorkspaceFromURL() {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const workspaceId = urlParams.get('id');
      const workspaceTitle = urlParams.get('title');

      if (workspaceTitle) {
        // Workspace 제목 표시
        this.displayWorkspaceTitle(workspaceTitle);
        
        // 생성일 설정 (현재 날짜)
        const currentDate = new Date().toLocaleDateString('ko-KR', {
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        });
        
        const createdDateElement = document.getElementById('workspace-created-date');
        if (createdDateElement) {
          createdDateElement.textContent = `생성일: ${currentDate}`;
        }

        console.log(`✅ Workspace 로드됨: ${workspaceTitle} (ID: ${workspaceId})`);
      } else {
        console.log('⚠️ URL에 Workspace 정보가 없습니다.');
      }
    } catch (error) {
      console.error('❌ Workspace 정보 로드 실패:', error);
    }
  }

  displayWorkspaceTitle(title) {
    const titleDisplay = document.getElementById('workspace-title-display');
    const titleText = document.getElementById('workspace-title-text');
    
    if (titleDisplay && titleText) {
      titleText.textContent = title;
      titleDisplay.style.display = 'block';
    }
  }

  // ================================================== //
  // 분개 생성 함수
  // ================================================== //
  
  async generateJournal() {
    try {
      const workspaceName = this.getWorkspaceNameFromURL();
      
      if (!workspaceName) {
        throw new Error('워크스페이스 정보를 찾을 수 없습니다.');
      }
  
      console.log('🔄 분개 생성 시작...', workspaceName);
      window.toast?.show('info', 'OCR 처리 중', '업로드된 이미지들을 OCR 처리하고 분개를 생성 중입니다...');
      
      const baseUrl = getBaseUrl();
      const response = await fetch(`${baseUrl}/workspaces/${workspaceName}/pipeline/ocr-journal`, {
        method: 'POST',
        headers: this.apiHeaders
      });
  
      if (!response.ok) {
        throw new Error(`OCR 처리 실패: ${response.statusText}`);
      }
  
      const result = await response.json();
      
      if (result.ok) {
        const journalEntries = result.data?.journal || [];
        console.log('✅ 분개 생성 완료:', journalEntries);
        
        window.toast?.show('success', '분개 생성 완료', 
          `${journalEntries.length}개의 분개가 성공적으로 생성되었습니다.`);
        
        return journalEntries;
      } else {
        throw new Error(result.error || 'OCR 처리 실패');
      }
      
    } catch (error) {
      console.error('❌ 분개 생성 실패:', error);
      
      let errorMessage = error.message || '알 수 없는 오류가 발생했습니다.';
      if (error.status === 500) {
        errorMessage = '서버에서 오류가 발생했습니다. 업로드된 파일이 있는지 확인해주세요.';
      }
      
      window.toast?.show('error', '분개 생성 실패', errorMessage);
      throw error;
    }
  }

  // ================================================== //
  // 업로드된 파일 목록 로드
  // ================================================== //
  
  async loadUploadedFiles() {
    try {
      const workspaceName = this.getWorkspaceNameFromURL();
      if (!workspaceName) {
        console.warn('워크스페이스 이름을 찾을 수 없습니다.');
        return;
      }

      console.log('📂 업로드된 파일 목록 로드 중...');
      
      const baseUrl = getBaseUrl();
      const response = await fetch(`${baseUrl}/workspaces/${encodeURIComponent(workspaceName)}/uploads`);
      
      if (!response.ok) {
        throw new Error(`파일 목록 로드 실패: ${response.statusText}`);
      }
      
      const result = await response.json();
      
      if (result.ok && result.data) {
        console.log('📂 로드된 파일 목록:', result.data);
        
        // 기존 테이블 초기화
        this.clearFileTable();
        
        // 새로운 파일들로 테이블 채우기
        const uploadedFiles = result.data.files || [];
        uploadedFiles.forEach(fileInfo => {
          const fileRow = this.createFileRowFromServer(fileInfo);
          this.fillEmptyRow(fileRow);
        });
        
        console.log(`✅ ${uploadedFiles.length}개 파일 로드 완료`);
      } else {
        throw new Error(result.error || '파일 목록 로드 실패');
      }
      
    } catch (error) {
      console.error('❌ 파일 목록 로드 실패:', error);
      // 에러가 발생해도 사용자에게는 알리지 않음 (백그라운드 작업)
    }
  }

  // 서버에서 받은 파일 정보로 fileRow 생성
  createFileRowFromServer(fileInfo) {
    // Windows 경로 구분자 \와 Unix 경로 구분자 / 모두 처리
    let fileName = 'Unknown';
    if (fileInfo.name) {
      fileName = fileInfo.name;
    } else if (fileInfo.rel) {
      // Windows 경로(\\)와 Unix 경로(/) 모두 처리
      const pathParts = fileInfo.rel.split(/[\\\/]/);
      fileName = pathParts[pathParts.length - 1]; // 마지막 부분이 파일명
    }
    
    return {
      id: `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: fileName,
      size: fileInfo.size || 0,
      type: fileInfo.mime || 'application/octet-stream',
      status: 'completed',
      serverId: fileInfo.rel,
      project: fileInfo.project || null,
      excluded: fileInfo.excluded || false
    };
  }

  // 파일 테이블 초기화
  clearFileTable() {
    this.fileRows.clear();
    
    // 테이블의 모든 파일 행 제거 (헤더는 유지)
    const fileTable = document.querySelector('.file-table tbody');
    if (fileTable) {
      const rows = fileTable.querySelectorAll('tr:not(.empty-row)');
      rows.forEach(row => row.remove());
    }
  }

  // URL에서 워크스페이스 이름 추출
  getWorkspaceNameFromURL() {
    const urlParams = new URLSearchParams(window.location.search);
    
    // 1순위: id 파라미터 (가장 정확)
    let workspaceName = urlParams.get('id');
    
    // 2순위: workspace 파라미터
    if (!workspaceName) {
      workspaceName = urlParams.get('workspace');
    }
    
    // 3순위: title 파라미터
    if (!workspaceName) {
      workspaceName = urlParams.get('title');
    }
    
    // 4순위: URL 경로에서 추출
    if (!workspaceName) {
      const pathParts = window.location.pathname.split('/');
      const workspaceIndex = pathParts.indexOf('workspace');
      if (workspaceIndex !== -1 && pathParts[workspaceIndex + 1]) {
        workspaceName = pathParts[workspaceIndex + 1];
      }
    }
    
    // 5순위: DOM에서 제목 추출
    if (!workspaceName) {
      const titleElement = document.getElementById('workspace-title-text');
      if (titleElement && titleElement.textContent) {
        workspaceName = titleElement.textContent.trim();
      }
    }
    
    console.log('🔍 추출된 워크스페이스 이름:', workspaceName);
    return workspaceName;
  }
}

// ================================================== //
// 앱 초기화
// ================================================== //
document.addEventListener('DOMContentLoaded', () => {
  window.workspaceManager = new WorkspaceManager();
});
