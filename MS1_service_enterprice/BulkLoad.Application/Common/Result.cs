namespace BulkLoad.Application.Common;

/// <summary>
/// Result pattern para respuesta consistentes
/// </summary>

public class Result<T>
{
    public bool IsSuccess { get; }
    public T? Data { get; }
    public string? ErrorMessage { get; }
    public List<string>? Errors { get; }

    private Result(bool isSuccess, T? data, string? errorMessage, List<string>? errors = null)
    {
        IsSuccess = isSuccess;
        Data = data;
        ErrorMessage = errorMessage;
        Errors = errors ?? new List<string>();
    }

    public static Result<T> Success(T data) => new(true, data, null);
    public static Result<T> Failure(string errorMessage) => new(false, default, errorMessage);
    public static Result<T> Failure(List<string> errors) =>
        new(false, default, "Multiple validation errors", errors);
}

/// <summary>
/// Result sin data (void)
/// </summary>
public class Result
{
    public bool IsSuccess { get; }
    public string? ErrorMessage { get; }
    public List<string>? Errors { get; }

    private Result(bool isSuccess, string? errorMessage, List<string>? errors = null)
    {
        IsSuccess = isSuccess;
        ErrorMessage = errorMessage;
        Errors = errors ?? new List<string>();
    }

    public static Result Success() => new(true, null);
    public static Result Failure(string errorMessage) => new(false, errorMessage);
    public static Result Failure(List<string> errors) =>
        new(false, "Multiple validation errors", errors);
}

