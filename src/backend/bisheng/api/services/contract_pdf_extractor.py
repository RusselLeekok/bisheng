import argparse
import base64
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import fitz
import requests
from json_repair import repair_json
from openai import OpenAI


CONTRACT_FIELD_MAP = {
    "合同编号": "contractNumber",
    "合同名称": "contractFullName",
    "甲方名称": "lessorName",
    "甲方住所/联系地址": "lessorAddress",
    "甲方授权代表/联系人": "lessorContactPerson",
    "甲方联系电话": "lessorContactPhone",
    "乙方名称": "customer",
    "乙方证件号码": "customerIdNumber",
    "乙方联系地址": "customerAddress",
    "乙方联系电话": "customerPhone",
    "租赁标的类型": "contractType",
    "详细地址": "leaseUnit",
    "建筑面积": "buildingArea",
    "结构": "buildingStructure",
    "用途": "usage",
    "租赁开始日期": "startDate",
    "租赁结束日期": "expireDate",
    "租赁期限": "leaseTerm",
    "交付日期": "deliveryDate",
    "月租金（小写）": "amountPerMonth",
    "月租金（大写）": "monthlyRentCapital",
    "租金支付方式（月/季/年）": "rentPaymentMethod",
    "签订合同甲方授权代表人": "lessorSignatory",
    "签订合同甲方授权代表电话": "lessorSignatoryPhone",
    "签订合同甲方授权代表签订日期": "lessorSignDate",
    "签订合同的乙方授权代表人": "customerSignatory",
    "签订合同乙方授权代表电话": "customerSignatoryPhone",
    "签订合同乙方授权代表签订日期": "customerSignDate",
}

SIGNATURE_FIELDS = {
    "lessorSignatory",
    "lessorSignatoryPhone",
    "lessorSignDate",
    "customerSignatory",
    "customerSignatoryPhone",
    "customerSignDate",
}


@dataclass
class PageExtraction:
    page_number: int
    ocr_text: str
    page_text: str
    fields: dict[str, str]


