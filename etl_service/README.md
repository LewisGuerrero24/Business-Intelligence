# ETL Service

Servicio Python para importar archivos Excel/CSV/API hacia PostgreSQL usando el flujo:

1. Crear registro en `Control.data_imports`.
2. Cargar datos crudos en tablas `Staging.staging_*`.
3. Limpiar y validar cada fila.
4. Registrar errores en `Control.import_error_details`.
5. Insertar filas validas en las tablas finales del DW.

El proyecto esta separado de `GestionDatafono` y vive en:

```text
C:\Users\USUARIO\Documents\etl_service
```

## Estructura

```text
src/etl_service/
  api/              API HTTP opcional con FastAPI
  core/             configuracion y logging
  db/               conexion PostgreSQL e identificadores SQL
  domain/           modelos y enums internos
  etl/              registry, pipeline, validadores y transformadores
  repositories/     acceso a Control, Staging y DW
  services/         casos de uso de importacion
  workers/          CLI y procesos ejecutables
```

## Instalacion

```powershell
cd C:\Users\USUARIO\Documents\etl_service
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

Edita `.env` y coloca la clave real de PostgreSQL.

Si prefieres instalacion simple:

```powershell
pip install -r requirements.txt
```

## Comandos

Probar conexion:

```powershell
etl-service check-db
```

Importar y procesar un archivo:

```powershell
etl-service import-file `
  --company-id "00000000-0000-0000-0000-000000000000" `
  --import-type branches `
  --file-path "C:\ruta\archivo.xlsx" `
  --source-type excel `
  --process
```

Procesar una importacion ya creada:

```powershell
etl-service process --import-id "00000000-0000-0000-0000-000000000000"
```

Levantar API:

```powershell
uvicorn etl_service.api.app:create_app --factory --reload
```

## Tipos soportados

El registry soporta estos `import_type` iniciales:

- `companies`
- `branches`
- `categories`
- `customers`
- `suppliers`
- `products`
- `product_suppliers`
- `purchases`
- `purchase_details`
- `purchases_details`
- `sales`
- `sales_details`
- `inventory`
- `inventory_movement`

Para agregar una nueva tabla, normalmente solo editas:

- `src/etl_service/etl/registry.py`
- `src/etl_service/etl/transformers/common.py`
- `src/etl_service/etl/validators/common.py` si requiere reglas especiales
