using AutoMapper;
using BulkLoad.Application.DTOs.Requests;
using BulkLoad.Application.DTOs.Responses;
using BulkLoad.Domain.Entities.Control;

namespace BulkLoad.Application.Mapping;

public class MappingProfile : Profile
{
    public MappingProfile()
    {
        // BranchData -> StagingBranchInput
        CreateMap<BranchData, Dictionary<string, object>>()
            .ConvertUsing((src, dest, context) => new Dictionary<string, object>
            {
                { "CompanyId", src.CompanyId},
                { "Name", src.Name},
                { "Code", src.Code ?? string.Empty},
                { "Address", src.Address ?? string.Empty},
                { "City", src.City ?? string.Empty},
                { "Phone", src.Phone ?? string.Empty},
                { "IsActive", src.IsActive}
            });
        
        // DataImport -> CreateImportResponse
        CreateMap<DataImport, CreateImportResponse>()
            .ForMember(dest => dest.Status, opt => opt.MapFrom(src => src.Status.ToString()));
    }
}