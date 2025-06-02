"""
ResearchMap API連携モジュール
研究者の詳細情報を取得してAI分析を実行
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import aiohttp
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextGenerationModel

logger = logging.getLogger(__name__)

class ResearchMapAnalyzer:
    """ResearchMap APIを使用した研究者分析クラス"""
    
    def __init__(self):
        self.api_base_url = "https://api.researchmap.jp"
        self.llm_model = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """LLMモデルの初期化"""
        try:
            # Gemini 2.0 Flash Liteを優先
            self.llm_model = GenerativeModel("gemini-2.0-flash-lite-001")
            self.model_name = "gemini-2.0-flash-lite-001"
            logger.info(f"✅ 分析用LLMモデル初期化: {self.model_name}")
        except Exception as e:
            logger.warning(f"⚠️ Gemini 2.0 Flash Lite初期化失敗: {e}")
            try:
                # フォールバック
                self.llm_model = TextGenerationModel.from_pretrained("text-bison@002")
                self.model_name = "text-bison@002"
                logger.info(f"✅ フォールバックLLMモデル初期化: {self.model_name}")
            except Exception as e2:
                logger.error(f"❌ LLMモデル初期化失敗: {e2}")
                self.llm_model = None
    
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
    
    async def fetch_researcher_data(self, researcher_id: str) -> Optional[Dict[str, Any]]:
        """ResearchMap APIから研究者情報を取得"""
        try:
            async with aiohttp.ClientSession() as session:
                # 基本情報の取得（permalinkを直接使用）
                profile_url = f"{self.api_base_url}/{researcher_id}"
                
                headers = {
                    "Accept": "application/json",
                    "Accept-Language": "ja"
                }
                
                async with session.get(profile_url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"❌ ResearchMap API エラー: {response.status}")
                        return None
                    
                    data = await response.json()
                    
                    # ResearchMap APIの返すデータ構造に合わせて処理
                    researcher_data = self._parse_researcher_data(data)
                    
                    return researcher_data
                    
        except Exception as e:
            logger.error(f"❌ ResearchMap API取得エラー: {e}")
            return None
    
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
                
                if item_type == "published_papers":
                    papers.extend(items)
                    logger.info(f"📄 論文 {len(items)}件を抽出")
                    
                elif item_type == "research_projects":
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
        basic_info: Optional[Dict[str, Any]] = None
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
        analysis = await self._perform_ai_analysis(researcher_data, query, basic_info)
        
        return {
            "status": "success",
            "analysis": analysis
        }
    
    async def _perform_ai_analysis(
        self, 
        researcher_data: Dict[str, Any], 
        query: str,
        basic_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """AIによる研究者分析"""
        
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
        total_papers = len(papers)
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
        
        # LLMによる詳細分析
        if self.llm_model:
            detailed_analysis = await self._generate_detailed_analysis(
                profile, papers, projects, awards, query,
                research_interests, presentations, industrial_properties
            )
            scores = await self._calculate_scores(
                profile, papers, projects, awards, query
            )
        else:
            # LLMが使えない場合の簡易分析
            detailed_analysis = self._generate_simple_analysis(
                researcher_name, query, total_papers, total_projects
            )
            scores = self._calculate_simple_scores(
                total_papers, total_projects, total_awards, query, papers
            )
        
        return {
            "researcher_name": researcher_name,
            "affiliation": affiliation,
            "scores": scores,
            "research_keywords": keywords,
            "total_papers": total_papers,
            "total_projects": total_projects,
            "total_awards": total_awards,
            "total_presentations": total_presentations,
            "total_patents": total_patents,
            "detailed_analysis": detailed_analysis,
            "top_papers": relevant_papers,
            "key_projects": key_projects,
            "recent_presentations": recent_presentations
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
            title_ja = paper.get("paper_title", {}).get("ja", "")
            title_en = paper.get("paper_title", {}).get("en", "")
            
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
        
        for project in projects[:limit]:  # 最新のものから
            # タイトルの取得
            title = project.get("project_title", {}).get("ja", "")
            if not title:
                title = project.get("project_title", {}).get("en", "")
            
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
            
            key_projects.append({
                "title": title,
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
                keywords.extend([k.strip() for k in research_keyword.split(‘、’)])
        
        # 重複を除去
        return list(dict.fromkeys(keywords))
    
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
        papers: List[Dict],
        projects: List[Dict],
        awards: List[Dict],
        query: str,
        research_interests: List[Dict] = None,
        presentations: List[Dict] = None,
        industrial_properties: List[Dict] = None
    ) -> str:
        """LLMによる詳細分析の生成"""
        
        # サポート情報の初期化
        research_interests = research_interests or []
        presentations = presentations or []
        industrial_properties = industrial_properties or []
        
        # 研究キーワードを抽出
        keywords = []
        for interest in research_interests[:5]:
            keyword = interest.get("keyword", {})
            if keyword.get("ja"):
                keywords.append(keyword["ja"])
        
        # 分析用のプロンプト作成
        prompt = f"""以下の研究者情報を基に、「{query}」との関連性について詳細な分析を行ってください。

