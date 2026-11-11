using Companion.Core;
using Companion.Scenarios;
using System.Text.Json;

var failures = new List<string>();
var count = 0;
void Check(string name, Action test)
{
    count++;
    try { test(); Console.WriteLine($"PASS {name}"); }
    catch (Exception ex) { failures.Add(name); Console.Error.WriteLine($"FAIL {name}: {ex.Message}"); }
}
void Require(bool condition, string message = "Condição não satisfeita")
{ if (!condition) throw new Exception(message); }
Assessment Evaluate(Snapshot snapshot, string code = TacticalEngine.LocalCode) =>
    new TacticalEngine().Analyze(DemoScenarios.Wrap(snapshot)).Assessments.Single(a => a.Code == code);
void Reject(AnalysisDocument doc)
{
    try { new TacticalEngine().Analyze(doc); }
    catch (ArgumentException) { return; }
    throw new Exception("Entrada inválida foi aceita.");
}
Snapshot Scene(int own = 4, int enemy = 10, int distant = 0) => DemoScenarios.Military("test", 600, own, enemy, distant);
Snapshot ChangeFirst(Snapshot scene, Func<UnitState, UnitState> change) => scene with
{ Units = scene.Units.Select((u, i) => i == 0 ? change(u) : u).ToArray() };

