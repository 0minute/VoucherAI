// Settings Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 사이드바 메뉴 스크롤 네비게이션
    const sidebarLinks = document.querySelectorAll('.sidebar-link');
    const contentSections = document.querySelectorAll('.content-section');

    // 스크롤 이벤트로 현재 섹션 감지
    function updateActiveSection() {
        const scrollPosition = window.scrollY + 100; // 약간의 오프셋

        contentSections.forEach((section, index) => {
            const sectionTop = section.offsetTop;
            const sectionBottom = sectionTop + section.offsetHeight;

            if (scrollPosition >= sectionTop && scrollPosition < sectionBottom) {
                // 모든 링크에서 active 클래스 제거
                sidebarLinks.forEach(link => link.classList.remove('active'));
                // 현재 섹션에 해당하는 링크에 active 클래스 추가
                sidebarLinks[index].classList.add('active');
            }
        });
    }

    // 스크롤 이벤트 리스너
    window.addEventListener('scroll', updateActiveSection);

    // 초기 활성 섹션 설정
    updateActiveSection();

    // 사이드바 링크 클릭 시 해당 섹션으로 스크롤
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            
            if (targetSection) {
                // 부드러운 스크롤로 해당 섹션으로 이동
                targetSection.scrollIntoView({ 
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // 테이블 데이터 초기화
    initializeTables();

    // Excel 업로드 기능
    setupExcelUpload('coa', 'btn-upload-coa', 'coa-file-input');
    setupExcelUpload('project', 'btn-upload-project', 'project-file-input');
    setupExcelUpload('transaction', 'btn-upload-transaction', 'transaction-file-input');

    // Excel 다운로드 기능
    setupExcelDownload('coa', 'btn-download-coa');
    setupExcelDownload('project', 'btn-download-project');
    setupExcelDownload('transaction', 'btn-download-transaction');

    // 모바일 메뉴 토글
    const mobileToggle = document.querySelector('.mobile-toggle');
    const sidebar = document.querySelector('.settings-sidebar');
    
    if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
});

// 테이블 초기화 함수
function initializeTables() {
    // CoA 테이블 초기화 (JSON 데이터 사용)
    initializeCoATable();
    
    // 프로젝트 테이블 초기화 (더미데이터)
    initializeProjectTable();
    
    // 거래유형 테이블 초기화 (더미데이터)
    initializeTransactionTable();
}

// CoA 테이블 초기화
function initializeCoATable() {
    const tableBody = document.getElementById('coa-rows');
    if (!tableBody) return;
    
    // dummy.json의 데이터를 직접 하드코딩
    const coaData = [
        { accountName: "상품매출원가", accountCode: 45100 },
        { accountName: "음원제작_작곡,편곡", accountCode: 45501 },
        { accountName: "음원제작_앨범제작,인지대", accountCode: 45502 },
        { accountName: "음원제작_M/V 제작", accountCode: 45503 },
        { accountName: "음원제작_세션", accountCode: 45504 },
        { accountName: "음원제작_기타", accountCode: 45599 },
        { accountName: "드라마매출원가", accountCode: 45700 },
        { accountName: "공연매출원가", accountCode: 46200 },
        { accountName: "용역매출원가", accountCode: 46400 },
        { accountName: "제품매출원가", accountCode: 46600 },
        { accountName: "복리후생비_식대", accountCode: 51103 },
        { accountName: "지급임차료", accountCode: 51900 },
        { accountName: "보험료_자동차보험", accountCode: 52101 },
        { accountName: "보험료_법정보험료", accountCode: 52102 },
        { accountName: "차량유지비", accountCode: 52200 },
        { accountName: "차량유지비_법인카드", accountCode: 52201 },
        { accountName: "운반비", accountCode: 52400 },
        { accountName: "운반비_법인카드", accountCode: 52401 },
        { accountName: "교육훈련비", accountCode: 52500 },
        { accountName: "도서인쇄비_법인카드", accountCode: 52601 },
        { accountName: "소모품비", accountCode: 53000 },
        { accountName: "소모품비_법인카드", accountCode: 53001 },
        { accountName: "지급수수료", accountCode: 53100 },
        { accountName: "지급수수료_법인카드", accountCode: 53101 },
        { accountName: "대행수수료", accountCode: 53700 },
        { accountName: "연예보조_의상ㆍ스타일링", accountCode: 53801 },
        { accountName: "연예보조_헤어/메이크업", accountCode: 53802 },
        { accountName: "연예보조_법인카드", accountCode: 53811 },
        { accountName: "연예보조_기타", accountCode: 53899 },
        { accountName: "지급인세_아티스트", accountCode: 53901 },
        { accountName: "지급인세_FT", accountCode: 53907 },
        { accountName: "지급인세_CN", accountCode: 53908 },
        { accountName: "지급인세_연기자", accountCode: 53909 },
        { accountName: "지급인세_코미디언", accountCode: 53910 },
        { accountName: "광고선전비", accountCode: 54100 },
        { accountName: "차량리스료", accountCode: 55400 },
        { accountName: "통신비", accountCode: 56000 },
        { accountName: "통신비_법인카드", accountCode: 56001 },
        { accountName: "전기요금", accountCode: 56100 },
        { accountName: "수도요금", accountCode: 56101 },
        { accountName: "가스요금", accountCode: 56102 },
        { accountName: "여비교통비_국내", accountCode: 56200 },
        { accountName: "여비교통비_해외", accountCode: 56201 },
        { accountName: "여비교통비_법인카드", accountCode: 56202 },
        { accountName: "접대비", accountCode: 56300 },
        { accountName: "접대비_법인카드", accountCode: 56301 },
        { accountName: "기부금", accountCode: 56400 },
        { accountName: "잡손실", accountCode: 56500 },
        { accountName: "잡이익", accountCode: 56600 },
        { accountName: "이자비용", accountCode: 56700 },
        { accountName: "이자수익", accountCode: 56800 },
        { accountName: "외환손실", accountCode: 56900 },
        { accountName: "외환이익", accountCode: 56901 },
        { accountName: "해외공연경비", accountCode: 57000 },
        { accountName: "국내공연경비", accountCode: 57001 },
        { accountName: "연습실임차료", accountCode: 57100 },
        { accountName: "연습실관리비", accountCode: 57101 },
        { accountName: "음반제작기타경비", accountCode: 57200 },
        { accountName: "드라마제작기타경비", accountCode: 57201 },
        { accountName: "뮤직비디오촬영비", accountCode: 57300 },
        { accountName: "공연세트제작비", accountCode: 57301 },
        { accountName: "연습생지원비", accountCode: 57400 },
        { accountName: "연습생숙소비", accountCode: 57401 },
        { accountName: "연습생식대", accountCode: 57402 },
        { accountName: "연습생교육비", accountCode: 57403 },
        { accountName: "스태프인건비", accountCode: 57500 },
        { accountName: "아티스트인건비", accountCode: 57501 },
        { accountName: "기타인건비", accountCode: 57502 },
        { accountName: "무대장치비", accountCode: 57600 },
        { accountName: "조명장치비", accountCode: 57601 },
        { accountName: "음향장치비", accountCode: 57602 },
        { accountName: "의상제작비", accountCode: 57700 },
        { accountName: "소품제작비", accountCode: 57701 },
        { accountName: "연예홍보비", accountCode: 57800 },
        { accountName: "연예홍보비_법인카드", accountCode: 57801 },
        { accountName: "콘텐츠플랫폼이용료", accountCode: 57900 },
        { accountName: "플랫폼수수료", accountCode: 57901 },
        { accountName: "음원유통수수료", accountCode: 57902 },
        { accountName: "저작권사용료", accountCode: 57903 },
        { accountName: "저작권수익", accountCode: 57904 },
        { accountName: "연예관련보험료", accountCode: 57905 },
        { accountName: "행사비", accountCode: 58000 },
        { accountName: "행사비_법인카드", accountCode: 58001 },
        { accountName: "법률자문료", accountCode: 58100 },
        { accountName: "회계자문료", accountCode: 58101 },
        { accountName: "세무자문료", accountCode: 58102 },
        { accountName: "컨설팅비", accountCode: 58103 }
    ];
    
    // 테이블 본문 생성
    tableBody.innerHTML = coaData.map((item, index) => `
        <tr>
            <td>${item.accountCode}</td>
            <td>${item.accountName}</td>
            <td>2025-06-30</td>
            <td>
                <button class="btn-edit" onclick="editCoA(${index + 1})">
                    <i class="fas fa-edit"></i>
                </button>
            </td>
            <td>
                <button class="btn-delete" onclick="deleteCoA(${index + 1})">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
    
    console.log(`✅ COA 테이블에 ${coaData.length}개 계정이 로드되었습니다.`);
    console.log('📊 첫 번째 계정 데이터:', coaData[0]);
}


// 프로젝트 테이블 초기화
function initializeProjectTable() {
    const tableBody = document.getElementById('project-rows');
    if (!tableBody) return;
    
    // 기존 빈 행들 제거
    const emptyRows = tableBody.querySelectorAll('.empty-row');
    emptyRows.forEach(row => row.remove());
    
    // 프로젝트 JSON 데이터 (pjt_dummy.json에서 가져온 데이터)
    const projectData = [
        { code: "P001", name: "루미 (HUNTRIX)", startDate: "2020-01-01", endDate: "2021-01-31", status: "진행중" },
        { code: "P002", name: "미라 (HUNTRIX)", startDate: "2020-02-15", endDate: "2021-03-15", status: "완료" },
        { code: "P003", name: "조이 (HUNTRIX)", startDate: "2020-04-01", endDate: "2021-04-30", status: "진행중" },
        { code: "P004", name: "진우 (SajaBoys)", startDate: "2020-05-10", endDate: "2021-06-10", status: "계획" },
        { code: "P005", name: "베이비 (SajaBoys)", startDate: "2020-06-20", endDate: "2021-07-20", status: "완료" },
        { code: "P006", name: "미스터리 (SajaBoys)", startDate: "2020-08-01", endDate: "2021-08-31", status: "진행중" },
        { code: "P007", name: "로맨스 (SajaBoys)", startDate: "2020-09-15", endDate: "2021-10-15", status: "계획" },
        { code: "P008", name: "애비 (SajaBoys)", startDate: "2020-11-01", endDate: "2021-11-30", status: "완료" },
        { code: "P009", name: "HUNTRIX 유닛 프로젝트", startDate: "2020-03-01", endDate: "2021-05-31", status: "진행중" },
        { code: "P010", name: "SajaBoys 유닛 프로젝트", startDate: "2020-07-01", endDate: "2021-09-30", status: "완료" }
    ];
    
    // 10행까지만 표시
    projectData.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.code}</td>
            <td>${item.name}</td>
            <td>${item.startDate}</td>
            <td>${item.endDate}</td>
            <td>${item.status}</td>
            <td>
                <button class="btn-edit" onclick="editItem('project', '${item.code}')" title="수정">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="m18.5 2.5 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
            </td>
            <td>
                <button class="btn-delete" onclick="deleteItem('project', '${item.code}')" title="삭제">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18"></path>
                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                        <line x1="10" y1="11" x2="10" y2="17"></line>
                        <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// 거래유형 테이블 초기화
function initializeTransactionTable() {
    const tableBody = document.getElementById('transaction-rows');
    if (!tableBody) return;
    
    // 기존 빈 행들 제거
    const emptyRows = tableBody.querySelectorAll('.empty-row');
    emptyRows.forEach(row => row.remove());
    
    // 거래유형 더미데이터
    const transactionData = [
        { code: "T001", name: "음원 제작비", category: "제작비", active: true },
        { code: "T002", name: "아티스트 인세", category: "인세", active: true },
        { code: "T003", name: "광고 제작비", category: "제작비", active: true },
        { code: "T004", name: "공연 제작비", category: "제작비", active: true },
        { code: "T005", name: "저작권료", category: "권리금", active: true },
        { code: "T006", name: "대행 수수료", category: "수수료", active: true },
        { code: "T007", name: "연예 보조비", category: "보조비", active: true },
        { code: "T008", name: "프로모션 비용", category: "마케팅", active: true },
        { code: "T009", name: "장비 임대료", category: "임대료", active: false },
        { code: "T010", name: "기타 비용", category: "기타", active: true }
    ];
    
    // 10행까지만 표시
    transactionData.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.code}</td>
            <td>${item.name}</td>
            <td>${item.category}</td>
            <td>${item.active ? '사용' : '미사용'}</td>
            <td>
                <button class="btn-edit" onclick="editItem('transaction', '${item.code}')" title="수정">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="m18.5 2.5 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                </button>
            </td>
            <td>
                <button class="btn-delete" onclick="deleteItem('transaction', '${item.code}')" title="삭제">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18"></path>
                        <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                        <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                        <line x1="10" y1="11" x2="10" y2="17"></line>
                        <line x1="14" y1="11" x2="14" y2="17"></line>
                    </svg>
                </button>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// Excel 업로드 설정
function setupExcelUpload(type, buttonId, inputId) {
    const uploadButton = document.getElementById(buttonId);
    const fileInput = document.getElementById(inputId);
    
    if (uploadButton && fileInput) {
        uploadButton.addEventListener('click', function() {
            fileInput.click();
        });
        
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                handleExcelUpload(type, file);
            }
        });
    }
}

// Excel 다운로드 설정
function setupExcelDownload(type, buttonId) {
    const downloadButton = document.getElementById(buttonId);
    
    if (downloadButton) {
        downloadButton.addEventListener('click', function() {
            handleExcelDownload(type);
        });
    }
}

// Excel 업로드 처리
function handleExcelUpload(type, file) {
    // 파일 유효성 검사
    if (!file.name.match(/\.(xlsx|xls)$/)) {
        showToast('Excel 파일만 업로드 가능합니다.', 'error');
        return;
    }
    
    // 파일 크기 검사 (10MB 제한)
    if (file.size > 10 * 1024 * 1024) {
        showToast('파일 크기는 10MB 이하여야 합니다.', 'error');
        return;
    }
    
    // FormData 생성
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);
    
    // 로딩 상태 표시
    showToast(`${type.toUpperCase()} 데이터 업로드 중...`, 'info');
    
    // API 호출 (백엔드 연동 시)
    // uploadExcelData(formData, type);
    
    // 임시 성공 메시지 (백엔드 연동 전)
    setTimeout(() => {
        showToast(`${type.toUpperCase()} 데이터가 성공적으로 업로드되었습니다.`, 'success');
        // 테이블 데이터 새로고침 로직 추가 예정
    }, 1000);
}

// Excel 다운로드 처리
function handleExcelDownload(type) {
    showToast(`${type.toUpperCase()} 데이터 다운로드 중...`, 'info');
    
    // API 호출 (백엔드 연동 시)
    // downloadExcelData(type);
    
    // 임시 성공 메시지 (백엔드 연동 전)
    setTimeout(() => {
        showToast(`${type.toUpperCase()} 데이터 다운로드가 완료되었습니다.`, 'success');
    }, 1000);
}

// Toast 메시지 표시
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 3000);
}

// 백엔드 API 연동 함수들 (향후 구현)
function uploadExcelData(formData, type) {
    // fetch('/api/upload-excel', {
    //     method: 'POST',
    //     body: formData
    // })
    // .then(response => response.json())
    // .then(data => {
    //     if (data.success) {
    //         showToast(`${type.toUpperCase()} 데이터 업로드 성공`, 'success');
    //         refreshTableData(type);
    //     } else {
    //         showToast(data.message || '업로드 실패', 'error');
    //     }
    // })
    // .catch(error => {
    //     console.error('Upload error:', error);
    //     showToast('업로드 중 오류가 발생했습니다.', 'error');
    // });
}

function downloadExcelData(type) {
    // fetch(`/api/download-excel?type=${type}`)
    // .then(response => response.blob())
    // .then(blob => {
    //     const url = window.URL.createObjectURL(blob);
    //     const a = document.createElement('a');
    //     a.href = url;
    //     a.download = `${type}_data.xlsx`;
    //     document.body.appendChild(a);
    //     a.click();
    //     window.URL.revokeObjectURL(url);
    //     document.body.removeChild(a);
    //     showToast(`${type.toUpperCase()} 데이터 다운로드 완료`, 'success');
    // })
    // .catch(error => {
    //     console.error('Download error:', error);
    //     showToast('다운로드 중 오류가 발생했습니다.', 'error');
    // });
}

function refreshTableData(type) {
    // 테이블 데이터 새로고침 로직
    // fetch(`/api/${type}-data`)
    // .then(response => response.json())
    // .then(data => {
    //     updateTable(type, data);
    // })
    // .catch(error => {
    //     console.error('Data refresh error:', error);
    // });
}

function updateTable(type, data) {
    // 테이블 업데이트 로직
    const tableBody = document.getElementById(`${type}-rows`);
    if (!tableBody) return;
    
    // 기존 빈 행들 제거
    const emptyRows = tableBody.querySelectorAll('.empty-row');
    emptyRows.forEach(row => row.remove());
    
    // 새로운 데이터로 행 생성
    data.forEach(item => {
        const row = document.createElement('tr');
        // 데이터에 따라 행 내용 생성
        row.innerHTML = createTableRow(type, item);
        tableBody.appendChild(row);
    });
}

function createTableRow(type, item) {
    // 타입별로 다른 테이블 행 생성
    switch(type) {
        case 'coa':
            return `
                <td>${item.code || '-'}</td>
                <td>${item.name || '-'}</td>
                <td>${item.category || '-'}</td>
                <td>${item.parent || '-'}</td>
                <td><button class="btn-edit" onclick="editItem('coa', '${item.id}')">수정</button></td>
                <td><button class="btn-delete" onclick="deleteItem('coa', '${item.id}')">삭제</button></td>
            `;
        case 'project':
            return `
                <td>${item.code || '-'}</td>
                <td>${item.name || '-'}</td>
                <td>${item.startDate || '-'}</td>
                <td>${item.endDate || '-'}</td>
                <td>${item.status || '-'}</td>
                <td><button class="btn-edit" onclick="editItem('project', '${item.id}')">수정</button></td>
                <td><button class="btn-delete" onclick="deleteItem('project', '${item.id}')">삭제</button></td>
            `;
        case 'transaction':
            return `
                <td>${item.code || '-'}</td>
                <td>${item.name || '-'}</td>
                <td>${item.category || '-'}</td>
                <td>${item.active ? '사용' : '미사용'}</td>
                <td><button class="btn-edit" onclick="editItem('transaction', '${item.id}')">수정</button></td>
                <td><button class="btn-delete" onclick="deleteItem('transaction', '${item.id}')">삭제</button></td>
            `;
        default:
            return '';
    }
}

// COA 관련 함수들
function editCoA(id) {
    showToast(`COA 계정 ${id} 수정 기능은 향후 구현 예정입니다.`, 'info');
}

function deleteCoA(id) {
    if (confirm('정말 삭제하시겠습니까?')) {
        showToast(`COA 계정 ${id} 삭제 기능은 향후 구현 예정입니다.`, 'info');
    }
}

// 아이템 수정/삭제 함수들 (향후 구현)
function editItem(type, id) {
    showToast(`${type} 아이템 수정 기능은 향후 구현 예정입니다.`, 'info');
}

function deleteItem(type, id) {
    if (confirm('정말 삭제하시겠습니까?')) {
        showToast(`${type} 아이템 삭제 기능은 향후 구현 예정입니다.`, 'info');
    }
}
