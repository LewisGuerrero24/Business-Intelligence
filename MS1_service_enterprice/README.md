Comandos genereales usados:

*Crear solucion del proyecto:*  dotnet new sln -n MS1_BulkLoadService

*Listar versiones de .NET:* dotnet --list-sdks

*Instalar .NET version traer paquete de repositorio:*  sudo dnf install -y https://packages.microsoft.com/config/fedora/43/packages-microsoft-prod.rpm

*Instalar version de .NET:* sudo dnf install dotnet-sdk-10.0

Crear capas y ferencias:

  556  dotnet new classlib -n BulkLoad.Domain
  557  dotnet new classlib -n BulkLoad.Application
  558  dotnet new classlib -n BulkLoad.Infrastructure
  559  dotnet new webapi -n BulkLoad.ApiAdministrator
  560  dotnet sln add BulkLoad.Domain/
  561  dotnet sln add BulkLoad.Application/
  562  dotnet sln add BulkLoad.Infrastructure/
  563  dotnet sln add BulkLoad.ApiAdministrator/
  564  dotnet add  BulkLoad.Application/ reference BulkLoad.Domain/
  565  dotnet add  BulkLoad.Infrastructure/ reference BulkLoad.Domain/
  566  dotnet add  BulkLoad.ApiAdministrator/ reference BulkLoad.Application/
  567  dotnet add  BulkLoad.ApiAdministrator/ reference BulkLoad.Infrastructure/
  568  dotnet add  BulkLoad.ApiAdministrator/ reference BulkLoad.Domain/



  PostgreSQL COPY es un comando SQL de alto rendimiento utilizado para mover datos masivamente entre tablas y archivos estándar (como CSV) o la entrada/salida estándar. Es mucho más rápido que INSERT para cargas de datos, permitiendo exportar (COPY TO) e importar (COPY FROM) archivos, soportando formatos CSV, texto y binario.




  🧠 Usa FUNCTIONS cuando:

Las funciones son ideales para devolver valores y trabajar dentro de consultas.

Casos típicos:

Calcular algo (ej: impuestos, totales)
Transformar datos
Usarlas dentro de un SELECT, WHERE, JOIN, etc.
Retornar un valor escalar, tabla o conjunto de filas

Ejemplo:

SELECT calcular_descuento(precio) FROM productos;

Ventajas:

Se pueden usar directamente en queries
Son más “declarativas”
Buenas para lógica reutilizable y pura (sin efectos secundarios)
⚙️ Usa STORED PROCEDURES (SP) cuando:

Los procedimientos son mejores para ejecutar acciones más complejas, especialmente con control de transacciones.

Casos típicos:

Procesos largos o múltiples pasos
Inserciones/actualizaciones masivas
Manejo de transacciones (COMMIT, ROLLBACK)
Lógica tipo “flujo” (if, loops, etc.)

Ejemplo:

CALL procesar_pedido(123);

Ventajas:

Permiten control de transacciones (desde PostgreSQL 11+)
Mejor para operaciones con efectos secundarios
Más cercanos a “scripts” o procesos batch
🔑 Diferencia clave (resumen)
Característica	Function	Stored Procedure
Retorna valor	✅ Sí	❌ No obligatorio
Uso en SELECT	✅ Sí	❌ No
Control de transacción	❌ Limitado	✅ Completo
Llamada	SELECT fn()	CALL sp()
🧩 Regla práctica rápida
👉 Si necesitas un resultado dentro de una consulta → FUNCTION
👉 Si necesitas ejecutar un proceso con pasos y transacciones → PROCEDURE


Usar procolo de comuniacion gRPC para comunicar con otros servicios