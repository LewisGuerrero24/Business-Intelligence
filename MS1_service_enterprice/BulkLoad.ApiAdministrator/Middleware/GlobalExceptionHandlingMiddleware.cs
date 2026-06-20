using BulkLoad.Application.Common;
using System.Net;
using System.Text.Json;

namespace BulkLoad.ApiAdministrator.Middleware;

public class GlobalExceptionHandlingMiddleware
{
    private readonly RequestDelegate _next;
    private readonly ILogger<GlobalExceptionHandlingMiddleware> _logger;

    public GlobalExceptionHandlingMiddleware(
        RequestDelegate next,
        ILogger<GlobalExceptionHandlingMiddleware> logger
    )
    {
        _next = next;
        _logger = logger;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        try
        {
            await _next(context);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unhandled exception occurred");
            await HandleExceptionAsync(context, ex);
        }
    }

    private static async Task HandleExceptionAsync(HttpContext context, Exception exception)
    {
        context.Response.ContentType = "application/json";

        var response = exception switch
        {
            ArgumentException => CreateErrorResponse(
                HttpStatusCode.BadRequest,
                exception.Message
            ),

            KeyNotFoundException => CreateErrorResponse(
                HttpStatusCode.NotFound,
                exception.Message
            ),
            
            InvalidOperationException => CreateErrorResponse(
                HttpStatusCode.BadRequest,
                exception.Message
            ),
            
            UnauthorizedAccessException => CreateErrorResponse(
                HttpStatusCode.Unauthorized,
                "Unauthorized access"
            ),

            _=> CreateErrorResponse(
                HttpStatusCode.InternalServerError,
                "Internal server error"
            )
        };

        context.Response.StatusCode = (int)response.StatusCode;

        var jsonResponse = JsonSerializer.Serialize(response.ApiResponse, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        });

        await context.Response.WriteAsync(jsonResponse);
    }


    private static (HttpStatusCode StatusCode, ApiResponse<object> ApiResponse) CreateErrorResponse(
        HttpStatusCode statusCode,
        string message)
    {
        return (statusCode, ApiResponse<object>.FailureResponse(message));
    }

}

public static class GlobalExceptionHandlingMiddlewareExtensions
{
    public static IApplicationBuilder UseGlobalExceptionHandling(this IApplicationBuilder app)
    {
        return app.UseMiddleware<GlobalExceptionHandlingMiddleware>();
    }
}
