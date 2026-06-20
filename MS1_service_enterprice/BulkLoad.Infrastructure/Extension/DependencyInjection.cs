using BulkLoad.Domain.Repositories.Control;
using BulkLoad.Domain.Repositories.Staging;
using BulkLoad.Infrastructure.Persistence.Repositories.Control;
using BulkLoad.Infrastructure.Persistence.Repositories.Staging;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Npgsql;

namespace BulkLoad.Infrastructure.Extension;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructure(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        var connectionString = configuration.GetConnectionString("PostgresConnection")
            ?? throw new InvalidOperationException("PostgresConnection not configured");

        services.AddScoped<NpgsqlConnection>(_ =>
            new NpgsqlConnection(connectionString)
        );
        services.AddScoped<IDataImportRepository, DataImportRepository>();
        services.AddScoped<IStagingBranchRepository, StagingBranchRepository>();

        return services;
    }
}