Check("inferioridade local e razão conhecida 4/10", () =>
{
    var result = Evaluate(Scene());
    Require(result.Status == EvaluationStatus.Finding);
    Require(Math.Abs(result.Finding!.Metrics.Single(m => m.Name == "localPowerRatio").Value - .4) < 1e-10);
});
Check("forças iguais sem alerta", () => Require(Evaluate(Scene(8, 8)).Status == EvaluationStatus.NoFinding));
Check("superioridade própria sem alerta", () => Require(Evaluate(Scene(12, 4)).Status == EvaluationStatus.NoFinding));
Check("limiar exato não emite inferioridade", () => Require(Evaluate(Scene(8, 10)).Status == EvaluationStatus.NoFinding));
Check("posição ausente impede conclusão enviesada", () => Require(Evaluate(ChangeFirst(Scene(), u => u with { Position = null })).Status == EvaluationStatus.InsufficientEvidence));
Check("posição antiga é rejeitada", () => Require(Evaluate(ChangeFirst(Scene(), u => u with { Position = DemoScenarios.Sim(new Point(50, 50), 590) })).Status == EvaluationStatus.InsufficientEvidence));
Check("posição futura é rejeitada", () => Require(Evaluate(ChangeFirst(Scene(), u => u with { Position = DemoScenarios.Sim(new Point(50, 50), 601) })).Status == EvaluationStatus.InsufficientEvidence));
Check("HP desconhecido é rejeitado", () => Require(Evaluate(ChangeFirst(Scene(), u => u with { HitPoints = new(60, EvidenceOrigin.Unknown, 600) })).Status == EvaluationStatus.InsufficientEvidence));
Check("cobertura incompleta causa abstenção", () =>
{
    var s = Scene();
    Require(Evaluate(s with { Battle = s.Battle! with { VisibleAreaComplete = DemoScenarios.Sim(false, 600) } }).Status == EvaluationStatus.InsufficientEvidence);
});
Check("inimigos ocultos não alteram avaliação", () =>
{
    var s = Scene();
    var hidden = DemoScenarios.Unit(900, 2, 50, 50, 600) with { Knowledge = UnitKnowledge.HiddenEnemy, Position = null };
    var a = Evaluate(s).Finding!;
    var b = Evaluate(s with { Units = s.Units.Append(hidden).ToArray() }).Finding!;
    Require(a.Metrics.SequenceEqual(b.Metrics) && a.UnitIds.SequenceEqual(b.UnitIds));
});
Check("sem inimigo visível não inventa confronto", () => Require(Evaluate(Scene(4, 0)).Status == EvaluationStatus.NoFinding));
Check("bônus de contramedida altera razão", () =>
{
    var s = Scene(4, 10);
    var converted = s with { Units = s.Units.Select(u => DemoScenarios.Unit(u.Id, u.PlayerId,
        u.Position!.Value.X, u.Position.Value.Y, 600, kind: u.PlayerId == 1 ? UnitClass.Spearman : UnitClass.Cavalry)).ToArray() };
    var baseline = Evaluate(s).Finding!.Metrics.Single(m => m.Name == "localPowerRatio").Value;
    var bonus = Evaluate(converted).Finding!.Metrics.Single(m => m.Name == "localPowerRatio").Value;
    Require(bonus > baseline);
});
Check("reduzir HP próprio reduz índice", () =>
{
    var s = Scene();
    var weak = s with { Units = s.Units.Select(u => u.PlayerId == 1 ? u with { HitPoints = DemoScenarios.Sim(15d, 600) } : u).ToArray() };
    var before = Evaluate(s).Finding!.Metrics.Single(m => m.Name == "ownLocalPower").Value;
    var after = Evaluate(weak).Finding!.Metrics.Single(m => m.Name == "ownLocalPower").Value;
    Require(Math.Abs(after / before - .5) < 1e-10);
});
Check("reforços distantes do mesmo grupo geram alerta", () =>
{
    var result = Evaluate(Scene(distant: 8), TacticalEngine.DispersionCode);
    Require(result.Status == EvaluationStatus.Finding);
    Require(result.Finding!.Metrics.Single(m => m.Name == "minimumArrivalSeconds").Value > 40);
});
Check("outro grupo não é tratado como reforço", () =>
{
    var s = Scene(distant: 8);
    s = s with { Units = s.Units.Select(u => u.Id >= 201 ? u with { GroupId = "raiding" } : u).ToArray() };
    Require(Evaluate(s, TacticalEngine.DispersionCode).Status == EvaluationStatus.NoFinding);
});
Check("reforços próximos não geram alerta de atraso", () =>
{
    var s = Scene(distant: 8);
    s = s with { Units = s.Units.Select(u => u.Id >= 201 ? u with { Position = DemoScenarios.Sim(new Point(75, 50), 600) } : u).ToArray() };
    Require(Evaluate(s, TacticalEngine.DispersionCode).Status == EvaluationStatus.NoFinding);
});
Check("velocidade zero não vira tempo infinito", () => Require(Evaluate(ChangeFirst(Scene(), u => u with
{ Profile = DemoScenarios.Sim(u.Profile!.Value with { Speed = 0 }, 600) })).Status == EvaluationStatus.InsufficientEvidence));
Snapshot Economy(EconomyState e) => new("economy", 600, 1, null, Array.Empty<UnitState>(), e);
Check("estoque persistente com capacidade ociosa gera conclusão", () => Require(Evaluate(Economy(DemoScenarios.Economy(600)), TacticalEngine.EconomyCode).Status == EvaluationStatus.Finding));
Check("reserva planejada protege poupança intencional", () => Require(Evaluate(Economy(DemoScenarios.Economy(600, reserve: 1200)), TacticalEngine.EconomyCode).Status == EvaluationStatus.NoFinding));
Check("sem plano explícito motor se abstém", () => Require(Evaluate(Economy(DemoScenarios.Economy(600) with { PlannedReserve = null }), TacticalEngine.EconomyCode).Status == EvaluationStatus.InsufficientEvidence));
Check("capacidade menor que renda não é ociosidade acionável", () => Require(Evaluate(Economy(DemoScenarios.Economy(600, capacity: 4)), TacticalEngine.EconomyCode).Status == EvaluationStatus.NoFinding));
Check("excesso transitório não dispara alerta", () => Require(Evaluate(Economy(DemoScenarios.Economy(600, duration: 10)), TacticalEngine.EconomyCode).Status == EvaluationStatus.NoFinding));
Check("produção ocupada não dispara alerta", () => Require(Evaluate(Economy(DemoScenarios.Economy(600, idle: .1)), TacticalEngine.EconomyCode).Status == EvaluationStatus.NoFinding));
Check("economia antiga não é evidência atual", () => Require(Evaluate(Economy(DemoScenarios.Economy(590)), TacticalEngine.EconomyCode).Status == EvaluationStatus.InsufficientEvidence));
Check("duração maior que partida é inválida", () => Require(Evaluate(Economy(DemoScenarios.Economy(600, duration: 900)), TacticalEngine.EconomyCode).Status == EvaluationStatus.InsufficientEvidence));
Check("IDs repetidos são rejeitados", () =>
{
    var s = Scene(); Reject(DemoScenarios.Wrap(s with { Units = s.Units.Append(s.Units[0]).ToArray() }));
});
Check("jogador incoerente é rejeitado", () => Reject(DemoScenarios.Wrap(ChangeFirst(Scene(), u => u with { PlayerId = 2 }))));
Check("valores não finitos causam abstenção", () => Require(Evaluate(ChangeFirst(Scene(), u => u with { HitPoints = DemoScenarios.Sim(double.NaN, 600) })).Status == EvaluationStatus.InsufficientEvidence));
Check("schema desconhecido é rejeitado", () => Reject(DemoScenarios.Create() with { SchemaVersion = 2 }));
Check("origem desconhecida é rejeitada", () => Reject(DemoScenarios.Create() with { Source = DataSource.Unknown }));
Check("dados simulados não são aceitos como replay", () =>
{
    var report = new TacticalEngine().Analyze(DemoScenarios.Wrap(Scene()) with { Source = DataSource.Replay });
    Require(report.Findings.Length == 0);
    Require(report.Assessments.All(a => a.Status == EvaluationStatus.InsufficientEvidence));
});
Check("mesmo documento produz exatamente o mesmo relatório", () =>
{
    var engine = new TacticalEngine(); var doc = DemoScenarios.Create();
    Require(DocumentJson.Write(engine.Analyze(doc)) == DocumentJson.Write(engine.Analyze(doc)));
});
Check("round-trip JSON preserva conclusões", () =>
{
    var doc = DemoScenarios.Create(); var engine = new TacticalEngine();
    var restored = DocumentJson.Read(DocumentJson.Write(doc));
    Require(DocumentJson.Write(engine.Analyze(doc)) == DocumentJson.Write(engine.Analyze(restored)));
});
Check("ordem de entrada não muda linha do tempo", () =>
{
    var doc = DemoScenarios.Create(); var engine = new TacticalEngine();
    Require(DocumentJson.Write(engine.Analyze(doc)) == DocumentJson.Write(engine.Analyze(doc with { Snapshots = doc.Snapshots.Reverse().ToArray() })));
});
Check("demonstração tem quatro conclusões identificadas como simuladas", () =>
{
    var report = new TacticalEngine().Analyze(DemoScenarios.Create());
    Require(report.Findings.Length == 4);
    Require(report.Findings.All(f => f.Source == DataSource.Simulated && f.Confidence.Contains("Simulada")));
    Require(report.Findings.Select(f => f.TimeSeconds).SequenceEqual(new[] { 600d, 630d, 630d, 840d }));
});
Check("JSON com campo desconhecido é rejeitado", () =>
{
    try { DocumentJson.Read("{\"notAField\": 1}"); }
    catch (JsonException) { return; }
    throw new Exception("Campo desconhecido aceito.");
});
Check("perfil antigo pode omitir tecnologias e causa abstenção", () => Require(Evaluate(ChangeFirst(Scene(), u => u with
{ Profile = u.Profile! with { AtSeconds = 500 } })).Status == EvaluationStatus.InsufficientEvidence));
Check("coordenada omitida no JSON não vira zero", () =>
{
    var json = DocumentJson.Write(DemoScenarios.Wrap(Scene())).Replace("\"x\": 50.1,", "");
    try { DocumentJson.Read(json); }
    catch (JsonException) { return; }
    throw new Exception("Coordenada ausente aceita.");
});
Check("ordem das unidades não muda o resultado matemático", () =>
{
    var s = Scene(distant: 8); var engine = new TacticalEngine();
    Require(DocumentJson.Write(engine.Analyze(DemoScenarios.Wrap(s))) ==
        DocumentJson.Write(engine.Analyze(DemoScenarios.Wrap(s with { Units = s.Units.Reverse().ToArray() }))));
});
Console.WriteLine($"{count - failures.Count}/{count} verificações passaram.");
return failures.Count == 0 ? 0 : 1;