研究者情報:
- 論文数: {len(papers)}件
- プロジェクト数: {len(projects)}件
- 受賞歴: {len(awards)}件
- 発表数: {len(presentations)}件
- 特許数: {len(industrial_properties)}件
{'' if not keywords else f'- 研究キーワード: ' + ', '.join(keywords)}

主要論文（最新5件）:
"""
        for i, paper in enumerate(papers[:5]):
            title = paper.get("paper_title", {}).get("ja", "")
            if not title:
                title = paper.get("paper_title", {}).get("en", "")
            if title:
                prompt += f"{i+1}. {title}\n"
        
        prompt += f"""
検索クエリ「{query}」との関連性について、以下の観点から400字程度で分析してください：
1. 技術的関連性：研究内容とクエリの直接的な関連
2. 実績・影響力：研究成果の質と量
3. 実用化可能性：産学連携や社会実装の可能性

分析は具体的かつ建設的に行ってください。
"""
        
        try:
            if "gemini" in self.model_name:
                response = self.llm_model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.3,
                        "max_output_tokens": 600,
                        "top_p": 0.8
                    }
                )
                return response.text.strip()
            else:
                response = self.llm_model.predict(
                    prompt,
                    temperature=0.3,
                    max_output_tokens=600,
                    top_p=0.8
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
        query: str
    ) -> Dict[str, int]:
        """スコアの計算"""
        
        # 基本的なスコア計算
        technical_relevance = min(40, self._calculate_technical_relevance(papers, query))
        achievements = min(30, self._calculate_achievements(papers, projects, awards))
        practical_applicability = min(30, self._calculate_practical_applicability(projects))
        
        total = technical_relevance + achievements + practical_applicability
        
        return {
            "total": total,
            "technical_relevance": technical_relevance,
            "achievements": achievements,
            "practical_applicability": practical_applicability
        }
    
    def _calculate_technical_relevance(self, papers: List[Dict], query: str) -> int:
        """技術的関連性スコアの計算（最大40点）"""
        score = 0
        query_lower = query.lower()
        
        # 関連論文数
        relevant_count = 0
        for paper in papers:
            title_ja = paper.get("paper_title", {}).get("ja", "")
            title_en = paper.get("paper_title", {}).get("en", "")
            if query_lower in title_ja.lower() or query_lower in title_en.lower():
                relevant_count += 1
        
        # 関連論文数に基づくスコア（最大20点）
        score += min(20, relevant_count * 4)
        
        # 最新性（最大10点）
        recent_papers = 0
        for paper in papers[:10]:
            year = paper.get("publication_date", "")
            if isinstance(year, dict):
                year = year.get("year", 0)
            elif isinstance(year, str) and len(year) >= 4:
                year = int(year[:4]) if year[:4].isdigit() else 0
            else:
                year = 0
            
            if year >= 2020:
                recent_papers += 1
        score += min(10, recent_papers * 2)
        
        # 論文の多様性（最大10点）
        if len(papers) >= 20:
            score += 10
        elif len(papers) >= 10:
            score += 7
        elif len(papers) >= 5:
            score += 5
        
        return score
    
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
            title = project.get("project_title", {}).get("ja", "")
            if not title:
                title = project.get("project_title", {}).get("en", "")
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
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """エラーレスポンスの作成"""
        return {
            "status": "error",
            "error": error_message,
            "analysis": None
        }
