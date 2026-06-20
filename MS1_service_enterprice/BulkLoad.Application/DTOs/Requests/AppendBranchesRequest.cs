namespace BulkLoad.Application.DTOs.Requests;

public class AppendBranchesRequest
{
    public List<BranchData> Branches { get; set; } = new();
}

public class BranchData
{
    public required string CompanyId { get; set; }
    public string Name { get; set; } = string.Empty;
    public string? Code { get; set; }
    public string? Address { get; set; }
    public string? City { get; set; }
    public string? Phone { get; set; }
    public bool IsActive { get; set; } = true;
}