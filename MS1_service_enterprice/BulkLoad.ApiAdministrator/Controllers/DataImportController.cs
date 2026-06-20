
using BulkLoad.Application.Common;
using BulkLoad.Application.DTOs.Requests;
using BulkLoad.Application.DTOs.Responses;
using BulkLoad.Application.UseCases.Imports;
using Microsoft.AspNetCore.Mvc;

namespace BulkLoad.ApiAdministrator.Controllers;

[ApiController]
[Route("api/v1/imports")]
[Tags("Data Import")]
[Produces("application/json")]
public class DataImportController : ControllerBase
{
    private readonly CreateImportUseCase _createImportUseCase;
    private readonly AppendBranchesUseCase _appendBranchesUseCase;
    private readonly CompleteImportUseCase _completeImportUseCase;
    private readonly ILogger<DataImportController> _logger;

    public DataImportController(CreateImportUseCase createImportUseCase, AppendBranchesUseCase appendBranchesUseCase, CompleteImportUseCase completeImportUseCase, ILogger<DataImportController> logger)
    {
        _createImportUseCase = createImportUseCase;
        _appendBranchesUseCase = appendBranchesUseCase;
        _completeImportUseCase = completeImportUseCase;
        _logger = logger;
    }



    /// <summary>
    /// Create a new import for bulk data loading
    /// </summary>
    /// <remarks>
    /// Step 1 of the chunked upload process. Creates an import container that will receive data chunks.
    /// </remarks>
    [HttpPost("create")]
    [ProducesResponseType(typeof(ApiResponse<CreateImportResponse>), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ApiResponse<object>), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> CreateImport(
        [FromBody] CreateImportRequest request,
        CancellationToken cancellationToken)
    {
        var userId = GetCurrentUserId();

        var result = await _createImportUseCase.ExecuteAsync(
            request,
            userId,
            cancellationToken);

        if (!result.IsSuccess)
        {
            return BadRequest(ApiResponse<object>.FailureResponse(result.Errors));
        }

        return Created(
            $"/api/v1/imports/{result.Data!.ImportId}/status",
            ApiResponse<CreateImportResponse>.SuccessResponse(result.Data));
    }










    /// <summary>
    /// Append branch data to an existing import
    /// </summary>
    /// <remarks>
    /// Step 2 of chunked upload. Can be called multiple times until all data is uploaded.
    /// Maximum 100,000 records per request.
    /// </remarks>
    [HttpPost("{importId:guid}/branches/append")]
    [ProducesResponseType(typeof(ApiResponse<AppendBranchesResponse>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object>), StatusCodes.Status404NotFound)]
    [ProducesResponseType(typeof(ApiResponse<object>), StatusCodes.Status400BadRequest)]
    public async Task<IActionResult> AppendBranches(
        [FromRoute] Guid importId,
        [FromBody] AppendBranchesRequest request,
        CancellationToken cancellationToken)
    {
        var result = await _appendBranchesUseCase.ExecuteAsync(
            importId,
            request,
            cancellationToken);

        if (!result.IsSuccess)
        {
            if (result.ErrorMessage?.Contains("not found") == true)
            {
                return NotFound(ApiResponse<object>.FailureResponse(result.ErrorMessage));
            }

            return BadRequest(ApiResponse<object>.FailureResponse(result.Errors));
        }

        return Ok(ApiResponse<AppendBranchesResponse>.SuccessResponse(result.Data!));
    }

    /// <summary>
    /// TESTING ONLY: Generate and append random branch data
    /// </summary>
    /// <remarks>
    /// Development endpoint to easily test bulk imports without manually creating JSON.
    /// Generates random branch data for the specified count.
    /// </remarks>
    // [HttpPost("{importId:guid}/branches/append/test")]
    // [ProducesResponseType(typeof(ApiResponse<AppendBranchesResponse>), StatusCodes.Status200OK)]
    // public async Task<IActionResult> AppendBranchesTest(
    //     [FromRoute] Guid importId,
    //     [FromQuery] int count = 10000,
    //     CancellationToken cancellationToken = default)
    // {
    //     if (count > 100000)
    //     {
    //         return BadRequest(ApiResponse<object>.FailureResponse(
    //             "Count cannot exceed 100,000"));
    //     }

    //     var branches = Enumerable.Range(1, count)
    //         .Select(i => new BranchData
    //         {
    //             CompanyId = string.Empty,
    //             Name = $"Test Branch {i}",
    //             Code = $"TB{i:D6}",
    //             Address = $"Test Address {i}",
    //             City = "Test City",
    //             Phone = $"+57 300 {i:D7}",
    //             IsActive = true
    //         })
    //         .ToList();

    //     var request = new AppendBranchesRequest { Branches = branches };

    //     return await AppendBranches(importId, request, cancellationToken);
    // }

    private Guid GetCurrentUserId()
    {
        // TODO: Extraer del JWT cuando implementes autenticación
        return Guid.Parse("00000000-0000-0000-0000-000000000001");
    }

    /// <summary>
    /// Complete the upload phase of an import
    /// </summary>
    /// <remarks>
    /// Step 3: Call this after sending all data chunks.
    /// Changes status from PENDING to UPLOADED and validates record counts.
    /// Use force=true if the total was unknown at import creation (API source).
    /// </remarks>
    [HttpPost("{importId:guid}/complete")]
    [ProducesResponseType(typeof(ApiResponse<CompleteImportResponse>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object>), StatusCodes.Status404NotFound)]
    public async Task<IActionResult> CompleteImport(
        [FromRoute] Guid importId,
        [FromBody] CompleteImportRequest request,
        CancellationToken cancellationToken)
    {
        var result = await _completeImportUseCase.ExecuteAsync(importId, request, cancellationToken);

        if (!result.IsSuccess)
        {
            if (result.ErrorMessage?.Contains("not found") == true)
                return NotFound(ApiResponse<object>.FailureResponse(result.ErrorMessage!));

            return BadRequest(ApiResponse<object>.FailureResponse(result.Errors!));
        }

        return Ok(ApiResponse<CompleteImportResponse>.SuccessResponse(result.Data!));
    }
}


