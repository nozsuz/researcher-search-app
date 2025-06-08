"""
大学名正規化システム - 完全統合版（JSONデータ分析結果対応）
残存パターンを完全に統合
"""

import re
import logging

logger = logging.getLogger(__name__)

def normalize_university_name(university_name: str) -> str:
    """
    大学名を正規化する（完全統合版）
    JSONデータ分析結果に基づく完全パターン対応
    """
    if not university_name:
        return ""
    
    # 全角スペース等の正規化
    normalized = university_name.strip()
    normalized = re.sub(r'　+', '', normalized)  # 全角スペース除去
    normalized = re.sub(r'\s+', '', normalized)  # 半角スペース除去
    normalized = re.sub(r'[\(\)（）].*$', '', normalized)  # 括弧内容除去
    
    # 国立大学法人パターンの優先処理
    if '国立大学法人東海国立大学機構名古屋大学' in normalized:
        return '名古屋大学'
    if '国立大学法人東京科学大学' in normalized:
        return '東京科学大学'
    if '国立大学法人' in normalized:
        normalized = re.sub(r'^国立大学法人.*?([^　\s]+大学)', r'\1', normalized)
    
    # 大学統合処理（最優先）
    if '東京工業大学' in normalized or '東京医科歯科大学' in normalized:
        return '東京科学大学'
    
    # JSONデータから抽出した完全な正規化パターン
    patterns = [
        # 複合大学院パターン
        (r'大学院医学研究院$', ''),
        (r'大学院歯学研究院$', ''),
        (r'大学院新領域創成科学研究科$', ''),
        (r'大学院人文社会系研究科$', ''),
        (r'大学院総合文化研究科$', ''),
        (r'大学院農学生命科学研究科$', ''),
        (r'大学院薬学系研究科$', ''),
        (r'大学院医学系研究科$', ''),
        (r'大学院医学研究科$', ''),
        (r'大学院工学研究科$', ''),
        (r'大学院工学系研究科$', ''),
        (r'大学院歯学研究科$', ''),
        
        # 病院・医療機関
        (r'医学部附属病院$', ''),
        (r'歯学部附属病院$', ''),
        (r'附属病院$', ''),
        (r'病院$', ''),
        
        # 東京大学の特殊機関（JSONから抽出）
        (r'大気海洋研究所$', ''),
        (r'iPS細胞研究所$', ''),
        (r'物性研究所$', ''),
        (r'生産技術研究所$', ''),
        (r'史料編纂所$', ''),
        (r'定量生命科学研究所$', ''),
        (r'地震研究所$', ''),
        (r'医科学研究所$', ''),
        (r'先端科学技術研究センター$', ''),
        (r'東洋文化研究所$', ''),
        (r'未来ビジョン研究センター$', ''),
        (r'宇宙線研究所$', ''),
        (r'国際高等研究所$', ''),
        (r'社会科学研究所$', ''),
        (r'総合研究博物館$', ''),
        
        # 東北大学特殊機関
        (r'加齢医学研究所$', ''),
        (r'東北メディカル・メガバンク機構$', ''),
        (r'東北メディカルメガバンク機構$', ''),
        (r'材料科学高等研究所$', ''),
        (r'金属材料研究所$', ''),
        (r'多元物質科学研究所$', ''),
        (r'電気通信研究所$', ''),
        (r'流体科学研究所$', ''),
        (r'災害科学国際研究所$', ''),
        (r'学際科学フロンティア研究所$', ''),
        
        # 北海道大学特殊機関
        (r'遺伝子病制御研究所$', ''),
        (r'低温科学研究所$', ''),
        (r'触媒科学研究所$', ''),
        (r'人獣共通感染症国際共同研究所$', ''),
        (r'創成研究機構$', ''),
        (r'化学反応創成研究拠点$', ''),
        (r'北方生物圏フィールド科学センター$', ''),
        
        # 九州大学特殊機関
        (r'生体防御医学研究所$', ''),
        (r'総合研究博物館$', ''),
        (r'先導物質化学研究所$', ''),
        (r'応用力学研究所$', ''),
        (r'熱帯農学研究センター$', ''),
        
        # 京都大学特殊機関
        (r'防災研究所$', ''),
        (r'化学研究所$', ''),
        (r'基礎物理学研究所$', ''),
        (r'数理解析研究所$', ''),
        (r'人文科学研究所$', ''),
        (r'東南アジア地域研究研究所$', ''),
        (r'ウイルス・再生医科学研究所$', ''),
        (r'生存圏研究所$', ''),
        (r'生態学研究センター$', ''),
        (r'霊長類研究所$', ''),
        (r'複合原子力科学研究所$', ''),
        (r'エネルギー理工学研究所$', ''),
        (r'経済研究所$', ''),
        
        # 大阪大学特殊機関
        (r'免疫学フロンティア研究センター$', ''),
        (r'微生物病研究所$', ''),
        (r'蛋白質研究所$', ''),
        (r'産業科学研究所$', ''),
        (r'核物理研究センター$', ''),
        (r'レーザー科学研究所$', ''),
        (r'接合科学研究所$', ''),
        (r'社会経済研究所$', ''),
        
        # 名古屋大学特殊機関
        (r'宇宙地球環境研究所$', ''),
        (r'素粒子宇宙起源研究所$', ''),
        (r'環境医学研究所$', ''),
        (r'未来材料・システム研究所$', ''),
        (r'トランスフォーマティブ生命分子研究所$', ''),
        
        # 筑波大学特殊機関
        (r'国際統合睡眠医科学研究機構$', ''),
        (r'計算科学研究センター$', ''),
        (r'働く人への心理支援開発研究センター$', ''),
        (r'健幸ライフスタイル開発研究センター$', ''),
        
        # 東京科学大学特殊機関
        (r'難治疾患研究所$', ''),
        (r'生体材料工学研究所$', ''),
        (r'総合研究院$', ''),
        (r'統合研究機構$', ''),
        
        # 大学院・研究科パターン
        (r'大学院人間・環境学研究科$', ''),
        (r'大学院人間・環境学$', ''),
        (r'大学院人文学研究科$', ''),
        (r'大学院理学研究科$', ''),
        (r'大学院理学系研究科$', ''),
        (r'大学院工学研究院$', ''),
        (r'大学院情報科学研究科$', ''),
        (r'大学院環境科学研究科$', ''),
        (r'大学院生命科学研究科$', ''),
        (r'大学院文学研究科$', ''),
        (r'大学院法学研究科$', ''),
        (r'大学院経済学研究科$', ''),
        (r'大学院教育学研究科$', ''),
        (r'大学院保健科学研究院$', ''),
        (r'大学院薬学研究院$', ''),
        (r'大学院農学研究院$', ''),
        (r'大学院水産科学研究院$', ''),
        (r'大学院獣医学研究院$', ''),
        (r'大学院基礎工学研究科$', ''),
        (r'大学院連合小児発達学研究科$', ''),
        
        # 学部パターン
        (r'医学部$', ''),
        (r'歯学部$', ''),
        (r'工学部$', ''),
        (r'理学部$', ''),
        (r'農学部$', ''),
        (r'文学部$', ''),
        (r'法学部$', ''),
        (r'経済学部$', ''),
        (r'教育学部$', ''),
        
        # 研究院・研究所パターン
        (r'医学研究院$', ''),
        (r'歯学研究院$', ''),
        (r'工学研究院$', ''),
        (r'理学研究院$', ''),
        (r'農学研究院$', ''),
        (r'文学研究院$', ''),
        (r'人文科学研究院$', ''),
        (r'人間科学研究院$', ''),
        (r'地球環境科学研究院$', ''),
        (r'先端生命科学研究院$', ''),
        (r'総合理工学研究院$', ''),
        (r'芸術工学研究院$', ''),
        
        # 一般的パターン
        (r'研究科$', ''),
        (r'研究院$', ''),
        (r'研究所$', ''),
        (r'学部$', ''),
        (r'センター$', ''),
        (r'機構$', ''),
        (r'機関$', ''),
        
        # 短期大学パターン
        (r'短期大学部$', ''),
        (r'短期大$', ''),
        
        # その他
        (r'大学院$', ''),
    ]
    
    # パターンマッチング適用
    for pattern, replacement in patterns:
        normalized = re.sub(pattern, replacement, normalized)
    
    return normalized.strip()

