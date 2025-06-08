"""
大学名正規化システム（完全強化版）
すべての複雑な大学名パターンに対応する包括的な正規化ロジック
"""

import re
import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

class UniversityNormalizer:
    """
    大学名正規化クラス（完全強化版）
    あらゆる大学名パターンに対応する包括的な正規化ルールを実装
    """
    
    def __init__(self):
        # キャッシュ
        self._normalization_cache: Dict[str, str] = {}
    
    def normalize_university_name(self, university_name: str) -> str:
        """
        大学名を正規化する（完全強化版）
        
        Args:
            university_name: 元の大学名
            
        Returns:
            正規化された大学名
        """
        if not university_name or not university_name.strip():
            return ""
        
        original_name = university_name.strip()
        
        # キャッシュチェック
        if original_name in self._normalization_cache:
            return self._normalization_cache[original_name]
        
        normalized = original_name
        
        # Step 1: 特別なマッピング（統合・名称変更）
        special_mappings = {
            '東京医科歯科大学': '東京科学大学',
            '東京工業大学': '東京科学大学',
        }
        
        for old_name, new_name in special_mappings.items():
            if old_name in normalized:
                normalized = normalized.replace(old_name, new_name)
        
        # Step 2: 法人格の除去
        normalized = re.sub(r'^学校法人(.+大学).*$', r'\1', normalized)
        normalized = re.sub(r'^国立大学法人(.+大学).*$', r'\1', normalized)
        normalized = re.sub(r'^公立大学法人(.+大学).*$', r'\1', normalized)
        
        # Step 3: 大学院の除去
        normalized = re.sub(r'^(.+大学)大学院.*$', r'\1', normalized)
        
        # Step 4: 附属機関の除去（超強化版）
        
        # 病院系
        normalized = re.sub(r'^(.+大学).+附属病院.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学)病院$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+医学部附属病院.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+病院.*$', r'\1', normalized)
        
        # 医学系
        normalized = re.sub(r'^(.+大学)医学医療系.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+医学研究院.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学)医学系.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+医学部.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+医学研究科.*$', r'\1', normalized)
        
        # 研究所・センター系
        normalized = re.sub(r'^(.+大学).+研究所.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+センター.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+機構.*$', r'\1', normalized)
        
        # 特殊機関
        normalized = re.sub(r'^(.+大学).+史料編纂所.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+博物館.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+図書館.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+資料館.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+文書館.*$', r'\1', normalized)
        
        # 学部・研究科系（より詳細）
        normalized = re.sub(r'^(.+大学).+学部.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+研究科.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+学科.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+専攻.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+コース.*$', r'\1', normalized)
        
        # 追加の複雑なパターン
        normalized = re.sub(r'^(.+大学).+事務局.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+本部.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+分校.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+キャンパス.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+分院.*$', r'\1', normalized)
        
        # 総合・連携系
        normalized = re.sub(r'^(.+大学).+総合.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+連携.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+共同.*$', r'\1', normalized)
        
        # より細かい機関名
        normalized = re.sub(r'^(.+大学).+実験.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+観測.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+施設.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+室.*$', r'\1', normalized)
        normalized = re.sub(r'^(.+大学).+所.*$', r'\1', normalized)
        
        # Step 5: 空白の正規化
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'　+', '', normalized)
        normalized = normalized.strip()
        
        # Step 6: 品質チェック
        # 大学が含まれていない、重複文字がある、異常な長さの場合は元のデータを保持
        if (not normalized or 
            not '大学' in normalized or 
            '学学' in normalized or 
            '大大' in normalized or 
            len(normalized) < 3 or 
            len(normalized) > 50):
            normalized = original_name
        
        # 結果をキャッシュ
        self._normalization_cache[original_name] = normalized
        
        logger.debug(f"大学名正規化: '{original_name}' → '{normalized}'")
        
        return normalized
    
    def get_normalized_university_stats_query(self, table_name: str) -> str:
        """
        正規化された大学名統計用のBigQueryクエリを生成（完全強化版）
        
        Args:
            table_name: テーブル名
            
        Returns:
            正規化統計用SQLクエリ
        """
        
        return f"""
        WITH university_normalization AS (
            SELECT 
                name_ja,
                main_affiliation_name_ja as original_university,
                CASE 
                    -- 特別なマッピング（統合・名称変更された大学）
                    WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
                    WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
                    
                    -- 一般的な正規化処理（超強化版）
                    ELSE 
                        TRIM(
                            REGEXP_REPLACE(
                                REGEXP_REPLACE(
                                    REGEXP_REPLACE(
                                        REGEXP_REPLACE(
                                            REGEXP_REPLACE(
                                                REGEXP_REPLACE(
                                                    REGEXP_REPLACE(
                                                        REGEXP_REPLACE(
                                                            REGEXP_REPLACE(
                                                                REGEXP_REPLACE(
                                                                    REGEXP_REPLACE(
                                                                        REGEXP_REPLACE(
                                                                            REGEXP_REPLACE(
                                                                                REGEXP_REPLACE(
                                                                                    REGEXP_REPLACE(
                                                                                        REGEXP_REPLACE(
                                                                                            REGEXP_REPLACE(
                                                                                                REGEXP_REPLACE(
                                                                                                    REGEXP_REPLACE(
                                                                                                        REGEXP_REPLACE(
                                                                                                            REGEXP_REPLACE(
                                                                                                                REGEXP_REPLACE(
                                                                                                                    REGEXP_REPLACE(
                                                                                                                        TRIM(main_affiliation_name_ja),
                                                                                                                        r'^学校法人(.+大学).*$', r'\\\\1'
                                                                                                                    ),
                                                                                                                    r'^国立大学法人(.+大学).*$', r'\\\\1'
                                                                                                                ),
                                                                                                                r'^公立大学法人(.+大学).*$', r'\\\\1'
                                                                                                            ),
                                                                                                            r'^(.+大学)大学院.*$', r'\\\\1'
                                                                                                        ),
                                                                                                        r'^(.+大学).+附属病院.*$', r'\\\\1'
                                                                                                    ),
                                                                                                    r'^(.+大学)病院$', r'\\\\1'
                                                                                                ),
                                                                                                r'^(.+大学).+医学部附属病院.*$', r'\\\\1'
                                                                                            ),
                                                                                            r'^(.+大学).+病院.*$', r'\\\\1'
                                                                                        ),
                                                                                        r'^(.+大学)医学医療系.*$', r'\\\\1'
                                                                                    ),
                                                                                    r'^(.+大学).+医学研究院.*$', r'\\\\1'
                                                                                ),
                                                                                r'^(.+大学)医学系.*$', r'\\\\1'
                                                                            ),
                                                                            r'^(.+大学).+医学部.*$', r'\\\\1'
                                                                        ),
                                                                        r'^(.+大学).+医学研究科.*$', r'\\\\1'
                                                                    ),
                                                                    r'^(.+大学).+研究所.*$', r'\\\\1'
                                                                ),
                                                                r'^(.+大学).+センター.*$', r'\\\\1'
                                                            ),
                                                            r'^(.+大学).+機構.*$', r'\\\\1'
                                                        ),
                                                        r'^(.+大学).+史料編纂所.*$', r'\\\\1'
                                                    ),
                                                    r'^(.+大学).+博物館.*$', r'\\\\1'
                                                ),
                                                r'^(.+大学).+図書館.*$', r'\\\\1'
                                            ),
                                            r'^(.+大学).+学部.*$', r'\\\\1'
                                        ),
                                        r'^(.+大学).+研究科.*$', r'\\\\1'
                                    ),
                                    r'^(.+大学).+学科.*$', r'\\\\1'
                                ),
                                r'^(.+大学).+総合.*$', r'\\\\1'
                            ),
                            r'^(.+大学).+所.*$', r'\\\\1'
                        )
                END as normalized_university
            FROM `{table_name}`
            WHERE main_affiliation_name_ja IS NOT NULL
              AND main_affiliation_name_ja != ''
              AND main_affiliation_name_ja LIKE '%大学%'
              AND LENGTH(main_affiliation_name_ja) >= 3
              AND LENGTH(main_affiliation_name_ja) <= 100  -- 異常に長い名前を除外
        )
        SELECT 
            normalized_university as university_name,
            COUNT(DISTINCT name_ja) as researcher_count,
            ARRAY_AGG(DISTINCT original_university ORDER BY original_university LIMIT 10) as original_names
        FROM university_normalization
        WHERE normalized_university IS NOT NULL 
          AND normalized_university != ''
          AND normalized_university LIKE '%大学%'
          AND LENGTH(normalized_university) >= 3
          AND LENGTH(normalized_university) <= 50  -- 異常に長い名前を除外
          AND NOT REGEXP_CONTAINS(normalized_university, r'学学|大大')  -- 重複文字を除外
        GROUP BY normalized_university
        HAVING COUNT(DISTINCT name_ja) >= 5  -- 5名以上の研究者がいる大学のみ
        ORDER BY researcher_count DESC
        """
    
    def get_university_normalization_sql(self, source_column: str = "main_affiliation_name_ja") -> str:
        """
        検索フィルタリング用の正規化SQLを生成（完全強化版）
        
        Args:
            source_column: 元の大学名カラム名
            
        Returns:
            正規化用SQL
        """
        
        return f"""
        CASE 
            -- 特別なマッピング
            WHEN {source_column} LIKE '%東京医科歯科大学%' THEN '東京科学大学'
            WHEN {source_column} LIKE '%東京工業大学%' THEN '東京科学大学'
            
            -- 一般的な正規化（超強化版）
            ELSE 
                TRIM(
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            REGEXP_REPLACE(
                                REGEXP_REPLACE(
                                    REGEXP_REPLACE(
                                        REGEXP_REPLACE(
                                            REGEXP_REPLACE(
                                                REGEXP_REPLACE(
                                                    REGEXP_REPLACE(
                                                        REGEXP_REPLACE(
                                                            REGEXP_REPLACE(
                                                                REGEXP_REPLACE(
                                                                    REGEXP_REPLACE(
                                                                        REGEXP_REPLACE(
                                                                            REGEXP_REPLACE(
                                                                                TRIM({source_column}),
                                                                                r'^学校法人(.+大学).*$', r'\\\\1'
                                                                            ),
                                                                            r'^国立大学法人(.+大学).*$', r'\\\\1'
                                                                        ),
                                                                        r'^(.+大学)大学院.*$', r'\\\\1'
                                                                    ),
                                                                    r'^(.+大学).+附属病院.*$', r'\\\\1'
                                                                ),
                                                                r'^(.+大学)病院$', r'\\\\1'
                                                            ),
                                                            r'^(.+大学).+病院.*$', r'\\\\1'
                                                        ),
                                                        r'^(.+大学)医学医療系.*$', r'\\\\1'
                                                    ),
                                                    r'^(.+大学).+医学研究院.*$', r'\\\\1'
                                                ),
                                                r'^(.+大学).+研究所.*$', r'\\\\1'
                                            ),
                                            r'^(.+大学).+センター.*$', r'\\\\1'
                                        ),
                                        r'^(.+大学).+史料編纂所.*$', r'\\\\1'
                                    ),
                                    r'^(.+大学).+博物館.*$', r'\\\\1'
                                ),
                                r'^(.+大学).+学部.*$', r'\\\\1'
                            ),
                            r'^(.+大学).+研究科.*$', r'\\\\1'
                        ),
                        r'^(.+大学).+総合.*$', r'\\\\1'
                    ),
                    r'^(.+大学).+所.*$', r'\\\\1'
                )
        END
        """

