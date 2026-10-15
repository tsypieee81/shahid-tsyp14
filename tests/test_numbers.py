"""Every number in the proposal-facing documents traces to the ledger or a cited result file, and
every ledger number matches the result files it cites (shahid/check_numbers.py)."""
from shahid import check_numbers as cn


def test_document_numbers_trace_to_ledger_or_results():
    total, bad = cn.check()
    assert total > 500 and not bad, bad[:10]


def test_ledger_numbers_match_cited_result_files():
    total, bad = cn.level2(cn.ledger_rows())
    assert total > 200 and not bad, bad[:10]


def test_generated_estimates_follow_rounding_rule():
    total, bad = cn.level3()
    assert total > 20 and not bad, bad[:10]


def test_allowlist_holds_no_measured_result():
    counts, untagged = cn.allowlist_tags()
    assert not untagged, untagged


def test_external_document_mode(tmp_path):
    """--doc mode: ledger and result-file numbers pass, an invented number is reported; .docx is read."""
    import zipfile
    body = ("<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body>"
            "<w:p><w:r><w:t>Held-out coverage 0.723 and outage recall 0.670.</w:t></w:r></w:p>"
            "<w:p><w:r><w:t>Invented accuracy 97.31 percent.</w:t></w:r></w:p></w:body></w:document>")
    doc = tmp_path / "proposal.docx"
    with zipfile.ZipFile(doc, "w") as z:
        z.writestr("word/document.xml", body)
    total, bad = cn.check_external(doc)
    assert total == 3 and [b[1] for b in bad] == ["97.31"]
    extra = tmp_path / "extra_ledger.md"
    extra.write_text("| X-1 | proposed row with 97.31 | file | cmd | — | — |\n", encoding="utf8")
    assert cn.check_external(doc, extra)[1] == []


def test_proposal_tables_match_results_verbatim():
    """Every number in every LaTeX proposal table is printed verbatim in RESULTS.md, the ledger, a
    study README or the allowlist (shahid.check_tables)."""
    import pytest
    from shahid import check_tables
    with pytest.raises(SystemExit) as e:
        check_tables.main()
    assert e.value.code == 0
