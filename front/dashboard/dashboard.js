// ================================================== //
// Dashboard Manager - 작업 기록 및 전표 미리보기
// ================================================== //

class DashboardManager {
  constructor() {
    this.selectedWorklogs = new Set();
    this.worklogs = [];
    this.journals = [];
    this.visibleColumns = new Set(['date', 'customer', 'amount', 'type', 'account', 'source']);
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupSidebarNavigation();
    this.loadWorklogs();
    this.updateURL();
    
    console.log('📊 Dashboard Manager initialized');
  }

  setupEventListeners() {
    // 검색 및 필터
    const searchInput = document.getElementById('worklog-search');
    const dateFrom = document.getElementById('date-from');
    const dateTo = document.getElementById('date-to');
    const sortOption = document.getElementById('sort-option');

    [searchInput, dateFrom, dateTo, sortOption].forEach(el => {
      if (el) {
        el.addEventListener('input', () => this.applyFilters());
      }
    });

    // 컬럼 토글 드롭다운
    const columnToggle = document.querySelector('[data-testid="column-toggle"]');
    if (columnToggle) {
      columnToggle.addEventListener('click', () => this.toggleColumnDropdown());
    }

    // 컬럼 체크박스
    document.querySelectorAll('#column-dropdown input[type="checkbox"]').forEach(checkbox => {
      checkbox.addEventListener('change', (e) => this.toggleColumn(e.target.value, e.target.checked));
    });

    // 다운로드 버튼
    const downloadCSV = document.getElementById('download-csv');
    const downloadExcel = document.getElementById('download-excel');
    
    if (downloadCSV) downloadCSV.addEventListener('click', () => this.downloadCSV());
    if (downloadExcel) downloadExcel.addEventListener('click', () => this.downloadExcel());

    // URL 변경 감지
    window.addEventListener('popstate', () => this.updateFromURL());

    // 드롭다운 외부 클릭 시 닫기
    document.addEventListener('click', (e) => {
      const dropdown = document.querySelector('.dropdown');
      if (dropdown && !dropdown.contains(e.target)) {
        dropdown.classList.remove('active');
      }
    });
  }

