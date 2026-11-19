-- 암장 페이지(/gyms)용 데이터 추출 쿼리 (MySQL 8)
--
-- 운영 DB에서 읽기 전용으로 실행하고, 결과(gyms 컬럼 한 칸의 JSON)를
-- scripts/gyms.json 으로 저장한 뒤 `python3 scripts/build-gyms.py` 를 실행한다.
--
--   mysql -h <host> -u <readonly-user> -p climbing_db --default-character-set=utf8mb4 --raw --skip-column-names \
--     -e "source scripts/export-gyms.sql" > scripts/gyms.json
--
-- 담는 기준
--   - 운영 중인 암장만: is_active = 1, closed_at IS NULL
--   - 난이도 체계를 관리자가 검수한 암장만: difficulty_scheme_admin_verified = 1
--     (검수 안 된 암장은 페이지를 만들지 않는다. 얇은 페이지가 사이트 전체 평가를 깎지 않도록)
--   - 난이도·홀드 색은 CONFIRMED 항목만 (앱의 PUBLIC_BROWSE 기준과 같다)
--
-- 일부러 빼는 것
--   - gym_image_url, gym_blog_posts: 외부에서 수집한 이미지·글이라 공개 레포에 올리지 않는다
--   - kakao_id, source, last_synced_at: 내부 수집 메타데이터
--   - price_items, business_hours: 한 번 뽑은 값은 금방 낡는다. 틀린 가격·시간이 노출되지 않도록 뺀다

SET SESSION group_concat_max_len = 16777216;

SELECT JSON_OBJECT(
  'exportedAt', DATE_FORMAT(UTC_TIMESTAMP(), '%Y-%m-%dT%H:%i:%sZ'),
  'gyms', COALESCE(JSON_ARRAYAGG(g.gym), JSON_ARRAY())
) AS gyms
FROM (
  SELECT JSON_OBJECT(
    'id',          cg.gym_id,
    'name',        cg.name,
    'region',      cg.region,
    'address',     cg.address,
    'latitude',    cg.latitude,
    'longitude',   cg.longitude,
    'subway',      cg.subway,
    'naverMapUrl', cg.naver_map_url,
    'instagramUrl',cg.instagram_url,
    'holdSchemeVerified', cg.hold_scheme_admin_verified = 1,
    'facilities', (
      SELECT COALESCE(JSON_ARRAYAGG(gf.facility_type), JSON_ARRAY())
      FROM gym_facilities gf
      WHERE gf.gym_id = cg.gym_id
    ),
    'difficulties', (
      SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT(
        'sortOrder', gd.sort_order,
        'type',      gd.type,
        'label',     gd.label,
        'hex',       COALESCE(gd.hex_code, cc.default_hex_code),
        'colorName', cc.name,
        'standard',  sd.name
      )), JSON_ARRAY())
      FROM gym_difficulties gd
      LEFT JOIN color_codes cc ON cc.color_code_id = gd.color_code_id
      LEFT JOIN standard_difficulties sd ON sd.standard_difficulty_id = gd.standard_difficulty_id
      WHERE gd.gym_id = cg.gym_id AND gd.status = 'CONFIRMED'
    ),
    'holdColors', (
      SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT(
        'sortOrder', hc.sort_order,
        'hex',       hc.hex_code,
        'colorName', cc.name
      )), JSON_ARRAY())
      FROM gym_hold_colors hc
      LEFT JOIN color_codes cc ON cc.color_code_id = hc.color_code_id
      WHERE hc.gym_id = cg.gym_id AND hc.status = 'CONFIRMED'
    )
  ) AS gym
  FROM climbing_gyms cg
  WHERE cg.is_active = 1
    AND cg.closed_at IS NULL
    AND cg.difficulty_scheme_admin_verified = 1
  ORDER BY cg.region, cg.name
) g;
