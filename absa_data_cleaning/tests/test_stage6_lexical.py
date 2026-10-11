import pandas as pd

from transforms.stage6_lexical import (
    SOURCE_ROW_COL,
    SUSPECT_TOKENS_COL,
    TOKEN_DETAIL_COL,
    annotate_suggestions,
    build_token_stats,
    classify_token,
    list_nonstandard_token_reviews,
    token_frequency_table,
    vote_suggestion,
)

C = "Nội dung tự do"


def test_list_nonstandard_tokens():
    texts = ["hàng đẹp lắm"] * 5 + ["Hàng ko đẹp, iphone 200k", "hang dep ship nhanh", "con mèo còn đẹp lắm", "nhaa", "ngừi bán nhanh"]
    df = pd.DataFrame({C: texts + [None]})
    stats = build_token_stats(df[C].dropna())
    out = list_nonstandard_token_reviews(df, stats)
    assert out.index.tolist() == [5, 6, 8, 9]  # 'con': 'còn' không gấp >= 3 lần 'con' -> bỏ qua
    assert out[SOURCE_ROW_COL].tolist() == [7, 8, 10, 11]
    assert list(out.columns[:4]) == [SOURCE_ROW_COL, C, SUSPECT_TOKENS_COL, TOKEN_DETAIL_COL]
    assert out[SUSPECT_TOKENS_COL].tolist() == ["ko, iphone, 200k", "hang, dep, ship", "nhaa", "ngừi"]
    assert out[TOKEN_DETAIL_COL].iloc[2] == "nhaa [ngoài từ điển]"  # 'nha' quá hiếm: không gợi ý lặp
    assert out[TOKEN_DETAIL_COL].iloc[3] == "ngừi [âm tiết lạ (ngoài vi_VN.dic)]"  # đúng luật ghép vần nhưng không có thật
    assert out[TOKEN_DETAIL_COL].iloc[0] == "ko -> không [teencode/viết tắt]; iphone [ngoài từ điển]; 200k [lẫn chữ số]"
    assert out[TOKEN_DETAIL_COL].iloc[1].startswith("hang -> hàng [thiếu/sai dấu]; dep -> đẹp [teencode/viết tắt]")
    assert df[C].iloc[5] == "Hàng ko đẹp, iphone 200k"  # không sửa câu

    freq = token_frequency_table({"ao": out}, stats)
    assert freq.set_index("Token").loc["hang", "Gợi ý luật"] == "hàng"
    assert freq["Số câu"].tolist() == [1] * 8


def test_vote_and_annotate():
    assert vote_suggestion({"luật": "nhé / nhà", "ViLexNorm": "nhà", "bmd1905": ""}) == ("nhà", 2)
    assert vote_suggestion({"model dấu": "giữ nguyên", "luật": "còn"}) == ("giữ nguyên", 1)  # hoà: nguồn đầu thắng
    assert vote_suggestion({"luật": ""}) == ("", 0)
    assert vote_suggestion({"model dấu": "giữ nguyên", "luật": "mình", "ViLexNorm": "mình"}, "model dấu") == ("giữ nguyên", 1)

    df = pd.DataFrame({C: ["hàng đẹp lắm"] * 5 + ["giao hang nhanh, sale rùi"]})
    stats = build_token_stats(df[C])
    assert classify_token("sale", stats) == ("tiếng Anh", "")
    out = annotate_suggestions(list_nonstandard_token_reviews(df, stats), stats, {"model dấu": [{"hang": "hàng"}]})
    assert out[TOKEN_DETAIL_COL].iloc[0] == (
        "hang -> hàng [thiếu/sai dấu] (2/2: model dấu=hàng; luật=hàng) | sale [tiếng Anh]"
        " | rùi -> rồi [âm tiết lạ (ngoài vi_VN.dic)] (1/1: ViLexNorm=rồi)"
    )
    freq = token_frequency_table({"ao": out}, stats, {"ao": {"model dấu": [{"hang": "hàng"}]}}).set_index("Token")
    assert freq.loc["hang", ["Gợi ý đồng thuận", "Số nguồn đồng ý", "Gợi ý model dấu"]].tolist() == ["hàng", 2, "hàng (1)"]


def test_row_replacements_and_apply():
    from transforms.stage6_lexical import apply_replacements, criteria_columns, format_replaced, row_replacements

    df = pd.DataFrame({C: ["hàng đẹp lắm"] * 5 + ["Ko tốt, giao hang nhanh, sale rùi, qua đẹp, 200 k, đường may"]})
    stats = build_token_stats(df[C])
    suspect = list_nonstandard_token_reviews(df, stats)
    ctx = {"model dấu": [{"hang": "hàng", "qua": "giữ nguyên"}]}
    (repl,) = row_replacements(suspect, stats, ctx, min_restorations=1)
    assert repl["ko"] == "không" and repl["hang"] == "hàng"  # >= 2 phiếu
    assert not {"rùi", "sale", "qua", "may"} & set(repl)  # 1 phiếu / không gợi ý / model giữ nguyên / NO_AUTO_REPLACE
    text = df[C].iloc[5]
    new, applied = apply_replacements(text, {**repl, "k": "không"})
    assert new == "Không tốt, giao hàng nhanh, sale rùi, qua đẹp, 200 k, đường may"  # giữ hoa đầu câu, '200 k' không đổi
    assert format_replaced(applied) == "ko -> không; hang -> hàng"
    assert len(row_replacements(suspect, stats, ctx, min_votes=1, min_restorations=1)[0]) > len(repl)
    assert "hang" not in row_replacements(suspect, stats, ctx)[0]  # mặc định cần >= 2 từ khôi phục dấu trong câu

    cols = pd.DataFrame({C: ["x"], "Chất liệu": ["vải"], "emojis": [None], "text_norm": ["x"], "Tiêu chí đánh giá": ["a: b"]})
    assert criteria_columns(cols) == ["Chất liệu"]