def get_complete_university_stats_query(table_name: str) -> str:
    """
    完全統合版の大学統計クエリ
    JSONデータ分析結果に基づく完全パターン対応
    """
    return f"""
    WITH normalized_universities AS (
      SELECT 
        CASE
          -- 国立大学法人パターンの特別処理
          WHEN main_affiliation_name_ja LIKE '%国立大学法人東海国立大学機構名古屋大学%' THEN '名古屋大学'
          WHEN main_affiliation_name_ja LIKE '%国立大学法人東京科学大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東京工業大学%' THEN '東京科学大学'
          WHEN main_affiliation_name_ja LIKE '%東京医科歯科大学%' THEN '東京科学大学'
          ELSE
            -- 段階的正規化処理
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
                                                                                                      -- 基本的な正規化
                                                                                                      REGEXP_REPLACE(
                                                                                                        REGEXP_REPLACE(
                                                                                                          main_affiliation_name_ja,
                                                                                                          r'　+', ''
                                                                                                        ),
                                                                                                        r'\\s+', ''
                                                                                                      ),
                                                                                                      r'\\([^)]*\\)', ''
                                                                                                    ),
                                                                                                    r'^国立大学法人.*?([^　\\s]+大学)', '\\1'
                                                                                                  ),
                                                                                                  r'大学院医学研究院$', ''
                                                                                                ),
                                                                                                r'大学院歯学研究院$', ''
                                                                                              ),
                                                                                              r'大学院新領域創成科学研究科$', ''
                                                                                            ),
                                                                                            r'大学院人文社会系研究科$', ''
                                                                                          ),
                                                                                          r'大学院総合文化研究科$', ''
                                                                                        ),
                                                                                        r'大学院農学生命科学研究科$', ''
                                                                                      ),
                                                                                      r'大学院薬学系研究科$', ''
                                                                                    ),
                                                                                    r'大学院医学系研究科$', ''
                                                                                  ),
                                                                                  r'大学院医学研究科$', ''
                                                                                ),
                                                                                r'大学院工学研究科$', ''
                                                                              ),
                                                                              r'大学院工学系研究科$', ''
                                                                            ),
                                                                            r'大学院歯学研究科$', ''
                                                                          ),
                                                                          r'医学部附属病院$', ''
                                                                        ),
                                                                        r'歯学部附属病院$', ''
                                                                      ),
                                                                      r'附属病院$', ''
                                                                    ),
                                                                    r'病院$', ''
                                                                  ),
                                                                  r'大気海洋研究所$', ''
                                                                ),
                                                                r'iPS細胞研究所$', ''
                                                              ),
                                                              r'物性研究所$', ''
                                                            ),
                                                            r'生産技術研究所$', ''
                                                          ),
                                                          r'史料編纂所$', ''
                                                        ),
                                                        r'定量生命科学研究所$', ''
                                                      ),
                                                      r'地震研究所$', ''
                                                    ),
                                                    r'医科学研究所$', ''
                                                  ),
                                                  r'加齢医学研究所$', ''
                                                ),
                                                r'遺伝子病制御研究所$', ''
                                              ),
                                              r'生体防御医学研究所$', ''
                                            ),
                                            r'総合研究博物館$', ''
                                          ),
                                          r'防災研究所$', ''
                                        ),
                                        r'化学研究所$', ''
                                      ),
                                      r'基礎物理学研究所$', ''
                                    ),
                                    r'数理解析研究所$', ''
                                  ),
                                  r'難治疾患研究所$', ''
                                ),
                                r'宇宙地球環境研究所$', ''
                              ),
                              r'国際統合睡眠医科学研究機構$', ''
                            ),
                            r'計算科学研究センター$', ''
                          ),
                          r'先端科学技術研究センター$', ''
                        ),
                        r'東北メディカル・メガバンク機構$', ''
                      ),
                      r'大学院人間・環境学$', ''
                    ),
                    r'大学院理学系$', ''
                  ),
                  r'大学院教育学$', ''
                ),
                r'大学院工学$', ''
              ),
              r'医学研究院$', ''
            ) 
        END as university_name,
        name_ja,
        main_affiliation_name_ja as original_name
      FROM `{table_name}`
      WHERE main_affiliation_name_ja IS NOT NULL
        AND main_affiliation_name_ja LIKE '%大学%'
        AND main_affiliation_name_ja NOT LIKE '%元%'
        AND main_affiliation_name_ja NOT LIKE '%前%'
        AND main_affiliation_name_ja NOT LIKE '%-'
    ),
    
    final_cleanup AS (
      SELECT 
        -- 最終クリーンアップ
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
                            university_name,
                            r'研究科$', ''
                          ),
                          r'研究院$', ''
                        ),
                        r'研究所$', ''
                      ),
                      r'学部$', ''
                    ),
                    r'センター$', ''
                  ),
                  r'機構$', ''
                ),
                r'機関$', ''
              ),
              r'短期大学部$', ''
            ),
            r'短期大$', ''
          ),
          r'大学院$', ''
        ) as university_name,
        name_ja,
        original_name
      FROM normalized_universities
    ),
    
    university_stats AS (
      SELECT 
        university_name,
        COUNT(DISTINCT name_ja) as researcher_count,
        ARRAY_AGG(DISTINCT original_name LIMIT 15) as original_names
      FROM final_cleanup
      WHERE LENGTH(university_name) > 2
        AND university_name LIKE '%大学%'
      GROUP BY university_name
      HAVING COUNT(DISTINCT name_ja) >= 5
    )
    
    SELECT 
      university_name,
      researcher_count,
      original_names
    FROM university_stats
    ORDER BY researcher_count DESC
    LIMIT 100
    """
