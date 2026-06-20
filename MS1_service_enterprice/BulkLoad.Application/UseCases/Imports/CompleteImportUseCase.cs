using BulkLoad.Application.Common;
using BulkLoad.Application.DTOs.Requests;
using BulkLoad.Application.DTOs.Responses;
using BulkLoad.Domain.Repositories.Control;
using Microsoft.Extensions.Logging;

namespace BulkLoad.Application.UseCases.Imports;

public class CompleteImportUseCase
{
    private readonly IDataImportRepository _importRepository;
    private readonly ILogger<CompleteImportUseCase> _logger;

    public CompleteImportUseCase(
        IDataImportRepository importRepository,
        ILogger<CompleteImportUseCase> logger)
    {
        _importRepository = importRepository;
        _logger = logger;
    }

    public async Task<Result<CompleteImportResponse>> ExecuteAsync(
        Guid importId,
        CompleteImportRequest request,
        CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Completing upload for import {ImportId}", importId);

        try
        {
            var (success, message, totalStaged, totalExpected) =
                await _importRepository.CompleteUploadAsync(importId, request.Force, cancellationToken);

            if (!success)
                return Result<CompleteImportResponse>.Failure(message);

            return Result<CompleteImportResponse>.Success(new CompleteImportResponse
            {
                ImportId     = importId,
                Status       = "UPLOADED",
                TotalStaged  = totalStaged,
                TotalExpected = totalExpected,
                Message      = message
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error completing import {ImportId}", importId);
            return Result<CompleteImportResponse>.Failure($"Failed to complete import: {ex.Message}");
        }
    }
}