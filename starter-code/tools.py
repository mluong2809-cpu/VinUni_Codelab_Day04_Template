import json
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw-data")

# ---------------------------------------------------------------------------
# Tool #1: search_product_catalog
# TODO: Hoàn thiện hàm này — đọc file product_catalog.json, lọc theo category và max_price.
# ---------------------------------------------------------------------------

def search_product_catalog(category: str, max_price: int = 999999999999) -> List[Dict[str, Any]]:
    """
    Tra cứu sản phẩm/dịch vụ Vingroup theo danh mục và giá tối đa.
    
    Args:
        category: Loại sản phẩm ('xe_dien' hoặc 'du_lich').
        max_price: Giá tối đa (VNĐ). Mặc định không giới hạn.
    
    Returns:
        Danh sách sản phẩm phù hợp điều kiện.
    """
    catalog_file = os.path.join(RAW_DATA_DIR, "product_catalog.json")
    # TODO: Kiểm tra file tồn tại, đọc JSON, lọc sản phẩm
    # Gợi ý: Lọc theo p["category"] == category AND p["price_vnd"] <= max_price
    if not os.path.exists(catalog_file):
        return [{"error": "Product catalog file not found."}]

    try:
        with open(catalog_file, "r", encoding="utf-8") as file:
            products = json.load(file)
    except (OSError, json.JSONDecodeError):
        return [{"error": "Product catalog could not be read."}]

    normalized_category = category.strip().lower()
    return [
        product
        for product in products
        if str(product.get("category", "")).lower() == normalized_category
        and isinstance(product.get("price_vnd"), (int, float))
        and product["price_vnd"] <= max_price
    ]


# ---------------------------------------------------------------------------
# Tool #2: submit_support_ticket
# TODO: Hoàn thiện hàm này — tạo ticket mới và lưu vào support_tickets.json.
# ---------------------------------------------------------------------------

def submit_support_ticket(
    customer_name: str,
    issue_description: str,
    priority: str = "medium"
) -> Dict[str, Any]:
    """
    Ghi nhận yêu cầu hỗ trợ của khách hàng vào hệ thống ticket.
    
    Args:
        customer_name: Tên khách hàng.
        issue_description: Mô tả vấn đề cần hỗ trợ.
        priority: Mức độ ưu tiên ('low', 'medium', 'high'). Mặc định 'medium'.
    
    Returns:
        Thông tin ticket vừa tạo bao gồm ticket_id, status.
    """
    tickets_file = os.path.join(RAW_DATA_DIR, "support_tickets.json")
    # TODO: Load existing tickets, generate new ticket_id, append new ticket, save file
    # Gợi ý: ticket_id = f"TK-{today}-{seq:03d}" với today = datetime.now().strftime("%Y%m%d")
    existing_tickets: List[Dict[str, Any]] = []
    if os.path.exists(tickets_file):
        try:
            with open(tickets_file, "r", encoding="utf-8") as file:
                loaded_tickets = json.load(file)
            if isinstance(loaded_tickets, list):
                existing_tickets = loaded_tickets
        except (OSError, json.JSONDecodeError):
            return {"error": "Support ticket file could not be read.", "status": "error"}

    now = datetime.now(timezone(timedelta(hours=7)))
    today = now.strftime("%Y%m%d")
    ticket_id = f"TK-{today}-{len(existing_tickets) + 1:03d}"
    normalized_priority = priority.strip().lower()
    if normalized_priority not in {"low", "medium", "high"}:
        normalized_priority = "medium"

    new_ticket = {
        "ticket_id": ticket_id,
        "customer_name": customer_name.strip(),
        "issue_description": issue_description.strip(),
        "priority": normalized_priority,
        "status": "open",
        "created_at": now.isoformat(),
        "category": "general",
    }
    existing_tickets.append(new_ticket)
    try:
        with open(tickets_file, "w", encoding="utf-8") as file:
            json.dump(existing_tickets, file, indent=2, ensure_ascii=False)
    except OSError:
        return {"error": "Support ticket file could not be saved.", "status": "error"}

    return {
        "ticket_id": ticket_id,
        "customer_name": new_ticket["customer_name"],
        "priority": normalized_priority,
        "status": "open",
        "message": f"Ticket {ticket_id} đã được tạo thành công.",
    }


# ---------------------------------------------------------------------------
# TOOL_DEFINITIONS — JSON Schemas mô tả cho LLM
# TODO: Định nghĩa JSON Schema cho từng tool (name, description, parameters).
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "search_product_catalog",
        "description": "Tra cứu sản phẩm hoặc dịch vụ Vingroup theo danh mục và giá tối đa.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Danh mục cần tìm.",
                    "enum": ["xe_dien", "du_lich"],
                },
                "max_price": {
                    "type": "integer",
                    "description": "Giá tối đa tính bằng VNĐ.",
                    "minimum": 0,
                },
            },
            "required": ["category"],
            "additionalProperties": False,
        },
    },
    {
        "name": "submit_support_ticket",
        "description": "Tạo yêu cầu hỗ trợ cho khách hàng trong hệ sinh thái Vingroup.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "description": "Họ tên khách hàng."},
                "issue_description": {"type": "string", "description": "Mô tả vấn đề cần hỗ trợ."},
                "priority": {
                    "type": "string",
                    "description": "Mức độ ưu tiên.",
                    "enum": ["low", "medium", "high"],
                    "default": "medium",
                },
            },
            "required": ["customer_name", "issue_description"],
            "additionalProperties": False,
        },
    },
]


# ---------------------------------------------------------------------------
# TOOL_MAP — Ánh xạ tên tool → hàm thực thi
# ---------------------------------------------------------------------------

TOOL_MAP = {
    "search_product_catalog": search_product_catalog,
    "submit_support_ticket": submit_support_ticket
}
