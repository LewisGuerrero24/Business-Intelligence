namespace BulkLoad.Domain.ValueObjects;

public sealed class ImportStatus : IEquatable<ImportStatus>
{
    public string Value { get; }

    private ImportStatus(string value)
    {
        Value = value;
    }

    // 🔒 Instancias válidas (tipo enum pero mejor)
    public static readonly ImportStatus Pending = new("PENDING");
    public static readonly ImportStatus Uploaded = new("UPLOADED");
    public static readonly ImportStatus Processing = new("PROCESSING");
    public static readonly ImportStatus Completed = new("COMPLETED");
    public static readonly ImportStatus Partial = new("PARTIAL");
    public static readonly ImportStatus Failed = new("FAILED");
    public static readonly ImportStatus Cancelled = new("CANCELLED");

    // 📌 Lista de valores válidos
    private static readonly List<ImportStatus> _all = new()
    {
        Pending, Uploaded, Processing, Completed, Partial, Failed, Cancelled
    };


    // 🔍 Factory segura (para DB o input)
    public static ImportStatus From(string value)
    {
        var status = _all.FirstOrDefault(x => x.Value == value.ToUpper());

        if (status is null)
            throw new ArgumentException($"Invalid ImportStatus: {value}");

        return status;
    }

        public static implicit operator string(ImportStatus status) => status.Value;

    public override string ToString() => Value;

    public override bool Equals(object? obj)
        => obj is ImportStatus other && Value == other.Value;

    public bool Equals(ImportStatus? other)
        => other is not null && Value == other.Value;

    public override int GetHashCode()
        => Value.GetHashCode();

}



// namespace BulkLoad.Domain.ValueObjects;

// public enum ImportStatus
// {
//     Pending,    // Creado, esperando datos
//     Uploaded,   // Datos cargados en staging
//     Processing, // ETL procesando
//     Completed,  // Todo exitoso
//     Partial,    // Algunos errores
//     Failed,     // Falló completamente
//     Cancelled   // Usuario canceló
// }