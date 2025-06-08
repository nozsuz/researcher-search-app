"""
大学名正規化効果レポート生成
統合前後の大学数や研究者数の変化を分析する
"""

import asyncio
import logging
from typing import Dict, List, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

class NormalizationReportGenerator:
    """
    大学名正規化効果のレポート生成クラス
    """
    
    def __init__(self):
        pass
    
    async def generate_normalization_report(self, bq_client) -> Dict:
        """
        正規化効果のレポートを生成
        
        Args:
            bq_client: BigQueryクライアント
            
        Returns:
            正規化効果レポート
        """
        try:
            logger.info("📊 正規化効果レポート生成開始")
            
            # 正規化前のデータを取得
            before_data = await self._get_original_university_data(bq_client)
            
            # 正規化後のデータを取得
            after_data = await self._get_normalized_university_data(bq_client)
            
            # 効果を分析
            analysis = self._analyze_normalization_effect(before_data, after_data)
            
            # レポートを生成
            report = {
                "summary": {
                    "universities_before": len(before_data),
                    "universities_after": len(after_data),
                    "consolidation_rate": (len(before_data) - len(after_data)) / len(before_data) * 100,
                    "total_researchers": sum(data["count"] for data in after_data),
                    "generated_at": "2025-06-08"
                },
                "top_consolidations": analysis["top_consolidations"],
                "new_university_pattern": analysis["new_patterns"],
                "before_after_comparison": {
                    "before": before_data[:20],  # 上位20校
                    "after": after_data[:20]
                },
                "normalization_details": analysis["details"]
            }
            
            logger.info(f"✅ レポート生成完了: {len(before_data)} → {len(after_data)}校 ({report['summary']['consolidation_rate']:.1f}% 削減)")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ レポート生成エラー: {e}")
            return {"error": str(e)}
    
    async def _get_original_university_data(self, bq_client) -> List[Dict]:
        """
        正規化前の大学データを取得
        """
        query = """
        SELECT 
            main_affiliation_name_ja as university_name,
            COUNT(DISTINCT name_ja) as researcher_count
        FROM `apt-rope-217206.researcher_data.rd_250524`
        WHERE main_affiliation_name_ja IS NOT NULL
        GROUP BY main_affiliation_name_ja
        ORDER BY researcher_count DESC
        """
        
        query_job = bq_client.query(query)
        results = []
        
        for row in query_job:
            results.append({
                "name": row.university_name,
                "count": row.researcher_count
            })
        
        return results
    
    async def _get_normalized_university_data(self, bq_client) -> List[Dict]:
        """
        正規化後の大学データを取得
        """
        from university_normalizer import get_normalized_university_stats_query
        
        query = get_normalized_university_stats_query("apt-rope-217206.researcher_data.rd_250524")
        query_job = bq_client.query(query)
        results = []
        
        for row in query_job:
            results.append({
                "name": row.university_name,
                "count": row.researcher_count,
                "original_names": list(row.original_names) if hasattr(row, 'original_names') else [row.university_name]
            })
        
        return results
    
    def _analyze_normalization_effect(self, before_data: List[Dict], after_data: List[Dict]) -> Dict:
        """
        正規化効果を分析
        """
        # 統合効果の高い大学を特定
        consolidations = []
        
        for after_item in after_data:
            if "original_names" in after_item and len(after_item["original_names"]) > 1:
                consolidations.append({
                    "normalized_name": after_item["name"],
                    "original_count": len(after_item["original_names"]),
                    "researcher_count": after_item["count"],
                    "original_names": after_item["original_names"]
                })
        
        # 統合効果でソート
        consolidations.sort(key=lambda x: x["original_count"], reverse=True)
        
        # 新しい大学パターンを分析
        new_patterns = self._identify_new_university_patterns(before_data)
        
        return {
            "top_consolidations": consolidations[:10],
            "new_patterns": new_patterns,
            "details": {
                "total_consolidations": len(consolidations),
                "total_original_names": sum(c["original_count"] for c in consolidations),
                "largest_consolidation": consolidations[0] if consolidations else None
            }
        }
    
    def _identify_new_university_patterns(self, before_data: List[Dict]) -> List[Dict]:
        """
        新規大学のパターンを特定
        """
        patterns = []
        
        # 新しい大学名のパターンを探す
        new_keywords = ["科学技術", "先端", "革新", "未来", "創造", "国際", "グローバル"]
        
        for item in before_data:
            name = item["name"]
            if any(keyword in name for keyword in new_keywords):
                patterns.append({
                    "name": name,
                    "count": item["count"],
                    "pattern": "new_university_candidate"
                })
        
        return patterns[:5]  # 上位5件

