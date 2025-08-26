from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional, Dict, List, Any
import uuid, json, os
from src.api.utils import _atomic_write_json, _now_iso, _read_json, _ensure_iso_date, _to_decimal
from src.api.constants import get_voucher_db_path

# --- Voucher 엔티티 -----------------------------------------------------------
@dataclass
class Voucher:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: str = field(default_factory=lambda: _now_iso()[:10])  # 'YYYY-MM-DD'
    amount: Decimal = field(default_factory=lambda: Decimal("0"))

    # 사용자/도메인 필드
    type: Optional[str] = None                 # 거래유형
    biz_no: Optional[str] = None               # 사업자등록번호
    representative: Optional[str] = None       # 대표자
    address: Optional[str] = None              # 주소
    evidence_type: Optional[str] = None        # 증빙유형
    account_title: Optional[str] = None        # 계정과목
    account_code: Optional[str] = None         # 계정코드
    project_name: Optional[str] = None         # 프로젝트명
    customer_code: Optional[str] = None        # 거래처코드
    customer_name: Optional[str] = None        # 거래처명

    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    # --- 도메인 행위 ---
    def set_fields(self, **kwargs) -> None:
        if "date" in kwargs:
            self.date = _ensure_iso_date(kwargs["date"])
        if "amount" in kwargs:
            self.amount = _to_decimal(kwargs["amount"])
        for k in [
            "type","biz_no","representative","address","evidence_type",
            "account_title","account_code","project_name","customer_code","customer_name"
        ]:
            if k in kwargs:
                setattr(self, k, kwargs[k] if kwargs[k] != "" else None)
        self.updated_at = _now_iso()

    # --- 직렬화 ---
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "amount": str(self.amount),  # JSON에는 문자열로 저장(정밀도 보존)
            "type": self.type,
            "biz_no": self.biz_no,
            "representative": self.representative,
            "address": self.address,
            "evidence_type": self.evidence_type,
            "account_title": self.account_title,
            "account_code": self.account_code,
            "project_name": self.project_name,
            "customer_code": self.customer_code,
            "customer_name": self.customer_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Voucher":
        v = cls(
            id=d.get("id") or str(uuid.uuid4()),
            date=_ensure_iso_date(d.get("date") or _now_iso()[:10]),
            amount=_to_decimal(d.get("amount")),
            type=d.get("type"),
            biz_no=d.get("biz_no"),
            representative=d.get("representative"),
            address=d.get("address"),
            evidence_type=d.get("evidence_type"),
            account_title=d.get("account_title"),
            account_code=d.get("account_code"),
            project_name=d.get("project_name"),
            customer_code=d.get("customer_code"),
            customer_name=d.get("customer_name"),
            created_at=d.get("created_at") or _now_iso(),
            updated_at=d.get("updated_at") or _now_iso(),
        )
        return v


