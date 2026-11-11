using Companion.Core;
using Companion.Scenarios;
using System.Text.Json;

try
{
    if (args.Length == 2 && args[0] == "--write-demo")
    {
        File.WriteAllText(args[1], DocumentJson.Write(DemoScenarios.Create()));
        Console.WriteLine($"Cenários simulados gravados em {args[1]}");
        return 0;
    }
    if (args.Length > 1 || (args.Length == 1 && args[0].StartsWith('-') && args[0] != "--demo"))
    {
        Console.Error.WriteLine("Uso: Companion.Cli [--demo | documento.json] ou --write-demo arquivo.json");
        return 2;
    }
    var document = args.Length == 0 || args[0] == "--demo"
        ? DemoScenarios.Create() : DocumentJson.Read(File.ReadAllText(args[0]));
    var report = new TacticalEngine().Analyze(document);
    Console.WriteLine(DocumentJson.Write(report));
    return 0;
}
catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException or ArgumentException)
{
    Console.Error.WriteLine($"Não foi possível analisar: {ex.Message}");
    return 1;
}
