using BulkLoad.Domain.ValueObjects;

namespace BulkLoad.Domain.Entities.Control;

public class DataImport
{
    public Guid ImportId { get; set; }
    public Guid CompanyId { get; set; }
    public string ImportType { get; set; } = string.Empty;
    public string SourceType { get; set; } = string.Empty;
    public string? OriginalFilename { get; set; }
    public string? FilePath { get; set; }
    public long? FileSizeBytes { get; set; }
    
    public ImportStatus Status { get; set; } = ImportStatus.Pending;
    
    public int TotalRecords { get; set; }
    public int ProcessedRecords { get; set; }
    public int SuccessRecords { get; set; }
    public int FailedRecords { get; set; }
    public int SkippedRecords { get; set; }
    
    public DateTime? UploadStartedAt { get; set; }
    public DateTime? UploadCompletedAt { get; set; }
    public DateTime? ProcessingStartedAt { get; set; }
    public DateTime? ProcessingCompletedAt { get; set; }
    public int? TotalDurationSeconds { get; set; }
    
    public Guid CreatedBy { get; set; }
    public string? ErrorSummary { get; set; }

        public DataImport() { }


    // Factory method para crear desde un archivo 
    public static DataImport CreateFromFile(
        Guid companyId,
        string importType,
        string sourceType,
        string? originalFilename,
        string? filePath,
        long? fileSizeBytes,
        Guid createdBy)
    {
        return new DataImport
        {
            CompanyId = companyId,
            ImportType = importType,
            SourceType = sourceType,
            OriginalFilename = originalFilename,
            FilePath = filePath,
            FileSizeBytes = fileSizeBytes,
            Status = ImportStatus.Pending,
            UploadStartedAt = DateTime.UtcNow,
            CreatedBy = createdBy
        };
    }

    // Factory method para crear desde la API
    public static DataImport CreateFromApi(
        Guid companyId,
        string importType,
        int totalRecords,
        string sourceType,
        Guid createdBy
    )
    {
        return new DataImport
        {
          CompanyId = companyId,
          ImportType = importType,
          SourceType = sourceType,
          Status = ImportStatus.Pending,
          TotalRecords = totalRecords,
          UploadStartedAt = DateTime.UtcNow,
          CreatedBy = createdBy
        };
    }
}