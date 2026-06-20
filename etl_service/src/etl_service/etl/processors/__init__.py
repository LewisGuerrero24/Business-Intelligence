from etl_service.etl.processors.branches import BranchProcessor
from etl_service.etl.processors.categories import CategoryProcessor
from etl_service.etl.processors.customers import CustomerProcessor
from etl_service.etl.processors.inventory_movement import InventoryMovementProcessor
from etl_service.etl.processors.products import ProductProcessor
from etl_service.etl.processors.purchase_details import PurchaseDetailProcessor
from etl_service.etl.processors.purchases import PurchaseProcessor
from etl_service.etl.processors.sale_details import SaleDetailProcessor
from etl_service.etl.processors.sales import SaleProcessor
from etl_service.etl.processors.suppliers import SupplierProcessor


__all__ = [
    "BranchProcessor",
    "CategoryProcessor",
    "CustomerProcessor",
    "InventoryMovementProcessor",
    "ProductProcessor",
    "PurchaseDetailProcessor",
    "PurchaseProcessor",
    "SaleDetailProcessor",
    "SaleProcessor",
    "SupplierProcessor",
]
