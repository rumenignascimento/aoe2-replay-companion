using System.Text.Json;
using System.Text.Json.Serialization;
namespace Companion.Core;

public static class DocumentJson
{
    public static JsonSerializerOptions Options { get; } = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true,
        WriteIndented = true,
        RespectRequiredConstructorParameters = true,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        Converters = { new JsonStringEnumConverter(allowIntegerValues: false) }
    };
    public static AnalysisDocument Read(string json) =>
        JsonSerializer.Deserialize<AnalysisDocument>(json, Options)
        ?? throw new JsonException("Documento vazio.");
    public static string Write<T>(T document) => JsonSerializer.Serialize(document, Options);
}
