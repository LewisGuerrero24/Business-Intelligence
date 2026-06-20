namespace BulkLoad.Application.DTOs.Requests;

public class CreateImportRequest
{
    public Guid CompanyId { get; set; }
    public string ImportType { get; set; } = string.Empty;// Branches, Productos, etc.
    public string SourceType { get; set; } = string.Empty;// API, CSV, etc.
    public int TotalRecords { get; set; }
}