async def generate_and_save_report(output_file: str = "normalization_report.md"):
    """
    正規化レポートを生成してファイルに保存
    """
    try:
        from gcp_auth import get_bigquery_client
        
        bq_client = get_bigquery_client()
        if not bq_client:
            print("❌ BigQueryクライアントが利用できません")
            return
        
        generator = NormalizationReportGenerator()
        report = await generator.generate_normalization_report(bq_client)
        
        if "error" in report:
            print(f"❌ レポート生成エラー: {report['error']}")
            return
        
        # Markdownレポートを生成
        markdown_content = _generate_markdown_report(report)
        
        # ファイルに保存
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"✅ レポートを保存しました: {output_file}")
        print(f"📊 統合効果: {report['summary']['universities_before']} → {report['summary']['universities_after']}校")
        print(f"📈 削減率: {report['summary']['consolidation_rate']:.1f}%")
        
    except Exception as e:
        print(f"❌ レポート生成・保存エラー: {e}")

def _generate_markdown_report(report: Dict) -> str:
    """
    Markdownレポートを生成
    """
    summary = report["summary"]
    
    content = f"""# 大学名正規化効果レポート

生成日: {summary['generated_at']}

## 概要

- **正規化前大学数**: {summary['universities_before']:,}校
- **正規化後大学数**: {summary['universities_after']:,}校
- **統合効果**: {summary['consolidation_rate']:.1f}% 削減
- **総研究者数**: {summary['total_researchers']:,}名

## 主要な統合効果

"""
    
    # 上位統合を表示
    if report["top_consolidations"]:
        content += "| 正規化後大学名 | 統合前数 | 研究者数 | 統合前大学名（例） |\n"
        content += "|---|---|---|---|\n"
        
        for consolidation in report["top_consolidations"]:
            examples = ", ".join(consolidation["original_names"][:3])
            if len(consolidation["original_names"]) > 3:
                examples += f" など{len(consolidation['original_names'])}校"
            
            content += f"| {consolidation['normalized_name']} | {consolidation['original_count']} | {consolidation['researcher_count']:,} | {examples} |\n"
    
    content += f"""

## 動的正規化システムの効果

### 特徴

1. **ルールベース正規化**: 明示的なマッピングではなく、パターンマッチングで動的に処理
2. **新規大学対応**: 新しく登録された大学も自動的に正規化ルールが適用
3. **メンテナンスフリー**: 大学名の追加時にシステム変更が不要

### 正規化パターン

- 大学院・学部・研究科の統合
- 附属病院・研究所・センターの統合
- 法人格の除去
- 空白・記号の正規化

## 新規大学パターン分析

"""
    
    if report["new_university_pattern"]:
        content += "| 大学名 | 研究者数 | 分類 |\n"
        content += "|---|---|---|\n"
        
        for pattern in report["new_university_pattern"]:
            content += f"| {pattern['name']} | {pattern['count']} | {pattern['pattern']} |\n"
    
    content += f"""

## 技術的詳細

### 正規化前後比較（上位20校）

#### 正規化前
"""
    
    for i, before in enumerate(report["before_after_comparison"]["before"], 1):
        content += f"{i}. {before['name']} ({before['count']:,}名)\n"
    
    content += "\n#### 正規化後\n"
    
    for i, after in enumerate(report["before_after_comparison"]["after"], 1):
        content += f"{i}. {after['name']} ({after['count']:,}名)\n"
    
    content += """

## 結論

動的正規化システムにより、大学名の表記揺れが効果的に統合され、検索精度の向上が期待できます。
特に新規登録される大学についても、既存のルールが自動的に適用されるため、メンテナンス性が大幅に向上しました。

---
*このレポートは動的大学名正規化システムにより自動生成されました*
"""
    
    return content

if __name__ == "__main__":
    asyncio.run(generate_and_save_report())
