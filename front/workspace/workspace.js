// ================================================== //
// Workspace Manager - 파일 업로드 및 분개 생성
// ================================================== //

class WorkspaceManager {
  constructor() {
    this.isMobile = window.innerWidth <= 768;
    this.fileRows = new Map(); // file ID -> fileRow object
    this.projects = new Map(); // project ID -> project object
    this.selectedFiles = new Set(); // selected file IDs
    this.fileCounter = 0;
    this.uploadQueue = new Map(); // file ID -> upload promise
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupScrollSpy();
    this.setupUploadHandlers();
    this.setupTableHandlers();
    this.setupModalHandlers();
    this.loadProjects();
    
    this.updateEmptyState();
    
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

    // 버튼 클릭
    btnUploadImages?.addEventListener('click', () => fileInput.click());
    btnUploadZip?.addEventListener('click', () => zipInput.click());

    // 파일 선택
    fileInput.addEventListener('change', (e) => {
      this.handleFileSelect(Array.from(e.target.files));
      e.target.value = ''; // 리셋
    });

    zipInput?.addEventListener('change', (e) => {
      this.handleZipSelect(Array.from(e.target.files));
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
      this.handleFileSelect(files);
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
  handleFileSelect(files) {
    const validFiles = files.filter(file => this.validateFile(file));
    
    if (validFiles.length === 0) return;

    // 중복 방지 (name + size 해시)
    const uniqueFiles = validFiles.filter(file => {
      const hash = this.getFileHash(file);
      return !Array.from(this.fileRows.values()).some(row => row.hash === hash);
    });

    if (uniqueFiles.length === 0) {
      window.toast.show('warning', '중복 파일', '선택한 파일들이 이미 업로드되어 있습니다.');
      return;
    }

    // 파일별로 테이블 행 추가 및 업로드 시작
    uniqueFiles.forEach(file => {
      const fileRow = this.createFileRow(file);
      this.fillEmptyRow(fileRow);
      this.startUpload(fileRow);
    });

    this.updateEmptyState();
    window.toast.show('info', '업로드 시작', `${uniqueFiles.length}개 파일 업로드를 시작합니다.`);
  }

  handleZipSelect(files) {
    if (files.length === 0) return;
    
    const zipFile = files[0];
    if (!zipFile.name.toLowerCase().endsWith('.zip')) {
      window.toast.show('error', '파일 형식 오류', 'ZIP 파일만 선택할 수 있습니다.');
      return;
    }

    window.toast.show('info', 'ZIP 처리', 'ZIP 파일을 분석 중입니다...');
    
    // 실제 구현에서는 백엔드 API 호출
    setTimeout(() => {
      // 모의 ZIP 해제 결과
      const mockExtractedFiles = [
        { name: 'receipt_001.jpg', size: 234567 },
        { name: 'receipt_002.png', size: 345678 },
        { name: 'invoice_001.pdf', size: 456789 }
      ];

      mockExtractedFiles.forEach(fileData => {
        const mockFile = new File([''], fileData.name, { type: 'image/jpeg' });
        Object.defineProperty(mockFile, 'size', { value: fileData.size });
        
        const fileRow = this.createFileRow(mockFile);
        this.fillEmptyRow(fileRow);
        this.startUpload(fileRow);
      });

      this.updateEmptyState();
      window.toast.show('success', 'ZIP 해제 완료', `${mockExtractedFiles.length}개 파일이 추출되었습니다.`);
    }, 2000);
  }

  validateFile(file) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = ['image/jpeg', 'image/png', 'application/pdf'];

    if (file.size > maxSize) {
      window.toast.show('error', '파일 크기 오류', `${file.name}은 크기가 너무 큽니다. (최대 10MB)`);
      return false;
    }

    if (!allowedTypes.includes(file.type)) {
      window.toast.show('error', '파일 형식 오류', `${file.name}은 지원되지 않는 형식입니다.`);
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
    }
  }

  convertEmptyRowToFileRow(emptyRow, fileRow) {
    // 빈 행을 일반 행으로 변경
    emptyRow.classList.remove('empty-row');
    emptyRow.dataset.fileId = fileRow.id;
    emptyRow.innerHTML = this.getTableRowHTML(fileRow);
    this.attachRowEventListeners(emptyRow, fileRow);
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
          <option value="">프로젝트 선택</option>
          ${projectOptions}
        </select>
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
      // 행을 빈 행으로 되돌리기
      this.convertToEmptyRow(row);
      
      this.fileRows.delete(fileId);
      this.selectedFiles.delete(fileId);
      this.uploadQueue.delete(fileId);
      
      this.updateSelectionState();
      this.renumberFiles();
      
      window.toast.show('success', '파일 삭제', `${fileRow.name}이 삭제되었습니다.`);
    }
  }

  convertToEmptyRow(row) {
    row.classList.add('empty-row');
    row.removeAttribute('data-file-id');
    row.innerHTML = `
      <td><input type="checkbox" disabled /></td>
      <td>-</td>
      <td class="empty-cell"></td>
      <td>
        <select class="project-select" disabled>
          <option>프로젝트 선택</option>
        </select>
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

  renumberFiles() {
    // 빈 행이 아닌 행들만 넘버링
    const fileRows = document.querySelectorAll('#file-rows tr:not(.empty-row)');
    fileRows.forEach((row, index) => {
      const numberCell = row.children[1];
      if (numberCell) {
        numberCell.textContent = index + 1;
      }
    });
    
    // 빈 행은 '-'로 유지
    const emptyRows = document.querySelectorAll('#file-rows tr.empty-row');
    emptyRows.forEach((row) => {
      const numberCell = row.children[1];
      if (numberCell) {
        numberCell.textContent = '-';
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

    // 전체 선택 체크박스 상태
    const selectAll = document.getElementById('select-all');
    if (selectAll) {
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
    // 빈 행을 사용하므로 테이블은 항상 표시
    const emptyState = document.getElementById('empty-table');
    const tableContainer = document.querySelector('.table-container');
    
    emptyState?.setAttribute('hidden', '');
    tableContainer?.removeAttribute('hidden');
  }

  // ================================================== //
  // 업로드 처리
  // ================================================== //
  async startUpload(fileRow) {
    try {
      fileRow.status = 'uploading';

      // 실제 구현에서는 FormData로 백엔드 API 호출
      const uploadPromise = this.simulateUpload(fileRow);
      this.uploadQueue.set(fileRow.id, uploadPromise);
      
      await uploadPromise;
      
      this.uploadQueue.delete(fileRow.id);
      window.toast.show('success', '업로드 완료', `${fileRow.name} 업로드가 완료되었습니다.`);
      
    } catch (error) {
      fileRow.status = 'failed';
      this.uploadQueue.delete(fileRow.id);
      
      window.toast.show('error', '업로드 실패', `${fileRow.name} 업로드에 실패했습니다.`);
    }
  }

  simulateUpload(fileRow) {
    return new Promise((resolve) => {
      // 1-3초 랜덤 지연으로 업로드 시뮬레이션
      const delay = 1000 + Math.random() * 2000;
      setTimeout(resolve, delay);
    });
  }

  // ================================================== //
  // 프로젝트 관리
  // ================================================== //
  async loadProjects() {
    try {
      // 실제 구현에서는 GET /projects API 호출
      const mockProjects = [
        { id: 'proj_1', name: '2025_Q1_엔터테인먼트', code: 'P-001' },
        { id: 'proj_2', name: '2025_Q1_광고비', code: 'P-002' },
        { id: 'proj_3', name: '2025_사무용품', code: 'P-003' },
        { id: 'proj_4', name: '2025_마케팅', code: 'P-004' },
        { id: 'proj_5', name: '2025_법무비용', code: 'P-005' }
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
      window.toast.show('error', '프로젝트 로딩 실패', '프로젝트 목록을 불러오지 못했습니다. 다시 시도해주세요.');
    }
  }

  updateModalProjectOptions() {
    const select = document.getElementById('bulk-project-select');
    if (!select) return;

    select.innerHTML = Array.from(this.projects.values())
      .map(p => `<option value="${p.id}">${p.name} (${p.code})</option>`)
      .join('');
  }

  // ================================================== //
  // 일괄 수정 모달
  // ================================================== //
  openBulkProjectModal() {
    const selectedCount = this.selectedFiles.size;
    if (selectedCount === 0) {
      window.toast.show('warning', '선택 필요', '수정할 파일을 먼저 선택해주세요.');
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

  confirmBulkProject() {
    const projectSelect = document.getElementById('bulk-project-select');
    const selectedProjectId = projectSelect?.value;
    
    if (!selectedProjectId) return;

    const selectedProject = this.projects.get(selectedProjectId);
    if (!selectedProject) return;

    // 선택된 파일들의 프로젝트 업데이트
    let updatedCount = 0;
    this.selectedFiles.forEach(fileId => {
      const fileRow = this.fileRows.get(fileId);
      if (fileRow) {
        fileRow.projectId = selectedProjectId;
        
        // DOM 업데이트
        const row = document.querySelector(`tr[data-file-id="${fileId}"]`);
        const projectSelectInRow = row?.querySelector('.project-select');
        if (projectSelectInRow) {
          projectSelectInRow.value = selectedProjectId;
        }
        
        updatedCount++;
      }
    });

    this.closeBulkProjectModal();
    window.toast.show('success', '일괄 수정 완료', 
      `${updatedCount}개 파일의 프로젝트가 "${selectedProject.name}"(으)로 변경되었습니다.`);
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
}

// ================================================== //
// 앱 초기화
// ================================================== //
document.addEventListener('DOMContentLoaded', () => {
  window.workspaceManager = new WorkspaceManager();
});
