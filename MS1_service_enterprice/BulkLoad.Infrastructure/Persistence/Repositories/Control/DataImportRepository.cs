using BulkLoad.Domain.Entities.Control;
using BulkLoad.Domain.Repositories.Control;
using BulkLoad.Domain.ValueObjects;
using Microsoft.Extensions.Logging;
using Npgsql;

namespace BulkLoad.Infrastructure.Persistence.Repositories.Control;

public class DataImportRepository : IDataImportRepository
{

    public readonly NpgsqlConnection Connection;
    private readonly ILogger<DataImportRepository> _logger; // Usado en produccion

    public DataImportRepository(ILogger<DataImportRepository> logger, NpgsqlConnection connection)
    {
        _logger = logger;
        Connection = connection;
    }

    public async Task<Guid> CreateAsync(
        DataImport dataImport,
        CancellationToken cancellationToken = default
    )
    {
        try
        {
            await using var connection = new NpgsqlConnection(Connection.ConnectionString);
            await connection.OpenAsync(cancellationToken);

            // Query directo - Simple INSERT
            await using var command = new NpgsqlCommand(@"
                INSERT INTO ""Control"".data_imports (
                    company_id,
                    import_type,
                    source_type,
                    original_filename,
                    file_path,
                    file_size_bytes,
                    status,
                    total_records,
                    upload_started_at,
                    created_by
                ) VALUES (
                    @companyId,
                    @importType,
                    @sourceType,
                    @originalFilename,
                    @filePath,
                    @fileSizeBytes,
                    @status,
                    @totalRecords,
                    @uploadStartedAt,
                    @createdBy
                )
                RETURNING import_id;
            ", connection);
            
            command.Parameters.AddWithValue("@companyId", dataImport.CompanyId);
            command.Parameters.AddWithValue("@importType", dataImport.ImportType);
            command.Parameters.AddWithValue("@sourceType", dataImport.SourceType);
            command.Parameters.AddWithValue("@originalFilename", (object?)dataImport.OriginalFilename ?? DBNull.Value);
            command.Parameters.AddWithValue("@filePath", (object?)dataImport.FilePath ?? DBNull.Value);
            command.Parameters.AddWithValue("@fileSizeBytes", (object?)dataImport.FileSizeBytes ?? DBNull.Value);
            command.Parameters.AddWithValue("@status", dataImport.Status.Value);
            command.Parameters.AddWithValue("@totalRecords", dataImport.TotalRecords);
            command.Parameters.AddWithValue("@uploadStartedAt", dataImport.UploadStartedAt ?? DateTime.UtcNow);
            command.Parameters.AddWithValue("@createdBy", dataImport.CreatedBy);

            var result = await command.ExecuteScalarAsync(cancellationToken);

            if (result is not Guid importId)
            {
                throw new InvalidOperationException("Failed to create import. No ID returned.");
            }

            _logger.LogInformation( // TODO: Log the data import
                "Import {ImportId} created successfully for company {CompanyId}",
                importId,
                dataImport.CompanyId);
            
            return importId;

        } catch (PostgresException ex)
        {
            _logger.LogError(ex,
                "Database error creating import for company {CompanyId}. Error code: {ErrorCode}",
                dataImport.CompanyId,
                ex.SqlState);

            // Re-throw con mensaje más amigable
            throw new InvalidOperationException(
                $"Failed to create import due to database error: {ex.MessageText}",
                ex);
        } catch (Exception ex)
        {
            _logger.LogError(ex,
                "Unexpected error creating import for company {CompanyId}",
                dataImport.CompanyId);

            throw;
        }

    }

    public async Task<DataImport> GetByIdAsync(
        Guid importId,
        CancellationToken cancellationToken = default
    )
    {
        try
        {
            await using var connection = new NpgsqlConnection(Connection.ConnectionString);
            await connection.OpenAsync(cancellationToken);

            await using var command = new NpgsqlCommand(@"
                SELECT
                    import_id,
                    company_id,
                    import_type,
                    source_type,
                    original_filename,
                    file_path,
                    file_size_bytes,
                    status,
                    total_records,
                    processed_records,
                    success_records,
                    failed_records,
                    skipped_records,
                    upload_started_at,
                    upload_completed_at,
                    processing_started_at,
                    processing_completed_at,
                    total_duration_seconds,
                    created_by,
                    error_summary
                FROM ""Control"".data_imports
                WHERE import_id = @importId", connection);

            command.Parameters.AddWithValue("@importId", importId);

            await using var reader = await command.ExecuteReaderAsync(cancellationToken);

            if (await reader.ReadAsync(cancellationToken))
            {
                return new DataImport
                {
                    ImportId = reader.GetGuid(0),
                    CompanyId = reader.GetGuid(1),
                    ImportType = reader.GetString(2),
                    SourceType = reader.GetString(3),
                    OriginalFilename = reader.IsDBNull(4) ? null : reader.GetString(4),
                    FilePath = reader.IsDBNull(5) ? null : reader.GetString(5),
                    FileSizeBytes = reader.IsDBNull(6) ? null : reader.GetInt64(6),
                    Status = ImportStatus.From(reader.GetString(7)),
                    TotalRecords = reader.GetInt32(8),
                    ProcessedRecords = reader.GetInt32(9),
                    SuccessRecords = reader.GetInt32(10),
                    FailedRecords = reader.GetInt32(11),
                    SkippedRecords = reader.GetInt32(12),
                    UploadStartedAt = reader.IsDBNull(13) ? null : reader.GetDateTime(13),
                    UploadCompletedAt = reader.IsDBNull(14) ? null : reader.GetDateTime(14),
                    ProcessingStartedAt = reader.IsDBNull(15) ? null : reader.GetDateTime(15),
                    ProcessingCompletedAt = reader.IsDBNull(16) ? null : reader.GetDateTime(16),
                    TotalDurationSeconds = reader.IsDBNull(17) ? null : reader.GetInt32(17),
                    CreatedBy = reader.GetGuid(18),
                    ErrorSummary = reader.IsDBNull(19) ? null : reader.GetString(19)
                };
            }
            return null;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting import {ImportId}", importId);
            throw;
        }  
    }

    public async Task UpdateStatusAsync(
        Guid importId,
        string status,
        int? totalRecords = null,
        int? processedRecords = null,
        int? successRecords = null,
        int? failedRecords = null,
        int? skippedRecords = null,
        string? errorSummary = null,
        CancellationToken cancellationToken = default
    )
    {
        try
        {
            await using var connection = new NpgsqlConnection(Connection.ConnectionString);
            await connection.OpenAsync(cancellationToken);

            await using var command = new NpgsqlCommand(@"
                SELECT ""Control"".sp_update_import_status(
                    @importId,
                    @status,
                    @totalRecords,
                    @processedRecords,
                    @successRecords,
                    @failedRecords,
                    @skippedRecords,
                    @errorSummary
                );", connection);

            command.Parameters.AddWithValue("@importId", importId);
            command.Parameters.AddWithValue("@status", status);
            command.Parameters.AddWithValue("@totalRecords", (object?)totalRecords ?? DBNull.Value);
            command.Parameters.AddWithValue("@processedRecords", (object?)processedRecords ?? DBNull.Value);
            command.Parameters.AddWithValue("@successRecords", (object?)successRecords ?? DBNull.Value);
            command.Parameters.AddWithValue("@failedRecords", (object?)failedRecords ?? DBNull.Value);
            command.Parameters.AddWithValue("@skippedRecords", (object?)skippedRecords ?? DBNull.Value);
            command.Parameters.AddWithValue("@errorSummary", (object?)errorSummary ?? DBNull.Value);

            await command.ExecuteNonQueryAsync(cancellationToken);

            _logger.LogInformation("Import {ImportId} updated successfully", importId);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error updating import {ImportId}", importId);
            throw;
        }
    }

    public async Task<(bool Success, string Message, int TotalStaged, int TotalExpected)> CompleteUploadAsync(
        Guid importId,
        bool force,
        CancellationToken cancellationToken
    )
    {
        await using var connection = new NpgsqlConnection(Connection.ConnectionString);
        await connection.OpenAsync(cancellationToken);

        await using var command = new NpgsqlCommand(@"
            SELECT success, message, total_staged, total_expected
            FROM ""Control"".fn_complete_import_upload(@importId, @force);
        ", connection);

        command.Parameters.AddWithValue("@importId", importId);
        command.Parameters.AddWithValue("@force", force);

        await using var reader = await command.ExecuteReaderAsync(cancellationToken);
        await reader.ReadAsync(cancellationToken);

        return (
            reader.GetBoolean(0),
            reader.GetString(1),
            reader.GetInt32(2),
            reader.GetInt32(3)
        );
    }

}