# グローバルインスタンス
normalizer = UniversityNormalizer()

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（簡易関数）
    
    Args:
        university_name: 元の大学名
        
    Returns:
        正規化された大学名
    """
    return normalizer.normalize_university_name(university_name)

def get_university_normalization_sql(source_column: str = "main_affiliation_name_ja") -> str:
    """
    BigQuery用の正規化SQLを取得
    
    Args:
        source_column: 元の大学名カラム名
        
    Returns:
        正規化用SQL
    """
    return normalizer.get_university_normalization_sql(source_column)

def get_normalized_university_stats_query(table_name: str) -> str:
    """
    正規化された大学名統計用クエリを取得
    
    Args:
        table_name: テーブル名
        
    Returns:
        統計用SQLクエリ
    """
    return normalizer.get_normalized_university_stats_query(table_name)

# テスト用関数
def test_normalization():
    """
    正規化機能のテスト（強化版）
    """
    test_cases = [
        # 基本ケース
        "東京大学大学院",
        "東京大学医学部附属病院",
        "京都大学大学院医学研究科",
        "大阪大学核物理研究センター",
        "東北大学金属材料研究所",
        "九州大学病院",
        
        # 今回問題になったケース
        "筑波大学附属病院",
        "東京大学史料編纂所",
        "筑波大学医学医療系",
        "九州大学総合研究博物館",
        "北海道大学医学研究院",
        
        # 追加の複雑なケース
        "学校法人慶應義塾大学",
        "国立大学法人筑波大学",
        "東京科学大学大学院",
        "東京医科歯科大学",
        "東京工業大学大学院",
        "名古屋大学附属図書館",
        "京都大学総合博物館",
        "大阪大学医学系研究科",
        
        # 異常ケース
        "東京都大学学",
        "大大阪大学学",
    ]
    
    print("大学名正規化テスト（完全強化版）:")
    for name in test_cases:
        normalized = normalize_university_name(name)
        status = "✅ 正規化" if name != normalized else "📝 保持"
        print(f"  '{name}' → '{normalized}' ({status})")

if __name__ == "__main__":
    test_normalization()
