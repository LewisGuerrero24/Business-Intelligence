from __future__ import annotations

from etl_service.etl.preclean.header_normalizer import compact_field_name


class BusinessVocabulary:
    def __init__(self) -> None:
        self.enum_terms = {
            "customer_type": {
                "individual": "INDIVIDUAL",
                "persona": "INDIVIDUAL",
                "persona_natural": "INDIVIDUAL",
                "natural": "INDIVIDUAL",
                "business": "BUSINESS",
                "empresa": "BUSINESS",
                "compania": "BUSINESS",
                "juridica": "BUSINESS",
                "persona_juridica": "BUSINESS",
            },
            "unit_of_measure": {
                "unit": "UNIT",
                "unidad": "UNIT",
                "unidades": "UNIT",
                "und": "UNIT",
                "ud": "UNIT",
                "kg": "KG",
                "kilo": "KG",
                "kilos": "KG",
                "kilogramo": "KG",
                "kilogramos": "KG",
                "l": "L",
                "lt": "L",
                "litro": "L",
                "litros": "L",
                "m": "M",
                "metro": "M",
                "metros": "M",
                "box": "BOX",
                "caja": "BOX",
                "cajas": "BOX",
                "pack": "PACK",
                "paquete": "PACK",
                "paquetes": "PACK",
            },
            "payment_method": {
                "cash": "CASH",
                "efectivo": "CASH",
                "contado": "CASH",
                "dinero": "CASH",
                "card": "CARD",
                "tarjeta": "CARD",
                "tarjeta_credito": "CARD",
                "tarjeta_debito": "CARD",
                "transfer": "TRANSFER",
                "transferencia": "TRANSFER",
                "transferencia_bancaria": "TRANSFER",
                "banco": "TRANSFER",
                "consignacion": "TRANSFER",
                "credit": "CREDIT",
                "credito": "CREDIT",
                "a_credito": "CREDIT",
            },
            "payment_status": {
                "pending": "PENDING",
                "pendiente": "PENDING",
                "por_pagar": "PENDING",
                "sin_pagar": "PENDING",
                "partial": "PARTIAL",
                "parcial": "PARTIAL",
                "abono": "PARTIAL",
                "abonado": "PARTIAL",
                "paid": "PAID",
                "pagado": "PAID",
                "pago": "PAID",
                "cancelado": "PAID",
            },
            "status": {
                "draft": "DRAFT",
                "borrador": "DRAFT",
                "pendiente": "DRAFT",
                "confirmed": "CONFIRMED",
                "confirmado": "CONFIRMED",
                "aprobado": "CONFIRMED",
                "received": "RECEIVED",
                "recibido": "RECEIVED",
                "entregado": "RECEIVED",
                "cancelled": "CANCELLED",
                "canceled": "CANCELLED",
                "cancelado": "CANCELLED",
                "anulado": "CANCELLED",
            },
            "movement_type": {
                "in": "IN",
                "entrada": "IN",
                "ingreso": "IN",
                "compra": "IN",
                "out": "OUT",
                "salida": "OUT",
                "egreso": "OUT",
                "venta": "OUT",
                "adjustment": "ABJUSTMENT",
                "ajuste": "ABJUSTMENT",
                "abjustment": "ABJUSTMENT",
                "traslado": "T",
                "transferencia": "T",
                "t": "T",
            },
            "reference_type": {
                "sale": "SALE",
                "venta": "SALE",
                "factura": "SALE",
                "purchase": "PURCHASE",
                "compra": "PURCHASE",
                "orden_compra": "PURCHASE",
                "adjustment": "ABJUSTMENT",
                "ajuste": "ABJUSTMENT",
                "abjustment": "ABJUSTMENT",
            },
        }

    def enum_value(self, field_name: str, value: object, allowed_values: tuple[str, ...]) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        if not text:
            return None

        normalized = compact_field_name(text)
        direct = text.upper()
        if direct in allowed_values:
            return direct

        field_terms = self.enum_terms.get(field_name, {})
        resolved = field_terms.get(normalized)
        if resolved and resolved in allowed_values:
            return resolved
        return None
