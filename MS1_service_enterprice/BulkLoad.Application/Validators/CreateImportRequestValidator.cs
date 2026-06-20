using System.Data;
using BulkLoad.Application.DTOs.Requests;
using FluentValidation;

namespace BulkLoad.Application.Validators;

public class CreateImportRequestValidator : AbstractValidator<CreateImportRequest>
{
    public CreateImportRequestValidator()
    {
        RuleFor(x => x.CompanyId)
            .NotEmpty()
            .WithMessage("CompanyId is required");

        RuleFor(x => x.ImportType)
            .NotEmpty()
            .WithMessage("ImportType is required")
            .MaximumLength(50)
            .WithMessage("ImportType must be less than 50 characters")
            .Must(BeValidImportType)
            .WithMessage("ImportType must be one of: branches, products, customers, suppliers, sales, purchases");

        RuleFor(x => x.SourceType)
            .NotEmpty()
            .WithMessage("SourceType is required")
            .Must(BeValidSourceType)
            .WithMessage("SourceType must be one of: api, excel, csv, manual");
        
        RuleFor(x => x.TotalRecords)
            .GreaterThan(0)
            .When(x => x.TotalRecords > 0)
            .WithMessage("TotalRecords must be greater than 0");
    
    }


    private bool BeValidImportType(string importType)
    {
        var validTypes = new[] { "branches", "products", "customers", "suppliers", "sales", "purchases" };
        return validTypes.Contains(importType.ToLowerInvariant());
    }

    private bool BeValidSourceType(string sourceType)
    {
        var validTypes = new[] { "api", "excel", "csv", "manual" };
        return validTypes.Contains(sourceType.ToLowerInvariant());
    }
}