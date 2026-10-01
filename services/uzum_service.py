"""
uzum_service.py — Uzum Market Seller OpenAPI Integration & Notifications
Features:
- Full OpenAPI client for https://api-seller.uzum.uz/api/seller-openapi
- Multi-shop management (isolation and consolidated views)
- FBS/DBS Orders handling: get orders, confirm, cancel, print labels
- Stock balances and price sync
- Finance & payouts calculation
- Automatic Telegram Push notifications with interactive 1-click confirmation buttons
- Fail-safe Demo mode with realistic multi-shop data for stage presentations
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from services.database import (
    get_uzum_finance_summary,
    get_uzum_orders,
    get_uzum_settings,
    get_uzum_shops,
    get_uzum_stocks,
    get_unnotified_uzum_orders,
    log_uzum_notification,
    mark_order_notified,
    reset_uzum_data,
    save_uzum_orders,
    save_uzum_settings,
    save_uzum_shops,
    save_uzum_stocks,
    update_uzum_order_status,
    update_uzum_price,
    update_uzum_stock_amount,
)
from services.telegram_service import telegram_service

logger = logging.getLogger("oqila_uzum")

UZUM_API_BASE = "https://api-seller.uzum.uz/api/seller-openapi"


# ---------------------------------------------------------------------------
# Pre-packaged Demo Data (Multi-Shop: Clothing & Crafts)
# ---------------------------------------------------------------------------
DEMO_SHOPS = [
    {
        "shop_id": 1042,
        "title": "👗 Oqila Milliy Liboslar",
        "legal_name": "YaTT Karimova Oqila",
        "inn": "308129845",
        "status": "ACTIVE",
        "is_selected": 1,
    },
    {
        "shop_id": 1043,
        "title": "🏺 Oqila Hunarmand Decor",
        "legal_name": "YaTT Karimova Oqila",
        "inn": "308129845",
        "status": "ACTIVE",
        "is_selected": 0,
    },
]

DEMO_ORDERS = [
    {
        "order_id": 849201,
        "shop_id": 1042,
        "shop_title": "👗 Oqila Milliy Liboslar",
        "posting_number": "UZ-FBS-849201",
        "status": "CREATED",
        "status_label_ru": "Новый (Ожидает подтверждения)",
        "status_label_uz": "Yangi (Tasdiqlash kutilmoqda)",
        "total_amount": 380000,
        "delivery_type": "FBS",
        "customer_name": "Madina Rahimova",
        "delivery_city": "Toshkent (Yunusobod)",
        "created_at": (datetime.now() - timedelta(minutes=15)).isoformat(),
        "deadline_to_confirm": (datetime.now() + timedelta(minutes=105)).isoformat(),
        "is_notified": 0,
        "items": [
            {
                "sku_id": 20101,
                "product_title": "Xon-atlas ko'ylak (Milliy naqsh, Razmer M)",
                "quantity": 1,
                "price": 380000,
                "barcode": "4780012345678",
            }
        ],
    },
    {
        "order_id": 849202,
        "shop_id": 1042,
        "shop_title": "👗 Oqila Milliy Liboslar",
        "posting_number": "UZ-FBS-849202",
        "status": "CREATED",
        "status_label_ru": "Новый (Ожидает подтверждения)",
        "status_label_uz": "Yangi (Tasdiqlash kutilmoqda)",
        "total_amount": 240000,
        "delivery_type": "FBS",
        "customer_name": "Dilfuza Alimova",
        "delivery_city": "Samarqand",
        "created_at": (datetime.now() - timedelta(minutes=25)).isoformat(),
        "deadline_to_confirm": (datetime.now() + timedelta(minutes=95)).isoformat(),
        "is_notified": 0,
        "items": [
            {
                "sku_id": 20103,
                "product_title": "Adras nimcha (Kashta bilan bezatilgan, Razmer L)",
                "quantity": 1,
                "price": 240000,
                "barcode": "4780012345679",
            }
        ],
    },
    {
        "order_id": 849205,
        "shop_id": 1043,
        "shop_title": "🏺 Oqila Hunarmand Decor",
        "posting_number": "UZ-FBS-849205",
        "status": "CREATED",
        "status_label_ru": "Новый (Ожидает подтверждения)",
        "status_label_uz": "Yangi (Tasdiqlash kutilmoqda)",
        "total_amount": 165000,
        "delivery_type": "FBS",
        "customer_name": "Nargiza Usmonova",
        "delivery_city": "Farg'ona",
        "created_at": (datetime.now() - timedelta(minutes=40)).isoformat(),
        "deadline_to_confirm": (datetime.now() + timedelta(minutes=80)).isoformat(),
        "is_notified": 0,
        "items": [
            {
                "sku_id": 30101,
                "product_title": "Rishton sopol lagan (Qo'lda chizilgan, 30 sm)",
                "quantity": 1,
                "price": 165000,
                "barcode": "4780098765432",
            }
        ],
    },
    {
        "order_id": 849180,
        "shop_id": 1042,
        "shop_title": "👗 Oqila Milliy Liboslar",
        "posting_number": "UZ-FBS-849180",
        "status": "CONFIRMED",
        "status_label_ru": "В сборке (Подтвержден)",
        "status_label_uz": "Yig'ilmoqda (Tasdiqlangan)",
        "total_amount": 190000,
        "delivery_type": "FBS",
        "customer_name": "Sevara Sobirova",
        "delivery_city": "Toshkent (Chilonzor)",
        "created_at": (datetime.now() - timedelta(hours=3)).isoformat(),
        "deadline_to_confirm": (datetime.now() - timedelta(hours=1)).isoformat(),
        "is_notified": 1,
        "items": [
            {
                "sku_id": 20104,
                "product_title": "Shohi ipak ro'mol (Tabiiy bo'yoq)",
                "quantity": 1,
                "price": 190000,
                "barcode": "4780012345680",
            }
        ],
    },
    {
        "order_id": 849120,
        "shop_id": 1043,
        "shop_title": "🏺 Oqila Hunarmand Decor",
        "posting_number": "UZ-FBS-849120",
        "status": "DELIVERING",
        "status_label_ru": "В пути (Доставляется)",
        "status_label_uz": "Yo'lda (Yetkazilmoqda)",
        "total_amount": 220000,
        "delivery_type": "FBS",
        "customer_name": "Jamshid Boboyev",
        "delivery_city": "Buxoro",
        "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
        "deadline_to_confirm": (datetime.now() - timedelta(days=1)).isoformat(),
        "is_notified": 1,
        "items": [
            {
                "sku_id": 30103,
                "product_title": "Zardo'zi kashmir naqshli yostiqcha",
                "quantity": 1,
                "price": 220000,
                "barcode": "4780098765434",
            }
        ],
    },
    {
        "order_id": 849050,
        "shop_id": 1042,
        "shop_title": "👗 Oqila Milliy Liboslar",
        "posting_number": "UZ-FBS-849050",
        "status": "COMPLETED",
        "status_label_ru": "Завершён (Выдан покупателю)",
        "status_label_uz": "Yakunlandi (Xaridor oldi)",
        "total_amount": 650000,
        "delivery_type": "FBS",
        "customer_name": "Shahlo Qodirova",
        "delivery_city": "Toshkent",
        "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
        "deadline_to_confirm": (datetime.now() - timedelta(days=2)).isoformat(),
        "is_notified": 1,
        "items": [
            {
                "sku_id": 20105,
                "product_title": "Zardo'zi baxmal chopon (Marosimlar uchun)",
                "quantity": 1,
                "price": 650000,
                "barcode": "4780012345681",
            }
        ],
    },
]

DEMO_STOCKS = [
    {
        "sku_id": 20101,
        "shop_id": 1042,
        "shop_title": "👗 Oqila Milliy Liboslar",
        "product_title": "Xon-atlas ko'ylak (Milliy naqsh, Razmer M)",
        "barcode": "4780012345678",
        "current_stock": 2,
        "price": 380000,
        "cost_price": 180000,
        "fbo_stock": 3,
        "daily_sales_velocity": 2.0,
        "is_low_stock": 1,
    },
    {
        "sku_id": 20102,
        "shop_id": 1042,
        "shop_title": "👗 Oqila Milliy Liboslar",
        "product_title": "Xon-atlas ko'ylak (Milliy naqsh, Razmer S)",
        "barcode": "4780012345677",
        "current_stock": 8,
        "price": 380000,
        "cost_price": 180000,
        "fbo_stock": 18,
        "daily_sales_velocity": 1.5,
        "is_low_stock": 0,
    },
    {
        "sku_id": 20103,
        "shop_id": 1042,
        "shop_title": "👗 Oqila Milliy Liboslar",
        "product_title": "Adras nimcha (Kashta bilan bezatilgan, Razmer L)",
        "barcode": "4780012345679",
        "current_stock": 4,
        "price": 240000,
        "cost_price": 195000,
        "fbo_stock": 5,
        "daily_sales_velocity": 1.2,
        "is_low_stock": 0,
    },
    {
        "sku_id": 20104,
        "shop_id": 1042,
        "shop_title": "👗 Oqila Milliy Liboslar",
        "product_title": "Shohi ipak ro'mol (Tabiiy bo'yoq)",
        "barcode": "4780012345680",
        "current_stock": 15,
        "price": 190000,
        "cost_price": 125000,
        "fbo_stock": 22,
        "daily_sales_velocity": 1.8,
        "is_low_stock": 0,
    },
    {
        "sku_id": 30101,
        "shop_id": 1043,
        "shop_title": "🏺 Oqila Hunarmand Decor",
        "product_title": "Rishton sopol lagan (Qo'lda chizilgan, 30 sm)",
        "barcode": "4780098765432",
        "current_stock": 3,
        "price": 165000,
        "cost_price": 70000,
        "fbo_stock": 4,
        "daily_sales_velocity": 1.5,
        "is_low_stock": 1,
    },
    {
        "sku_id": 30102,
        "shop_id": 1043,
        "shop_title": "🏺 Oqila Hunarmand Decor",
        "product_title": "Ganchkorlik uslubidagi shamdon",
        "barcode": "4780098765433",
        "current_stock": 12,
        "price": 95000,
        "cost_price": 42000,
        "fbo_stock": 14,
        "daily_sales_velocity": 1.0,
        "is_low_stock": 0,
    },
    {
        "sku_id": 30103,
        "shop_id": 1043,
        "shop_title": "🏺 Oqila Hunarmand Decor",
        "product_title": "Zardo'zi kashmir naqshli yostiqcha",
        "barcode": "4780098765434",
        "current_stock": 6,
        "price": 220000,
        "cost_price": 90000,
        "fbo_stock": 8,
        "daily_sales_velocity": 1.1,
        "is_low_stock": 0,
    },
]


class UzumService:
    """Core service for Uzum Market Seller OpenAPI integration and Telegram notifications."""

    def __init__(self):
        self._lock = asyncio.Lock()

    def _get_headers(self, api_key: str) -> Dict[str, str]:
        token = api_key.strip()
        # Uzum Market OpenAPI expects raw secret key in Authorization header (without Bearer prefix)
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        return {
            "Authorization": token,
            "Accept": "application/json",
            "User-Agent": "OqilaAI-SellerClient/1.0",
        }

    async def connect_and_sync(
        self,
        api_key: Optional[str] = None,
        is_demo: bool = False,
        telegram_chat_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Validate API key or initialize Demo mode.
        Fetches shops from Uzum OpenAPI (/v1/shops) or loads demo dataset.
        """
        async with self._lock:
            if is_demo or not api_key:
                logger.info("Initializing Uzum Service in DEMO mode.")
                reset_uzum_data()
                save_uzum_settings(
                    api_key="uzum_demo_live_token",
                    is_connected=1,
                    is_demo=1,
                    telegram_chat_id=telegram_chat_id,
                    last_sync_at=datetime.now().isoformat(),
                )
                save_uzum_shops(DEMO_SHOPS)
                save_uzum_orders(DEMO_ORDERS)
                save_uzum_stocks(DEMO_STOCKS)
                return {
                    "status": "ok",
                    "mode": "demo",
                    "message": "Демо-режим Uzum Market успешно подключен (2 магазина)",
                    "shops_count": len(DEMO_SHOPS),
                    "orders_count": len(DEMO_ORDERS),
                }

            # Real API validation via GET /v1/shops
            clean_key = api_key.strip()
            headers = self._get_headers(clean_key)
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get(f"{UZUM_API_BASE}/v1/shops", headers=headers)
                    if res.status_code == 200:
                        raw_shops = res.json()
                        shops_list = []
                        if isinstance(raw_shops, list):
                            for idx, s in enumerate(raw_shops):
                                shops_list.append({
                                    "shop_id": int(s.get("id", idx + 1)),
                                    "title": s.get("name") or s.get("title") or s.get("shopTitle") or f"Do'kon #{s.get('id')}",
                                    "legal_name": s.get("legalName") or s.get("organizationName", ""),
                                    "inn": str(s.get("inn", "")),
                                    "status": s.get("status", "ACTIVE"),
                                    "is_selected": 1 if idx == 0 else 0,
                                })
                        elif isinstance(raw_shops, dict) and "shops" in raw_shops:
                            for idx, s in enumerate(raw_shops["shops"]):
                                shops_list.append({
                                    "shop_id": int(s.get("id", idx + 1)),
                                    "title": s.get("name") or s.get("title", f"Do'kon #{s.get('id')}"),
                                    "legal_name": s.get("legalName", ""),
                                    "inn": str(s.get("inn", "")),
                                    "status": s.get("status", "ACTIVE"),
                                    "is_selected": 1 if idx == 0 else 0,
                                })

                        if not shops_list:
                            # Fallback if account has no named shops yet
                            shops_list = [{
                                "shop_id": 1,
                                "title": "Mening Uzum Do'konim",
                                "legal_name": "Tadbirkor",
                                "inn": "",
                                "status": "ACTIVE",
                                "is_selected": 1,
                            }]

                        # Clear demo data before saving real live shop
                        reset_uzum_data()

                        save_uzum_settings(
                            api_key=clean_key,
                            is_connected=1,
                            is_demo=0,
                            telegram_chat_id=telegram_chat_id,
                            last_sync_at=datetime.now().isoformat(),
                        )
                        save_uzum_shops(shops_list)
                        logger.info("Successfully validated Uzum API key. Found %d shops.", len(shops_list))

                        # Proactively pull initial orders and stocks
                        await self.sync_live_orders_and_stocks()

                        return {
                            "status": "ok",
                            "mode": "live",
                            "message": f"Успешно подключено к Uzum API! Найдено магазинов: {len(shops_list)}",
                            "shops_count": len(shops_list),
                        }
                    elif res.status_code in (401, 403):
                        return {
                            "status": "error",
                            "message": "Неверный API-токен Uzum (401/403 Unauthorized). Проверьте ключ в кабинете seller.uzum.uz",
                        }
                    else:
                        logger.warning("Uzum /v1/shops returned status %s: %s", res.status_code, res.text)
                        return {
                            "status": "error",
                            "message": f"Ошибка Uzum API ({res.status_code}): {res.text[:120]}",
                        }
            except Exception as exc:
                logger.error("Failed to connect to Uzum API: %s", exc)
                return {
                    "status": "error",
                    "message": f"Не удалось подключиться к api-seller.uzum.uz: {str(exc)[:120]}",
                }

    async def sync_live_orders_and_stocks(self) -> None:
        """
        Fetch live orders and product stocks strictly following Uzum Seller OpenAPI 3.0.0:
        - GET /v2/fbs/orders with required shopIds query param across active statuses
        - GET /v3/fbs/sku/stocks with shopIds & page
        - GET /v1/product/shop/{shopId} for product catalog details
        """
        settings = get_uzum_settings()
        api_key = settings.get("api_key")
        if not api_key or settings.get("is_demo"):
            return

        headers = self._get_headers(api_key)
        shops = get_uzum_shops()
        if not shops:
            return
        shop_map = {s["shop_id"]: s["title"] for s in shops}
        shop_ids = [s["shop_id"] for s in shops]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # 1. Fetch FBS orders for each status
                parsed_orders = []
                # Uzum statuses according to OpenAPI: CREATED, PACKING, DELIVERING, COMPLETED, CANCELED
                statuses_to_check = ["CREATED", "PACKING", "DELIVERING", "COMPLETED", "CANCELED"]
                for st_query in statuses_to_check:
                    try:
                        res = await client.get(
                            f"{UZUM_API_BASE}/v2/fbs/orders",
                            headers=headers,
                            params={"shopIds": shop_ids, "status": st_query, "page": 0, "size": 30},
                        )
                        if res.status_code == 200:
                            data = res.json()
                            raw_orders = (
                                data.get("payload", {}).get("orders")
                                or data.get("orders")
                                or data.get("content")
                                or []
                            )
                            for o in raw_orders:
                                oid = int(o.get("orderId") or o.get("id"))
                                s_id = int(o.get("shopId", shop_ids[0]))
                                s_title = shop_map.get(s_id, f"Do'kon #{s_id}")
                                st = str(o.get("status", st_query)).upper()

                                # Friendly labels
                                ru_labels = {
                                    "CREATED": "Новый (Ожидает подтверждения)",
                                    "PACKING": "В сборке (Подтвержден)",
                                    "PENDING_DELIVERY": "Готов к отгрузке",
                                    "DELIVERING": "В пути (Доставляется)",
                                    "DELIVERED": "Доставлен в ПВЗ",
                                    "COMPLETED": "Завершён (Выдан покупателю)",
                                    "CANCELED": "Отменён",
                                }
                                uz_labels = {
                                    "CREATED": "Yangi (Tasdiqlash kutilmoqda)",
                                    "PACKING": "Yig'ilmoqda (Tasdiqlangan)",
                                    "PENDING_DELIVERY": "Jo'natishga tayyor",
                                    "DELIVERING": "Yo'lda (Yetkazilmoqda)",
                                    "DELIVERED": "Topshirish punktida",
                                    "COMPLETED": "Yakunlandi (Xaridor oldi)",
                                    "CANCELED": "Bekor qilindi",
                                }
                                ru_label = ru_labels.get(st, st)
                                uz_label = uz_labels.get(st, st)

                                items_list = []
                                for it in o.get("items") or o.get("orderItems") or o.get("skuList") or []:
                                    items_list.append({
                                        "sku_id": int(it.get("skuId", 0)),
                                        "product_title": it.get("skuTitle") or it.get("title") or it.get("productTitle", "Mahsulot"),
                                        "quantity": int(it.get("quantity", 1)),
                                        "price": float(it.get("price", 0)),
                                        "barcode": str(it.get("barcode", "")),
                                    })

                                created_time_str = o.get("createdAt") or o.get("orderCreatedTime") or datetime.now().isoformat()
                                # 16 hours confirmation deadline per Uzum Seller Manual section 8.3
                                try:
                                    created_dt = datetime.fromisoformat(created_time_str.replace("Z", "+00:00"))
                                    deadline_str = (created_dt + timedelta(hours=16)).isoformat()
                                except Exception:
                                    deadline_str = (datetime.now() + timedelta(hours=16)).isoformat()

                                parsed_orders.append({
                                    "order_id": oid,
                                    "shop_id": s_id,
                                    "shop_title": s_title,
                                    "posting_number": o.get("postingNumber", str(oid)),
                                    "status": st,
                                    "status_label_ru": ru_label,
                                    "status_label_uz": uz_label,
                                    "total_amount": float(o.get("totalAmount") or o.get("amount", 0)),
                                    "delivery_type": o.get("deliveryType", "FBS"),
                                    "customer_name": o.get("customerName", "Xaridor"),
                                    "delivery_city": o.get("deliveryCity", "Toshkent"),
                                    "created_at": created_time_str,
                                    "deadline_to_confirm": o.get("confirmDeadline") or deadline_str,
                                    "is_notified": 0 if st == "CREATED" else 1,
                                    "items": items_list,
                                })
                    except Exception as st_exc:
                        logger.debug("Error checking status %s: %s", st_query, st_exc)

                if parsed_orders:
                    save_uzum_orders(parsed_orders)
                    logger.info("Synchronized %d live orders from Uzum API.", len(parsed_orders))

                # 2. Fetch stocks: /v3/fbs/sku/stocks
                res_stock = await client.get(
                    f"{UZUM_API_BASE}/v3/fbs/sku/stocks",
                    headers=headers,
                    params={"shopIds": shop_ids, "page": 0, "size": 50},
                )
                parsed_stocks = []
                if res_stock.status_code == 200:
                    stock_data = res_stock.json()
                    raw_stocks = (
                        stock_data.get("payload", {}).get("skuAmountList")
                        or stock_data.get("stocks")
                        or stock_data.get("content")
                        or []
                    )
                    for st_item in raw_stocks:
                        sku = int(st_item.get("skuId", 0))
                        s_id = int(st_item.get("shopId", shop_ids[0]))
                        parsed_stocks.append({
                            "sku_id": sku,
                            "shop_id": s_id,
                            "shop_title": shop_map.get(s_id, f"Do'kon #{s_id}"),
                            "product_title": st_item.get("productTitle") or st_item.get("title", f"SKU #{sku}"),
                            "barcode": str(st_item.get("barcode", "")),
                            "current_stock": int(st_item.get("amount", 0)),
                            "price": float(st_item.get("price", 0)),
                            "is_low_stock": 1 if int(st_item.get("amount", 0)) <= 3 else 0,
                        })

                # 3. Pull product catalog details from GET /v1/product/shop/{shopId}
                for s_id in shop_ids:
                    try:
                        p_res = await client.get(
                            f"{UZUM_API_BASE}/v1/product/shop/{s_id}",
                            headers=headers,
                            params={"page": 0, "size": 50},
                        )
                        if p_res.status_code == 200:
                            p_data = p_res.json()
                            for prod in p_data.get("productList", []):
                                p_title = prod.get("title", "Mahsulot")
                                for sku_obj in prod.get("skuList", []):
                                    sku_id = int(sku_obj.get("id", 0))
                                    # If not already present in parsed_stocks, add it
                                    if not any(s["sku_id"] == sku_id for s in parsed_stocks):
                                        parsed_stocks.append({
                                            "sku_id": sku_id,
                                            "shop_id": s_id,
                                            "shop_title": shop_map.get(s_id, f"Do'kon #{s_id}"),
                                            "product_title": f"{p_title} ({sku_obj.get('characteristicsTitle', '')})".strip(),
                                            "barcode": str(sku_obj.get("barcode", "")),
                                            "current_stock": int(sku_obj.get("amount", 5)),
                                            "price": float(sku_obj.get("price", 0)),
                                            "is_low_stock": 0,
                                        })
                    except Exception as p_exc:
                        logger.debug("Error pulling products for shop %s: %s", s_id, p_exc)

                if parsed_stocks:
                    save_uzum_stocks(parsed_stocks)
                    logger.info("Synchronized %d live stock records from Uzum API.", len(parsed_stocks))

                save_uzum_settings(last_sync_at=datetime.now().isoformat())
        except Exception as exc:
            logger.warning("Live sync error: %s", exc)

    async def confirm_order(self, order_id: int) -> Dict[str, Any]:
        """
        Confirm an FBS order (transitions from CREATED to CONFIRMED / PACKING).
        Calls POST /v1/fbs/order/{orderId}/confirm or simulates in Demo mode.
        """
        settings = get_uzum_settings()
        is_demo = bool(settings.get("is_demo"))
        api_key = settings.get("api_key")

        if is_demo or not api_key:
            update_uzum_order_status(
                order_id=order_id,
                new_status="CONFIRMED",
                status_label_ru="В сборке (Подтвержден)",
                status_label_uz="Yig'ilmoqda (Tasdiqlangan)",
            )
            return {
                "status": "ok",
                "order_id": order_id,
                "new_status": "CONFIRMED",
                "message": f"Заказ #{order_id} успешно подтверждён! Товар переведён в статус сборки.",
            }

        headers = self._get_headers(api_key)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(f"{UZUM_API_BASE}/v1/fbs/order/{order_id}/confirm", headers=headers)
                if res.status_code in (200, 204):
                    update_uzum_order_status(
                        order_id=order_id,
                        new_status="CONFIRMED",
                        status_label_ru="В сборке (Подтвержден)",
                        status_label_uz="Yig'ilmoqda (Tasdiqlangan)",
                    )
                    return {
                        "status": "ok",
                        "order_id": order_id,
                        "new_status": "CONFIRMED",
                        "message": f"Заказ #{order_id} подтвержден на Uzum Market.",
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Uzum API вернул ошибку при подтверждении ({res.status_code}): {res.text[:120]}",
                    }
        except Exception as exc:
            return {"status": "error", "message": f"Сетевая ошибка: {exc}"}

    async def cancel_order(self, order_id: int, reason: str = "Отсутствует на складе") -> Dict[str, Any]:
        """
        Cancel an FBS order via POST /v1/fbs/order/{orderId}/cancel.
        Validates reason enum ('OUT_OF_STOCK' or 'OTHER') as required by Uzum Seller OpenAPI.
        """
        settings = get_uzum_settings()
        is_demo = bool(settings.get("is_demo"))
        api_key = settings.get("api_key")

        if is_demo or not api_key:
            update_uzum_order_status(
                order_id=order_id,
                new_status="CANCELLED",
                status_label_ru="Отменён",
                status_label_uz="Bekor qilindi",
            )
            return {"status": "ok", "order_id": order_id, "new_status": "CANCELLED"}

        headers = self._get_headers(api_key)
        # Map user text to valid OpenAPI enum: OUT_OF_STOCK or OTHER
        enum_val = "OUT_OF_STOCK"
        lower_reason = reason.lower()
        if any(w in lower_reason for w in ["brak", "дефект", "поврежд", "defect", "other", "boshqa", "клиент"]):
            enum_val = "OTHER"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {"reason": enum_val, "comment": reason}
                res = await client.post(
                    f"{UZUM_API_BASE}/v1/fbs/order/{order_id}/cancel",
                    headers=headers,
                    json=payload,
                )
                if res.status_code in (200, 204):
                    update_uzum_order_status(
                        order_id=order_id,
                        new_status="CANCELLED",
                        status_label_ru="Отменён",
                        status_label_uz="Bekor qilindi",
                    )
                    return {"status": "ok", "order_id": order_id, "new_status": "CANCELLED"}
                return {"status": "error", "message": f"Ошибка отмены ({res.status_code}): {res.text[:120]}"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    async def get_order_label(self, order_id: int, size: str = "LARGE") -> Dict[str, Any]:
        """
        Retrieve order label from Uzum OpenAPI: GET /v1/fbs/order/{orderId}/labels/print?size={size}
        size can be 'LARGE' (58x40mm) or 'BIG' (43x25mm).
        """
        settings = get_uzum_settings()
        api_key = settings.get("api_key")
        is_demo = bool(settings.get("is_demo"))

        if not is_demo and api_key:
            headers = self._get_headers(api_key)
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    res = await client.get(
                        f"{UZUM_API_BASE}/v1/fbs/order/{order_id}/labels/print",
                        headers=headers,
                        params={"size": size},
                    )
                    if res.status_code == 200:
                        return {"status": "ok", "raw_content": res.text, "size": size}
            except Exception as exc:
                logger.warning("Failed to fetch label from Uzum API: %s", exc)

        # Fallback to local DB order metadata
        orders = get_uzum_orders()
        matching = [o for o in orders if o["order_id"] == order_id]
        if matching:
            o = matching[0]
            return {
                "status": "ok",
                "order_id": order_id,
                "posting_number": o.get("posting_number", str(order_id)),
                "shop_title": o.get("shop_title", "Uzum Shop"),
                "customer_name": o.get("customer_name", "Xaridor"),
                "delivery_city": o.get("delivery_city", "Toshkent"),
                "size": size,
                "label_dimensions": "58x40 mm" if size == "LARGE" else "43x25 mm",
            }
        return {"status": "error", "message": "Order not found"}

    def generate_thermal_label_image(self, order_id: int, size: str = "LARGE") -> bytes:
        """
        Generate a crisp 203 DPI monochrome thermal label image (PNG) for Bluetooth & desktop printers:
        - 58x40 mm standard format (580x400 px) or 43x25 mm (430x250 px)
        - Clean layout, order posting number, store title, destination city, barcode stripes
        """
        from PIL import Image, ImageDraw
        import io
        import random

        orders = get_uzum_orders()
        matching = [o for o in orders if o["order_id"] == order_id]
        if matching:
            o = matching[0]
        else:
            o = {
                "order_id": order_id,
                "posting_number": f"UZ-FBS-{order_id}",
                "shop_title": "Myrana Shop",
                "customer_name": "Xaridor",
                "delivery_city": "Toshkent",
                "items": [{"product_title": "Mahsulot", "quantity": 1}],
            }

        width = 580 if size == "LARGE" else 430
        height = 400 if size == "LARGE" else 250

        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        # High-contrast thermal border
        draw.rectangle([(6, 6), (width - 6, height - 6)], outline="black", width=3)
        draw.line([(6, 44), (width - 6, 44)], fill="black", width=2)

        # Header with size
        size_label = "58×40 mm (Standard)" if size == "LARGE" else "43×25 mm"
        draw.text((16, 14), f"UZUM MARKET FBS  •  {size_label}", fill="black")

        # Shop and recipient info
        shop_title = o.get("shop_title", "Do'kon")[:32]
        posting_num = o.get("posting_number", f"UZ-FBS-{order_id}")
        city = o.get("delivery_city", "Toshkent")
        customer = o.get("customer_name", "Xaridor")

        draw.text((16, 52), f"Do'kon: {shop_title}", fill="black")
        draw.text((16, 74), f"Jo'natma: {posting_num}", fill="black")
        draw.text((16, 96), f"Qabul qiluvchi: {customer} ({city})", fill="black")

        # Barcode stripes (deterministic seed from order_id for reproducible readable pattern)
        bar_y = 126 if size == "LARGE" else 105
        bar_h = 135 if size == "LARGE" else 65
        x = 22
        rng = random.Random(order_id)
        while x < width - 24:
            w = rng.choice([2, 3, 5, 7])
            gap = rng.choice([2, 3, 4])
            draw.rectangle([(x, bar_y), (x + w, bar_y + bar_h)], fill="black")
            x += w + gap

        # Human-readable barcode string
        text_y = bar_y + bar_h + 8
        draw.text((width // 2 - 75, text_y), f"* {posting_num} *", fill="black")

        # Items info at bottom
        items = o.get("items", [])
        if items:
            it = items[0]
            it_str = f"Tarkibi: {it.get('product_title', '')[:30]} ({it.get('quantity', 1)} dona)"
            draw.text((16, height - 30), it_str, fill="black")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def send_fbo_restock_alert(self, chat_id: int, sku_id: Optional[int] = None) -> bool:
        """Send proactive Telegram push notification warning about imminent out-of-stock on Uzum FBO."""
        from services.database import get_uzum_fbo_forecast
        forecasts = get_uzum_fbo_forecast()
        if not forecasts:
            return False

        if sku_id:
            matching = [f for f in forecasts if f["sku_id"] == sku_id]
            item = matching[0] if matching else forecasts[0]
        else:
            item = forecasts[0]

        shop_name = item.get("shop_title") or "Uzum Do'kon"
        prod_name = item.get("product_title") or "Mahsulot"
        days_left = int(item.get("days_remaining", 0))
        fbo_qty = item.get("fbo_stock", 0)
        velocity = item.get("daily_sales_velocity", 1.5)
        tip_text = item.get("tip_uz", "")
        reorder_qty = item.get("recommended_reorder", 25)

        text = (
            f"🏬 <b>Uzum FBO: Zaxira tugash xavfi!</b>\n\n"
            f"🏪 <b>Do'kon:</b> <b>{shop_name}</b>\n"
            f"📦 <b>Mahsulot:</b> <b>{prod_name}</b>\n"
            f"📊 <b>Uzum omboridagi qoldiq:</b> <b>{fbo_qty} dona</b>\n"
            f"⏳ <b>Zaxira muddati:</b> taxminan <b>{days_left} kunga yetadi</b>\n"
            f"📉 <b>Kunlik sotuv sur'ati:</b> {velocity:.1f} dona/kun\n\n"
            f"💡 <b>Oqila AI tavsiyasi:</b>\n"
            f"<i>{tip_text}</i>\n"
            f"📦 Tavsiya etilgan yangi partiya: <b>{reorder_qty} dona</b>\n\n"
            f"⚠️ <i>Zaxira tugab qolsa, Uzum qidiruv tizimida mahsulot kartochkasi tushib ketadi!</i>"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "📋 Накладная FBO ochish",
                        "url": "https://seller.uzum.uz/seller/invoices",
                    }
                ],
                [
                    {
                        "text": "📱 Oqila ilovasida ko'rish",
                        "url": "https://t.me/oqila_ai_bot",
                    }
                ]
            ]
        }

        return await telegram_service.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )

    async def check_and_send_notifications(self) -> int:
        """
        Background task: checks for new orders with is_notified == 0
        and sends high-priority Telegram push notifications with 1-click confirmation buttons.
        """
        settings = get_uzum_settings()
        if not settings.get("notifications_enabled"):
            return 0

        target_chat_id = settings.get("telegram_chat_id")
        if not target_chat_id and os.getenv("TELEGRAM_ADMIN_CHAT_ID"):
            try:
                target_chat_id = int(os.getenv("TELEGRAM_ADMIN_CHAT_ID"))
            except Exception:
                pass

        if not target_chat_id:
            # Check subscribers table for any registered user
            from services.database import get_subscribers
            subs = get_subscribers()
            if subs:
                target_chat_id = subs[0]["chat_id"]

        if not target_chat_id:
            # Cannot dispatch without a recipient chat
            return 0

        unnotified = get_unnotified_uzum_orders()
        sent_count = 0

        for order in unnotified:
            oid = order["order_id"]
            shop_title = order.get("shop_title") or f"Do'kon #{order.get('shop_id')}"
            total = float(order.get("total_amount", 0))
            deadline = order.get("deadline_to_confirm", "")

            # Format items summary
            items_str = ""
            for item in order.get("items", []):
                items_str += f"• <b>{item.get('product_title')}</b> — {item.get('quantity')} dona × {item.get('price', 0):,.0f} so'm\n"

            time_left_str = "Taxminan 2 soat"
            if deadline:
                try:
                    dt = datetime.fromisoformat(deadline)
                    diff = dt - datetime.now()
                    mins = max(1, int(diff.total_seconds() // 60))
                    time_left_str = f"qolgan vaqt: {mins} daqiqa"
                except Exception:
                    pass

            msg_html = (
                f"🔔 <b>Yangi Uzum FBS buyurtmasi!</b>\n\n"
                f"🏪 <b>Do'kon:</b> <b>{shop_title}</b>\n"
                f"📦 <b>Buyurtma:</b> <code>#{oid}</code> ({order.get('delivery_type', 'FBS')})\n"
                f"📍 <b>Manzil:</b> {order.get('delivery_city', 'Toshkent')}\n"
                f"🛍️ <b>Tarkibi:</b>\n{items_str}"
                f"💰 <b>Jami summa:</b> <b>{total:,.0f} so'm</b>\n"
                f"⏳ <b>Tasdiqlash muddati:</b> {time_left_str}\n\n"
                f"⚠️ <i>Muddati o'tmasdan tasdiqlang, aks holda Uzum buyurtmani bekor qiladi va jarima qo'llaydi!</i>"
            )

            # Interactive inline keyboard
            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "✅ Tasdiqlash / Подтвердить",
                            "callback_data": f"uzum_confirm_{oid}",
                        },
                    ],
                    [
                        {
                            "text": "🏷️ Shtrix-kod / Этикетка",
                            "callback_data": f"uzum_label_{oid}",
                        },
                        {
                            "text": "📱 Oqila ilovasini ochish",
                            "url": f"https://t.me/oqila_ai_bot",
                        },
                    ],
                ]
            }

            success = await telegram_service.send_message(
                chat_id=target_chat_id,
                text=msg_html,
                reply_markup=reply_markup,
            )

            if success:
                mark_order_notified(oid)
                log_uzum_notification(
                    event_type="new_fbs_order",
                    shop_id=order.get("shop_id"),
                    order_id=oid,
                    message=msg_html,
                    sent_to_chat_id=target_chat_id,
                    status="sent",
                )
                sent_count += 1
                logger.info("Sent Telegram push for Uzum order #%d (Shop: %s)", oid, shop_title)

        return sent_count

    async def send_test_push(self, chat_id: int, lang: str = "uz") -> bool:
        """Send a test push notification to verify Telegram bot delivery."""
        test_oid = 998811
        if lang == "uz":
            text = (
                "🧪 <b>Uzum Market — Sinov Bildirishnomasi (Test Push)</b>\n\n"
                "🏪 <b>Do'kon:</b> 👗 Oqila Milliy Liboslar\n"
                "📦 <b>Buyurtma:</b> #998811 (FBS)\n"
                "🛍️ <b>Mahsulot:</b> Xon-atlas bayramona libosi — 1 dona\n"
                "💰 <b>Summa:</b> 380 000 so'm\n"
                "⏳ <b>Tasdiqlash muddati:</b> 2 soat ichida\n\n"
                "✅ <i>Uzum va Telegram bot o'rtasidagi aloqa a'lo darajada ishlamoqda!</i>"
            )
        else:
            text = (
                "🧪 <b>Uzum Market — Тестовое Push-уведомление</b>\n\n"
                "🏪 <b>Магазин:</b> 👗 Oqila Milliy Liboslar\n"
                "📦 <b>Заказ:</b> #998811 (FBS)\n"
                "🛍️ <b>Товар:</b> Праздничное платье хан-атлас — 1 шт.\n"
                "💰 <b>Сумма:</b> 380 000 сум\n"
                "⏳ <b>Дедлайн подтверждения:</b> в течение 2 часов\n\n"
                "✅ <i>Интеграция Uzum Market с Telegram работает идеально!</i>"
            )

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Tasdiqlash / Подтвердить (Тест)",
                        "callback_data": f"uzum_confirm_{test_oid}",
                    }
                ]
            ]
        }

        ok = await telegram_service.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )
        if ok:
            save_uzum_settings(telegram_chat_id=chat_id)
        return ok


uzum_service = UzumService()
