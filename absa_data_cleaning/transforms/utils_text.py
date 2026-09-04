"""
transforms/utils_text.py
==========================
Hàm tiện ích thuần (pure) dùng chung giữa nhiều file tang*_*.py — regex,
chuẩn hoá unicode, đo độ tương đồng chuỗi, v.v.

Nguyên tắc: mọi hàm ở đây phải THUẦN (không side-effect, cùng input luôn ra
cùng output) để các hàm ở tang*_*.py có thể compose lại một cách an toàn.
"""


def normalize_unicode(text: str) -> str:
    """Chuẩn hoá Unicode (NFC) cho tiếng Việt — nền tảng cho nhiều bước Tầng 2.

    TODO: implement bằng unicodedata.normalize("NFC", text).
    """
    raise NotImplementedError


def strip_extra_whitespace(text: str) -> str:
    """Loại khoảng trắng thừa / nhiều khoảng trắng liên tiếp (T2.24).

    TODO: implement bằng regex.
    """
    raise NotImplementedError


def is_emoji_only(text: str) -> bool:
    """Kiểm tra chuỗi chỉ gồm emoji (hỗ trợ T2.9).

    TODO: implement.
    """
    raise NotImplementedError


def count_meaningful_tokens(text: str) -> int:
    """Đếm số "từ có nghĩa" trong chuỗi — hỗ trợ T2.11, T2.12
    (review quá ngắn / chỉ có ký tự vô nghĩa).

    TODO: implement — cân nhắc dùng tokenizer tiếng Việt (underthesea/pyvi) khi
    triển khai thật, hiện để interface trung lập với thư viện cụ thể.
    """
    raise NotImplementedError


def text_similarity(a: str, b: str) -> float:
    """Trả về điểm tương đồng [0,1] giữa 2 chuỗi — dùng cho near-duplicate (T2.16).

    TODO: implement (VD: dùng difflib.SequenceMatcher hoặc cosine trên TF-IDF/embedding
    — quyết định khi có số liệu thực nghiệm về hiệu năng/độ chính xác).
    """
    raise NotImplementedError


def contains_url(text: str) -> bool:
    """Kiểm tra chuỗi có chứa URL không — hỗ trợ T2.13 (review chỉ chứa URL/quảng cáo).

    TODO: implement bằng regex URL.
    """
    raise NotImplementedError
