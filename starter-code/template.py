"""
Lab #4: System Prompt Engineering & Tool Calling Engine
Học viên hoàn thiện các mục TODO để hoàn thành bài lab.

Kiến trúc:
  - ChatbotBaseline: LLM thuần, không dùng tool → quan sát hallucination.
  - ToolCallingAgent: Agent dùng System Prompt + 2 Tool Schemas.
"""

import json
import re
import unicodedata
from typing import Dict, Any, List
from tools import TOOL_DEFINITIONS, TOOL_MAP, search_product_catalog, submit_support_ticket

# ═══════════════════════════════════════════════════════════════════════════
# TODO 1: Thiết kế SYSTEM PROMPT cấp sản xuất
# Yêu cầu: Phải chứa Persona, Core Rules, Operational Boundaries, Output Contract.
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """
Bạn là VinAssistant, trợ lý AI của hệ sinh thái Vingroup.

## PERSONA
- Vai trò: tư vấn sản phẩm, dịch vụ VinFast/Vinpearl và tiếp nhận yêu cầu hỗ trợ.
- Giọng điệu: chuyên nghiệp, thân thiện, rõ ràng và chính xác.

## AVAILABLE TOOLS
- search_product_catalog: tra cứu danh mục xe điện hoặc du lịch theo mức giá tối đa.
- submit_support_ticket: tạo và lưu yêu cầu hỗ trợ của khách hàng.

## CORE RULES
1. Không bịa giá, thông số, tình trạng sản phẩm hoặc mã ticket.
2. Phải gọi search_product_catalog khi người dùng yêu cầu tìm sản phẩm theo danh mục/giá.
3. Phải gọi submit_support_ticket khi người dùng muốn ghi nhận sự cố hay yêu cầu hỗ trợ.
4. Có thể gọi cả hai tool nếu câu hỏi chứa cả hai nhu cầu; chỉ dùng observation để trả lời.
5. Nếu thiếu dữ liệu quan trọng, nói rõ điều còn thiếu; nếu không có kết quả, thông báo lịch sự.

## OPERATIONAL BOUNDARIES
- Chỉ hỗ trợ chủ đề thuộc hệ sinh thái Vingroup.
- Không tự nhận đã thực hiện hành động ngoài các tool được cung cấp.

## OUTPUT CONTRACT
- Nội bộ tuân theo Thought -> Action -> Observation; không tiết lộ suy luận riêng tư.
- Chỉ gửi Final Answer súc tích bằng tiếng Việt, kèm dữ liệu thực từ tool.
"""


# ═══════════════════════════════════════════════════════════════════════════
# CLASS: ChatbotBaseline
# ═══════════════════════════════════════════════════════════════════════════

class ChatbotBaseline:
    """Baseline LLM Chatbot — Không sử dụng Tool Calling hay ReAct Loop."""

    def query(self, user_input: str) -> Dict[str, Any]:
        # TODO 2: Trả về câu trả lời tĩnh (mock) hoặc gọi Gemini API 1 lượt (không dùng tool)
        # Mục tiêu: Quan sát hiện tượng bịa thông tin (hallucination)
        return {
            "answer": f"[Chatbot Baseline] Trả lời cho: {user_input}",
            "tool_calls": [],
            "status": "success",
            "mode": "mock_baseline"
        }


# ═══════════════════════════════════════════════════════════════════════════
# CLASS: ToolCallingAgent
# ═══════════════════════════════════════════════════════════════════════════

