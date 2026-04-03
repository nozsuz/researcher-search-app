"""
ResearchMap API連携モジュール
研究者の詳細情報を取得してAI分析を実行
"""

import logging
import json
import re
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import aiohttp
import collections
import itertools
from collections import Counter
try:
    from vertexai.generative_models import GenerativeModel
    VERTEX_AI_AVAILABLE = True
except ImportError:
    GenerativeModel = None
    VERTEX_AI_AVAILABLE = False

# --- グラフ解析ライブラリをインポート ---
try:
    import networkx as nx
    import community as community_louvain
    GRAPH_LIBS_AVAILABLE = True
except ImportError:
    GRAPH_LIBS_AVAILABLE = False
# --- ここまで ---

logger = logging.getLogger(__name__)

# 日本語ストップワード
JAPANESE_STOPWORDS = {
    'について', 'という', 'である', 'として', 'において', 'による', 'によって',
    'しかし', 'また', 'さらに', 'したがって', 'そして', 'および', 'これ', 'それ',
    '研究', '分析', '検討', '実験', '結果', '考察', '方法', '手法', '技術',
    'システム', 'データ', '評価', '開発', '提案', '改善', '効果', '報告',
    'はじめに', 'おわりに', 'まとめ', '概要', '背景', '目的'
}

# 英語ストップワード
ENGLISH_STOPWORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
    'does', 'did', 'we', 'i', 'you', 'he', 'she', 'it', 'they', 'this', 'that',
    'research', 'study', 'analysis', 'method', 'approach', 'system', 'data',
    'results', 'conclusion', 'introduction', 'paper', 'work'
}

# 研究分野特有の重要キーワードを優先
TECHNICAL_KEYWORDS = {
    'AI', 'IOT', 'DX', 'ICT', 'IT', 'VR', 'AR', 'ML', 'NLP', 'CNN', 'RNN',
    '機械学習', '人工知能', 'データマイニング', 'ディープラーニング', '深層学習',
    'ベイズ最適化', 'マテリアルズインフォマティクス'
}


