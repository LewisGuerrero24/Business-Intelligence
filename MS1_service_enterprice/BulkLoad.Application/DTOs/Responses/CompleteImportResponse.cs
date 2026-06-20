namespace BulkLoad.Application.DTOs.Responses;

public class CompleteImportResponse
{
    public Guid ImportId { get; set; }
    public string Status { get; set; } = string.Empty;
    public int TotalStaged { get; set; }
    public int TotalExpected { get; set; }
    public string Message { get; set; } = string.Empty;
}