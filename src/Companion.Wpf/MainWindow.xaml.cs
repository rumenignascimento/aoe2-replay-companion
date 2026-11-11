using System.ComponentModel;
using System.Globalization;
using System.Runtime.CompilerServices;
using System.Text.Json;
using System.Windows;
using Microsoft.Win32;
using Companion.Core;
using Companion.Scenarios;

namespace Companion.Wpf;
public partial class MainWindow : Window, INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;
    private AnalysisReport? report;
    private Finding? selected;
    public Finding[] Findings => report?.Findings ?? Array.Empty<Finding>();
    public string DatasetLabel { get; private set; } = "";
    public string Diagnostics { get; private set; } = "";
    public string Status { get; private set; } = "";
    public Finding? SelectedFinding
    {
        get => selected;
        set { selected = value; Notify(); Notify(nameof(SelectedDetails)); }
    }
    public string SelectedDetails => selected is null ? "Selecione uma conclusão." :
        $"Código: {selected.Code}\nInstante: {selected.TimeLabel} | Jogador: {selected.PlayerId}\nEstado: {selected.SnapshotId}\nUnidades: {string.Join(", ", selected.UnitIds)}\n\n"
        + string.Join("\n", selected.Metrics.Select(m => $"{m.Name}: {m.Value.ToString("0.00", CultureInfo.InvariantCulture)} {m.Unit}"));
    public MainWindow()
    {
        InitializeComponent();
        DataContext = this;
        Analyze(DemoScenarios.Create());
    }
    private void Notify([CallerMemberName] string? property = null) => PropertyChanged?.Invoke(this, new(property));
    private void Analyze(AnalysisDocument document)
    {
        var next = new TacticalEngine().Analyze(document);
        report = next;
        DatasetLabel = $"{document.DatasetId} | Fonte: {document.Source} | Perspectiva: {document.Perspective}. "
            + (document.Source == DataSource.Simulated ? "DADOS SIMULADOS — sem validação em replay real." : "Estados fornecidos por JSON; origem declarada pelo fornecedor dos dados.");
        var missing = next.Assessments.Count(a => a.Status == EvaluationStatus.InsufficientEvidence);
        Diagnostics = string.Join("\n\n", next.Assessments.Select(a => $"{TimeSpan.FromSeconds(a.TimeSeconds):hh\\:mm\\:ss} | {a.Code} | {a.Status}\n{a.Reason}"));
        Status = $"{Findings.Length} conclusões; {missing} avaliações sem evidência suficiente. Selecionar mostra o estado; reprodução de replay ainda não implementada.";
        SelectedFinding = Findings.FirstOrDefault();
        Notify(nameof(Findings)); Notify(nameof(DatasetLabel)); Notify(nameof(Diagnostics)); Notify(nameof(Status));
    }
    private void LoadDemo(object sender, RoutedEventArgs e) => Analyze(DemoScenarios.Create());
    private void OpenDocument(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog { Filter = "Estados de análise JSON (*.json)|*.json", Title = "Abrir estados — não aceita .aoe2record" };
        if (dialog.ShowDialog() != true) return;
        try { Analyze(DocumentJson.Read(System.IO.File.ReadAllText(dialog.FileName))); }
        catch (Exception ex) when (ex is System.IO.IOException or UnauthorizedAccessException or JsonException or ArgumentException)
        { MessageBox.Show(this, ex.Message, "Documento não carregado", MessageBoxButton.OK, MessageBoxImage.Warning); }
    }
    private void ExportReport(object sender, RoutedEventArgs e)
    {
        if (report is null) return;
        var dialog = new SaveFileDialog { Filter = "Relatório JSON (*.json)|*.json", FileName = "companion-report.json" };
        if (dialog.ShowDialog() != true) return;
        try { System.IO.File.WriteAllText(dialog.FileName, DocumentJson.Write(report)); }
        catch (Exception ex) when (ex is System.IO.IOException or UnauthorizedAccessException)
        { MessageBox.Show(this, ex.Message, "Falha ao exportar", MessageBoxButton.OK, MessageBoxImage.Warning); }
    }
}
