using BulkLoad.Domain.Entities.Staging;

namespace BulkLoad.Domain.Repositories.Staging;

public interface IStagingBranchRepository
{
    /// <summary>
    /// Bulk Insert usando PostgreSQL COPY (ultra rápido)
    /// </summary>
    Task<int> BulkInsertAsync(
        Guid importId,
        List<StagingBranchInput> branches,
        CancellationToken cancellationToken = default
    );

    /// <summary>
    /// Contar registros por import
    /// </summary>
    Task<int> CountByImportIdAsync(
        Guid importId,
        CancellationToken cancellationToken = default
    );

    /// <summary>
    /// Obtener el último row_number para conitnuar secuencia
    /// </summary>
    Task<int> GetLastRowNumberAsync(
        Guid importId,
        CancellationToken cancellationToken = default
    );
}