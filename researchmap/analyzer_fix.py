"""
技術的関連性スコア計算の修正案
"""

def _calculate_technical_relevance_fixed(self, papers: List[Dict], projects: List[Dict], query: str, research_interests: List[Dict] = None) -> int:
    """技術的関連性スコアの計算（最大40点）- 修正版"""
    score = 0
    query_lower = query.lower()
    
    # クエリを単語に分割（形態素解析の簡易版）
    # 「腎臓がん治療」→ ["腎臓がん", "治療", "腎臓", "がん", "腎", "癌"]
    query_keywords = self._extract_query_keywords(query_lower)
    
    # 1. 研究キーワードとの関連性（最大15点）
    if research_interests:
        keyword_score = 0
        for interest in research_interests:
            keyword_dict = interest.get("keyword", {})
            research_keyword = keyword_dict.get("ja", "").lower()
            
            # 完全一致
            if query_lower in research_keyword or research_keyword in query_lower:
                keyword_score += 5
            # 部分一致
            elif any(kw in research_keyword for kw in query_keywords):
                keyword_score += 3
        
        score += min(15, keyword_score)
    
    # 2. 論文タイトルとの関連性（最大15点）
    relevant_count = 0
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
            relevant_count += 2  # 完全一致は2倍の重み
        elif any(kw in title_ja or kw in title_en for kw in query_keywords):
            relevant_count += 1
    
    score += min(15, relevant_count * 3)
    
    # 3. プロジェクトとの関連性（最大10点）
    project_score = 0
    for project in projects[:5]:  # 最新5件のプロジェクト
        project_title = project.get("research_project_title") or project.get("project_title", {})
        
        if isinstance(project_title, str):
            title = project_title.lower()
        elif isinstance(project_title, dict):
            title = project_title.get("ja", "").lower()
        else:
            title = ""
        
        if any(kw in title for kw in query_keywords):
            project_score += 2
    
    score += min(10, project_score)
    
    return score

def _extract_query_keywords(self, query: str) -> List[str]:
    """クエリからキーワードを抽出（同義語展開含む）"""
    query_lower = query.lower()
    keywords = [query_lower]  # 元のクエリ
    
    # 基本的な分割
    # 「がん」「癌」の同義語処理
    if "がん" in query_lower:
        keywords.append(query_lower.replace("がん", "癌"))
        keywords.append(query_lower.replace("がん", ""))  # 「腎臓がん」→「腎臓」
    if "癌" in query_lower:
        keywords.append(query_lower.replace("癌", "がん"))
        keywords.append(query_lower.replace("癌", ""))
    
    # 「腎臓」と「腎」の同義語処理
    if "腎臓" in query_lower:
        keywords.append(query_lower.replace("腎臓", "腎"))
    if "腎" in query_lower and "腎臓" not in query_lower:
        keywords.append(query_lower.replace("腎", "腎臓"))
    
    # 一般的な単語分割
    # 日本語の複合語を簡易的に分割
    if len(query_lower) > 4:
        # 2文字、3文字の部分文字列を追加
        for i in range(len(query_lower) - 1):
            keywords.append(query_lower[i:i+2])
            if i + 3 <= len(query_lower):
                keywords.append(query_lower[i:i+3])
    
    # 重複を除去
    return list(set(keywords))
