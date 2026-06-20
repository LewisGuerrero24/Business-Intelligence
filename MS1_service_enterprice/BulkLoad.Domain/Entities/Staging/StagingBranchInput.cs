namespace BulkLoad.Domain.Entities.Staging;

public class StagingBranchInput
{
    public int RowNumber { get; set; }
    public Dictionary<string, object> RawData { get; set; } = new();
}