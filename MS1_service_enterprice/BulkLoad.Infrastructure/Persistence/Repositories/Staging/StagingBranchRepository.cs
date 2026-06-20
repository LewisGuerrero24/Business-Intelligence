using BulkLoad.Domain.Repositories.Staging;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Configuration;
using Npgsql;
using System.Text.Json;
using BulkLoad.Domain.Entities.Staging;
using NpgsqlTypes;

namespace BulkLoad.Infrastructure.Persistence.Repositories.Staging;

public class StagingBranchRepository : IStagingBranchRepository
{
    public readonly NpgsqlConnection Connection;
    private readonly ILogger<StagingBranchRepository> _logger; // Usado en produccion

    public StagingBranchRepository(ILogger<StagingBranchRepository> logger, NpgsqlConnection connection)
    {
        _logger = logger;
        Connection = connection;
    }

    public async Task<int> BulkInsertAsync(
        Guid importId,
        List<StagingBranchInput> branches,
        CancellationToken cancellationToken = default
    )
    {
        try
        {
            await using var connection = new NpgsqlConnection(Connection.ConnectionString);
            await connection.OpenAsync(cancellationToken);

            // PostgreSQL COPY - Más RÁPIDO para bulk insert
            var copyCommand = @"
                COPY ""Staging"".staging_branches (
                    import_id,
                    row_number,
                    raw_data,
                    is_processed,
                    is_valid
                )
                FROM STDIN (FORMAT BINARY)";

            await using var writer = await connection.BeginBinaryImportAsync(
                copyCommand,
                cancellationToken);
            
            foreach (var branch in branches)
            {
                await writer.StartRowAsync(cancellationToken);

                await writer.WriteAsync(importId, NpgsqlDbType.Uuid, cancellationToken);
                await writer.WriteAsync(branch.RowNumber, NpgsqlDbType.Integer, cancellationToken);

                var rawDataJson = JsonSerializer.Serialize(branch.RawData);
                await writer.WriteAsync(rawDataJson, NpgsqlDbType.Jsonb, cancellationToken);
            
                await writer.WriteAsync(false, NpgsqlDbType.Boolean, cancellationToken);
                await writer.WriteAsync(false, NpgsqlDbType.Boolean, cancellationToken);
            }
            await writer.CompleteAsync(cancellationToken);
            
            _logger.LogInformation(
                "Bulk inserted {BranchesCount} branches for import {ImportId}",
                branches.Count,
                importId);
            
            return branches.Count;
        } 
        catch (Exception ex)
        {
            _logger.LogError(ex,
                "Error bulk inserting branches for import {ImportId}",
                importId);
            throw;
        }
    }

    public async Task<int> CountByImportIdAsync(
        Guid importId,
        CancellationToken cancellationToken = default
    )
    {
        try
        {
            await using var connection = new NpgsqlConnection(Connection.ConnectionString);
            await connection.OpenAsync(cancellationToken);

            await using var command = new NpgsqlCommand(@"
                SELECT COUNT(*)
                FROM ""Staging"".staging_branches
                WHERE import_id = @importId", connection);

            command.Parameters.AddWithValue("@importId", importId);

            var result = await command.ExecuteScalarAsync(cancellationToken);
            return Convert.ToInt32(result);  
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error counting branches for import {ImportId}", importId);
            throw;
        }
    }

    public async Task<int> GetLastRowNumberAsync(
        Guid importId,
        CancellationToken cancellationToken = default
    )
    {
        try
        {
            await using var connection = new NpgsqlConnection(Connection.ConnectionString);
            await connection.OpenAsync(cancellationToken);

            await using var command = new NpgsqlCommand(@"
                SELECT COALESCE(MAX(row_number), 0)
                FROM ""Staging"".staging_branches
                WHERE import_id = @importId", connection);
            
            command.Parameters.AddWithValue("@importId", importId);

            var result = await command.ExecuteScalarAsync(cancellationToken);
            return Convert.ToInt32(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting last row number for import {ImportId}", importId);
            throw;  
        }
    }
}