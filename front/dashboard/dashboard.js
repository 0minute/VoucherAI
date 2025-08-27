// ================================================== //
// Dashboard Manager - 작업 기록 및 전표 미리보기
// ================================================== //

class DashboardManager {
  constructor() {
    this.workspaces = [];
    this.journals = [];
    this.isExpanded = false;
    
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupSidebarNavigation();
    this.loadWorkspaces();
    
    console.log('📊 Dashboard Manager initialized');
  }

  setupEventListeners() {
    // Workspace 생성 버튼
    const createWorkspaceBtn = document.getElementById('create-workspace-btn');
    if (createWorkspaceBtn) {
      createWorkspaceBtn.addEventListener('click', () => this.showWorkspaceModal());
    }

    // Workspace 검색
    const workspaceSearch = document.getElementById('workspace-search');
    if (workspaceSearch) {
      workspaceSearch.addEventListener('input', () => this.applyWorkspaceFilters());
    }

    // 전표 미리보기 정렬 옵션
    const sortSelect = document.getElementById('sort-option');
    if (sortSelect) {
      sortSelect.addEventListener('change', () => this.applyJournalSort());
    }

    // 펼치기/접기 버튼
    const expandBtn = document.getElementById('expand-workspaces');
    const collapseBtn = document.getElementById('collapse-workspaces');
    if (expandBtn) {
      expandBtn.addEventListener('click', () => this.expandWorkspaces());
    }
    if (collapseBtn) {
      collapseBtn.addEventListener('click', () => this.collapseWorkspaces());
    }
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

  async loadWorkspaces() {
    try {
      // 로컬 스토리지 초기화하고 새로운 더미 데이터 강제 적용
      localStorage.removeItem('workspaces');
      
      // 기본 Workspace 데이터 생성 (첫 번째는 비우고, 나머지는 dummy data)
      this.workspaces = [
        {
          id: '',
          title: '',
          status: '',
          createdAt: ''
        },
        {
          id: 'ws_002',
          title: '2506 HUNTRIX 공연매출 정산',
          status: 'active',
          createdAt: '2025-07-05T00:00:00Z'
        },
        {
          id: 'ws_003',
          title: '2505 SajaBoys 스타일링 비용 정산',
          status: 'completed',
          createdAt: '2025-06-03T00:00:00Z'
        }
      ];
      localStorage.setItem('workspaces', JSON.stringify(this.workspaces));

      // 생성일 순으로 정렬 (최신순)
      this.workspaces.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      
      this.renderWorkspaceGrid();
      
      // 더미 분개 데이터 로드
      this.loadDummyJournals();
      
    } catch (error) {
      console.error('Workspace 로딩 실패:', error);
      window.toast.show('error', '로딩 실패', 'Workspace를 불러오지 못했습니다.');
      this.showEmptyState('workspace');
    }
  }



  renderWorkspaceGrid() {
    const grid = document.getElementById('workspace-grid');
    const empty = document.getElementById('workspace-empty');
    
    if (this.workspaces.length === 0) {
      grid.style.display = 'none';
      empty.style.display = 'block';
      return;
    }

    grid.style.display = 'grid';
    empty.style.display = 'none';
    
    // 펼치기/접기 상태에 따라 표시할 workspace 결정
    let displayWorkspaces = this.workspaces;
    if (!this.isExpanded && this.workspaces.length > 3) {
      displayWorkspaces = this.workspaces.slice(0, 3);
    }
    
    grid.innerHTML = displayWorkspaces.map(workspace => this.createWorkspaceCard(workspace)).join('');
    
    // 카드 이벤트 리스너 추가
    this.attachWorkspaceCardListeners();
    
    // 펼치기/접기 버튼 상태 업데이트
    this.updateExpandControls();
  }

  // 더미 분개 데이터 로드
  async loadDummyJournals() {
    try {
      // dashboard_dummy_transaction.json 파일 로드
      const response = await fetch('../common/dashboard_dummy_transaction.json');
      const dummyData = await response.json();
      
      this.journals = dummyData;
      this.renderJournalTable();
      
    } catch (error) {
      console.error('더미 분개 데이터 로딩 실패:', error);
      // 에러 발생 시 하드코딩된 데이터 사용
      this.loadHardcodedJournals();
    }
  }

  // 하드코딩된 분개 데이터 (JSON 파일 로드 실패 시 사용)
  loadHardcodedJournals() {
    this.journals = [
      {"날짜":"2025/01/15","번호":14,"계정코드":25301,"계정과목":"미지급금(일반)","차변":null,"대변":429000,"적요":"#HUNTRIX_미니 1집 JK 의상 수선비_25.01","거래처코드":"18761","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/15","번호":14,"계정코드":13500,"계정과목":"부가세대급금","차변":39000,"대변":null,"적요":"#HUNTRIX_미니 1집 JK 의상 수선비_25.01","거래처코드":"18761","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/15","번호":14,"계정코드":53801,"계정과목":"연예보조_의상ㆍ스타일링","차변":390000,"대변":null,"적요":"#HUNTRIX_미니 1집 JK 의상 수선비_25.01","거래처코드":"18761","거래처명":"DemonHunters","PJT":"H000000001","PJT7":"HUNTRIX"},
      {"날짜":"2025/01/21","번호":19,"계정코드":10800,"계정과목":"외상매출금","차변":3850000,"대변":null,"적요":"행사_#루미_HUNTRIX 쇼케이스 출연료","거래처코드":"10916","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/21","번호":19,"계정코드":25500,"계정과목":"부가세예수금","차변":null,"대변":350000,"적요":"행사_#루미_HUNTRIX 쇼케이스 출연료","거래처코드":"10916","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/21","번호":19,"계정코드":41305,"계정과목":"출연료매출_행사","차변":null,"대변":3500000,"적요":"행사_#루미_HUNTRIX 쇼케이스 출연료","거래처코드":"10916","거래처명":"DemonHunters","PJT":"LUMI0000001","PJT7":"루미"},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":300000,"대변":null,"적요":"SajaBoys#진우_서울 팬미팅 아트워크(바리에이션) 비용(예술인)","거래처코드":"71682","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":250000,"대변":null,"적요":"#조이_서울 팬미팅 아트워크(바리에이션) 비용(예술인)","거래처코드":"71682","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":13200000,"대변":null,"적요":"#SajaBoys_스타일링 인건비_24.12_(원천사업)","거래처코드":"71738","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":2750000,"대변":null,"적요":"#SajaBoys_스타일링 인건비_24.12_(원천사업)_JP","거래처코드":"71738","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일general)","차변":5000000,"대변":null,"적요":"#HUNTRIX_미니 1집 JK 스타일링비_(원천사업)","거래처코드":"72026","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":900000,"대변":null,"적요":"#SajaBoys,#HUNTRIX_MD 촬영 비하인드/언박싱 영상 편집 외주비_24.12_(원천사업)","거래처코드":"71996","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":500000,"대변":null,"적요":"#SajaBoys_페스티벌 비하인드 영상 편집 외주비_24.12_(원천사업)","거래처코드":"72022","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":1900000,"대변":null,"적요":"HUNTRIX#루미,SajaBoys#진우_비하인드 영상 편집 외주비_24.12_(원천사업)","거래처코드":"71998","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":1188000,"대변":null,"적요":"#HUNTRIX_미니1집 JK H버전 발전차 비용","거래처코드":"29895","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":1540000,"대변":null,"적요":"#HUNTRIX_미니1집 JK H버전 스튜디오 추가 대관 비용","거래처코드":"11435","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":4300000,"대변":null,"적요":"DemonHunters 협회 정기회비(연회비)","거래처코드":"11193","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":2102000,"대변":null,"적요":"SajaBoys#로맨스_피부클리닉 비용_25.01_(현금영수증)","거래처코드":"14634","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":220000,"대변":null,"적요":"#조이_연말 팬미팅 라이브 보컬 메인 튠비_JP","거래처코드":"16999","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":300000,"대변":null,"적요":"#조이_서울 팬미팅 '그대와 함께' INST 제작비","거래처코드":"16918","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/23","번호":13,"계정코드":25301,"계정과목":"미지급금(일반)","차변":800000,"대변":null,"적요":"HUNTRIX#미라_아티스트 숙소 지원비_25.01","거래처코드":"70357","거래처명":"DemonHunters","PJT":"","PJT7":""},
    
      {"날짜":"2025/01/31","번호":161,"계정코드":53801,"계정과목":"연예보조_의상ㆍ스타일링","차변":2000000,"대변":null,"적요":"#조이_1월 스타일리스트 비용(스케줄:영화 촬영)_JP","거래처코드":"29033","거래처명":"DemonHunters","PJT":"JOY0002","PJT7":"조이"},
      {"날짜":"2025/01/31","번호":161,"계정코드":53801,"계정과목":"연예보조_의상ㆍ스타일링","차변":300000,"대변":null,"적요":"#조이_1월 스타일리스트 비용(스케줄:드라마 촬영)","거래처코드":"29033","거래처명":"DemonHunters","PJT":"JOY0002","PJT7":"조이"},
      {"날짜":"2025/01/31","번호":161,"계정코드":53801,"계정과목":"연예보조_의상ㆍ스타일링","차변":1000000,"대변":null,"적요":"#조이_1월 스타일리스트 비용(스케줄:패션위크)","거래처코드":"29033","거래처명":"DemonHunters","PJT":"JOY0002","PJT7":"조이"},
      {"날짜":"2025/01/31","번호":161,"계정코드":53801,"계정과목":"연예보조_의상ㆍ스타일링","차변":26400,"대변":null,"적요":"#조이_1월 의상 세탁 비용","거래처코드":"29033","거래처명":"DemonHunters","PJT":"JOY0002","PJT7":"조이"},
      {"날짜":"2025/01/31","번호":161,"계정코드":13500,"계정과목":"부가세대급금","차변":332640,"대변":null,"적요":"#조이_1월 스타일리스트 비용","거래처코드":"29033","거래처명":"DemonHunters","PJT":"","PJT7":""},
      {"날짜":"2025/01/31","번호":161,"계정코드":25301,"계정과목":"미지급금(일반)","차변":null,"대변":3659040,"적요":"#조이_1월 스타일리스트 비용","거래처코드":"29033","거래처명":"DemonHunters","PJT":"","PJT7":""}
    ]
    ;
    
    this.renderJournalTable();
  }

  createWorkspaceCard(workspace) {
    // 빈 workspace인 경우 빈 카드 표시
    if (!workspace.title || !workspace.id) {
    return `
        <div class="workspace-card empty-workspace-card" 
             data-workspace-id="" 
             data-testid="workspace-card-empty"
           tabindex="0">
          <div class="workspace-card-header">
            <div class="workspace-title empty-title">새로운 Workspace를 생성해주세요</div>
            <div class="workspace-status empty-status">
              <i class="fas fa-plus"></i>
              대기중
          </div>
        </div>
        
          <div class="workspace-footer">
            <span class="workspace-created empty-created">생성일: -</span>
            <button class="workspace-action empty-action" disabled>생성 필요</button>
          </div>
          </div>
      `;
    }
    
    const createdAt = new Date(workspace.createdAt).toLocaleDateString('ko-KR');
    const statusText = workspace.status === 'active' ? '진행중' : '완료';
    const statusClass = workspace.status === 'active' ? 'active' : 'completed';
    
    return `
      <div class="workspace-card" 
           data-workspace-id="${workspace.id}" 
           data-testid="workspace-card"
           tabindex="0">
        <div class="workspace-card-header">
          <div class="workspace-title">${workspace.title}</div>
          <div class="workspace-status ${statusClass}">
            <i class="fas fa-${workspace.status === 'active' ? 'play' : 'check'}"></i>
            ${statusText}
          </div>
        </div>
        
        <div class="workspace-footer">
          <span class="workspace-created">생성일: ${createdAt}</span>
          <button class="workspace-action" onclick="openWorkspace('${workspace.id}', '${workspace.title}')">열기</button>
        </div>
      </div>
    `;
  }

  attachWorkspaceCardListeners() {
    document.querySelectorAll('.workspace-card').forEach(card => {
      const workspaceId = card.dataset.workspaceId;
      const workspaceTitle = card.querySelector('.workspace-title').textContent;
      const actionBtn = card.querySelector('.workspace-action');

      // 빈 카드인 경우 이벤트 리스너 추가하지 않음
      if (!workspaceId || !workspaceTitle || workspaceTitle === '새로운 Workspace를 생성해주세요') {
        return;
      }

      // 카드 클릭
      card.addEventListener('click', (e) => {
        if (!e.target.classList.contains('workspace-action')) {
          this.openWorkspace(workspaceId, workspaceTitle);
        }
      });

      // 열기 버튼
      actionBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.openWorkspace(workspaceId, workspaceTitle);
      });

      // 키보드 접근성
      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.openWorkspace(workspaceId, workspaceTitle);
        }
      });
    });
  }



  // 분개 테이블 렌더링
  renderJournalTable() {
    const tbody = document.getElementById('journal-rows');
    if (!tbody) return;

    // 20줄까지만 표시
    const visibleJournals = this.journals.slice(0, 20);
    
    tbody.innerHTML = visibleJournals.map(journal => this.createJournalRow(journal)).join('');
    
    // 20줄 이상인 경우 스크롤 안내 메시지 추가
    if (this.journals.length > 20) {
      const infoRow = document.createElement('tr');
      infoRow.className = 'scroll-info-row';
      infoRow.innerHTML = `
        <td colspan="11" style="text-align: center; padding: 1rem; color: var(--text-muted); font-style: italic; background: var(--background-light);">
          아래로 스크롤하여 더 많은 데이터를 확인하세요 (총 ${this.journals.length}건)
        </td>
      `;
      tbody.appendChild(infoRow);
    }
  }

  // 분개 행 생성
  createJournalRow(journal) {
    const formatAmount = (amount) => {
      if (amount === null || amount === undefined) return '-';
      return amount.toLocaleString();
    };

    return `
      <tr>
        <td>${journal.날짜 || '-'}</td>
        <td>${journal.번호 || '-'}</td>
        <td>${journal.계정코드 || '-'}</td>
        <td>${journal.계정과목 || '-'}</td>
        <td>${formatAmount(journal.차변)}</td>
        <td>${formatAmount(journal.대변)}</td>
        <td>${journal.적요 || '-'}</td>
        <td>${journal.거래처코드 || '-'}</td>
        <td>${journal.거래처명 || '-'}</td>
        <td>${journal.PJT || '-'}</td>
        <td>${journal.PJT7 || '-'}</td>
      </tr>
    `;
  }

  // Workspace 관련 메서드들
  openWorkspace(workspaceId, workspaceTitle) {
    try {
      // Workspace 페이지로 이동 (제목을 URL 파라미터로 전달)
      const encodedTitle = encodeURIComponent(workspaceTitle);
      window.location.href = `../workspace/workspace.html?id=${workspaceId}&title=${encodedTitle}`;
    } catch (error) {
      console.error('Workspace 열기 실패:', error);
      alert('Workspace 열기에 실패했습니다. 다시 시도해주세요.');
    }
  }



  updateControlButtons() {
    // 3개만 있으므로 더보기/접기 버튼 숨김
    const expandBtn = document.getElementById('expand-workspaces');
    const collapseBtn = document.getElementById('collapse-workspaces');
    
    if (expandBtn) expandBtn.style.display = 'none';
    if (collapseBtn) collapseBtn.style.display = 'none';
  }

  applyWorkspaceFilters() {
    const searchValue = document.getElementById('workspace-search').value.toLowerCase();
    
    if (!searchValue) {
      this.renderWorkspaceGrid();
      return;
    }

    const filteredWorkspaces = this.workspaces.filter(workspace => 
      workspace.title.toLowerCase().includes(searchValue)
    );

    const grid = document.getElementById('workspace-grid');
    const empty = document.getElementById('workspace-empty');
    
    if (filteredWorkspaces.length === 0) {
      grid.style.display = 'none';
      empty.style.display = 'block';
      empty.querySelector('h3').textContent = '검색 결과가 없습니다';
      empty.querySelector('p').textContent = '다른 키워드로 검색해보세요.';
    } else {
      grid.style.display = 'grid';
      empty.style.display = 'none';
      
      // 검색 결과는 모두 표시
      grid.innerHTML = filteredWorkspaces.map(workspace => this.createWorkspaceCard(workspace)).join('');
      this.attachWorkspaceCardListeners();
    }
  }







  showEmptyState(type) {
    if (type === 'workspace') {
      document.getElementById('workspace-grid').style.display = 'none';
      document.getElementById('workspace-empty').style.display = 'block';
    }
  }

  // Workspace 모달 관련 메서드들
  showWorkspaceModal() {
    const modal = document.getElementById('workspace-modal');
    const input = document.getElementById('workspace-title-input');
    
    if (modal && input) {
      modal.style.display = 'flex';
      modal.setAttribute('aria-hidden', 'false');
      input.focus();
      
      // 이벤트 리스너 설정
      this.setupWorkspaceModalListeners();
    }
  }

  closeWorkspaceModal() {
    const modal = document.getElementById('workspace-modal');
    const input = document.getElementById('workspace-title-input');
    
    if (modal && input) {
      modal.style.display = 'none';
      modal.setAttribute('aria-hidden', 'true');
      input.value = '';
    }
  }

  setupWorkspaceModalListeners() {
    const modal = document.getElementById('workspace-modal');
    const confirmBtn = document.getElementById('workspace-confirm');
    const cancelBtn = document.getElementById('workspace-cancel');
    const input = document.getElementById('workspace-title-input');

    if (!modal || !confirmBtn || !cancelBtn || !input) return;

    // 확인 버튼 클릭
    const handleConfirm = () => {
      const title = input.value.trim();
      if (!title) {
        alert('Workspace 제목을 입력해주세요.');
        input.focus();
        return;
      }
      
      // Workspace 생성 및 페이지 이동
      this.createWorkspace(title);
    };

    // 취소 버튼 클릭
    const handleCancel = () => {
      this.closeWorkspaceModal();
    };

    // Enter 키 입력
    const handleKeyPress = (e) => {
      if (e.key === 'Enter') {
        handleConfirm();
      } else if (e.key === 'Escape') {
        handleCancel();
      }
    };

    // 이벤트 리스너 등록
    confirmBtn.addEventListener('click', handleConfirm);
    cancelBtn.addEventListener('click', handleCancel);
    input.addEventListener('keydown', handleKeyPress);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        handleCancel();
      }
    });

    // 한 번만 실행되도록 이벤트 리스너 제거
    confirmBtn.removeEventListener('click', handleConfirm);
    cancelBtn.removeEventListener('click', handleCancel);
    input.removeEventListener('keydown', handleKeyPress);
    modal.removeEventListener('click', (e) => {
      if (e.target === modal) {
        handleCancel();
      }
    });

    // 다시 등록
    confirmBtn.addEventListener('click', handleConfirm);
    cancelBtn.addEventListener('click', handleCancel);
    input.addEventListener('keydown', handleKeyPress);
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        handleCancel();
      }
    });
  }

  async createWorkspace(title) {
    try {
      // TODO: 실제 API 호출로 Workspace 생성
      // const response = await fetch('/api/workspaces', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify({ title })
      // });
      
      // 새 Workspace 생성
      const workspace = {
        id: `ws_${Date.now()}`,
        title: title,
        status: 'active',
        uploadCount: 0,
        journalCount: 0,
        lastActivity: new Date().toISOString(),
        createdAt: new Date().toISOString()
      };
      
      // 로컬 스토리지에 저장
      const workspaces = JSON.parse(localStorage.getItem('workspaces') || '[]');
      workspaces.unshift(workspace); // 맨 앞에 추가
      localStorage.setItem('workspaces', JSON.stringify(workspaces));
      
      // 첫 번째 카드를 새로 생성된 workspace로 업데이트
      this.workspaces[0] = workspace;

      // 모달 닫기
      this.closeWorkspaceModal();
      
      // Workspace 그리드 다시 렌더링
      this.renderWorkspaceGrid();
      
      // Workspace 페이지로 이동 (제목을 URL 파라미터로 전달)
      const encodedTitle = encodeURIComponent(title);
      window.location.href = `../workspace/workspace.html?id=${workspace.id}&title=${encodedTitle}`;
      
    } catch (error) {
      console.error('Workspace 생성 실패:', error);
      alert('Workspace 생성에 실패했습니다. 다시 시도해주세요.');
    }
  }

  // ================================================== //
  // Workspace 펼치기/접기 기능
  // ================================================== //
  expandWorkspaces() {
    this.isExpanded = true;
    this.renderWorkspaceGrid();
    this.updateExpandControls();
    console.log('✅ Workspace 펼치기 완료');
  }

  collapseWorkspaces() {
    this.isExpanded = false;
    this.renderWorkspaceGrid();
    this.updateExpandControls();
    console.log('✅ Workspace 접기 완료');
  }

  updateExpandControls() {
    const expandBtn = document.getElementById('expand-workspaces');
    const collapseBtn = document.getElementById('collapse-workspaces');
    
    if (this.isExpanded) {
      expandBtn.style.display = 'none';
      collapseBtn.style.display = 'inline-flex';
    } else {
      expandBtn.style.display = 'inline-flex';
      collapseBtn.style.display = 'none';
    }
  }

  // ================================================== //
  // 전표 미리보기 정렬 기능
  // ================================================== //
  applyJournalSort() {
    const sortSelect = document.getElementById('sort-option');
    if (!sortSelect || !this.journals) return;

    const sortValue = sortSelect.value;
    let sortedJournals = [...this.journals];

    switch (sortValue) {
      case 'latest':
        // 최신 순 (날짜 기준, 내림차순)
        sortedJournals.sort((a, b) => {
          const dateA = new Date(a.날짜.replace(/\//g, '-'));
          const dateB = new Date(b.날짜.replace(/\//g, '-'));
          return dateB - dateA;
        });
        break;

      case 'oldest':
        // 오래된 순 (날짜 기준, 오름차순)
        sortedJournals.sort((a, b) => {
          const dateA = new Date(a.날짜.replace(/\//g, '-'));
          const dateB = new Date(b.날짜.replace(/\//g, '-'));
          return dateA - dateB;
        });
        break;

      case 'highest':
        // 큰 금액 순 (차변 또는 대변 중 큰 값 기준, 내림차순)
        sortedJournals.sort((a, b) => {
          const amountA = Math.max(a.차변 || 0, a.대변 || 0);
          const amountB = Math.max(b.차변 || 0, b.대변 || 0);
          return amountB - amountA;
        });
        break;

      case 'lowest':
        // 작은 금액 순 (차변 또는 대변 중 큰 값 기준, 오름차순)
        sortedJournals.sort((a, b) => {
          const amountA = Math.max(a.차변 || 0, a.대변 || 0);
          const amountB = Math.max(b.차변 || 0, b.대변 || 0);
          return amountA - amountB;
        });
        break;

      default:
        // 기본값은 최신 순
        sortedJournals.sort((a, b) => {
          const dateA = new Date(a.날짜.replace(/\//g, '-'));
          const dateB = new Date(b.날짜.replace(/\//g, '-'));
          return dateB - dateA;
        });
    }

    // 정렬된 데이터로 테이블 다시 렌더링
    this.journals = sortedJournals;
    this.renderJournalTable();
    
    console.log(`✅ 전표 미리보기 정렬 완료: ${sortValue}`);
  }
}

// ================================================== //
// 앱 초기화
// ================================================== //
document.addEventListener('DOMContentLoaded', () => {
  window.dashboardManager = new DashboardManager();
});