  setupSidebarNavigation() {
    // 사이드바 링크 (Dashboard)
    document.querySelectorAll('.dashboard-sidebar .sidebar-link').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const href = link.getAttribute('href');
        this.handleSidebarNavigation(href, link);
      });
    });
  }

  handleSidebarNavigation(href, clickedLink) {
    // 대시보드 사이드바 링크들의 active 상태 업데이트
    document.querySelectorAll('.dashboard-sidebar .sidebar-link').forEach(link => {
      link.classList.remove('active');
    });
    clickedLink.classList.add('active');

    // 섹션으로 스크롤
    const targetSection = document.querySelector(href);
    if (targetSection) {
      targetSection.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  }

  async loadWorklogs() {
    try {
      // Mock API 호출 - 실제로는 GET /worklogs
      const mockWorklogs = [
        {
          id: 'wl_2025_w34',
          title: '2025-W34',
          period: { from: '2025-08-18', to: '2025-08-24' },
          uploadCount: 15,
          journalCount: 12,
          updatedAt: '2025-08-24T15:30:00Z'
        },
        {
          id: 'wl_2025_w33',
          title: '2025-W33',
          period: { from: '2025-08-11', to: '2025-08-17' },
          uploadCount: 8,
          journalCount: 6,
          updatedAt: '2025-08-17T09:45:00Z'
        },
        {
          id: 'wl_2025_w32',
          title: '2025-W32',
          period: { from: '2025-08-04', to: '2025-08-10' },
          uploadCount: 22,
          journalCount: 18,
          updatedAt: '2025-08-10T14:20:00Z'
        }
      ];

      this.worklogs = mockWorklogs;
      this.renderWorklogGrid();
      this.updateFromURL();
      
    } catch (error) {
      console.error('Worklog 로딩 실패:', error);
      window.toast.show('error', '로딩 실패', 'Workspace 기록을 불러오지 못했습니다.');
      this.showEmptyState('worklog');
    }
  }

  renderWorklogGrid() {
    const grid = document.getElementById('worklog-grid');
    const empty = document.getElementById('worklog-empty');
    
    if (this.worklogs.length === 0) {
      grid.style.display = 'none';
      empty.style.display = 'block';
      return;
    }

    grid.style.display = 'grid';
    empty.style.display = 'none';
    
    grid.innerHTML = this.worklogs.map(worklog => this.createWorklogCard(worklog)).join('');
    
    // 카드 이벤트 리스너 추가
    this.attachWorklogCardListeners();
  }

  createWorklogCard(worklog) {
    const isSelected = this.selectedWorklogs.has(worklog.id);
    const updatedDate = new Date(worklog.updatedAt).toLocaleDateString('ko-KR');
    
    return `
      <div class="worklog-card ${isSelected ? 'selected' : ''}" 
           data-worklog-id="${worklog.id}" 
           data-testid="worklog-card"
           tabindex="0">
        <div class="worklog-card-header">
          <div>
            <div class="worklog-title">${worklog.title}</div>
            <div class="worklog-period">${worklog.period.from} ~ ${worklog.period.to}</div>
          </div>
          <input type="checkbox" class="worklog-checkbox" ${isSelected ? 'checked' : ''} />
        </div>
        
        <div class="worklog-stats">
          <div class="stat-item">
            <span class="stat-value">${worklog.uploadCount}</span>
            <span class="stat-label">업로드</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">${worklog.journalCount}</span>
            <span class="stat-label">분개</span>
          </div>
        </div>
        
        <div class="worklog-footer">
          <span class="worklog-updated">${updatedDate}</span>
          <button class="worklog-action">열기</button>
        </div>
      </div>
    `;
  }

  attachWorklogCardListeners() {
    document.querySelectorAll('.worklog-card').forEach(card => {
      const worklogId = card.dataset.worklogId;
      const checkbox = card.querySelector('.worklog-checkbox');
      const actionBtn = card.querySelector('.worklog-action');

      // 카드 클릭
      card.addEventListener('click', (e) => {
        if (e.target.type !== 'checkbox' && !e.target.classList.contains('worklog-action')) {
          this.toggleWorklogSelection(worklogId, !this.selectedWorklogs.has(worklogId));
        }
      });

      // 체크박스 변경
      checkbox.addEventListener('change', (e) => {
        e.stopPropagation();
        this.toggleWorklogSelection(worklogId, e.target.checked);
      });

      // 열기 버튼
      actionBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleWorklogSelection(worklogId, true);
      });

      // 키보드 접근성
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.toggleWorklogSelection(worklogId, !this.selectedWorklogs.has(worklogId));
        }
      });
    });
  }

  toggleWorklogSelection(worklogId, selected) {
    if (selected) {
      this.selectedWorklogs.add(worklogId);
    } else {
      this.selectedWorklogs.delete(worklogId);
    }

    this.updateWorklogCards();
    this.updateSelectionInfo();
    this.loadJournals();
    this.updateURL();
  }

  updateWorklogCards() {
    document.querySelectorAll('.worklog-card').forEach(card => {
      const worklogId = card.dataset.worklogId;
      const isSelected = this.selectedWorklogs.has(worklogId);
      
      card.classList.toggle('selected', isSelected);
      const checkbox = card.querySelector('.worklog-checkbox');
      if (checkbox) checkbox.checked = isSelected;
    });
  }

  updateSelectionInfo() {
    const selectionInfo = document.getElementById('selection-info');
    const selectionBadge = document.querySelector('[data-testid="selection-badge"]');
    
    if (this.selectedWorklogs.size > 0) {
      selectionInfo.style.display = 'block';
      selectionBadge.textContent = `${this.selectedWorklogs.size}개 선택됨`;
    } else {
      selectionInfo.style.display = 'none';
    }
  }

  async loadJournals() {
    if (this.selectedWorklogs.size === 0) {
      this.showEmptyJournalState();
      return;
    }

    try {
      // Mock API 호출 - 실제로는 GET /journals?worklog_ids=a,b,c
      const mockJournals = [
        {
          id: 'j1',
          worklogId: 'wl_2025_w34',
          date: '2025-08-20',
          customer: '카페베네',
          amount: 15000,
          type: '지출',
          account: '복리후생비',
          artist: '김아티스트',
          memo: '직원 간식',
          sourceFile: 'receipt_001.jpg'
        },
        {
          id: 'j2', 
          worklogId: 'wl_2025_w34',
          date: '2025-08-21',
          customer: '서울택시',
          amount: 8500,
          type: '지출',
          account: '차량비',
          artist: '이아티스트',
          memo: '업무용 택시',
          sourceFile: 'receipt_002.jpg'
        },
        {
          id: 'j3',
          worklogId: 'wl_2025_w33',
          date: '2025-08-15',
          customer: '스타벅스',
          amount: 12000,
          type: '지출',
          account: '복리후생비',
          artist: '박아티스트',
          memo: '회의용 음료',
          sourceFile: 'receipt_003.jpg'
        }
      ];

      this.journals = mockJournals.filter(j => this.selectedWorklogs.has(j.worklogId));
      this.renderJournalTable();
      this.renderSelectedWorklogBadges();
      
    } catch (error) {
      console.error('Journal 로딩 실패:', error);
      window.toast.show('error', '로딩 실패', '분개 데이터를 불러오지 못했습니다.');
    }
  }

  renderSelectedWorklogBadges() {
    const container = document.getElementById('selected-worklogs');
    const selectedWorklogData = this.worklogs.filter(w => this.selectedWorklogs.has(w.id));
    
    container.innerHTML = selectedWorklogData.map(worklog => `
      <div class="worklog-badge">
        <span>${worklog.title}</span>
        <span class="worklog-badge-close" data-worklog-id="${worklog.id}">×</span>
      </div>
    `).join('');

    // 뱃지 닫기 이벤트
    container.querySelectorAll('.worklog-badge-close').forEach(closeBtn => {
      closeBtn.addEventListener('click', () => {
        const worklogId = closeBtn.dataset.worklogId;
        this.toggleWorklogSelection(worklogId, false);
      });
    });
  }

  renderJournalTable() {
    const container = document.getElementById('journal-table-container');
    const summary = document.getElementById('journal-summary');
    const controls = document.getElementById('journal-controls');
    const empty = document.getElementById('journal-empty');
    
    if (this.journals.length === 0) {
      this.showEmptyJournalState();
      return;
    }

    // 테이블 표시
    container.style.display = 'block';
    summary.style.display = 'flex';
    controls.style.display = 'block';
    empty.style.display = 'none';

    // 테이블 내용 렌더링
    const tbody = document.getElementById('journal-agg-tbody');
    tbody.innerHTML = this.journals.map(journal => this.createJournalRow(journal)).join('');

    // 합계 업데이트
    this.updateJournalSummary();
    
    // 컬럼 표시/숨김 적용
    this.applyColumnVisibility();
  }

  createJournalRow(journal) {
    return `
      <tr data-journal-id="${journal.id}">
        <td data-column="date">${journal.date}</td>
        <td data-column="customer">${journal.customer}</td>
        <td data-column="amount">₩${journal.amount.toLocaleString()}</td>
        <td data-column="type">${journal.type}</td>
        <td data-column="account">${journal.account}</td>
        <td data-column="artist">${journal.artist || '-'}</td>
        <td data-column="memo">${journal.memo || '-'}</td>
        <td data-column="source">${journal.sourceFile}</td>
      </tr>
    `;
  }

  updateJournalSummary() {
    const totalCount = this.journals.length;
    const totalAmount = this.journals.reduce((sum, j) => sum + j.amount, 0);
    
    document.getElementById('total-count').textContent = totalCount;
    document.getElementById('total-amount').textContent = `₩${totalAmount.toLocaleString()}`;
  }

  showEmptyJournalState() {
    document.getElementById('journal-table-container').style.display = 'none';
    document.getElementById('journal-summary').style.display = 'none';
    document.getElementById('journal-controls').style.display = 'none';
    document.getElementById('journal-empty').style.display = 'block';
  }

  toggleColumn(column, visible) {
    if (visible) {
      this.visibleColumns.add(column);
    } else {
      this.visibleColumns.delete(column);
    }
    this.applyColumnVisibility();
  }

  applyColumnVisibility() {
    document.querySelectorAll('[data-column]').forEach(cell => {
      const column = cell.dataset.column;
      cell.style.display = this.visibleColumns.has(column) ? '' : 'none';
    });
  }

  toggleColumnDropdown() {
    const dropdown = document.querySelector('.dropdown');
    dropdown.classList.toggle('active');
  }

  downloadCSV() {
    const headers = Array.from(this.visibleColumns).map(col => {
      const columnMap = {
        date: '발생일',
        customer: '거래처',
        amount: '금액',
        type: '유형',
        account: '계정과목',
        artist: '아티스트',
        memo: '메모',
        source: '출처'
      };
      return columnMap[col] || col;
    });
    
    const rows = this.journals.map(journal => 
      Array.from(this.visibleColumns).map(col => {
        let value = journal[col] || '-';
        if (col === 'amount') {
          value = journal.amount;
        }
        return value;
      }).join(',')
    );
    
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `journal_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    window.toast.show('success', 'CSV 다운로드', '파일이 성공적으로 다운로드되었습니다.');
  }

  downloadExcel() {
    // CSV 다운로드로 대체 (실제 구현에서는 Excel 라이브러리 사용)
    this.downloadCSV();
  }

  applyFilters() {
    // 필터링 로직 (실제 구현에서는 API 호출)
    const searchValue = document.getElementById('worklog-search').value.toLowerCase();
    const dateFrom = document.getElementById('date-from').value;
    const dateTo = document.getElementById('date-to').value;
    const sortOption = document.getElementById('sort-option').value;

    let filteredWorklogs = [...this.worklogs];

    // 검색 필터
    if (searchValue) {
      filteredWorklogs = filteredWorklogs.filter(worklog => 
        worklog.title.toLowerCase().includes(searchValue)
      );
    }

    // 날짜 필터
    if (dateFrom) {
      filteredWorklogs = filteredWorklogs.filter(worklog => 
        worklog.period.from >= dateFrom
      );
    }
    if (dateTo) {
      filteredWorklogs = filteredWorklogs.filter(worklog => 
        worklog.period.to <= dateTo
      );
    }

    // 정렬
    switch (sortOption) {
      case 'uploads':
        filteredWorklogs.sort((a, b) => b.uploadCount - a.uploadCount);
        break;
      case 'journals':
        filteredWorklogs.sort((a, b) => b.journalCount - a.journalCount);
        break;
      case 'recent':
      default:
        filteredWorklogs.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
        break;
    }

    // 임시로 필터된 결과를 렌더링
    const grid = document.getElementById('worklog-grid');
    const empty = document.getElementById('worklog-empty');
    
    if (filteredWorklogs.length === 0) {
      grid.style.display = 'none';
      empty.style.display = 'block';
      empty.querySelector('h3').textContent = '검색 결과가 없습니다';
      empty.querySelector('p').textContent = '다른 키워드로 검색해보세요.';
    } else {
      grid.style.display = 'grid';
      empty.style.display = 'none';
      grid.innerHTML = filteredWorklogs.map(worklog => this.createWorklogCard(worklog)).join('');
      this.attachWorklogCardListeners();
    }
  }

  updateURL() {
    const url = new URL(window.location);
    if (this.selectedWorklogs.size > 0) {
      url.searchParams.set('worklogIds', Array.from(this.selectedWorklogs).join(','));
    } else {
      url.searchParams.delete('worklogIds');
    }
    
    window.history.replaceState({}, '', url);
  }

  updateFromURL() {
    const url = new URL(window.location);
    const worklogIds = url.searchParams.get('worklogIds');
    
    if (worklogIds) {
      this.selectedWorklogs = new Set(worklogIds.split(','));
      this.updateWorklogCards();
      this.updateSelectionInfo();
      this.loadJournals();
    }
  }

  showEmptyState(type) {
    if (type === 'worklog') {
      document.getElementById('worklog-grid').style.display = 'none';
      document.getElementById('worklog-empty').style.display = 'block';
    }
  }
}

// ================================================== //
// 앱 초기화
// ================================================== //
document.addEventListener('DOMContentLoaded', () => {
  window.dashboardManager = new DashboardManager();
});