class ToolCallingAgent:
    """Agent với System Prompt Engineering & Tool Calling."""

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self.trace: List[Dict[str, Any]] = []

    def run(self, user_input: str) -> Dict[str, Any]:
        """Điểm vào chính — chạy Agent Loop."""
        self.trace = []

        # TODO 3: Phân tích intent từ user_input
        #   - Xác định cần gọi tool nào (catalog? ticket? cả hai? FAQ?)
        #   - Gợi ý: Dùng keyword matching hoặc regex

        # TODO 4: Xây dựng Agent Loop (while iteration <= self.max_iterations)
        #   - Iteration 1: Gọi tool #1 nếu cần (search_product_catalog)
        #   - Iteration 2: Gọi tool #2 nếu cần (submit_support_ticket)
        #   - Iteration 3+: Tổng hợp Final Answer từ trace
        #   - Lưu mỗi bước vào self.trace

        normalized = self._normalize(user_input)
        intents = self._detect_intents(normalized)
        self.trace.append({"step": "intent_detection", "intents": intents})

        actions: List[tuple[str, Dict[str, Any]]] = []
        if intents["needs_catalog"]:
            actions.append(("search_product_catalog", self._catalog_arguments(normalized)))
        if intents["needs_ticket"]:
            actions.append(("submit_support_ticket", self._ticket_arguments(user_input, normalized)))

        if not actions:
            if self.max_iterations < 1:
                return self._max_iterations_result(0)
            answer = self._direct_answer(normalized)
            self.trace.append({"step": "final_answer", "answer": answer})
            return {"answer": answer, "trace": self.trace, "iterations": 1, "status": "completed"}

        observations: List[tuple[str, Any]] = []
        iteration = 0
        for tool_name, arguments in actions:
            if iteration >= self.max_iterations:
                return self._max_iterations_result(iteration)
            iteration += 1
            observation = TOOL_MAP[tool_name](**arguments)
            observations.append((tool_name, observation))
            self.trace.append({
                "step": iteration,
                "action": tool_name,
                "arguments": arguments,
                "observation": observation,
            })

        answer = self._format_answer(observations)
        self.trace.append({"step": "final_answer", "answer": answer})
        return {
            "answer": answer,
            "trace": self.trace,
            "iterations": iteration,
            "status": "completed",
        }

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFD", text.lower())
        return "".join(char for char in text if unicodedata.category(char) != "Mn").replace("đ", "d")

    @staticmethod
    def _detect_intents(text: str) -> Dict[str, bool]:
        catalog_terms = (
            "gia duoi", "gia toi da", "bao nhieu", "xem xe", "tim xe",
            "resort", "vinpearl", "du lich",
        )
        ticket_terms = (
            "bi loi", "su co", "ho tro", "khieu nai", "phan hoi",
            "ghi nhan", "xu ly gap", "nghiem trong",
        )
        is_faq = "bao hanh" in text and not any(term in text for term in ticket_terms)
        return {
            "needs_catalog": not is_faq and any(term in text for term in catalog_terms),
            "needs_ticket": any(term in text for term in ticket_terms),
            "is_faq": is_faq,
        }

    @staticmethod
    def _catalog_arguments(text: str) -> Dict[str, Any]:
        category = "du_lich" if any(
            term in text for term in ("du lich", "resort", "vinpearl", "phong")
        ) else "xe_dien"
        max_price = 999999999999
        price_match = re.search(r"(?:duoi|toi da|khoang)\s+([\d.,]+)\s*(trieu|ty|ti)?", text)
        if price_match:
            number = float(price_match.group(1).replace(".", "").replace(",", "."))
            unit = price_match.group(2)
            multiplier = 1_000_000 if unit == "trieu" else 1_000_000_000 if unit in {"ty", "ti"} else 1
            max_price = int(number * multiplier)
        return {"category": category, "max_price": max_price}

    @staticmethod
    def _ticket_arguments(original: str, normalized: str) -> Dict[str, Any]:
        name_match = re.search(
            r"(?:tôi tên|tên tôi là|tên là)\s+([^,.]+)", original, flags=re.IGNORECASE
        )
        customer_name = name_match.group(1).strip() if name_match else "Khách hàng"
        issue_match = re.search(
            r"((?:xe|phòng|dịch vụ)[^.]*?(?:bị|lỗi)[^.]*?)(?:\.|,\s*(?:mức độ|cần)|$)",
            original,
            flags=re.IGNORECASE,
        )
        issue_description = issue_match.group(1).strip() if issue_match else original.strip()
        high_terms = ("gap", "nghiem trong", "khan cap", "high")
        low_terms = ("khong gap", "muc do thap", "low")
        priority = (
            "high" if any(term in normalized for term in high_terms)
            else "low" if any(term in normalized for term in low_terms)
            else "medium"
        )
        return {
            "customer_name": customer_name,
            "issue_description": issue_description,
            "priority": priority,
        }

    @staticmethod
    def _direct_answer(text: str) -> str:
        if "bao hanh" in text and "pin" in text:
            return "Chính sách bảo hành pin xe điện VinFast trong dữ liệu hiện có là 10 năm. Điều kiện cụ thể có thể tùy mẫu xe."
        if not any(brand in text for brand in ("vinfast", "vinpearl", "vingroup")):
            return "Xin lỗi, tôi chỉ hỗ trợ thông tin và dịch vụ thuộc hệ sinh thái Vingroup."
        return "Bạn vui lòng nêu rõ sản phẩm, dịch vụ hoặc vấn đề Vingroup cần hỗ trợ."

    @staticmethod
    def _format_answer(observations: List[tuple[str, Any]]) -> str:
        parts: List[str] = []
        for tool_name, observation in observations:
            if tool_name == "search_product_catalog":
                if not observation or (isinstance(observation, list) and observation[0].get("error")):
                    parts.append("Rất tiếc, không tìm thấy sản phẩm phù hợp.")
                else:
                    products = "; ".join(
                        f"{item['name']} ({item['price_vnd']:,} VNĐ)" for item in observation
                    )
                    parts.append(f"Các lựa chọn phù hợp: {products}.")
            elif observation.get("status") == "open":
                parts.append(
                    f"Đã tạo ticket {observation['ticket_id']} cho {observation['customer_name']} "
                    f"với mức ưu tiên {observation['priority']}."
                )
            else:
                parts.append("Không thể tạo ticket hỗ trợ lúc này.")
        return " ".join(parts)

    def _max_iterations_result(self, iterations: int) -> Dict[str, Any]:
        answer = "Lỗi: Vượt quá số bước tối đa."
        self.trace.append({"step": "guard", "reason": "max_iterations_reached"})
        return {
            "answer": answer,
            "trace": self.trace,
            "iterations": iterations,
            "status": "max_iterations_reached",
        }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN — Chạy thử nhanh
# ═══════════════════════════════════════════════════════════════════════════

def main():
    user_query = "Tôi muốn xem xe điện VinFast giá dưới 600 triệu."

    print("=== RUNNING CHATBOT BASELINE ===")
    chatbot = ChatbotBaseline()
    print(chatbot.query(user_query))

    print("\n=== RUNNING TOOL CALLING AGENT ===")
    agent = ToolCallingAgent(max_iterations=5)
    result = agent.run(user_query)
    print("Result:", result["answer"])
    print("Trace Log:", json.dumps(agent.trace, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
