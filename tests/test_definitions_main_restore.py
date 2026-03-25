"""IAS 계열 기준서에서 '용어의 정의' 이후 본문이 main으로 복원되는지 테스트.

근본 원인: ## 용어의 정의 → definitions 진입 후 서브섹션(###)이 나와도
definitions에 갇혀서 본문 문단이 검색 대상에서 누락됨.

영향: K-IFRS 1001, 1008, 1021, 1027, 1028, 1038, 1039, 1041 (8개)
"""

from pathlib import Path

import pytest

from ingester.md_parser import parse_markdown_file


# 영향받는 기준서와 기대되는 main 최소 문단 수
AFFECTED_STANDARDS = {
    "K-IFRS 1021": {"min_main": 30, "must_have_paras": ["23", "28", "39"]},
    "K-IFRS 1001": {"min_main": 50, "must_have_paras": ["15", "54", "82"]},
    "K-IFRS 1008": {"min_main": 20, "must_have_paras": ["14", "32"]},
    "K-IFRS 1038": {"min_main": 30, "must_have_paras": ["21", "57"]},
    "K-IFRS 1028": {"min_main": 15, "must_have_paras": ["10", "16"]},
    "K-IFRS 1039": {"min_main": 10, "must_have_paras": []},
    "K-IFRS 1041": {"min_main": 15, "must_have_paras": ["10", "26"]},
    "K-IFRS 1027": {"min_main": 10, "must_have_paras": ["10", "15"]},
}

MD_DIR = Path("output/md")


def _find_md_file(standard_number: str) -> Path | None:
    """기준서 번호로 마크다운 파일 찾기."""
    for f in MD_DIR.rglob("*.md"):
        if f"제{standard_number}호" in f.name:
            return f
    return None


def _parse_standard(standard_id: str):
    """기준서 파싱 후 main 청크만 반환."""
    number = standard_id.split()[-1]  # "K-IFRS 1021" → "1021"
    md_file = _find_md_file(number)
    assert md_file is not None, f"{standard_id} 마크다운 파일 없음"

    standard, chunks, _ = parse_markdown_file(md_file)
    main_chunks = [c for c in chunks if c.component == "main"]
    return main_chunks


class TestDefinitionsMainRestore:
    """용어의 정의 이후 본문이 main으로 복원되는지 검증."""

    @pytest.mark.parametrize("standard_id,expected", AFFECTED_STANDARDS.items())
    def test_main_chunk_count(self, standard_id, expected):
        """각 기준서의 main 청크 수가 최소 기대값 이상이어야 한다."""
        main_chunks = _parse_standard(standard_id)
        main_count = len(main_chunks)
        assert main_count >= expected["min_main"], (
            f"{standard_id}: main 청크 {main_count}개, "
            f"최소 {expected['min_main']}개 기대. "
            f"definitions 이후 본문 복원 실패?"
        )

    @pytest.mark.parametrize("standard_id,expected", AFFECTED_STANDARDS.items())
    def test_critical_paragraphs_in_main(self, standard_id, expected):
        """핵심 문단이 main 컴포넌트에 있어야 한다."""
        if not expected["must_have_paras"]:
            pytest.skip(f"{standard_id}: 검증할 문단번호 없음")

        main_chunks = _parse_standard(standard_id)
        main_paras = {c.para_number for c in main_chunks if c.para_number}

        for para in expected["must_have_paras"]:
            assert para in main_paras, (
                f"{standard_id}: 문단 {para}가 main에 없음. "
                f"main 문단: {sorted(main_paras)[:10]}..."
            )

    def test_1021_para23_not_in_definitions(self):
        """K-IFRS 1021 문단 23은 definitions가 아닌 main이어야 한다."""
        number = "1021"
        md_file = _find_md_file(number)
        assert md_file is not None

        _, chunks, _ = parse_markdown_file(md_file)
        para23 = [c for c in chunks if c.para_number == "23"]

        assert len(para23) > 0, "문단 23이 파싱되지 않음"
        assert para23[0].component == "main", (
            f"문단 23의 component={para23[0].component}, main이어야 함"
        )

    def test_definitions_only_contains_actual_definitions(self):
        """definitions 컴포넌트에는 실제 정의 내용만 있어야 한다."""
        md_file = _find_md_file("1021")
        assert md_file is not None

        _, chunks, _ = parse_markdown_file(md_file)
        def_chunks = [c for c in chunks if c.component == "definitions"]

        # 정의 섹션의 문단번호는 보통 낮은 번호 (8~17 정도)
        for c in def_chunks:
            if c.para_number and c.para_number.isdigit():
                para_num = int(c.para_number)
                # 정의 문단은 보통 20 미만
                assert para_num < 25, (
                    f"문단 {c.para_number}이 definitions에 있음 — "
                    f"본문이 definitions로 잘못 분류된 것으로 보임"
                )