class ResearchMapAnalyzer:
    """ResearchMap APIを使用した研究者分析クラス"""
    
    def __init__(self):
        self.api_base_url = "https://api.researchmap.jp"
        self.llm_model = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """LLMモデルの初期化"""
        if not VERTEX_AI_AVAILABLE:
            logger.warning("⚠️ VertexAI SDKが利用できません - 簡易分析モードで動作")
            self.llm_model = None
            self.model_name = "simple_analysis"
            return
            
        try:
            # Gemini 2.5 Flash Liteを優先（2.0系は2026-03-06以降新規利用不可）
            self.llm_model = GenerativeModel("gemini-2.5-flash-lite")
            self.model_name = "gemini-2.5-flash-lite"
            logger.info(f"✅ 分析用LLMモデル初期化: {self.model_name}")
        except Exception as e:
            logger.warning(f"⚠️ Gemini 2.5 Flash Lite初期化失敗: {e}")
            try:
                # フォールバック
                self.llm_model = GenerativeModel("gemini-2.5-flash")
                self.model_name = "gemini-2.5-flash"
                logger.info(f"✅ フォールバックLLMモデル初期化: {self.model_name}")
            except Exception as e2:
                logger.error(f"❌ LLMモデル初期化失敗: {e2}")
                self.llm_model = None
                self.model_name = "simple_analysis"
    
    def extract_researcher_id(self, researchmap_url: str) -> Optional[str]:
        """ResearchMap URLから研究者IDを抽出"""
        try:
            # URLパターン: https://researchmap.jp/{researcher_id}
            parsed_url = urlparse(researchmap_url)
            path_parts = parsed_url.path.strip('/').split('/')
            
            if path_parts and path_parts[0]:
                researcher_id = path_parts[0]
                logger.info(f"📌 研究者ID抽出: {researcher_id}")
                return researcher_id
            
            return None
        except Exception as e:
            logger.error(f"❌ 研究者ID抽出エラー: {e}")
            return None
    
    async def _fetch_all_papers(self, researcher_id: str, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """特定の研究者の全論文をページネーションを処理して取得する"""
        all_papers = []
        start_index = 1
        limit = 100  # 1回のリクエストで取得する最大件数
        headers = {"Accept": "application/json", "Accept-Language": "ja"}
        timeout = aiohttp.ClientTimeout(total=20)

        while True:
            papers_url = f"{self.api_base_url}/{researcher_id}/published_papers?start={start_index}&limit={limit}"
            try:
                async with session.get(papers_url, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        logger.warning(f"📄 論文取得でAPIエラー: status={response.status}, url={papers_url}")
                        break
                    
                    data = await response.json()
                    papers_on_page = data.get("items", [])
                    
                    if not papers_on_page:
                        logger.info("📄 全ての論文を取得完了。")
                        break
                    
                    all_papers.extend(papers_on_page)
                    logger.info(f"📄 論文を{len(papers_on_page)}件取得 (合計: {len(all_papers)}件)")
                    
                    if len(papers_on_page) < limit:
                        logger.info("📄 これが最終ページです。")
                        break
                        
                    start_index += limit
                    await asyncio.sleep(0.5) # APIへの負荷を軽減するための待機

            except asyncio.TimeoutError:
                logger.warning(f"📄 論文取得中にタイムアウト: {papers_url}")
                break
            except Exception as e:
                logger.error(f"📄 論文取得中に予期せぬエラー: {e}")
                break
                
        return all_papers

    async def _fetch_all_misc(self, researcher_id: str, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """特定の研究者の全その他業績(misc)をページネーションを処理して取得する"""
        all_misc = []
        start_index = 1
        limit = 100
        headers = {"Accept": "application/json", "Accept-Language": "ja"}
        timeout = aiohttp.ClientTimeout(total=20)

        while True:
            misc_url = f"{self.api_base_url}/{researcher_id}/misc?start={start_index}&limit={limit}"
            try:
                async with session.get(misc_url, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        logger.warning(f"📚 その他業績取得でAPIエラー: status={response.status}, url={misc_url}")
                        break
                    
                    data = await response.json()
                    misc_on_page = data.get("items", [])
                    
                    if not misc_on_page:
                        logger.info("📚 全てのその他業績を取得完了。")
                        break
                    
                    all_misc.extend(misc_on_page)
                    logger.info(f"📚 その他業績を{len(misc_on_page)}件取得 (合計: {len(all_misc)}件)")
                    
                    if len(misc_on_page) < limit:
                        logger.info("📚 これが最終ページです。")
                        break
                        
                    start_index += limit
                    await asyncio.sleep(0.5)

            except asyncio.TimeoutError:
                logger.warning(f"📚 その他業績取得中にタイムアウト: {misc_url}")
                break
            except Exception as e:
                logger.error(f"📚 その他業績取得中に予期せぬエラー: {e}")
                break
                
        return all_misc

    async def fetch_researcher_data(self, researcher_id: str) -> Optional[Dict[str, Any]]:
        """ResearchMap APIから研究者情報を取得し、全論文情報も取得する"""
        try:
            async with aiohttp.ClientSession() as session:
                # 基本情報の取得
                profile_url = f"{self.api_base_url}/{researcher_id}"
                headers = {"Accept": "application/json", "Accept-Language": "ja"}
                timeout = aiohttp.ClientTimeout(total=15)
                
                async with session.get(profile_url, headers=headers, timeout=timeout) as response:
                    if response.status != 200:
                        logger.error(f"❌ ResearchMap API エラー: {response.status}")
                        if response.status == 404 or response.status >= 500:
                            logger.info("🔄 ResearchMap API利用不可のためモックデータを使用")
                            return self._create_mock_researcher_data(researcher_id)
                        return None
                    
                    data = await response.json()
                    researcher_data = self._parse_researcher_data(data)
                    
                    # 全論文を取得
                    logger.info(f"📄 {researcher_id} の全論文取得を開始...")
                    all_papers = await self._fetch_all_papers(researcher_id, session)
                    researcher_data["papers"] = all_papers if all_papers else researcher_data.get("papers", [])
                    if not all_papers:
                        logger.warning("⚠️ 全論文を取得できませんでした。基本情報に含まれる論文のみを使用します。")

                    # 全その他業績(misc)を取得
                    logger.info(f"📚 {researcher_id} の全その他業績取得を開始...")
                    all_misc = await self._fetch_all_misc(researcher_id, session)

                    # 論文とその他業績の数をカウント
                    paper_count = len(researcher_data.get("papers", []))
                    misc_count = 0

                    if all_misc:
                        logger.info(f"✅ 全{len(all_misc)}件のその他業績を取得完了。")
                        # 論文とその他業績でキーが重複する可能性を考慮し、idでユニークにする
                        existing_paper_ids = {p.get("@id") for p in researcher_data["papers"]}
                        unique_misc = [m for m in all_misc if m.get("@id") not in existing_paper_ids]
                        misc_count = len(unique_misc)
                        # 業績リストにその他業績を追加
                        researcher_data["papers"].extend(unique_misc)
                        logger.info(f"✅ その他業績{misc_count}件を業績リストに追加。")
                    else:
                        logger.warning("⚠️ その他業績は取得できませんでした。")

                    # カウントを保存
                    researcher_data["paper_count"] = paper_count
                    researcher_data["misc_count"] = misc_count
                    logger.info(f"📊 カウント結果: 論文={paper_count}件, その他業績={misc_count}件, 合計={len(researcher_data['papers'])}件")

                    return researcher_data
                    
        except asyncio.TimeoutError:
            logger.warning("⚠️ ResearchMap APIタイムアウト - モックデータを使用")
            return self._create_mock_researcher_data(researcher_id)
        except Exception as e:
            logger.error(f"❌ ResearchMap API取得エラー: {e}")
            logger.info("🔄 エラーのためモックデータを使用")
            return self._create_mock_researcher_data(researcher_id)
    
    def _parse_researcher_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """ResearchMap APIのレスポンスを解析"""
        # 基本プロフィール情報（@graphの外側）
        profile_data = {
            "user_id": data.get("rm:user_id"),
            "permalink": data.get("permalink"),
            "family_name": data.get("family_name", {}),
            "given_name": data.get("given_name", {}),
            "display_name": data.get("display_name", {}),
            "image": data.get("image"),
            "affiliations": data.get("affiliations", []),
            "degrees": data.get("degrees", []),
            "see_also": data.get("see_also", []),
            "identifiers": data.get("identifiers", {})
        }
        
        # @graph内のデータを種類別に整理
        papers = []
        projects = []
        awards = []
        research_interests = []
        research_areas = []
        presentations = []
        misc_publications = []
        industrial_properties = []
        
        # @graphが存在する場合、各タイプごとにデータを抽出
        if "@graph" in data:
            for graph_item in data.get("@graph", []):
                item_type = graph_item.get("@type")
                items = graph_item.get("items", [])
                
                if item_type == "research_projects":
                    projects.extend(items)
                    logger.info(f"🔬 研究プロジェクト {len(items)}件を抽出")
                    
                elif item_type == "awards":
                    awards.extend(items)
                    logger.info(f"🏆 受賞歴 {len(items)}件を抽出")
                    
                elif item_type == "research_interests":
                    research_interests.extend(items)
                    logger.info(f"💡 研究関心 {len(items)}件を抽出")
                    
                elif item_type == "research_areas":
                    research_areas.extend(items)
                    logger.info(f"🎯 研究領域 {len(items)}件を抽出")
                    
                elif item_type == "presentations":
                    presentations.extend(items)
                    logger.info(f"🎤 発表 {len(items)}件を抽出")
                    
                elif item_type == "misc":
                    misc_publications.extend(items)
                    logger.info(f"📚 その他出版物 {len(items)}件を抽出")
                    
                elif item_type == "industrial_property_rights":
                    industrial_properties.extend(items)
                    logger.info(f"💼 特許 {len(items)}件を抽出")
        
        # 旧形式のデータ構造にも対応（@graphがない場合）
        else:
            if "published_papers" in data:
                papers = data.get("published_papers", [])
            if "research_projects" in data:
                projects = data.get("research_projects", [])
            if "awards" in data:
                awards = data.get("awards", [])
        
        return {
            "profile": profile_data,
            "papers": papers,
            "projects": projects,
            "awards": awards,
            "research_interests": research_interests,
            "research_areas": research_areas,
            "presentations": presentations,
            "misc_publications": misc_publications,
            "industrial_properties": industrial_properties
        }
    
    async def analyze_researcher(
        self, 
        researchmap_url: str, 
        query: str,
        basic_info: Optional[Dict[str, Any]] = None,
        include_keyword_map: bool = False
    ) -> Dict[str, Any]:
        """研究者の詳細分析を実行"""
        
        # 研究者IDの抽出
        researcher_id = self.extract_researcher_id(researchmap_url)
        if not researcher_id:
            logger.error("❌ 研究者IDが抽出できません")
            return self._create_error_response("無効なResearchMap URLです")
        
        # ResearchMapからデータ取得
        researcher_data = await self.fetch_researcher_data(researcher_id)
        if not researcher_data:
            logger.error("❌ ResearchMapからデータ取得失敗")
            return self._create_error_response("ResearchMapからデータを取得できませんでした")
        
        # AI分析の実行
        analysis = await self._perform_ai_analysis(researcher_data, query, basic_info, include_keyword_map)
        
        return {
            "status": "success",
            "analysis": analysis
        }
    
    async def _perform_ai_analysis(
        self, 
        researcher_data: Dict[str, Any], 
        query: str,
        basic_info: Optional[Dict[str, Any]] = None,
        include_keyword_map: bool = False
    ) -> Dict[str, Any]:
        """AIによる研究者分析"""
        logger.info(f"キーワードマップ生成フラグ: {include_keyword_map}")
        
        profile = researcher_data.get("profile", {})
        papers = researcher_data.get("papers", [])
        projects = researcher_data.get("projects", [])
        awards = researcher_data.get("awards", [])
        research_interests = researcher_data.get("research_interests", [])
        research_areas = researcher_data.get("research_areas", [])
        presentations = researcher_data.get("presentations", [])
        industrial_properties = researcher_data.get("industrial_properties", [])
        
        # 基本情報の抽出
        researcher_name = self._get_name(profile)
        affiliation = self._get_affiliation(profile)
        
        # 統計情報
        paper_count = researcher_data.get("paper_count", 0)
        misc_count = researcher_data.get("misc_count", 0)
        # フォールバック：カウントがない場合は論文リストの全長を論文数とする
        if paper_count == 0 and misc_count == 0:
            total_papers = len(papers)
        else:
            total_papers = paper_count

        total_achievements = len(papers) # これは論文＋その他業績の合計
        total_projects = len(projects)
        total_awards = len(awards)
        total_presentations = len(presentations)
        total_patents = len(industrial_properties)
        
        # 研究キーワードの抽出
        keywords = self._extract_research_keywords(research_interests, research_areas)
        
        # 関連する上位論文の抽出
        relevant_papers = self._extract_relevant_papers(papers, query, limit=5)
        
        # 主要プロジェクトの抽出
        key_projects = self._extract_key_projects(projects, query, limit=3)
        
        # 最近の発表の抽出
        recent_presentations = self._extract_recent_presentations(presentations, limit=3)
        
        # 主要特許の抽出
        key_patents = self._extract_key_patents(industrial_properties, query, limit=3)

        # キーワード分析の実行
        keyword_analysis = None
        if include_keyword_map:
            keyword_analysis = await self._create_keyword_analysis(
                researcher_name, papers, projects, research_interests, research_areas
            )

        # スコア計算と分析レポート生成
        scores = {}
        detailed_analysis = ""
        
        if self.llm_model and self.model_name != "simple_analysis":
            scores = await self._calculate_scores(
                profile, papers, projects, awards, query,
                research_interests, research_areas
            )
            # AIによる詳細な分析レポートを生成
            detailed_analysis = await self._generate_detailed_analysis(
                profile,
                paper_count,
                misc_count,
                papers, 
                projects, 
                awards, 
                query,
                research_interests, 
                presentations, 
                industrial_properties
            )
        else:
            logger.info("🔄 LLM利用不可のため簡易分析モードを使用")
            scores = self._calculate_simple_scores(
                total_achievements, total_projects, total_awards, query, papers
            )
            detailed_analysis = self._generate_simple_analysis(
                researcher_name, query, total_achievements, total_projects
            )
        
        return {
            "researcher_name": researcher_name,
            "affiliation": affiliation,
            "scores": scores,
            "research_keywords": keywords,
            "total_papers": total_achievements, # UI表示用に合計値を維持
            "total_projects": total_projects,
            "total_awards": total_awards,
            "total_presentations": total_presentations,
            "total_patents": total_patents,
            "detailed_analysis": detailed_analysis,
            "top_papers": relevant_papers,
            "key_projects": key_projects,
            "recent_presentations": recent_presentations,
            "key_patents": key_patents,
            "keyword_analysis": keyword_analysis
        }
    
    def _get_name(self, profile: Dict) -> str:
        """プロフィールから名前を取得"""
        # display_nameがあればそれを優先
        if "display_name" in profile:
            display_name = profile.get("display_name", {})
            if isinstance(display_name, dict) and display_name.get("ja"):
                return display_name.get("ja")
            elif isinstance(display_name, dict) and display_name.get("en"):
                return display_name.get("en")
        
        # family_nameとgiven_nameから構築
        family_name = profile.get("family_name", {})
        given_name = profile.get("given_name", {})
        
        # 日本語名
        if family_name.get("ja") and given_name.get("ja"):
            return f"{family_name['ja']} {given_name['ja']}"
        
        # 英語名
        if family_name.get("en") and given_name.get("en"):
            return f"{given_name['en']} {family_name['en']}"
        
        return "名前不明"
    
    def _get_affiliation(self, profile: Dict) -> str:
        """プロフィールから所属を取得"""
        # 現在の所属情報
        if "affiliation" in profile:
            affiliation = profile.get("affiliation", {})
            # 日本語名
            if isinstance(affiliation, dict) and "ja" in affiliation:
                return affiliation.get("ja", "")
            # 英語名
            if isinstance(affiliation, dict) and "en" in affiliation:
                return affiliation.get("en", "")
            # 文字列の場合
            if isinstance(affiliation, str):
                return affiliation
        
        # affiliationsフィールド（複数形）
        if "affiliations" in profile:
            affiliations = profile.get("affiliations", [])
            if affiliations and len(affiliations) > 0:
                latest = affiliations[0]
                if isinstance(latest, dict):
                    return latest.get("affiliation", {}).get("ja", latest.get("affiliation", {}).get("en", ""))
        
        return "所属不明"
    
    def _extract_relevant_papers(self, papers: List[Dict], query: str, limit: int = 5) -> List[Dict]:
        """クエリに関連する論文を抽出"""
        relevant_papers = []
        query_lower = query.lower()
        
        for paper in papers:
            # タイトルの取得（ResearchMapの実際の構造に合わせる）
            # paper_title または published_paper_title の両方に対応
            paper_title_data = paper.get("paper_title") or paper.get("published_paper_title", {})
            
            if isinstance(paper_title_data, dict):
                title_ja = paper_title_data.get("ja", "")
                title_en = paper_title_data.get("en", "")
            else:
                title_ja = ""
                title_en = ""
            
            # 旧形式のフィールドも確認
            if not title_ja and "titles" in paper:
                for title in paper.get("titles", []):
                    if title.get("lang") == "ja":
                        title_ja = title.get("title", "")
                    elif title.get("lang") == "en":
                        title_en = title.get("title", "")
            
            # 関連性チェック
            relevance_score = 0
            if query_lower in title_ja.lower():
                relevance_score += 2
            if query_lower in title_en.lower():
                relevance_score += 1
            
            # キーワードチェック
            for keyword in query_lower.split():
                if keyword in title_ja.lower() or keyword in title_en.lower():
                    relevance_score += 0.5
            
            if relevance_score > 0 or len(relevant_papers) < 2:  # 最低2件は含める
                # 年の取得
                year = paper.get("publication_date", "不明")
                if isinstance(year, dict):
                    year = year.get("year", "不明")
                elif isinstance(year, str) and len(year) >= 4:
                    year = year[:4]
                
                # ジャーナル名の取得
                journal = ""
                if "identifiers" in paper:
                    journal = paper.get("identifiers", {}).get("misc", [])
                    if isinstance(journal, list) and len(journal) > 0:
                        journal = journal[0]
                    else:
                        journal = ""
                
                if not journal and "misc" in paper:
                    journal = paper.get("misc", "")
                
                relevant_papers.append({
                    "year": year,
                    "title_ja": title_ja,
                    "title_en": title_en,
                    "journal": journal,
                    "relevance_score": relevance_score
                })
        
        # 関連性でソート
        relevant_papers.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # スコアを削除して返す
        for paper in relevant_papers[:limit]:
            paper.pop("relevance_score", None)
        
        return relevant_papers[:limit]
    
    def _extract_key_projects(self, projects: List[Dict], query: str, limit: int = 3) -> List[Dict]:
        """主要プロジェクトを抽出"""
        key_projects = []
        
        for i, project in enumerate(projects[:limit]):  # 最新のものから
            # デバッグ: プロジェクト全体の構造を確認
            logger.info(f"プロジェクト{i+1}のデータ構造: {json.dumps(project, ensure_ascii=False, indent=2)[:500]}...")
            
            # タイトルの取得 - ResearchMap APIの実際のフィールド名に対応
            # research_project_title または project_title の両方に対応
            project_title = project.get("research_project_title") or project.get("project_title", {})
            logger.info(f"project_title取得結果: {project_title}, 型: {type(project_title)}")
            
            # project_titleが文字列の場合とオブジェクトの場合に対応
            if isinstance(project_title, str):
                title = project_title
                logger.info(f"文字列型のタイトル: {title}")
            elif isinstance(project_title, dict):
                title_ja = project_title.get("ja")
                title_en = project_title.get("en")
                logger.info(f"辞書型のタイトル - ja: {repr(title_ja)}, en: {repr(title_en)}")
                
                # 日本語タイトルを優先
                if title_ja is not None and title_ja != "":
                    title = title_ja
                elif title_en is not None and title_en != "":
                    title = title_en
                else:
                    title = "タイトル不明"
                    logger.warning(f"タイトルが取得できません: {project_title}")
            else:
                title = "タイトル不明"
                logger.warning(f"予期しないproject_titleの型: {type(project_title)}, 値: {project_title}")
            
            # 期間の取得
            from_date = project.get("from_date", "")
            to_date = project.get("to_date", "")
            
            # 年を抽出
            start_year = "?"
            end_year = "継続中"
            
            if from_date:
                if isinstance(from_date, str) and len(from_date) >= 4:
                    start_year = from_date[:4]
                elif isinstance(from_date, dict):
                    start_year = from_date.get("year", "?")
            
            if to_date:
                if isinstance(to_date, str) and len(to_date) >= 4:
                    end_year = to_date[:4]
                elif isinstance(to_date, dict):
                    end_year = to_date.get("year", "継続中")
            
            period = f"{start_year}-{end_year}"
            
            # 最終的なタイトルの確認
            final_title = str(title) if title else "タイトル不明"
            logger.info(f"最終タイトル: {final_title}")
            
            key_projects.append({
                "title": final_title,
                "period": period
            })
        
        return key_projects
    
    def _extract_research_keywords(self, research_interests: List[Dict], research_areas: List[Dict]) -> List[str]:
        """研究キーワードを抽出"""
        keywords = []
        
        # 研究関心からキーワードを抽出
        for interest in research_interests:
            keyword_dict = interest.get("keyword", {})
            if keyword_dict.get("ja"):
                keywords.append(keyword_dict["ja"])
            elif keyword_dict.get("en"):
                keywords.append(keyword_dict["en"])
        
        # 研究領域からキーワードを抽出
        for area in research_areas:
            research_field = area.get("research_field", {})
            if research_field.get("ja"):
                keywords.append(research_field["ja"])
            
            research_keyword = area.get("research_keyword", {})
            if isinstance(research_keyword, dict) and research_keyword.get("ja"):
                keywords.append(research_keyword["ja"])
            elif isinstance(research_keyword, str) and research_keyword:
                # カンマ区切りのキーワードを分割
                keywords.extend([k.strip() for k in research_keyword.split("、")])
        
        # 重複を除去
        return list(dict.fromkeys(keywords))

    def _tokenize_text(self, text: str) -> List[str]:
        """テキストをトークン化し、ストップワードを除去"""
        tokens = re.findall(r'\b\w+\b', text.lower())
        filtered_tokens = [
            token for token in tokens 
            if token not in JAPANESE_STOPWORDS and 
               token not in ENGLISH_STOPWORDS and 
               len(token) > 1 # 1文字の単語は除外
        ]
        return filtered_tokens

    # --- ▼▼▼ ここから修正・追加されたメソッド群 ▼▼▼ ---
    
    async def _create_keyword_analysis(
        self,
        researcher_name: str,
        papers: List[Dict],
        projects: List[Dict],
        research_interests: List[Dict],
        research_areas: List[Dict]
    ) -> Dict[str, Any]:
        """
        キーワードの分析を行い、学問領域、研究トレンド、LLMコメントを生成する（最終確定版）
        """
        base_result = {
            "academic_fields": [],
            "research_trends": {},
            "word_cloud": [],
            "llm_comment": "LLMによる分析コメントは生成されませんでした。"
        }

        if not self.llm_model:
            logger.warning("⚠️ LLMモデルが利用できないため、キーワード分析をスキップします。")
            base_result["llm_comment"] = "LLMモデルが利用できないため、詳細なキーワード分析はできません。"
            return base_result

        try:
            all_texts = []
            paper_info = [] # (title, year) のタプルを格納

            for paper in papers:
                title_data = paper.get("paper_title") or paper.get("published_paper_title", {})
                title_text = ""
                if isinstance(title_data, dict):
                    title_text = title_data.get("ja", "") or title_data.get("en", "")
                
                if title_text: 
                    all_texts.append(title_text)
                    year_str = paper.get("publication_date", "")
                    year = None
                    if isinstance(year_str, dict):
                        year_str = year_str.get("year", "")
                    if isinstance(year_str, str) and len(year_str) >= 4 and year_str[:4].isdigit():
                        year = int(year_str[:4])
                    if year:
                        paper_info.append((title_text, year))

            for project in projects:
                title_data = project.get("research_project_title") or project.get("project_title", {})
                if isinstance(title_data, str):
                    all_texts.append(title_data)
                elif isinstance(title_data, dict):
                    all_texts.append(title_data.get("ja", "") or title_data.get("en", ""))
            
            all_texts.extend(self._extract_research_keywords(research_interests, research_areas))

            if not all_texts:
                base_result["llm_comment"] = "分析できるテキストデータがありませんでした。"
                return base_result

            combined_text = "\n".join(filter(None, all_texts))

            # 1. 学問領域、ワードクラウド、コメントをLLMで生成
            prompt1 = f"""研究者「{researcher_name}」氏の以下の研究活動テキストを分析し、主要な学問領域、頻出単語、そして総評コメントを抽出してください。

テキストデータ:
{combined_text}

出力は以下の形式で、各セクションを `###` で区切ってください。

### ACADEMIC_FIELDS
学問領域1; 簡単な説明1
学問領域2; 簡単な説明2

### WORD_CLOUD
頻出単語1; 95
Frequent Word 2; 80

### LLM_COMMENT
ここから総評コメントを開始。{researcher_name}氏の専門性や主要な研究テーマについて、同氏の研究活動を評価する形で簡潔にまとめてください。
"""
            llm_response_text = await self._generate_llm_response(prompt1, max_tokens=1500)
            if not llm_response_text:
                base_result["llm_comment"] = "LLMからの応答がありませんでした。"
                return base_result

            analysis = self._parse_llm_text_response(llm_response_text)

            # 2. 研究トレンドを計算
            if analysis["academic_fields"] and paper_info:
                # 論文タイトルと学問領域の関連付けをLLMに依頼
                field_names = [f["field"] for f in analysis["academic_fields"]]
                paper_titles = [p[0] for p in paper_info]
                
                prompt2 = f"""以下の論文タイトルのリストを、指定された学問領域のいずれか一つに分類してください。

学問領域リスト:
{', '.join(field_names)}

論文タイトルリスト:
{', '.join(paper_titles)}

出力形式は「論文タイトル; 学問領域」の形式で、一行に一つずつ記述してください。
例:
論文タイトルA; 学問領域1
論文タイトルB; 学問領域2
"""
                categorization_response = await self._generate_llm_response(prompt2, max_tokens=2000)
                
                paper_to_field = {}
                for line in categorization_response.split('\n'):
                    parts = [p.strip() for p in line.split(';', 1)]
                    if len(parts) == 2:
                        paper_to_field[parts[0]] = parts[1]

                # トレンドを計算
                papers_by_year = Counter(p[1] for p in paper_info)
                field_papers_by_year = collections.defaultdict(lambda: collections.defaultdict(int))

                for title, year in paper_info:
                    field = paper_to_field.get(title)
                    if field in field_names:
                        field_papers_by_year[field][year] += 1
                
                calculated_trends = {}
                for field_name, year_counts in field_papers_by_year.items():
                    calculated_trends[field_name] = {}
                    for year in sorted(year_counts.keys()):
                        if papers_by_year.get(year, 0) > 0:
                            calculated_trends[field_name][str(year)] = round(year_counts[year] / papers_by_year[year], 2)
                
                analysis["research_trends"] = calculated_trends

            return analysis

        except Exception as e:
            logger.error(f"❌ LLMキーワード分析中にエラー: {e}", exc_info=True)
            base_result["llm_comment"] = f"キーワード分析中にエラーが発生しました: {str(e)}"
            return base_result

    def _parse_llm_text_response(self, text: str) -> Dict[str, Any]:
        """LLMのテキスト応答をパースして辞書に変換する"""
        analysis = {
            "academic_fields": [],
            "word_cloud": [],
            "llm_comment": "コメントが抽出できませんでした。",
            "research_trends": {}
        }

        sections = {
            "ACADEMIC_FIELDS": [],
            "WORD_CLOUD": [],
            "LLM_COMMENT": []
        }
        current_section = None

        for line in text.split('\n'):
            line = line.strip()
            if line.startswith("###"):
                current_section = line.replace("###", "").strip()
            elif current_section and line:
                if current_section in sections:
                    sections[current_section].append(line)
        
        # Academic Fields
        for line in sections["ACADEMIC_FIELDS"]:
            parts = [p.strip() for p in line.split(';', 1)]
            if len(parts) == 2:
                analysis["academic_fields"].append({"field": parts[0], "description": parts[1]})

        # Word Cloud
        for line in sections["WORD_CLOUD"]:
            parts = [p.strip() for p in line.split(';', 1)]
            if len(parts) == 2:
                try:
                    size = int(parts[1])
                    analysis["word_cloud"].append({"text": parts[0], "size": size})
                except ValueError:
                    logger.warning(f"ワードクラウドのサイズ変換に失敗: {parts[1]}")

        # LLM Comment
        if sections["LLM_COMMENT"]:
            analysis["llm_comment"] = "\n".join(sections["LLM_COMMENT"])

        return analysis

    def _extract_json_from_response(self, text: str) -> Optional[str]:
        """LLMの応答からJSON文字列を抽出する"""
        # 1. ```json ... ``` コードブロックを探す
        match = re.search(r"```(?:json)?\s*({.*?})\s*```", text, re.DOTALL)
        if match:
            return match.group(1)
        
        # 2. コードブロックがない場合、最初の '{' から最後の '}' までを抽出
        start_index = text.find('{')
        end_index = text.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            return text[start_index:end_index+1]
            
        return None

    def _fix_malformed_json(self, json_string: str) -> str:
        """
        LLMが生成しがちな不正なJSONを修正する（堅牢な複数パターン版）
        """
        # 1. 末尾のカンマを削除 (例: [1, 2,])
        fixed_string = re.sub(r",\s*([}\]])", r"\1", json_string)

        # 2. 欠落しているカンマを追加する
        # パターン: (値の終わり)(空白)(次のキーの始まり) -> (値の終わり),(空白)(次のキーの始まり)
        # 値の終わり: ", }, ], true, false, または数字
        # 空白: \s+ (改行を含む)
        # 次のキーの始まり: "
        
        # 文字列の後: " ... " "..." -> " ... ", "..."
        fixed_string = re.sub(r'("\s*)\n(\s*")', r'\1,\n\2', fixed_string)
        # オブジェクトの後: } "..." -> }, "..."
        fixed_string = re.sub(r'(\}\s*)\n(\s*")', r'\1,\n\2', fixed_string)
        # 配列の後: ] "..." -> ], "..."
        fixed_string = re.sub(r'(\]\s*)\n(\s*")', r'\1,\n\2', fixed_string)
        # 数値の後: 123 "..." -> 123, "..."
        fixed_string = re.sub(r'(\d\s*)\n(\s*")', r'\1,\n\2', fixed_string)
        # ブール値/nullの後: true "..." -> true, "..."
        fixed_string = re.sub(r'(true|false|null)(\s*)\n(\s*")', r'\1,\2\n\3', fixed_string)

        return fixed_string

    async def _generate_llm_response(self, prompt: str, max_tokens: int = 200) -> str:
        """LLM応答を生成する共通関数"""
        if not self.llm_model:
            return ""
        try:
            response = await self.llm_model.generate_content_async(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": max_tokens, "top_p": 0.8}
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"LLM応答生成エラー: {e}")
            return ""

    def _extract_key_patents(self, industrial_properties: List[Dict], query: str, limit: int = 3) -> List[Dict]:
        """主要特許を抽出"""
        key_patents = []
        
        # 特許権のみをフィルタリング
        patents = [ip for ip in industrial_properties if ip.get("industrial_property_right_type") == "patent_right"]
        
        for i, patent in enumerate(patents[:limit]):
            # タイトルの取得
            patent_title = patent.get("industrial_property_right_title", {})
            
            if isinstance(patent_title, str):
                title = patent_title
            elif isinstance(patent_title, dict):
                title = patent_title.get("ja", "")
                if not title:
                    title = patent_title.get("en", "")
            else:
                title = "タイトル不明"
            
            # 出願番号・特許番号
            application_number = patent.get("application_number", "")
            patent_number = patent.get("patent_number", "")
            
            # 出願日
            application_date = patent.get("application_date", "")
            if isinstance(application_date, dict):
                year = application_date.get("year", "")
                month = application_date.get("month", "")
                day = application_date.get("day", "")
                application_date = f"{year}/{month}/{day}" if year else "不明"
            
            # 特許権者（出願人）の取得
            applicants = patent.get("applicants", [])
            applicant_names = []
            for applicant in applicants:
                if isinstance(applicant, dict):
                    applicant_info = applicant.get("applicant", {})
                    if isinstance(applicant_info, dict):
                        applicant_names.append(applicant_info.get("ja", applicant_info.get("en", "")))
                    elif isinstance(applicant_info, str):
                        applicant_names.append(applicant_info)
            
            # 特許権者が取得できない場合は発明者を使用（フォールバック）
            if not applicant_names:
                inventors = patent.get("inventors", {})
                if isinstance(inventors, dict) and "ja" in inventors:
                    inventor_list = inventors.get("ja", [])
                    for inventor in inventor_list:
                        if isinstance(inventor, dict):
                            name = inventor.get("name", {})
                            if isinstance(name, dict):
                                applicant_names.append(name.get("ja", name.get("en", "")))
                            elif isinstance(name, str):
                                applicant_names.append(name)
            
            key_patents.append({
                "title": title,
                "application_number": application_number,
                "patent_number": patent_number,
                "application_date": application_date,
                "patent_holders": "、".join(applicant_names) if applicant_names else "特許権者不明"
            })
        
        return key_patents
    
    def _extract_recent_presentations(self, presentations: List[Dict], limit: int = 3) -> List[Dict]:
        """最近の発表を抽出"""
        recent_presentations = []
        
        # 日付でソート（新しい順）
        sorted_presentations = sorted(
            presentations,
            key=lambda x: x.get("publication_date", ""),
            reverse=True
        )
        
        for presentation in sorted_presentations[:limit]:
            title = presentation.get("presentation_title", {})
            title_text = title.get("ja", title.get("en", "N/A"))
            
            event = presentation.get("event", {})
            event_name = event.get("ja", event.get("en", "N/A"))
            
            date = presentation.get("publication_date", "N/A")
            
            recent_presentations.append({
                "title": title_text,
                "event": event_name,
                "date": date,
                "type": presentation.get("presentation_type", "N/A")
            })
        
        return recent_presentations
    
    async def _generate_detailed_analysis(
        self,
        profile: Dict,
        paper_count: int,
        misc_count: int,
        papers: List[Dict],
        projects: List[Dict],
        awards: List[Dict],
        query: str,
        research_interests: List[Dict] = None,
        presentations: List[Dict] = None,
        industrial_properties: List[Dict] = None
    ) -> str:
        """LLMによる詳細分析の生成"""
        
        research_interests = research_interests or []
        presentations = presentations or []
        industrial_properties = industrial_properties or []
        
        keywords = self._extract_research_keywords(research_interests, [])
        
        paper_titles_text = ""
        for i, paper in enumerate(papers[:5]):
            paper_title_data = paper.get("paper_title") or paper.get("published_paper_title", {})
            title = ""
            if isinstance(paper_title_data, dict):
                title = paper_title_data.get("ja", paper_title_data.get("en", ""))
            if title:
                paper_titles_text += f"- {title}\n"

        prompt = f"""
あなたは、企業の研究開発担当者向けに、大学研究者の専門性を評価するプロのアナリストです。
以下の研究者情報と検索クエリを基に、プロフェッショナルな視点から詳細な分析レポートを作成してください。

### 研究者情報
- 研究キーワード: {', '.join(keywords) if keywords else 'N/A'}
- 論文数: {paper_count}件
- その他業績数: {misc_count}件
- プロジェクト数: {len(projects)}件
- 受賞歴: {len(awards)}件
- 発表数: {len(presentations)}件
- 特許数: {len(industrial_properties)}件
- 主要論文・業績（最新5件）:
{paper_titles_text if paper_titles_text else "N/A"}

### 検索クエリ
「{query}」

### 分析レポートの要件
以下の「高品質な分析レポートの例」を参考に、同様の構成と品質で、今回の研究者の分析レポートを作成してくだ��い。
各項目について、単に情報を羅列するのではなく、検索クエリとの関連性を深く考察し、具体的な評価や見解を記述してください。
特に「実績・影響力」の項目では、論文数とその他業績数を分けて評価してください。

---
### 高品質な分析レポートの例
（検索クエリ：「ナノ材料、人工知能、再生医療」の場合）

1.  **技術的関連性**: 「ナノ材料」は、グラフェンやカーボンナノチューブなどの材料を指し、AIハードウェアの基盤として利用されています。「人工知能」は、リザバー演算子やニューロモルフィックAIハードウェアの開発そのものを指します。一方、「再生医療」との直接的な関連性は、現時点では見当たりません。しかし、脳型デバイスの開発は、将来的に脳機能の解明や、神経細胞のシミュレーションに繋がり、再生医療分野への応用可能性を秘めていると言えます。
2.  **実績・影響力**: 論文数158件、その他業績25件、プロジェクト数20件、発表数20件と��う実績は、活発な研究活動を示しています。特に論文数が多く、学術的な貢献度が高いと評価できます。受賞歴2件は、研究成果の質を裏付ける指標となります。特許取得がない点は、基礎研究に重点を置いているか、あるいは知的財産戦略が異なる可能性を示唆しています。
3.  **実用化可能性**: 産学連携プロジェクトの実績があり、企業との共同研究に積極的であると推測されます。特に、AIハードウェアに関する研究は、半導体メーカーやデバイスメーカーとの連携が期待できます。
---

### あなたが作成する分析レポート
（検索クエリ：「{query}」の場合）

1.  **技術的関連性**:
2.  **実績・影響力**:
3.  **実用化可能性**:

上記3つの項目について、400字〜500字程度で記述してください。
"""
        
        try:
            response = self.llm_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.4,
                    "max_output_tokens": 800,
                    "top_p": 0.9
                }
            )
            return response.text.strip()
                
        except Exception as e:
            logger.error(f"❌ LLM分析エラー: {e}")
            return self._generate_simple_analysis(
                self._get_name(profile), query, len(papers), len(projects)
            )
    
    async def _calculate_scores(
        self,
        profile: Dict,
        papers: List[Dict],
        projects: List[Dict],
        awards: List[Dict],
        query: str,
        research_interests: List[Dict] = None,
        research_areas: List[Dict] = None
    ) -> Dict[str, int]:
        """ハイブリッドスコアの計算（ルールベース + LLM）"""
        
        # 1. ルールベースのスコア計算（改良版）
        rule_based_scores = self._calculate_rule_based_scores(
            papers, projects, awards, query, research_interests, research_areas
        )
        
        # 2. LLMが利用可能な場合はLLMベースのスコアも計算
        if self.llm_model:
            try:
                llm_scores = await self._calculate_llm_based_scores(
                    profile, papers, projects, awards, query, research_interests
                )
                
                # 3. ハイブリッドスコアの計算（重み付け平均）
                hybrid_scores = self._calculate_hybrid_scores(
                    rule_based_scores, llm_scores, weight=0.6  # LLMの重みを60%に
                )
                
                return hybrid_scores
                
            except Exception as e:
                logger.warning(f"LLMスコア計算失敗、ルールベースのみ使用: {e}")
                return rule_based_scores
        else:
            # LLMが使えない場合はルールベースのみ
            return rule_based_scores
    
    def _calculate_rule_based_scores(
        self,
        papers: List[Dict],
        projects: List[Dict],
        awards: List[Dict],
        query: str,
        research_interests: List[Dict] = None,
        research_areas: List[Dict] = None
    ) -> Dict[str, int]:
        """改良版ルールベーススコア計算"""
        
        technical_relevance = self._calculate_technical_relevance_improved(
            papers, projects, query, research_interests, research_areas
        )
        achievements = self._calculate_achievements(papers, projects, awards)
        practical_applicability = self._calculate_practical_applicability(projects)
        
        total = technical_relevance + achievements + practical_applicability
        
        return {
            "total": total,
            "technical_relevance": technical_relevance,
            "achievements": achievements,
            "practical_applicability": practical_applicability,
            "calculation_method": "rule_based"
        }
    
    def _extract_query_keywords(self, query: str) -> List[str]:
        """クエリからキーワードを抽出（同義語展開含む）"""
        query_lower = query.lower()
        keywords = [query_lower]  # 元のクエリ
        
        # 「がん」「癌」の同義語処理
        if "がん" in query_lower:
            keywords.append(query_lower.replace("がん", "癌"))
            keywords.append(query_lower.replace("がん", ""))  # 「腎臓がん」→「腎臓」
            # 部分キーワード
            keywords.append("がん")
            keywords.append("癌")
        if "癌" in query_lower:
            keywords.append(query_lower.replace("癌", "がん"))
            keywords.append(query_lower.replace("癌", ""))
            keywords.append("癌")
            keywords.append("がん")
        
        # 「腎臓」と「腎」の同義語処理
        if "腎臓" in query_lower:
            keywords.append(query_lower.replace("腎臓", "腎"))
            keywords.append("腎臓")
            keywords.append("腎")
        elif "腎" in query_lower:
            keywords.append(query_lower.replace("腎", "腎臓"))
            keywords.append("腎")
            keywords.append("腎臓")
        
        # 「治療」関連
        if "治療" in query_lower:
            keywords.append("治療")
            keywords.append("療法")
            keywords.append("手術")
        
        # スペースで分割されたキーワードも追加
        keywords.extend(query_lower.split())
        
        # 重複を除去して返す
        return list(set(keywords))
    
    def _calculate_technical_relevance_improved(
        self,
        papers: List[Dict],
        projects: List[Dict],
        query: str,
        research_interests: List[Dict] = None,
        research_areas: List[Dict] = None
    ) -> int:
        """改良版技術的関連性スコアの計算（最大40点）"""
        score = 0
        query_lower = query.lower()
        
        # クエリをキーワードに分解（同義語展開含む）
        query_keywords = self._extract_query_keywords(query_lower)
        
        # 1. 研究キーワード・研究分野との関連性（最大15点）
        keyword_score = 0
        
        # research_interestsから
        if research_interests:
            for interest in research_interests:
                keyword_dict = interest.get("keyword", {})
                research_keyword = keyword_dict.get("ja", "").lower()
                
                # 完全一致
                if query_lower in research_keyword or research_keyword in query_lower:
                    keyword_score += 5
                # 部分一致
                elif any(kw in research_keyword for kw in query_keywords):
                    keyword_score += 3
        
        # research_areasから
        if research_areas:
            for area in research_areas:
                research_field = area.get("research_field", {})
                field_name = research_field.get("ja", "").lower()
                
                research_keyword = area.get("research_keyword", {})
                if isinstance(research_keyword, dict):
                    keyword_text = research_keyword.get("ja", "").lower()
                elif isinstance(research_keyword, str):
                    keyword_text = research_keyword.lower()
                else:
                    keyword_text = ""
                
                # フィールドまたはキーワードとの一致をチェック
                for text in [field_name, keyword_text]:
                    if text:
                        if any(kw in text for kw in query_keywords):
                            keyword_score += 2
        
        score += min(15, keyword_score)
        
        # 2. プロジェクトとの関連性（最大10点）
        project_score = 0
        for project in projects:
            project_title = project.get("research_project_title") or project.get("project_title", {})
            
            if isinstance(project_title, str):
                title = project_title.lower()
            elif isinstance(project_title, dict):
                title = project_title.get("ja", "").lower()
            else:
                title = ""
            
            # 完全一致または部分一致をチェック
            if query_lower in title:
                project_score += 5
            elif any(kw in title for kw in query_keywords):
                project_score += 3
        
        score += min(10, project_score)
        
        # 3. 論文タイトルとの関連性（最大10点）
        paper_score = 0
        for paper in papers:
            paper_title_data = paper.get("paper_title") or paper.get("published_paper_title", {})
            
            if isinstance(paper_title_data, dict):
                title_ja = paper_title_data.get("ja", "").lower()
                title_en = paper_title_data.get("en", "").lower()
            else:
                title_ja = ""
                title_en = ""
            
            # 完全一致または部分一致をチェック
            if query_lower in title_ja or query_lower in title_en:
                paper_score += 2  # 完全一致
            elif any(kw in title_ja or kw in title_en for kw in query_keywords):
                paper_score += 1  # 部分一致
        
        score += min(10, paper_score)
        
        # 4. 研究の最新性（最大5点）
        recent_items = 0
        
        # 最近の論文
        for paper in papers[:5]:
            year = paper.get("publication_date", "")
            if isinstance(year, dict):
                year = year.get("year", 0)
            elif isinstance(year, str) and len(year) >= 4:
                year = int(year[:4]) if year[:4].isdigit() else 0
            else:
                year = 0
            
            if year >= 2020:
                recent_items += 1
        
        # 最近のプロジェクト
        for project in projects[:3]:
            to_date = project.get("to_date", "")
            if not to_date or to_date == "継続中":
                recent_items += 1
        
        score += min(5, recent_items)
        
        return min(40, score)  # 最大40点
    
    def _calculate_achievements(self, papers: List[Dict], projects: List[Dict], awards: List[Dict]) -> int:
        """実績・影響力スコアの計算（最大30点）"""
        score = 0
        
        # 論文数（最大10点）
        if len(papers) >= 50:
            score += 10
        elif len(papers) >= 30:
            score += 8
        elif len(papers) >= 20:
            score += 6
        elif len(papers) >= 10:
            score += 4
        elif len(papers) >= 5:
            score += 2
        
        # プロジェクト数（最大10点）
        if len(projects) >= 10:
            score += 10
        elif len(projects) >= 5:
            score += 7
        elif len(projects) >= 3:
            score += 5
        elif len(projects) >= 1:
            score += 3
        
        # 受賞歴（最大10点）
        score += min(10, len(awards) * 3)
        
        return score
    
    def _calculate_practical_applicability(self, projects: List[Dict]) -> int:
        """実用化可能性スコアの計算（最大30点）"""
        score = 0
        
        # プロジェクト数ベース
        if len(projects) >= 5:
            score += 15
        elif len(projects) >= 3:
            score += 10
        elif len(projects) >= 1:
            score += 5
        
        # 産学連携プロジェクトの推定（タイトルから）
        industry_keywords = ["企業", "産学", "実用", "開発", "製品", "システム", "応用"]
        industry_projects = 0
        
        for project in projects:
            # ResearchMap APIの実際のフィールド名に対応
            project_title = project.get("research_project_title") or project.get("project_title", {})
            
            if isinstance(project_title, str):
                title = project_title
            elif isinstance(project_title, dict):
                title = project_title.get("ja", "")
                if not title:
                    title = project_title.get("en", "")
            else:
                title = ""
            
            title_text = title.lower()
            if any(keyword in title_text for keyword in industry_keywords):
                industry_projects += 1
        
        score += min(15, industry_projects * 5)
        
        return score
    
    def _calculate_simple_scores(
        self,
        total_papers: int,
        total_projects: int,
        total_awards: int,
        query: str,
        papers: List[Dict]
    ) -> Dict[str, int]:
        """LLMを使わない簡易スコア計算"""
        
        # 簡易的な技術的関連性（論文タイトルのキーワードマッチ）
        technical_relevance = min(40, total_papers)
        
        # 実績スコア
        achievements = min(30, (total_papers // 3) + (total_projects * 2) + (total_awards * 3))
        
        # 実用化可能性
        practical_applicability = min(30, total_projects * 5)
        
        return {
            "total": technical_relevance + achievements + practical_applicability,
            "technical_relevance": technical_relevance,
            "achievements": achievements,
            "practical_applicability": practical_applicability
        }
    
    def _generate_simple_analysis(
        self,
        researcher_name: str,
        query: str,
        total_papers: int,
        total_projects: int
    ) -> str:
        """LLMを使わない簡易分析"""
        return f"""この研究者は「{query}」に関連する研究を行っており、以下の特徴があります：

1. 研究実績：{total_papers}件の論文を発表しており、活発な研究活動を行っています。

2. プロジェクト実績：{total_projects}件の研究プロジェクトに参画しており、実践的な研究経験を有しています。

3. 専門性：{query}分野での研究活動が確認でき、プロジェクトへの貢献が期待できます。

総合的に、この研究者は{query}の分野で一定の専門性と実績を持っており、プロジェクトへの参画が有益と考えられます。"""
    
    async def _calculate_llm_based_scores(
        self,
        profile: Dict,
        papers: List[Dict],
        projects: List[Dict],
        awards: List[Dict],
        query: str,
        research_interests: List[Dict] = None
    ) -> Dict[str, int]:
        """LLMを使用したスコア計算"""
        
        # 研究キーワードを抽出
        keywords = self._extract_research_keywords(research_interests or [], [])
        
        # プロジェクトタイトルのリスト作成
        project_titles = []
        for project in projects[:5]:  # 最新5件
            project_title = project.get("research_project_title") or project.get("project_title", {})
            if isinstance(project_title, str):
                project_titles.append(project_title)
            elif isinstance(project_title, dict):
                title = project_title.get("ja", project_title.get("en", ""))
                if title:
                    project_titles.append(title)
        
        # 構造化されたプロンプト
        prompt = f"""以下の研究者情報を基に、検索クエリ「{query}」との関連性を評価してください。

【研究者情報】
- 研究キーワード: {''.join(keywords[:10]) if keywords else 'なし'}
- 論文数: {len(papers)}件
- プロジェクト: {project_titles}
- 受賞歴: {len(awards)}件

【評価基準】
1. 技術的関連性（0-40点）
   - 研究内容とクエリの直接的な関連性
   - 研究キーワードの一致度
   - 関連論文・プロジェクトの有無
   - 同義語や類似概念も考慮（例：「癌」と「がん」、「腎」と「腎臓」）

2. 実績・影響力（0-30点）
   - 論文数と質
   - プロジェクト実績
   - 受賞歴

3. 実用化可能性（0-30点）
   - 産学連携の実績
   - 実用的なプロジェクトの有無
   - 治療法や技術の実装可能性

【重要】
- 各項目の点数は必ず指定された範囲内で採点してください
- 部分的な関連性も適切に評価してください
- 「腎癌」と「腎臓がん」のような同義語は同等に扱ってください

【出力形式】
必ず以下のJSON形式で出力してください：
{{
    "technical_relevance": 数値（0-40）,
    "achievements": 数値（0-30）,
    "practical_applicability": 数値（0-30）,
    "reasoning": {{
        "technical_relevance": "採点理由",
        "achievements": "採点理由",
        "practical_applicability": "採点理由"
    }}
}}"""
        
        try:
            response = self.llm_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0,  # 一貫性のため
                    "max_output_tokens": 400,
                    "top_p": 0.8
                }
            )
            response_text = response.text.strip()
            
            # JSONを抽出（マークダウンコードブロックに対応）
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # JSONパース
            scores = json.loads(response_text)
            
            # スコアの範囲チェックと型変換
            scores["technical_relevance"] = int(min(40, max(0, scores.get("technical_relevance", 0))))
            scores["achievements"] = int(min(30, max(0, scores.get("achievements", 0))))
            scores["practical_applicability"] = int(min(30, max(0, scores.get("practical_applicability", 0))))
            scores["total"] = scores["technical_relevance"] + scores["achievements"] + scores["practical_applicability"]
            scores["calculation_method"] = "llm_based"
            
            # reasoning情報も保持
            if "reasoning" in scores:
                scores["score_reasons"] = scores.pop("reasoning")
            
            logger.info(f"LLMスコア計算成功: {scores}")
            return scores
            
        except Exception as e:
            logger.error(f"LLMスコア計算エラー: {e}")
            # エラー時はルールベースにフォールバック
            raise e
    
    def _calculate_hybrid_scores(
        self,
        rule_based_scores: Dict[str, int],
        llm_scores: Dict[str, int],
        weight: float = 0.5
    ) -> Dict[str, int]:
        """ルールベースとLLMスコアの加重平均"""
        
        hybrid_scores = {}
        
        # 各スコアの加重平均を計算
        for key in ["technical_relevance", "achievements", "practical_applicability"]:
            rule_score = rule_based_scores.get(key, 0)
            llm_score = llm_scores.get(key, 0)
            
            # 加重平均（小数点以下は四捨五入）
            hybrid_scores[key] = int(round(
                rule_score * (1 - weight) + llm_score * weight
            ))
        
        # 合計スコア
        hybrid_scores["total"] = sum([
            hybrid_scores["technical_relevance"],
            hybrid_scores["achievements"],
            hybrid_scores["practical_applicability"]
        ])
        
        # メタ情報
        hybrid_scores["calculation_method"] = "hybrid"
        hybrid_scores["rule_weight"] = 1 - weight
        hybrid_scores["llm_weight"] = weight
        
        # 各手法のスコアも保持（デバッグ用）
        hybrid_scores["rule_based_scores"] = rule_based_scores
        hybrid_scores["llm_scores"] = llm_scores
        
        # LLMの採点理由があれば含める
        if "score_reasons" in llm_scores:
            hybrid_scores["score_reasons"] = llm_scores["score_reasons"]
        
        logger.info(f"ハイブリッドスコア計算完了: {hybrid_scores}")
        return hybrid_scores
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """エラーレスポンスの作成"""
        return {
            "status": "error",
            "error": error_message,
            "analysis": None
        }
    
    def _create_mock_researcher_data(self, researcher_id: str) -> Dict[str, Any]:
        """モック研究者データの作成（API利用不可時）"""
        return {
            "profile": {
                "user_id": researcher_id,
                "permalink": f"https://researchmap.jp/{researcher_id}",
                "display_name": {"ja": "サンプル研究者"},
                "affiliations": [{
                    "affiliation": {"ja": "サンプル大学"}
                }]
            },
            "papers": [
                {
                    "paper_title": {"ja": "サンプル論文1：AI材料探索の手法提案"},
                    "publication_date": "2023"
                },
                {
                    "paper_title": {"ja": "サンプル論文2：マテリアルズインフォマティクスとベイズ最適化"},
                    "publication_date": "2024"
                }
            ],
            "projects": [
                {
                    "research_project_title": {"ja": "サンプルプロジェクト：人工知能を用いた新技術の開発"},
                    "from_date": "2023",
                    "to_date": "継続中"
                }
            ],
            "awards": [
                {
                    "award_title": "優秀研究賞",
                    "award_date": "2023"
                }
            ],
            "research_interests": [
                {
                    "keyword": {"ja": "人工知能"}
                },
                {
                    "keyword": {"ja": "機械学習"}
                },
                {
                    "keyword": {"ja": "マテリアルズインフォマティクス"}
                }
            ],
            "research_areas": [],
            "presentations": [
                {
                    "presentation_title": {"ja": "サンプル発表：AI研究成果の報告"},
                    "event": {"ja": "学術会議"},
                    "publication_date": "2024"
                }
            ],
            "misc_publications": [],
            "industrial_properties": []
        }
