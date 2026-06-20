namespace BulkLoad.Application.Common;

/// <summary>
/// Respuesta base estandarizada para todos los endpoints
/// </summary>

public class ApiResponse<T>
{
    public bool Success { get; set; }
    public T? Data { get; set; }
    public string? Message { get; set; }
    public List<string>? Errors { get; set; } = new();
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;

    public static ApiResponse<T> SuccessResponse(T data, string? message = null)
    {
        return new ApiResponse<T>
        {
            Success = true,
            Data = data,
            Message = message ?? "Request completed successfully"  
        };
    }

    public static ApiResponse<T> FailureResponse(string errorMessage)
    {
        return new ApiResponse<T>
        {
            Success = false,
            Errors = new List<string> { errorMessage },
        };
    }

    public static ApiResponse<T> FailureResponse(List<string> errors)
    {
        return new ApiResponse<T>
        {
            Success = false,
            Errors = errors,
        };
    }
}