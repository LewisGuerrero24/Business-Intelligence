

using AutoMapper;
using BulkLoad.Application.Common;
using BulkLoad.Application.DTOs.Requests;
using BulkLoad.Application.DTOs.Responses;
using BulkLoad.Domain.Entities.Staging;
using BulkLoad.Domain.Repositories.Control;
using BulkLoad.Domain.Repositories.Staging;
using BulkLoad.Domain.ValueObjects;
using FluentValidation;
using Microsoft.Extensions.Logging;

namespace BulkLoad.Application.UseCases.Imports;

public class AppendBranchesUseCase
{
    private readonly IDataImportRepository _importRepository;
    private readonly IStagingBranchRepository _stagingBranchRepository;
    private readonly ILogger<AppendBranchesUseCase> _logger;
    private readonly IValidator<AppendBranchesRequest> _validator;
    private readonly IMapper _mapper;

    public AppendBranchesUseCase(
        IDataImportRepository importRepository,
        IStagingBranchRepository stagingBranchRepository,
        ILogger<AppendBranchesUseCase> logger,
        IValidator<AppendBranchesRequest> validator,
        IMapper mapper
    )
    {
        _importRepository = importRepository;
        _stagingBranchRepository = stagingBranchRepository;
        _logger = logger;
        _validator = validator;
        _mapper = mapper;
    }

    public async Task<Result<AppendBranchesResponse>> ExecuteAsync(
        Guid importId,
        AppendBranchesRequest request,
        CancellationToken cancellationToken = default
    )
    {
        // Validar request
        var validationResult = await _validator.ValidateAsync(request, cancellationToken);
        if (!validationResult.IsValid)
        {
            var errors = validationResult.Errors.Select(e => e.ErrorMessage).ToList();
            return Result<AppendBranchesResponse>.Failure(errors);
        }
                                                                                
        // Verificar import
        var import = await _importRepository.GetByIdAsync(importId, cancellationToken);
        if (import == null)
        {
            return Result<AppendBranchesResponse>.Failure($"Import {importId} not found");
        }

        if (import.Status != ImportStatus.Pending)
        {
            return Result<AppendBranchesResponse>.Failure(
                $"Import is in {import.Status} status. Cannot append data.");
        }

        _logger.LogInformation(
            "Appending {Count} branches to import {ImportId}",
            request.Branches.Count,
            importId);

        try
        {
            var lastRowNumber = await _stagingBranchRepository.GetLastRowNumberAsync(
                importId,
                cancellationToken
            );

            var stagingBranches = request.Branches
                .Select((branch, index) => new StagingBranchInput
                {
                    RowNumber = lastRowNumber + index + 1,
                    RawData = _mapper.Map<Dictionary<string, object>>(branch)
                }).ToList();
            
            var insertedCount = await _stagingBranchRepository.BulkInsertAsync(
                importId,
                stagingBranches,
                cancellationToken
            );

            var totalReceived = await _stagingBranchRepository.CountByImportIdAsync(
                importId,
                cancellationToken
            );

            // await _importRepository.UpdateStatusAsync(
            // importId: importId,
            // status: "Pending", // Mantener en Pending mientras se cargan chunks
            // processedRecords: totalReceived, // ← Actualizar con total acumulado
            // cancellationToken: cancellationToken);

            var progress = import.TotalRecords > 0
                ? (decimal)totalReceived / import.TotalRecords * 100
                : 0;
            
            var response = new AppendBranchesResponse
            {
                ImportId = importId,
                ChuckReceived = insertedCount,
                TotalReceived = totalReceived,
                TotalExpected = import.TotalRecords,
                Progress = Math.Round(progress, 2)
            };
            
            return Result<AppendBranchesResponse>.Success(response);
            
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error appending branches to import {ImportId}", importId);
            return Result<AppendBranchesResponse>.Failure($"Failed to append branches: {ex.Message}");
        }


    }
}