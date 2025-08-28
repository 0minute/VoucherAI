from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Iterable
import mimetypes, hashlib
from pathlib import Path
from src.api.constants import PROJECT_ROOT, get_uploads_index_path
import json, os
from pathlib import Path
from src.api.utils import _atomic_write_json

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

@dataclass
class UploadFileRow:
    rel: str                               # PROJECT_ROOT 기준 상대경로
    project: Optional[str] = None
    excluded: bool = False
    size: Optional[int] = None
    mime: Optional[str] = None
    created_at: str = field(default_factory=now_iso) #“이 필드의 기본값을 만들 때 **이 함수(now_iso)**를 호출해 나온 값을 써라”는 뜻이에요.
    updated_at: str = field(default_factory=now_iso) #“이 필드의 기본값을 만들 때 **이 함수(now_iso)**를 호출해 나온 값을 써라”는 뜻이에요.

    def set_project(self, name: Optional[str]) -> None:
        self.project = (name or None)
        self.updated_at = now_iso()

    def set_excluded(self, flag: bool) -> None:
        self.excluded = bool(flag)
        self.updated_at = now_iso()

    def snapshot(self) -> dict:
        return {
            "rel": self.rel, "project": self.project, "excluded": self.excluded,
            "size": self.size, "mime": self.mime,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(d: dict) -> "UploadFileRow":
        return UploadFileRow(
            rel=d["rel"],
            project=d.get("project"),
            excluded=bool(d.get("excluded", False)),
            size=d.get("size"),
            mime=d.get("mime"),
            created_at=d.get("created_at", now_iso()),
            updated_at=d.get("updated_at", now_iso()),
        )

@dataclass
class UploadFiles:
    files: Dict[str, UploadFileRow] = field(default_factory=dict)  # key = rel
    version: int = 1
    updated_at: str = field(default_factory=now_iso)

    # CRUD
    def upsert(self, f: UploadFileRow) -> None:
        self.files[f.rel] = f
        self.touch()

    def remove(self, rel: str) -> None:
        self.files.pop(rel, None)
        self.touch()

    def get(self, rel: str) -> Optional[UploadFileRow]:
        return self.files.get(rel)

    # Bulk ops
    def set_projects(self, mapping: Dict[str, Optional[str]]) -> None:
        for rel, proj in mapping.items():
            if rel in self.files:
                self.files[rel].set_project(proj)
        self.touch()

    def set_excluded_bulk(self, rels: Iterable[str], flag: bool) -> None:
        for rel in rels:
            if rel in self.files:
                self.files[rel].set_excluded(flag)
        self.touch()

    # Views
    def uploaded(self) -> list[str]:
        return sorted(self.files.keys())

    def excluded(self) -> list[str]:
        return sorted([r for r, f in self.files.items() if f.excluded])

    def effective(self) -> list[str]:
        return sorted([r for r, f in self.files.items() if not f.excluded])

    def records(self) -> list[dict]:
        return [f.snapshot() for f in self.files.values()]

    def touch(self) -> None:
        self.updated_at = now_iso()

    # Serialization
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "files": [f.snapshot() for f in self.files.values()],
        }
    @staticmethod
    def from_dict(d: dict) -> "UploadFiles":
        uf = UploadFiles(version=int(d.get("version", 1)), updated_at=d.get("updated_at", now_iso()))
        for row in d.get("files", []):
            f = UploadFileRow.from_dict(row)
            uf.files[f.rel] = f
        return uf



def _sha256(path: Path, chunk=1024*1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def compute_file_meta(rel_path: str) -> dict:
    """PROJECT_ROOT 기준 rel 경로에서 메타 뽑기"""
    abs_p = (PROJECT_ROOT / rel_path).resolve()
    size = abs_p.stat().st_size if abs_p.exists() else None
    mime = mimetypes.guess_type(abs_p.name)[0]
    # 해시는 선택 (부하 고려)
    filehash = _sha256(abs_p) if abs_p.exists() else None
    return {"size": size, "mime": mime, "sha256": filehash}





class UploadsIndexRepository:
    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> UploadFiles:
        if not self.index_path.exists():
            return UploadFiles()  # 빈 집계( version=1 등 )
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        return UploadFiles.from_dict(data)

    def save(self, uf: UploadFiles, *, if_match: int | None = None) -> UploadFiles:
        current = self.load()
        if if_match is not None and if_match != current.version:
            raise RuntimeError(f"version_conflict: client={if_match}, server={current.version}")
        uf.version = current.version + 1
        _atomic_write_json(self.index_path, uf.to_dict())
        return uf

    
# 업로드 인덱스 저장소 생성기
def get_uploads_repo(workspace_name: str):
    index_path = get_uploads_index_path(workspace_name)  # e.g. workspace/<WS>/db/uploads_index.json
    return UploadsIndexRepository(index_path)