"""
研究者評価システム
汎用的な評価軸に基づいて研究者と検索クエリの関連性を評価
"""

import logging
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextGenerationModel

logger = logging.getLogger(__name__)

@dataclass
class EvaluationCriteria:
    """評価基準の定義"""
    keyword_match: float = 0.25
    research_directness: float = 0.20
    expertise_depth: float = 0.15
    practical_evidence: float = 0.15
    research_quality: float = 0.10
    interdisciplinary: float = 0.10
    recency: float = 0.05

@dataclass
class ResearcherEvaluation:
    """研究者の評価結果"""
    researcher_data: Dict[str, Any]
    scores: Dict[str, float]
    total_score: float
    summary: str
    strengths: List[str]
    score_reasons: Optional[Dict[str, str]] = None
    
class UniversalResearchEvaluator:
    """汎用的な研究者評価システム"""
    
    def __init__(self):
        self.criteria = EvaluationCriteria()
        self.model = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """LLMモデルの初期化"""
        try:
            # Gemini 2.0 Flash Liteを優先
            self.model = GenerativeModel("gemini-2.0-flash-lite-001")
            self.model_name = "gemini-2.0-flash-lite-001"
            logger.info(f"✅ 評価用LLMモデル初期化: {self.model_name}")
        except Exception as e:
            logger.warning(f"⚠️ Gemini 2.0 Flash Lite初期化失敗: {e}")
            try:
                # フォールバック
                self.model = TextGenerationModel.from_pretrained("text-bison@002")
                self.model_name = "text-bison@002"
                logger.info(f"✅ フォールバックLLMモデル初期化: {self.model_name}")
            except Exception as e2:
                logger.error(f"❌ LLMモデル初期化失敗: {e2}")
                self.model = None
    
    async def evaluate_researchers(
        self, 
        researchers: List[Dict[str, Any]], 
        query: str,
        use_internal_evaluation: bool = True
    ) -> List[ResearcherEvaluation]:
        """
        研究者リストを評価
        
        Args:
            researchers: 研究者データのリスト
            query: 検索クエリ
            use_internal_evaluation: 内部評価モードを使用するか
            
        Returns:
            評価結果のリスト
        """
        if not use_internal_evaluation:
            # 従来の評価方式（互換性のため）
            return self._legacy_evaluate(researchers, query)
        
        logger.info(f"🎯 内部評価モード開始: {len(researchers)}名の研究者を評価")
        
        evaluations = []
        
        # バッチ処理で効率化（5人ずつ）
        batch_size = 5
        for i in range(0, len(researchers), batch_size):
            batch = researchers[i:i+batch_size]
            batch_evaluations = await self._evaluate_batch(batch, query)
            evaluations.extend(batch_evaluations)
            
            # レート制限対策
            if i + batch_size < len(researchers):
                time.sleep(0.5)
        
        # スコアでソート
        evaluations.sort(key=lambda x: x.total_score, reverse=True)
        
        logger.info(f"✅ 評価完了: 最高スコア {evaluations[0].total_score:.1f}/10")
        
        return evaluations
    
    async def _evaluate_batch(
        self, 
        researchers: List[Dict[str, Any]], 
        query: str
    ) -> List[ResearcherEvaluation]:
        """研究者のバッチを評価"""
        if not self.model:
            # LLMが使えない場合は簡易評価
            return [self._simple_evaluate(r, query) for r in researchers]
        
        prompt = self._create_batch_evaluation_prompt(researchers, query)
        
        try:
            if "gemini" in self.model_name:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 2048,
                        "top_p": 0.8
                    }
                )
                evaluation_text = response.text
            else:
                response = self.model.predict(
                    prompt,
                    temperature=0.1,
                    max_output_tokens=2048,
                    top_p=0.8
                )
                evaluation_text = response.text
            
            # JSON形式の評価結果をパース
            evaluations = self._parse_evaluation_response(evaluation_text, researchers, query)
            return evaluations
            
        except Exception as e:
            logger.error(f"❌ バッチ評価エラー: {e}")
            # エラー時は簡易評価にフォールバック
            return [self._simple_evaluate(r, query) for r in researchers]
    
    def _create_batch_evaluation_prompt(
        self, 
        researchers: List[Dict[str, Any]], 
        query: str
    ) -> str:
        """バッチ評価用のプロンプトを生成"""
        researchers_info = []
        for idx, r in enumerate(researchers):
            info = f"""
研究者{idx + 1}:
名前: {r.get('name_ja', '')}
所属: {r.get('main_affiliation_name_ja', '')}
研究キーワード: {r.get('research_keywords_ja', '')}
研究分野: {r.get('research_fields_ja', '')}
プロフィール: {str(r.get('profile_ja', ''))[:300] if r.get('profile_ja') else ''}
主要論文: {r.get('paper_title_ja_first', '')}
主要プロジェクト: {r.get('project_title_ja_first', '')}
"""
            researchers_info.append(info)
        
        prompt = f"""以下の研究者と検索クエリ「{query}」の関連性を評価してください。

{chr(10).join(researchers_info)}

各研究者について、以下の7つの観点で1-10点で評価し、各スコアの理由を含めてJSON形式で出力してください：

1. keyword_match: クエリと研究キーワードの一致度
2. research_directness: 研究内容とクエリの直接的関連性
3. expertise_depth: 該当分野での専門性の深さ
4. practical_evidence: 具体的な実績・エビデンス
5. research_quality: 研究の質と影響力
6. interdisciplinary: 学際性・応用可能性
7. recency: 研究の最新性

出力形式:
{{
  "evaluations": [
    {{
      "researcher_index": 1,
      "scores": {{
        "keyword_match": 8,
        "research_directness": 9,
        "expertise_depth": 7,
        "practical_evidence": 8,
        "research_quality": 7,
        "interdisciplinary": 6,
        "recency": 8
      }},
      "score_reasons": {{
        "keyword_match": "研究キーワードに『{query}』が直接含まれている",
        "research_directness": "主要プロジェクトが{query}の実用化に焦点",
        "expertise_depth": "該当分野で10年以上の研究実績",
        "practical_evidence": "関連特許3件、実用化事例あり",
        "research_quality": "トップジャーナルへの掲載実績",
        "interdisciplinary": "工学と医学の融合研究を推進",
        "recency": "2024年に最新の研究成果を発表"
      }},
      "summary": "研究キーワード、プロフィール、主要論文、主要プロジェクトを踏まえて、検索クエリとの関連性を200字程度で要約",
      "strengths": ["強み1", "強み2", "強み3"]
    }}
  ]
}}
"""
        return prompt
    
    def _parse_evaluation_response(
        self, 
        response_text: str, 
        researchers: List[Dict[str, Any]], 
        query: str
    ) -> List[ResearcherEvaluation]:
        """LLMの評価レスポンスをパース"""
        evaluations = []
        
        try:
            # JSONレスポンスを抽出
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                parsed = json.loads(json_text)
                
                for eval_data in parsed.get('evaluations', []):
                    idx = eval_data.get('researcher_index', 1) - 1
                    if 0 <= idx < len(researchers):
                        researcher = researchers[idx]
                        scores = eval_data.get('scores', {})
                        
                        # 総合スコアを計算
                        total_score = self._calculate_total_score(scores)
                        
                        evaluation = ResearcherEvaluation(
                            researcher_data=researcher,
                            scores=scores,
                            total_score=total_score,
                            summary=eval_data.get('summary', ''),
                            strengths=eval_data.get('strengths', []),
                            score_reasons=eval_data.get('score_reasons', {})
                        )
                        evaluations.append(evaluation)
            
        except Exception as e:
            logger.error(f"❌ 評価レスポンスのパースエラー: {e}")
        
        # パースできなかった研究者は簡易評価
        if len(evaluations) < len(researchers):
            for i, researcher in enumerate(researchers):
                if not any(e.researcher_data == researcher for e in evaluations):
                    evaluations.append(self._simple_evaluate(researcher, query))
        
        return evaluations
    
    def _calculate_total_score(self, scores: Dict[str, float]) -> float:
        """重み付けされた総合スコアを計算"""
        weighted_sum = 0
        total_weight = 0
        
        criteria_weights = {
            'keyword_match': self.criteria.keyword_match,
            'research_directness': self.criteria.research_directness,
            'expertise_depth': self.criteria.expertise_depth,
            'practical_evidence': self.criteria.practical_evidence,
            'research_quality': self.criteria.research_quality,
            'interdisciplinary': self.criteria.interdisciplinary,
            'recency': self.criteria.recency
        }
        
        for criterion, weight in criteria_weights.items():
            score = scores.get(criterion, 5)  # デフォルト5点
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight > 0:
            return round(weighted_sum / total_weight, 1)
        return 5.0
    
    def _simple_evaluate(
        self, 
        researcher: Dict[str, Any], 
        query: str
    ) -> ResearcherEvaluation:
        """LLMを使わない簡易評価"""
        query_lower = query.lower()
        keywords = (researcher.get('research_keywords_ja', '') or '').lower()
        fields = (researcher.get('research_fields_ja', '') or '').lower()
        profile = (researcher.get('profile_ja', '') or '').lower()
        
        # キーワードマッチング
        keyword_match = sum(1 for word in query_lower.split() if word in keywords)
        field_match = sum(1 for word in query_lower.split() if word in fields)
        profile_match = sum(1 for word in query_lower.split() if word in profile)
        
        # 簡易スコア計算
        scores = {
            'keyword_match': min(10, 3 + keyword_match * 2),
            'research_directness': min(10, 5 + field_match),
            'expertise_depth': 5,  # 不明
            'practical_evidence': 5,  # 不明
            'research_quality': 5,  # 不明
            'interdisciplinary': 5,  # 不明
            'recency': 5  # 不明
        }
        
        total_score = self._calculate_total_score(scores)
        
        return ResearcherEvaluation(
            researcher_data=researcher,
            scores=scores,
            total_score=total_score,
            summary=f"「{query}」に関連する研究を行っています。",
            strengths=[]
        )
        
    async def generate_single_summary(self, researcher_data: Dict[str, Any], query: str) -> Optional[str]:
        """
        単一の研究者データと検索クエリから関連性要約を生成する
        """
        # 最初にLLMが利用可能かチェック
        if not self.model:
            logger.warning("LLM not available for single summary generation.")
            return "LLMが利用できないため、要約を生成できませんでした。"

        # プロンプトを作成し、LLMを呼び出す
        try:
            prompt = self._create_single_summary_prompt(researcher_data, query)
            
            logger.info(f"単独要約生成のためLLMを呼び出し: {researcher_data.get('name_ja')} (Query: {query})")
            
            if "gemini" in self.model_name:
                response = self.model.generate_content(prompt, generation_config={"temperature": 0.2})
                summary = response.text
            else: # Fallback for text-bison
                response = self.model.predict(prompt, temperature=0.2)
                summary = response.text
            
            return summary.strip()

        except Exception as e:
            logger.error(f"❌ 単独要約の生成エラー: {e}")
            return None

    def _create_single_summary_prompt(self, researcher: Dict[str, Any], query: str) -> str:
        """単独要約生成用のプロンプトを生成"""
        info = f"""
研究者情報:
名前: {researcher.get('name_ja', '')}
所属: {researcher.get('main_affiliation_name_ja', '')}
研究キーワード: {researcher.get('research_keywords_ja', '')}
プロフィール: {str(researcher.get('profile_ja', ''))[:400] if researcher.get('profile_ja') else ''}
主要論文: {researcher.get('paper_title_ja_first', '')}
"""
        prompt = f"""
以下の研究者情報を基に、研究キーワード、プロフィール、主要論文、主要プロジェクトを踏まえて、検索クエリ「{query}」との関連性を200字程度で要約してください。要約文のみを出力してください。

{info}
"""
        return prompt

    def _legacy_evaluate(
        self, 
        researchers: List[Dict[str, Any]], 
        query: str
    ) -> List[ResearcherEvaluation]:
        """従来の評価方式（互換性のため）"""
        # 既存のllm_summaryを使用
        evaluations = []
        for researcher in researchers:
            # 簡易的なスコア計算
            relevance_score = researcher.get('relevance_score', 0)
            distance = researcher.get('distance', 1.0)
            
            if relevance_score:
                # キーワード検索の場合
                total_score = min(10, 3 + (relevance_score / 10))
            else:
                # セマンティック検索の場合
                similarity = 1 - distance
                total_score = round(similarity * 10, 1)
            
            evaluation = ResearcherEvaluation(
                researcher_data=researcher,
                scores={},  # 詳細スコアなし
                total_score=total_score,
                summary=researcher.get('llm_summary', ''),
                strengths=[]
            )
            evaluations.append(evaluation)
        
        evaluations.sort(key=lambda x: x.total_score, reverse=True)
        return evaluations
    
    def format_for_ui(
        self, 
        evaluations: List[ResearcherEvaluation], 
        max_results: int = 10
    ) -> Dict[str, Any]:
        """UI表示用にフォーマット"""
        top_evaluations = evaluations[:max_results]
        
        # サマリー生成
        if top_evaluations:
            best_match = top_evaluations[0]
            summary = {
                "best_match": f"{best_match.researcher_data.get('name_ja', '')}（{best_match.researcher_data.get('main_affiliation_name_ja', '')}）- 総合スコア {best_match.total_score}/10",
                "key_finding": f"上位{min(3, len(top_evaluations))}名の平均スコアは{sum(e.total_score for e in top_evaluations[:3]) / min(3, len(top_evaluations)):.1f}点。{best_match.summary}",
                "total_evaluated": len(evaluations)
            }
        else:
            summary = {
                "best_match": "該当する研究者が見つかりませんでした",
                "key_finding": "",
                "total_evaluated": 0
            }
        
        # 結果のフォーマット
        results = []
        for idx, evaluation in enumerate(top_evaluations):
            result = {
                "rank": idx + 1,
                "name": evaluation.researcher_data.get('name_ja', ''),
                "affiliation": evaluation.researcher_data.get('main_affiliation_name_ja', ''),
                "score": evaluation.total_score,
                "summary": evaluation.summary,
                "strengths": evaluation.strengths[:3],
                "keywords": evaluation.researcher_data.get('research_keywords_ja', ''),
                "fields": evaluation.researcher_data.get('research_fields_ja', ''),
                "profile": evaluation.researcher_data.get('profile_ja', ''),
                "paper_title": evaluation.researcher_data.get('paper_title_ja_first', ''),
                "project_title": evaluation.researcher_data.get('project_title_ja_first', ''),
                "url": evaluation.researcher_data.get('researchmap_url', ''),
                "is_young_researcher": evaluation.researcher_data.get('is_young_researcher', False),
                "young_researcher_reasons": evaluation.researcher_data.get('young_researcher_reasons', [])
            }
            
            # 詳細スコア（内部評価モードの場合のみ）
            if evaluation.scores:
                result["detail_scores"] = evaluation.scores
                
            # スコアの理由
            if evaluation.score_reasons:
                result["score_reasons"] = evaluation.score_reasons
            
            results.append(result)
        
        return {
            "summary": summary,
            "results": results,
            "metadata": {
                "total_found": len(evaluations),
                "displayed": len(results)
            }
        }
