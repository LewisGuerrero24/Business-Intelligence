namespace BulkLoad.Application.DTOs.Responses;

public class AppendBranchesResponse
{
    public Guid ImportId { get; set; }
    public int ChuckReceived { get; set; }
    public int TotalReceived { get; set; }
    public int TotalExpected { get; set; }
    public decimal Progress { get; set; }
}