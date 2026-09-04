"""
cli.py
======
Entry point dòng lệnh. Đây là nơi hiện thực hoá yêu cầu "chạy từng lần xử lý 1,
không bắt buộc chạy toàn bộ".

Cách dùng dự kiến (khi đã implement):

    # Chạy đúng 1 step (1 vấn đề trong taxonomy), trên tất cả sản phẩm:
    python cli.py run-step --id T2.17

    # Chạy đúng 1 step, chỉ trên 1 sản phẩm:
    python cli.py run-step --id T1.1 --product phone

    # Chạy toàn bộ 1 tầng:
    python cli.py run-tang --tang 2

    # Chạy toàn bộ pipeline (tuỳ chọn, không bắt buộc):
    python cli.py run-full

    # Xem tiến độ cài đặt so với 52 mục taxonomy:
    python cli.py coverage-report

TODO: implement bằng argparse hoặc click/typer (chọn 1, giữ tối giản dependency).
Mỗi subcommand chỉ gọi lại core.pipeline.Pipeline — KHÔNG chứa logic nghiệp vụ.
"""


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
