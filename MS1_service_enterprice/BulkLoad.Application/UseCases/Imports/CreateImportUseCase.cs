using Microsoft.Extensions.Logging;
using BulkLoad.Domain.Repositories.Control;
using BulkLoad.Application.DTOs.Responses;
using BulkLoad.Application.DTOs.Requests;
using BulkLoad.Domain.Entities.Control;
using AutoMapper;
using FluentValidation;
using BulkLoad.Application.Common;

namespace BulkLoad.Application.UseCases.Imports;

public class CreateImportUseCase
{
    private readonly IDataImportRepository _importRepository;
    private readonly ILogger<CreateImportUseCase> _logger;
    private readonly IMapper _mapper;
    private readonly IValidator<CreateImportRequest> _validator;

    public CreateImportUseCase(
        IDataImportRepository importRepository,
        ILogger<CreateImportUseCase> logger,
        IMapper mapper,
        IValidator<CreateImportRequest> validator
    )
    {
        _importRepository = importRepository;
        _logger = logger;
        _mapper = mapper;
        _validator = validator;
    }

    public async Task<Result<CreateImportResponse>> ExecuteAsync(
        CreateImportRequest request,
        Guid userId,
        CancellationToken cancellationToken = default
    )
    {
        // Validar request con FluentValidation
        var validationResult = await _validator.ValidateAsync(request, cancellationToken);
        if (!validationResult.IsValid)
        {
            var errors = validationResult.Errors.Select(e => e.ErrorMessage).ToList();
            _logger.LogWarning("Validation failed for CreateImport: {Errors}", string.Join(", ", errors));
            return Result<CreateImportResponse>.Failure(errors);
        }

        _logger.LogInformation(
            "Creating import for company {CompanyId} with type {ImportType}",
            request.CompanyId,
            request.ImportType);
        
        
        try
        {
            var import = DataImport.CreateFromApi(
                companyId: request.CompanyId,
                importType: request.ImportType,
                totalRecords: request.TotalRecords,
                sourceType: request.SourceType,
                createdBy: userId
            );

            var importId = await _importRepository.CreateAsync(import, cancellationToken);

            var response = new CreateImportResponse
            {
                ImportId = importId,
                Status = "Pending",
                Message = "Import created successfully. Ready to receive data."
            };

            _logger.LogInformation("Import {ImportId} created successfully", importId);

            return Result<CreateImportResponse>.Success(response);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error creating import");
            return Result<CreateImportResponse>.Failure($"Failed to create import: {ex.Message}");
        }
    }
        


}