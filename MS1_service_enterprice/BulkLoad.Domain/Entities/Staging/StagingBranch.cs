namespace BulkLoad.Domain.Entities.Staging;

public class StagingBranch
{
    public Guid StagingId { get; set; }
    public Guid ImportId { get; set; }
    public int RowNumber { get; set; }
    public string RawData { get; set; } = string.Empty;
    public string? CleanData { get; set; }
    public bool IsProcessed { get; set; }
    public bool IsValid { get; set; }
    public string? ValidationErrors { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime? ProcessedAt { get; set; }

    public StagingBranch() { }
}