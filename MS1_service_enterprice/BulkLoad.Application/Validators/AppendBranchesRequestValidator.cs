using BulkLoad.Application.DTOs.Requests;
using FluentValidation;

namespace BulkLoad.Application.Validators;

public class AppendBranchesRequestValidator : AbstractValidator<AppendBranchesRequest>
{
    public AppendBranchesRequestValidator()
    {
        RuleFor(x => x.Branches)
            .NotEmpty()
            .WithMessage("Branches cannot be null")
            .NotEmpty()
            .WithMessage("Branches cannot be empty")
            .Must(x => x.Count <= 100000)
            .WithMessage("Branches must have less than 100000 elements");
    }

    public class BranchDataValidator : AbstractValidator<BranchData>
    {
        public BranchDataValidator()
        {
            RuleFor(x => x.CompanyId)
                .NotEmpty()
                .WithMessage("CompanyId is required")
                .MaximumLength(50)
                .WithMessage("ComapnyId cannot exceed 50 characters");
            
            RuleFor(x => x.Name)
                .NotEmpty()
                .WithMessage("Name is required")
                .MaximumLength(255)
                .WithMessage("Name cannot exceed 255 characters");
            
            RuleFor(x => x.Code)
                .MaximumLength(50)
                .When(x => !string.IsNullOrEmpty(x.Code))
                .WithMessage("Code cannot exceed 50 characters");
            
            RuleFor(x => x.Address)
                .MaximumLength(255)
                .When(x => !string.IsNullOrEmpty(x.Address))
                .WithMessage("Address cannot exceed 255 characters");
            
            RuleFor(x => x.City)
                .MaximumLength(100)
                .When(x => !string.IsNullOrEmpty(x.City))
                .WithMessage("City cannot exceed 100 characters");
            
            RuleFor(x => x.Phone)
                .MaximumLength(20)
                .When(x => !string.IsNullOrEmpty(x.Phone))
                .WithMessage("Phone cannot exceed 20 characters");
            
            RuleFor(x => x.IsActive)
                .NotNull()
                .WithMessage("IsActive is required");
        }
    }
     
}