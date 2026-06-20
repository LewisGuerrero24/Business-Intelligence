namespace BulkLoad.Application.DTOs.Requests;

public class CompleteImportRequest
{
    // Si el cliente no sabía el total al crear el import (ej: API de tercero)
    // puede pasar force=true para omitir la validación de conteo
    public bool Force { get; set; } = false;
}