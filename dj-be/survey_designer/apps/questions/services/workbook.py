"""Small openpyxl compatibility helpers for in-memory workbook exports."""

from io import BytesIO


def save_virtual_workbook(workbook) -> bytes:
    """Save a workbook without relying on openpyxl's removed helper."""

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