# --- MultiVoucherDB (집계/저장소 + per-file 뷰 제공) --------------------------
class SingleVoucherDB:
    """
    저장 형식 예:
    {
      "schema_version": 2,
      "version": 7,
      "updated_at": "...Z",
      "by_file": {
        "<rel>": {
           "version": 3,
           "updated_at": "...Z",
           "voucher": { ... }          # 리스트가 아니라 단일 객체
        },
        ...
      }
    }
    """
    SCHEMA_VERSION = 2

    def __init__(self, workspace_name: str):
        self.workspace_name = workspace_name
        self.path = get_voucher_db_path(workspace_name)
        self._data = self._load_or_init()

    # ------------- 내부 I/O -------------
    def _load_or_init(self) -> dict:
        if not self.path.exists():
            base = {"schema_version": self.SCHEMA_VERSION, "version": 1, "updated_at": _now_iso(), "by_file": {}}
            _atomic_write_json(self.path, base)
            return base

        data = json.loads(self.path.read_text(encoding="utf-8"))

        # 구버전(배열) 마이그레이션: vouchers[] -> voucher 1개(최근 updated_at 기준)
        if "by_file" in data:
            changed = False
            for rel, bucket in list(data["by_file"].items()):
                if "vouchers" in bucket and isinstance(bucket["vouchers"], list):
                    chosen = None
                    if bucket["vouchers"]:
                        # updated_at 가장 최신 것을 선택 (없으면 마지막)
                        chosen = max(
                            bucket["vouchers"],
                            key=lambda r: r.get("updated_at") or r.get("created_at") or "",
                            default=bucket["vouchers"][-1]
                        )
                    bucket.pop("vouchers", None)
                    bucket["voucher"] = chosen or Voucher().to_dict()
                    bucket["version"] = int(bucket.get("version", 1)) + 1
                    bucket["updated_at"] = _now_iso()
                    changed = True
            if changed:
                data["schema_version"] = self.SCHEMA_VERSION
                data["version"] = int(data.get("version", 1)) + 1
                data["updated_at"] = _now_iso()
                _atomic_write_json(self.path, data)

        # 스키마 버전 갱신
        if int(data.get("schema_version", 1)) < self.SCHEMA_VERSION:
            data["schema_version"] = self.SCHEMA_VERSION
            data["version"] = int(data.get("version", 1)) + 1
            data["updated_at"] = _now_iso()
            _atomic_write_json(self.path, data)

        return data

    def save(self, *, if_match: int | None = None) -> dict:
        cur = self.version
        if if_match is not None and if_match != cur:
            raise RuntimeError(f"version_conflict: client={if_match}, server={cur}")
        self._data["version"] = cur + 1
        self._data["updated_at"] = _now_iso()
        _atomic_write_json(self.path, self._data)
        return self._data

    # ------------- 버전/스냅샷 -------------
    @property
    def version(self) -> int:
        return int(self._data.get("version", 1))

    def snapshot(self) -> dict:
        files = []
        for rel, bucket in self._data.get("by_file", {}).items():
            v = bucket.get("voucher")
            files.append({
                "rel": rel,
                "version": bucket.get("version", 1),
                "updated_at": bucket.get("updated_at"),
                "voucher": v
            })
        return {
            "schema_version": self._data.get("schema_version"),
            "version": self.version,
            "updated_at": self._data.get("updated_at"),
            "files": files
        }

    # ------------- CRUD (rel당 1건) -------------
    def get(self, rel: str) -> Optional[Voucher]:
        b = self._data.get("by_file", {}).get(rel)
        if not b or not b.get("voucher"):
            return None
        return Voucher.from_dict(b["voucher"])

    def upsert(self, rel: str, *, commit: bool = True, **fields) -> Voucher:
        """
        없으면 생성, 있으면 필드 갱신.
        date는 명시 입력을 권장(없으면 ValueError).
        """
        byf = self._data.setdefault("by_file", {})
        bucket = byf.get(rel)
        if not bucket:
            # 새로 생성
            v = Voucher()
            if "date" not in fields or fields["date"] is None:
                raise ValueError("date is required for new voucher (YYYY-MM-DD)")
            v.set_fields(**fields)
            byf[rel] = {
                "version": 1,
                "updated_at": _now_iso(),
                "voucher": v.to_dict()
            }
        else:
            v = Voucher.from_dict(bucket.get("voucher") or {})
            if "date" in fields and fields["date"] is None:
                # None을 넘겨서 지우는 행위는 허용하지 않음
                raise ValueError("date cannot be None")
            v.set_fields(**fields)
            bucket["voucher"] = v.to_dict()
            bucket["version"] = int(bucket.get("version", 1)) + 1
            bucket["updated_at"] = _now_iso()

        if commit: self.save()
        return v

    def update(self, rel: str, *, commit: bool = True, **fields) -> Voucher:
        bucket = self._data.get("by_file", {}).get(rel)
        if not bucket or not bucket.get("voucher"):
            raise KeyError(f"voucher not found for rel: {rel}")
        v = Voucher.from_dict(bucket["voucher"])
        if "date" in fields and fields["date"] is None:
            raise ValueError("date cannot be None")
        v.set_fields(**fields)
        bucket["voucher"] = v.to_dict()
        bucket["version"] = int(bucket.get("version", 1)) + 1
        bucket["updated_at"] = _now_iso()
        if commit: self.save()
        return v

    def delete(self, rel: str, *, commit: bool = True) -> bool:
        byf = self._data.get("by_file", {})
        if rel not in byf:
            return False
        byf.pop(rel, None)
        if commit: self.save()
        return True

# --- VoucherDB (단일 파일 rel용 조작기) --------------------------------------
class VoucherDB:
    def __init__(self, owner: SingleVoucherDB, rel: str):
        self.owner = owner
        self.rel = rel

    # 조회
    def list(self) -> List[Voucher]:
        b = self.owner._ensure_bucket(self.rel)
        return [Voucher.from_dict(r) for r in b.get("vouchers", [])]

    def get(self, voucher_id: str) -> Optional[Voucher]:
        for v in self.list():
            if v.id == voucher_id:
                return v
        return None

    # 추가/수정/삭제 (commit=True이면 디스크 저장까지 수행)
    def add(self, *, commit: bool = True, **fields) -> Voucher:
        # 필수: date, amount
        v = Voucher()
        v.set_fields(**fields)
        b = self.owner._ensure_bucket(self.rel)
        b["vouchers"].append(v.to_dict())
        self.owner._bump_bucket(self.rel)
        if commit: self.owner.save()
        return v

    def update(self, voucher_id: str, *, commit: bool = True, **fields) -> Voucher:
        b = self.owner._ensure_bucket(self.rel)
        rows = b.get("vouchers", [])
        for i, row in enumerate(rows):
            if row.get("id") == voucher_id:
                cur = Voucher.from_dict(row)
                cur.set_fields(**fields)
                rows[i] = cur.to_dict()
                self.owner._bump_bucket(self.rel)
                if commit: self.owner.save()
                return cur
        raise KeyError(f"voucher not found: {voucher_id}")

    def delete(self, voucher_id: str, *, commit: bool = True) -> bool:
        b = self.owner._ensure_bucket(self.rel)
        rows = b.get("vouchers", [])
        new_rows = [r for r in rows if r.get("id") != voucher_id]
        if len(new_rows) == len(rows):
            return False
        b["vouchers"] = new_rows
        self.owner._bump_bucket(self.rel)
        if commit: self.owner.save()
        return True

    # 벌크 업데이트(예: 계정과목/프로젝트 일괄 변경)
    def bulk_update(self, ids: List[str], *, commit: bool = True, **fields) -> int:
        b = self.owner._ensure_bucket(self.rel)
        rows = b.get("vouchers", [])
        cnt = 0
        for i, row in enumerate(rows):
            if row.get("id") in ids:
                cur = Voucher.from_dict(row)
                cur.set_fields(**fields)
                rows[i] = cur.to_dict()
                cnt += 1
        if cnt:
            self.owner._bump_bucket(self.rel)
            if commit: self.owner.save()
        return cnt