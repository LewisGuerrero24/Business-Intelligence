namespace BulkLoad.Application.DTOs.Responses;

public class CreateImportResponse
{
    public Guid ImportId { get; set; }
    public string Status { get; set;} = string.Empty;
    public string Message { get; set;} = string.Empty;
}