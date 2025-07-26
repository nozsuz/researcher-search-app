"""
プロジェクト管理API
仮プロジェクト作成、研究者選択、マッチング依頼の管理
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from google.cloud import bigquery
import json

logger = logging.getLogger(__name__)

class TempProject(BaseModel):
    """仮プロジェクトデータモデル"""
    id: str
    name: str
    description: str
    budget: Optional[int] = None
    duration: Optional[int] = None
    requirements: Optional[str] = None
    keywords: Optional[str] = None
    status: str = "draft"  # draft, active, matching_requested, completed
    created_at: str
    updated_at: Optional[str] = None
    user_id: Optional[str] = None
    selected_researchers: List[Dict[str, Any]] = []

class ProjectCreateRequest(BaseModel):
    """プロジェクト作成リクエスト"""
    name: str
    description: str
    budget: Optional[int] = None
    duration: Optional[int] = None
    requirements: Optional[str] = None
    keywords: Optional[str] = None
    user_id: Optional[str] = None

class ResearcherSelectionRequest(BaseModel):
    """研究者選択リクエスト"""
    project_id: str
    researcher_name: str
    researcher_affiliation: str
    researchmap_url: Optional[str] = None
    selection_reason: Optional[str] = None

class MatchingRequest(BaseModel):
    """マッチング依頼リクエスト"""
    project_id: str
    message: str
    priority: str = "normal"  # normal, high, urgent
    request_to_consultant: bool = False  # 専門コンサルタントへの依頼フラグ
    consultant_requirements: Optional[str] = None  # コンサルタント要件

class ResearcherMemoUpdate(BaseModel):
    """研究者メモ更新リクエスト"""
    project_id: str
    researcher_name: str
    memo: str

class ProjectManager:
    """プロジェクト管理クラス"""
    
    def __init__(self):
        self.projects_storage = {}  # メモリ内ストレージ（本番環境では外部DB使用）
        
    def create_temp_project(self, request: ProjectCreateRequest) -> TempProject:
        """仮プロジェクトを作成"""
        project_id = f"TEMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
        
        project = TempProject(
            id=project_id,
            name=request.name,
            description=request.description,
            budget=request.budget,
            duration=request.duration,
            requirements=request.requirements,
            keywords=request.keywords,
            status="draft",
            created_at=datetime.now().isoformat(),
            user_id=request.user_id
        )
        
        self.projects_storage[project_id] = project
        logger.info(f"✅ 仮プロジェクト作成: {project_id} - {request.name}")
        
        return project
    
    def get_temp_project(self, project_id: str) -> Optional[TempProject]:
        """仮プロジェクトを取得"""
        return self.projects_storage.get(project_id)
    
    def list_temp_projects(self, user_id: Optional[str] = None) -> List[TempProject]:
        """仮プロジェクト一覧を取得"""
        projects = list(self.projects_storage.values())
        
        if user_id:
            projects = [p for p in projects if p.user_id == user_id]
        
        # 作成日時の降順でソート
        projects.sort(key=lambda x: x.created_at, reverse=True)
        
        return projects
    
    def add_researcher_to_project(
        self, 
        project_id: str, 
        researcher: Dict[str, Any]
    ) -> bool:
        """プロジェクトに研究者を追加"""
        project = self.get_temp_project(project_id)
        if not project:
            return False
        
        # 重複チェック
        for existing_researcher in project.selected_researchers:
            if existing_researcher.get("name") == researcher.get("name"):
                logger.warning(f"研究者は既に追加済み: {researcher.get('name')}")
                return False
        
        # 研究者情報を追加
        researcher_data = {
            "name": researcher.get("name", ""),
            "affiliation": researcher.get("affiliation", ""),
            "researchmap_url": researcher.get("researchmap_url", ""),
            "selection_reason": researcher.get("selection_reason", ""),
            "memo": researcher.get("memo", ""),  # メモフィールドを追加
            "added_at": datetime.now().isoformat()
        }
        
        project.selected_researchers.append(researcher_data)
        project.updated_at = datetime.now().isoformat()
        
        logger.info(f"✅ 研究者追加: {project_id} に {researcher.get('name')} を追加")
        
        return True
    
    def remove_researcher_from_project(
        self, 
        project_id: str, 
        researcher_name: str
    ) -> bool:
        """プロジェクトから研究者を削除"""
        project = self.get_temp_project(project_id)
        if not project:
            return False
        
        # 研究者を検索して削除
        for i, researcher in enumerate(project.selected_researchers):
            if researcher.get("name") == researcher_name:
                project.selected_researchers.pop(i)
                project.updated_at = datetime.now().isoformat()
                logger.info(f"✅ 研究者削除: {project_id} から {researcher_name} を削除")
                return True
        
        return False
    
    def update_researcher_memo(
        self, 
        project_id: str, 
        researcher_name: str, 
        memo: str
    ) -> bool:
        """研究者のメモを更新"""
        project = self.get_temp_project(project_id)
        if not project:
            return False
        
        # 研究者を検索してメモを更新
        for researcher in project.selected_researchers:
            if researcher.get("name") == researcher_name:
                researcher["memo"] = memo
                researcher["memo_updated_at"] = datetime.now().isoformat()
                project.updated_at = datetime.now().isoformat()
                logger.info(f"📝 研究者メモ更新: {project_id} - {researcher_name}")
                return True
        
        return False
    
    def submit_matching_request(
        self, 
        project_id: str, 
        request: MatchingRequest
    ) -> Dict[str, Any]:
        """マッチング依頼を送信"""
        project = self.get_temp_project(project_id)
        if not project:
            return {"success": False, "error": "プロジェクトが見つかりません"}
        
        if len(project.selected_researchers) == 0:
            return {"success": False, "error": "研究者が選択されていません"}
        
        # プロジェクトステータスを更新
        project.status = "matching_requested"
        project.updated_at = datetime.now().isoformat()
        
        # マッチング依頼情報を保存
        matching_data = {
            "project_id": project_id,
            "message": request.message,
            "priority": request.priority,
            "request_to_consultant": request.request_to_consultant,
            "consultant_requirements": request.consultant_requirements if request.request_to_consultant else None,
            "researchers": project.selected_researchers,
            "submitted_at": datetime.now().isoformat(),
            "status": "submitted"
        }
        
        # 本番環境では外部システムに送信
        if request.request_to_consultant:
            logger.info(f"👨‍💼 専門コンサルタントへマッチング依頼送信: {project_id}")
            logger.info(f"   コンサルタント要件: {request.consultant_requirements}")
        else:
            logger.info(f"📤 研究者へ直接マッチング依頼送信: {project_id}")
            logger.info(f"   対象研究者: {len(project.selected_researchers)}名")
        logger.info(f"   メッセージ: {request.message[:100]}...")
        
        matching_id = f"MATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            "success": True,
            "matching_id": matching_id,
            "project_status": project.status,
            "researchers_count": len(project.selected_researchers),
            "request_type": "consultant" if request.request_to_consultant else "direct",
            "consultant_requirements": request.consultant_requirements if request.request_to_consultant else None
        }
    
    def update_project_status(
        self, 
        project_id: str, 
        status: str
    ) -> bool:
        """プロジェクトステータスを更新"""
        project = self.get_temp_project(project_id)
        if not project:
            return False
        
        project.status = status
        project.updated_at = datetime.now().isoformat()
        
        logger.info(f"🔄 プロジェクトステータス更新: {project_id} -> {status}")
        
        return True
    
    def delete_temp_project(self, project_id: str) -> bool:
        """仮プロジェクトを削除"""
        if project_id in self.projects_storage:
            project = self.projects_storage[project_id]
            del self.projects_storage[project_id]
            logger.info(f"🗑️ 仮プロジェクト削除: {project_id} - {project.name}")
            return True
        return False

# グローバルインスタンス
project_manager = ProjectManager()
