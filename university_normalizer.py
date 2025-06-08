"""
大学名正規化システム
明示的なマッピングではなく、ルールベースで動的に正規化を行う
新規登録された大学にも自動的に適用される
"""

import re
import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

class UniversityNormalizer:
    """
    大学名正規化クラス
    ルールベースで動的に大学名を正規化し、新規登録にも対応
    """
    
    def __init__(self):
        # 正規化ルールパターン
        self.normalization_patterns = [
            # 大学院系の統合
            (r'^(.+大学)大学院$', r'\1'),
            (r'^(.+大学)大学院.+$', r'\1'),
            
            # 附属機関・病院の統合
            (r'^(.+大学).+附属病院$', r'\1'),
            (r'^(.+大学).+病院$', r'\1'),
            (r'^(.+大学).+医学部附属病院$', r'\1'),
            
            # 研究科・学部の統合
            (r'^(.+大学)大学院.+研究科$', r'\1'),
            (r'^(.+大学).+研究科$', r'\1'),
            (r'^(.+大学).+学部$', r'\1'),
            (r'^(.+大学).+学院$', r'\1'),
            
            # 研究所・センターの統合
            (r'^(.+大学).+研究所$', r'\1'),
            (r'^(.+大学).+センター$', r'\1'),
            (r'^(.+大学).+機構$', r'\1'),
            (r'^(.+大学).+機関$', r'\1'),
            (r'^(.+大学).+本部$', r'\1'),
            
            # 特定の部門・組織の統合
            (r'^(.+大学).+科学研究院$', r'\1'),
            (r'^(.+大学).+医学研究院$', r'\1'),
            (r'^(.+大学).+工学研究院$', r'\1'),
            (r'^(.+大学).+研究院$', r'\1'),
            
            # その他の附属組織
            (r'^(.+大学).+博物館$', r'\1'),
            (r'^(.+大学).+図書館$', r'\1'),
            (r'^(.+大学).+事務局$', r'\1'),
            
            # 複数キャンパス・分校の統合
            (r'^(.+大学).+キャンパス$', r'\1'),
            (r'^(.+大学).+校$', r'\1'),
            (r'^(.+大学).+分校$', r'\1'),
            
            # 法人格の除去
            (r'^学校法人(.+大学)$', r'\1'),
            (r'^国立大学法人(.+大学)$', r'\1'),
            (r'^公立大学法人(.+大学)$', r'\1'),
            (r'^私立(.+大学)$', r'\1'),
            
            # 空白・記号の統一
            (r'\s+', ' '),  # 複数の空白を1つに
            (r'　+', ''),   # 全角空白を除去
        ]
        
        # 特別な統合ルール（名称変更など）
        self.special_mappings = {
            # 統合・名称変更された大学
            '東京医科歯科大学': '東京科学大学',
            '東京工業大学': '東京科学大学',
            
            # 略称の統一
            '東大': '東京大学',
            '京大': '京都大学',
            '阪大': '大阪大学',
            '東工大': '東京科学大学',
            '一橋大': '一橋大学',
            
            # 旧称の統一
            '帝国大学': '',  # 削除対象
        }
        
        # キャッシュ
        self._normalization_cache: Dict[str, str] = {}
    
    def normalize_university_name(self, university_name: str) -> str:
        """
        大学名を正規化する
        
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
        
        # 特別なマッピングを適用
        for old_name, new_name in self.special_mappings.items():
            if old_name in normalized:
                if new_name:  # 置換
                    normalized = normalized.replace(old_name, new_name)
                else:  # 削除
                    normalized = normalized.replace(old_name, '')
        
        # 正規化パターンを順次適用
        for pattern, replacement in self.normalization_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        
        # 前後の空白を除去
        normalized = normalized.strip()
        
        # 結果をキャッシュ
        self._normalization_cache[original_name] = normalized
        
        logger.debug(f"大学名正規化: '{original_name}' → '{normalized}'")
        
        return normalized
    
    def get_university_groups(self, university_names: List[str]) -> Dict[str, List[str]]:
        """
        大学名リストを正規化してグループ化する
        
        Args:
            university_names: 元の大学名リスト
            
        Returns:
            正規化名をキーとした大学名グループ
        """
        groups = defaultdict(list)
        
        for name in university_names:
            normalized = self.normalize_university_name(name)
            if normalized:  # 空でない場合のみ追加
                groups[normalized].append(name)
        
        return dict(groups)
    
    def generate_normalization_sql(self, source_column: str) -> str:
        """
        BigQuery用の正規化SQLを生成する
        
        Args:
            source_column: 元の大学名カラム名
            
        Returns:
            正規化用のSQL CASE文
        """
        sql_parts = ["CASE"]
        
        # 特別なマッピング
        for old_name, new_name in self.special_mappings.items():
            if new_name:  # 置換
                sql_parts.append(f"WHEN {source_column} LIKE '%{old_name}%' THEN REPLACE({source_column}, '{old_name}', '{new_name}')")
        
        # 正規化パターン
        current_column = source_column
        for i, (pattern, replacement) in enumerate(self.normalization_patterns):
            if pattern.startswith('^') and pattern.endswith('$'):
                # 完全一致パターンの場合
                regex_pattern = pattern[1:-1]  # ^ と $ を除去
                sql_parts.append(f"WHEN REGEXP_CONTAINS({current_column}, r'{regex_pattern}') THEN REGEXP_REPLACE({current_column}, r'{pattern}', '{replacement}')")
        
        sql_parts.append(f"ELSE {source_column}")
        sql_parts.append("END")
        
        return " ".join(sql_parts)
    
    def get_normalized_university_stats_query(self, table_name: str) -> str:
        """
        正規化された大学名統計用のBigQueryクエリを生成
        
        Args:
            table_name: テーブル名
            
        Returns:
            正規化統計用SQLクエリ
        """
        normalization_sql = self.generate_dynamic_normalization_sql("main_affiliation_name_ja")
        
        return f"""
        WITH normalized_universities AS (
            SELECT 
                name_ja,
                main_affiliation_name_ja as original_university,
                {normalization_sql} as normalized_university
            FROM `{table_name}`
            WHERE main_affiliation_name_ja IS NOT NULL
        )
        SELECT 
            normalized_university as university_name,
            COUNT(DISTINCT name_ja) as researcher_count,
            ARRAY_AGG(DISTINCT original_university IGNORE NULLS) as original_names
        FROM normalized_universities
        WHERE normalized_university IS NOT NULL AND normalized_university != ''
        GROUP BY normalized_university
        ORDER BY researcher_count DESC
        """
    
    def generate_dynamic_normalization_sql(self, source_column: str) -> str:
        """
        動的な正規化SQL（全パターンを適用）を生成
        
        Args:
            source_column: 元の大学名カラム名
            
        Returns:
            動的正規化用のSQL
        """
        sql = f"TRIM({source_column})"
        
        # 特別なマッピングを適用
        for old_name, new_name in self.special_mappings.items():
            if new_name:  # 置換
                sql = f"REPLACE({sql}, '{old_name}', '{new_name}')"
            else:  # 削除
                sql = f"REPLACE({sql}, '{old_name}', '')"
        
        # 正規化パターンを適用
        for pattern, replacement in self.normalization_patterns:
            # BigQuery用のREGEXP_REPLACEに変換
            if '(.+大学)' in pattern:
                # キャプチャグループを含むパターン
                sql = f"REGEXP_REPLACE({sql}, r'{pattern}', r'{replacement}')"
            elif pattern == r'\s+':
                # 空白の正規化
                sql = f"REGEXP_REPLACE({sql}, r'\\s+', ' ')"
            elif pattern == r'　+':
                # 全角空白の除去
                sql = f"REGEXP_REPLACE({sql}, r'　+', '')"
        
        return f"TRIM({sql})"

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
    BigQuery用の動的正規化SQLを取得
    
    Args:
        source_column: 元の大学名カラム名
        
    Returns:
        正規化用SQL
    """
    return normalizer.generate_dynamic_normalization_sql(source_column)

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
    正規化機能のテスト
    """
    test_cases = [
        "東京大学大学院",
        "東京大学医学部附属病院",
        "京都大学大学院医学研究科",
        "大阪大学核物理研究センター",
        "東北大学金属材料研究所",
        "学校法人慶應義塾大学",
        "国立大学法人筑波大学",
        "東京科学大学大学院",  # 新しい大学名
        "新設大学研究センター",  # 新規大学のテスト
    ]
    
    print("大学名正規化テスト:")
    for name in test_cases:
        normalized = normalize_university_name(name)
        print(f"  '{name}' → '{normalized}'")

if __name__ == "__main__":
    test_normalization()
