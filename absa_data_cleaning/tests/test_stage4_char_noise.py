import pandas as pd

from transforms.stage4_char_noise import (
    CLEANED_CONTENT_COL,
    EMOJIS_COL,
    changed_rows,
    handle_inline_emoji,
    normalize_repeated_characters,
    remove_meaningless_special_chars,
)

C = "Nội dung tự do"


def _df(*texts):
    return pd.DataFrame({C: list(texts)})


def test_inline_emoji_moves_to_column():
    out = handle_inline_emoji(_df("đẹp \U0001F60D quá \U0001F44D", "tốt"))
    assert out[C].str.split().str.join(" ").tolist() == ["đẹp rất_thích quá ưng_ý", "tốt"]
    assert out[EMOJIS_COL].iloc[0] == "\U0001F60D\U0001F44D" and pd.isna(out[EMOJIS_COL].iloc[1])
    assert out["emoji_sentiment"].iloc[0] == "pos" and pd.isna(out["emoji_sentiment"].iloc[1])
    # '_' từ emoji phải sống qua bước 15, '_' lẻ thì bị bỏ
    assert remove_meaningless_special_chars(out)[C].iloc[0].split()[1] == "rất_thích"
    assert remove_meaningless_special_chars(_df("a _ b"))[C].iloc[0].split() == ["a", "b"]


def test_special_chars():
    out = remove_meaningless_special_chars(_df("hàng~đẹp^^ giá 1.000₫!", "~~~"))
    assert out[C].iloc[0].split() == ["hàng", "đẹp", "giá", "1.000₫!"]
    assert pd.isna(out[C].iloc[1])


def test_repeated():
    out = normalize_repeated_characters(_df("đẹppppp quááá!!!!! 1000000", "gooood xoong ....."))
    assert out[C].tolist() == ["đẹp quá! 1000000", "good xoong ..."]


def test_changed_rows():
    b = _df("đẹppp", "tốt")
    s = changed_rows(b, normalize_repeated_characters(b))
    assert len(s) == 1 and s[CLEANED_CONTENT_COL].iloc[0] == "đẹp"