class ContractPDFExtractor:
    """Extract residential lease contract fields from PDF pages with OCR and local VLM."""

    def __init__(
        self,
        vlm_base_url: str,
        vlm_model: str,
        ocr_url: str,
        vlm_api_key: str = "EMPTY",
        dpi: int = 200,
        timeout: int = 120,
    ) -> None:
        self.vlm_model = vlm_model
        self.ocr_url = ocr_url
        self.dpi = dpi
        self.timeout = timeout
        self.vlm_client = OpenAI(api_key=vlm_api_key, base_url=vlm_base_url)
        self.http = requests.Session()

    def extract(self, pdf_path: str | Path) -> dict[str, str]:
        page_results = self.extract_pages(pdf_path)
        merged: dict[str, str] = {}
        for page_result in page_results:
            merged = self._merge_fields(merged, page_result.fields)
        return merged

    def extract_pages(self, pdf_path: str | Path) -> list[PageExtraction]:
        pdf_path = Path(pdf_path)
        if not pdf_path.is_file():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        page_results: list[PageExtraction] = []
        with fitz.open(pdf_path) as doc:
            for page_index, page in enumerate(doc):
                image_bytes = self._render_page(page)
                image_b64 = base64.b64encode(image_bytes).decode("ascii")
                page_text = self._normalize_space(page.get_text("text"))
                ocr_text = self._call_ocr(image_b64)
                fields = self._extract_page_fields(
                    page_number=page_index + 1,
                    total_pages=doc.page_count,
                    image_b64=image_b64,
                    page_text=page_text,
                    ocr_text=ocr_text,
                )
                page_results.append(
                    PageExtraction(
                        page_number=page_index + 1,
                        ocr_text=ocr_text,
                        page_text=page_text,
                        fields=fields,
                    )
                )
        return page_results

    def _render_page(self, page: fitz.Page) -> bytes:
        pix = page.get_pixmap(dpi=self.dpi, alpha=False)
        return pix.tobytes("png")

    def _call_ocr(self, image_b64: str) -> str:
        payload = {
            "data": [image_b64],
            "param": {
                "sort_filter_boxes": True,
                "enable_huarong_box_adjust": True,
                "support_long_image_segment": True,
                "rotateupright": True,
                "det": "general_text_det_mrcnn_v1.0",
                "recog": "transformer-v2.8-gamma-faster",
            },
        }
        response = self.http.post(self.ocr_url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return self._extract_ocr_text(response.json())

    def _extract_page_fields(
        self,
        page_number: int,
        total_pages: int,
        image_b64: str,
        page_text: str,
        ocr_text: str,
    ) -> dict[str, str]:
        prompt = self._build_page_prompt(page_number, total_pages, page_text, ocr_text)
        response = self.vlm_client.chat.completions.create(
            model=self.vlm_model,
            temperature=0,
            max_tokens=2048,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是合同信息抽取助手。只根据当前页图片、OCR 文本和 PDF 文本抽取字段，"
                        "输出严格 JSON 对象。不要解释、不要 Markdown。"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._coerce_fields(self._load_json_object(content))

    def _build_page_prompt(
        self,
        page_number: int,
        total_pages: int,
        page_text: str,
        ocr_text: str,
    ) -> str:
        field_lines = "\n".join(
            f"- {label} -> `{key}`" for label, key in CONTRACT_FIELD_MAP.items()
        )
        return f"""
当前处理第 {page_number}/{total_pages} 页。

任务：
1. 结合当前页图片、OCR 文本、PDF 可复制文本抽取合同字段。
2. 只抽取当前页明确出现的字段；当前页没出现的字段不要臆造。
3. 所有值必须是字符串，保持合同原文格式，不要改写日期、金额、电话、证件号码。
4. 同一字段在当前页出现多次时，选最完整、最靠近字段标签的原文值。
5. 签订合同相关字段优先来自签章/落款区域。
6. 只返回 JSON 对象，key 必须来自下面列表。

字段列表：
{field_lines}

OCR 文本：
{ocr_text or "（OCR 未识别到文本）"}

PDF 可复制文本：
{page_text or "（PDF 无可复制文本）"}
""".strip()

    def _merge_fields(
        self,
        merged: dict[str, str],
        incoming: dict[str, str],
    ) -> dict[str, str]:
        for key, value in incoming.items():
            value = self._normalize_space(value)
            if not value:
                continue
            old_value = merged.get(key, "")
            if not old_value:
                merged[key] = value
                continue
            if key in SIGNATURE_FIELDS:
                # 签署信息通常在后置签章页，以后出现的明确值为准。
                merged[key] = value
                continue
            if self._is_better_value(old_value, value):
                merged[key] = value
        return merged

    @staticmethod
    def _is_better_value(old_value: str, new_value: str) -> bool:
        if old_value == new_value:
            return False
        if old_value in new_value:
            return True
        if new_value in old_value:
            return False
        return len(new_value) > len(old_value) and len(new_value) <= 200

    def _coerce_fields(self, data: dict[str, Any]) -> dict[str, str]:
        allowed_keys = set(CONTRACT_FIELD_MAP.values())
        result: dict[str, str] = {}
        for key, value in data.items():
            if key not in allowed_keys:
                continue
            if value is None:
                continue
            if isinstance(value, (list, tuple)):
                value = "；".join(self._normalize_space(str(item)) for item in value if item)
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            else:
                value = str(value)
            value = self._normalize_space(value)
            if value:
                result[key] = value
        return result

    @staticmethod
    def _load_json_object(content: str) -> dict[str, Any]:
        content = content.strip()
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if match:
            content = match.group(0)
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = json.loads(repair_json(content))
        if not isinstance(data, dict):
            raise ValueError(f"模型返回不是 JSON 对象: {content[:200]}")
        return data

    @classmethod
    def _extract_ocr_text(cls, data: Any) -> str:
        texts = list(cls._walk_ocr_text(data))
        deduped: list[str] = []
        seen = set()
        for text in texts:
            text = cls._normalize_space(text)
            if not text or text in seen:
                continue
            seen.add(text)
            deduped.append(text)
        return "\n".join(deduped)

    @classmethod
    def _walk_ocr_text(cls, node: Any) -> Iterable[str]:
        text_keys = {
            "text",
            "words",
            "word",
            "content",
            "transcription",
            "rec_text",
            "recognized_text",
        }
        if isinstance(node, dict):
            for key, value in node.items():
                if key in text_keys and isinstance(value, str):
                    yield value
                else:
                    yield from cls._walk_ocr_text(value)
        elif isinstance(node, list):
            for item in node:
                yield from cls._walk_ocr_text(item)

    @staticmethod
    def _normalize_space(value: str) -> str:
        return re.sub(r"[ \t\r\f\v]+", " ", value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="逐页 OCR + 本地多模态大模型抽取 PDF 合同信息")
    parser.add_argument("pdf", help="合同 PDF 路径")
    parser.add_argument("--out", help="输出 JSON 文件路径；不传则打印到 stdout")
    parser.add_argument(
        "--vlm-base-url",
        default=os.getenv("LOCAL_VLM_BASE_URL", "http://127.0.0.1:8000/v1"),
        help="本地多模态模型 OpenAI 兼容接口地址",
    )
    parser.add_argument(
        "--vlm-model",
        default=os.getenv("LOCAL_VLM_MODEL", "qwen2.5-vl"),
        help="本地多模态模型名称",
    )
    parser.add_argument(
        "--vlm-api-key",
        default=os.getenv("LOCAL_VLM_API_KEY", "EMPTY"),
        help="本地 OpenAI 兼容服务 API Key；无鉴权可填 EMPTY",
    )
    parser.add_argument(
        "--ocr-url",
        default=os.getenv("LOCAL_OCR_URL", "http://127.0.0.1:36001/v2/idp/idp_app/infer"),
        help="本地 OCR 服务地址",
    )
    parser.add_argument("--dpi", type=int, default=200, help="PDF 页面渲染 DPI")
    parser.add_argument("--timeout", type=int, default=120, help="OCR 请求超时时间，单位秒")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    extractor = ContractPDFExtractor(
        vlm_base_url=args.vlm_base_url,
        vlm_model=args.vlm_model,
        vlm_api_key=args.vlm_api_key,
        ocr_url=args.ocr_url,
        dpi=args.dpi,
        timeout=args.timeout,
    )
    result = extractor.extract(args.pdf)
    json_text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(json_text, encoding="utf-8")
    else:
        print(json_text)


if __name__ == "__main__":
    main()
