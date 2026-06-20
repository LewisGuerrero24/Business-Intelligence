using BulkLoad.Domain.Entities.Control;

namespace BulkLoad.Domain.Repositories.Control;

public interface IDataImportRepository
{
    Task<DataImport> GetByIdAsync(Guid importId, CancellationToken cancellationToken = default);
    Task<Guid> CreateAsync(DataImport dataImport, CancellationToken cancellationToken = default);
    Task UpdateStatusAsync(
        Guid importId,
        string status,
        int? totalRecords = null,
        int? processedRecords = null,
        int? successRecords = null,
        int? failedRecords = null,
        int? skippedRecords = null,
        string? errorSummary = null,
        CancellationToken cancellationToken = default
    );

    Task<(bool Success, string Message, int TotalStaged, int TotalExpected)> CompleteUploadAsync(
        Guid importId,
        bool force = false,
        CancellationToken cancellationToken = default
    );
    
}