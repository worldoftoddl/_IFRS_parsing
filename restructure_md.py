#!/usr/bin/env python3
"""
K-IFRS 마크다운 파일 구조 통일 스크립트.

규칙:
1. 맨 앞의 저작권/보일러플레이트 제거
2. ## 용어의 정의 → ### 용어의 정의
3. ## 본 문 → ## 서문
4. ### 용어의 정의 다음부터 적용지침/결론도출근거 전까지 ## 본문으로 묶기
"""

import re
from pathlib import Path

OUTPUT_DIR = Path('/home/shin/Project/_IFRS_parsing/output/md')

# ## 서문 하위에 들어갈 ### 섹션 기본 이름
SEOMUN_NAMES = {'목적', '적용', '적용범위', '용어의 정의', '참조', '배경'}

# 구조적 H2 (제거 후 재구성)
STRUCTURAL_H2 = {'서문', '본 문', '본문'}


def normalize_heading(text):
    """헤딩 텍스트에서 장 번호, 괄호 부분을 제거하여 기본 이름 추출.
    예: '제1장 목적' → '목적', '용어의 정의(문단 AG3~AG23 참조)' → '용어의 정의'
    """
    # 괄호 이하 제거
    base = text.split('(')[0].strip()
    # '제N장 ' 접두어 제거
    base = re.sub(r'^제\d+장\s*', '', base)
    return base


def is_seomun_section(text):
    """H3 헤딩이 서문 섹션에 해당하는지 판단."""
    return normalize_heading(text) in SEOMUN_NAMES


def is_definitions_h2(text):
    """H2 헤딩이 '용어의 정의' 섹션인지 판단."""
    return normalize_heading(text) == '용어의 정의'


def parse_frontmatter(lines):
    if not lines or lines[0].strip() != '---':
        return [], 0
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return lines[:i + 1], i + 1
    return [], 0


def find_h1(lines, start):
    for i in range(start, len(lines)):
        if lines[i].startswith('# ') and not lines[i].startswith('## '):
            return lines[i], i
    return None, start


def parse_blocks(lines, start):
    """라인을 플랫 블록 리스트로 파싱. 각 블록 = 헤딩 + 내용."""
    blocks = []
    current = None

    for i in range(start, len(lines)):
        line = lines[i]

        if line.startswith('### '):
            if current is not None:
                blocks.append(current)
            current = {
                'level': 3,
                'heading_text': line[4:].strip(),
                'heading_line': line,
                'content': [],
            }
        elif line.startswith('## ') and not line.startswith('### '):
            if current is not None:
                blocks.append(current)
            current = {
                'level': 2,
                'heading_text': line[3:].strip(),
                'heading_line': line,
                'content': [],
            }
        else:
            if current is not None:
                current['content'].append(line)
            else:
                current = {
                    'level': 0,
                    'heading_text': '',
                    'heading_line': '',
                    'content': [line],
                }

    if current is not None:
        blocks.append(current)

    return blocks


def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    # 프론트매터 파싱
    fm_lines, rest_start = parse_frontmatter(lines)

    # H1 찾기
    h1_line, h1_idx = find_h1(lines, rest_start)
    if not h1_line:
        return None, "H1 없음"

    # 블록 파싱
    blocks = parse_blocks(lines, h1_idx + 1)

    # ### 헤딩 존재 확인
    has_h3 = any(b['level'] == 3 for b in blocks)
    if not has_h3:
        return None, "### 헤딩 없음"

    # 블록 분류
    SKIP = 'skip'
    SEOMUN = 'seomun'
    BONMUN = 'bonmun'
    STANDALONE = 'standalone'

    categorized = []
    in_standalone_zone = False  # 독립 H2를 만나면 True

    for block in blocks:
        level = block['level']
        text = block['heading_text']

        # 고아 콘텐츠 (저작권 등) → 스킵
        if level == 0:
            categorized.append((SKIP, block))
            continue

        # 구조적 H2 (서문/본 문/본문) → 스킵
        if level == 2 and text in STRUCTURAL_H2:
            categorized.append((SKIP, block))
            continue

        # 규칙 2: ## 용어의 정의 → ### 용어의 정의
        if level == 2 and is_definitions_h2(text):
            if not in_standalone_zone:
                # 본문 앞의 용어의 정의 → 서문으로
                block['level'] = 3
                block['heading_line'] = '### ' + text
                categorized.append((SEOMUN, block))
            else:
                # 적용지침/결론도출근거 내의 용어의 정의 → 그대로 유지
                categorized.append((STANDALONE, block))
            continue

        if level == 2:
            # 독립 H2 (적용지침, 결론도출근거, 경과규정 등)
            in_standalone_zone = True
            categorized.append((STANDALONE, block))
            continue

        # level == 3: 이름 기반 분류
        if not in_standalone_zone and is_seomun_section(text):
            categorized.append((SEOMUN, block))
        elif in_standalone_zone:
            categorized.append((STANDALONE, block))
        else:
            categorized.append((BONMUN, block))

    # 출력 조립
    output = []
    output.extend(fm_lines)
    output.append('')
    output.append(h1_line)
    output.append('')
    output.append('## 서문')
    output.append('<!-- component: main | authority: 1 -->')
    output.append('')

    seomun_blocks = [b for cat, b in categorized if cat == SEOMUN]
    bonmun_blocks = [b for cat, b in categorized if cat == BONMUN]
    standalone_blocks = [b for cat, b in categorized if cat == STANDALONE]

    for block in seomun_blocks:
        output.append(block['heading_line'])
        output.extend(block['content'])

    if bonmun_blocks:
        output.append('')
        output.append('## 본문')
        output.append('')
        for block in bonmun_blocks:
            output.append(block['heading_line'])
            output.extend(block['content'])

    for block in standalone_blocks:
        output.append(block['heading_line'])
        output.extend(block['content'])

    result = '\n'.join(output)
    # 과도한 빈 줄 정리 (3줄 이상 → 2줄)
    result = re.sub(r'\n{3,}', '\n\n', result)
    if not result.endswith('\n'):
        result += '\n'

    stats = {
        'seomun': len(seomun_blocks),
        'bonmun': len(bonmun_blocks),
        'standalone': len(standalone_blocks),
    }
    return result, stats


def main():
    md_files = sorted(OUTPUT_DIR.rglob('*.md'))
    print(f"총 {len(md_files)}개 마크다운 파일 발견\n")

    modified = 0
    skipped = 0

    for filepath in md_files:
        rel = filepath.relative_to(OUTPUT_DIR)
        result, info = process_file(filepath)

        if isinstance(info, str):
            print(f"  SKIP  {rel}  ({info})")
            skipped += 1
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(result)
            s = info
            print(f"  OK    {rel}  (서문:{s['seomun']} 본문:{s['bonmun']} 독립:{s['standalone']})")
            modified += 1

    print(f"\n완료: {modified}개 변환, {skipped}개 스킵")


if __name__ == '__main__':
    main()
