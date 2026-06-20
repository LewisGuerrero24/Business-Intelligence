using BulkLoad.Application.Mapping;
using BulkLoad.Application.UseCases.Imports;
using BulkLoad.Application.Validators;
using FluentValidation;
using Microsoft.Extensions.DependencyInjection;

namespace BulkLoad.Application.Extension;

public static class DependencyInjection
{
    public static IServiceCollection AddApplication(this IServiceCollection services)
    {
        services.AddAutoMapper(typeof(DependencyInjection));
        services.AddValidatorsFromAssembly(typeof(DependencyInjection).Assembly);

        services.AddScoped<CreateImportUseCase>();
        services.AddScoped<AppendBranchesUseCase>();
        services.AddScoped<CompleteImportUseCase>();

        services.AddAutoMapper(typeof(MappingProfile));
        services.AddValidatorsFromAssemblyContaining<AppendBranchesRequestValidator>();
        services.AddValidatorsFromAssemblyContaining<CreateImportRequestValidator>();

        return services;
    }
}