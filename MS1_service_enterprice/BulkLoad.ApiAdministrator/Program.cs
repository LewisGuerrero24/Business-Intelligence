using BulkLoad.Infrastructure.Extension;
using BulkLoad.Application.Extension;
using FluentValidation.AspNetCore;
using Microsoft.AspNetCore.Http.Features;
using BulkLoad.ApiAdministrator.Middleware;

var builder = WebApplication.CreateBuilder(args);


// // ========================================
// // SERILOG CONFIGURATION
// // ========================================
// Log.Logger = new LoggerConfiguration()
//     .ReadFrom.Configuration(builder.Configuration)
//     .Enrich.FromLogContext()
//     .WriteTo.Console()
//     .WriteTo.File("logs/bulkload-.txt", rollingInterval: RollingInterval.Day)
//     .CreateLogger();

// builder.Host.UseSerilog();


// Infrastructure
builder.Services.AddInfrastructure(builder.Configuration);
builder.Services.AddApplication();

builder.Services.AddFluentValidationAutoValidation();
builder.Services.AddFluentValidationClientsideAdapters();

builder.Services.AddControllers();
builder.Services.AddOpenApi();

// ========================================
// FILE UPLOAD LIMITS
// ========================================
builder.Services.Configure<FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = 2147483648; // 2GB
});

builder.WebHost.ConfigureKestrel(options =>
{
    options.Limits.MaxRequestBodySize = 2147483648;
});

// // ========================================
// // CORS
// // ========================================
// builder.Services.AddCors(options =>
// {
//     options.AddPolicy("AllowAll", policy =>
//     {
//         policy.AllowAnyOrigin()
//               .AllowAnyMethod()
//               .AllowAnyHeader();
//     });
// });


builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var app = builder.Build();

app.UseRequestLogging(); // Log todas las request
app.UseGlobalExceptionHandling(); // Maneja todos los errores


//app.UseMiddleware<ExceptionMiddleware>();

app.UseSwagger();
app.UseSwaggerUI();

app.UseHttpsRedirection();
//app.UseCors("AllowAll");
app.MapControllers();

app.Run();


