using System.Globalization;
namespace Companion.Core;

public sealed class TacticalEngine
{
    public const string LocalCode = "TACTICAL_LOCAL_INFERIORITY";
    public const string DispersionCode = "TACTICAL_DELAYED_REINFORCEMENTS";
    public const string EconomyCode = "STRATEGIC_IDLE_CAPACITY";
    private readonly AnalysisOptions options;
    public TacticalEngine(AnalysisOptions? options = null)
    {
        this.options = options ?? new();
        this.options.Validate();
    }

    public AnalysisReport Analyze(AnalysisDocument document)
    {
        Validate(document);
        var assessments = new List<Assessment>();
        foreach (var snapshot in document.Snapshots.OrderBy(s => s.TimeSeconds)
            .ThenBy(s => s.Id, StringComparer.Ordinal))
        {
            EvaluateMilitary(document, snapshot, assessments);
            assessments.Add(EvaluateEconomy(document, snapshot));
        }
        return new(document.DatasetId, document.Source, assessments.ToArray());
    }

    private static void Validate(AnalysisDocument document)
    {
        ArgumentNullException.ThrowIfNull(document);
        if (document.SchemaVersion != 1 || string.IsNullOrWhiteSpace(document.DatasetId)
            || !Enum.IsDefined(document.Source) || document.Source == DataSource.Unknown
            || !Enum.IsDefined(document.Perspective) || document.Perspective == Perspective.Unknown
            || document.Snapshots is null)
            throw new ArgumentException("Documento requer schemaVersion=1, datasetId, source e perspective explícitos.");
        if (document.Snapshots.Any(s => s is null || string.IsNullOrWhiteSpace(s.Id)
            || !double.IsFinite(s.TimeSeconds) || s.TimeSeconds < 0 || s.PlayerId <= 0
            || s.Units is null || s.Units.Any(u => u is null || u.Id <= 0 || u.PlayerId <= 0
                || !Enum.IsDefined(u.Knowledge)
                || (u.Knowledge == UnitKnowledge.Owned && u.PlayerId != s.PlayerId)
                || (u.Knowledge == UnitKnowledge.VisibleEnemy && u.PlayerId == s.PlayerId))
            || s.Units.Select(u => u.Id).Distinct().Count() != s.Units.Length)
            || document.Snapshots.Select(s => s.Id).Distinct(StringComparer.Ordinal).Count() != document.Snapshots.Length)
            throw new ArgumentException("Instantes, jogadores e IDs devem ser válidos; IDs não podem se repetir no mesmo estado.");
    }

    private bool Reliable<T>(Evidence<T>? evidence, AnalysisDocument doc, Snapshot s, bool dynamic = true)
    {
        return evidence is not null && evidence.Value is not null && Enum.IsDefined(evidence.Origin)
            && evidence.Origin != EvidenceOrigin.Unknown
            && (evidence.Origin != EvidenceOrigin.Simulated || doc.Source == DataSource.Simulated)
            && double.IsFinite(evidence.AtSeconds) && evidence.AtSeconds >= 0
            && evidence.AtSeconds <= s.TimeSeconds
            && (!dynamic || s.TimeSeconds - evidence.AtSeconds <= options.MaximumEvidenceAgeSeconds);
    }
    private static bool ValidPoint(Point p) => double.IsFinite(p.X) && double.IsFinite(p.Y) && p.X >= 0 && p.Y >= 0;
    private bool ValidUnit(UnitState u, AnalysisDocument doc, Snapshot s) =>
        Reliable(u.Position, doc, s) && ValidPoint(u.Position!.Value)
        && Reliable(u.HitPoints, doc, s) && double.IsFinite(u.HitPoints!.Value) && u.HitPoints.Value > 0
        && Reliable(u.Profile, doc, s) && ValidProfile(u.Profile!.Value);
    private static bool ValidProfile(CombatProfile p) => Enum.IsDefined(p.Class) && Enum.IsDefined(p.DamageKind)
        && double.IsFinite(p.Attack) && p.Attack >= 0
        && double.IsFinite(p.ReloadSeconds) && p.ReloadSeconds > 0
        && double.IsFinite(p.Speed) && p.Speed > 0 && double.IsFinite(p.Range) && p.Range >= 0
        && double.IsFinite(p.MeleeArmor) && p.MeleeArmor >= 0
        && double.IsFinite(p.RangedArmor) && p.RangedArmor >= 0
        && (p.BonusDamage is null || p.BonusDamage.All(kv => Enum.IsDefined(kv.Key) && double.IsFinite(kv.Value) && kv.Value >= 0));

    // A Lanchester-inspired index, not a probability or prediction of combat outcome.
    // Equal weighting of eligible target units is an explicit simplifying assumption.
    private static double UnitPower(UnitState unit, UnitState[] targets)
    {
        var p = unit.Profile!.Value;
        double AverageDps() => targets.Average(t =>
        {
            var target = t.Profile!.Value;
            var armor = p.DamageKind == DamageKind.Melee ? target.MeleeArmor : target.RangedArmor;
            var bonus = p.BonusDamage?.GetValueOrDefault(target.Class) ?? 0;
            return Math.Max(1, p.Attack + bonus - armor) / p.ReloadSeconds;
        });
        return Math.Sqrt(unit.HitPoints!.Value * AverageDps());
    }
    private static double Power(UnitState[] units, UnitState[] targets) => units.Sum(u => UnitPower(u, targets));
    // Numerical tolerance prevents a mathematically equal ratio crossing a threshold.
    private static bool Below(double value, double threshold) => value < threshold - 1e-9;
    private static string Number(double n) => n.ToString("0.00", CultureInfo.InvariantCulture);
    private static Assessment None(string code, Snapshot s, string reason, bool missing = false) =>
        new(code, s.Id, s.TimeSeconds, missing ? EvaluationStatus.InsufficientEvidence : EvaluationStatus.NoFinding, reason, null);

    private void EvaluateMilitary(AnalysisDocument doc, Snapshot s, List<Assessment> results)
    {
        void Abstain(string reason)
        {
            results.Add(None(LocalCode, s, reason, true));
            results.Add(None(DispersionCode, s, reason, true));
        }
        var battle = s.Battle;
        if (battle is null || string.IsNullOrWhiteSpace(battle.GroupId)
            || !Reliable(battle.Center, doc, s) || !ValidPoint(battle.Center!.Value)
            || !Reliable(battle.VisibleAreaComplete, doc, s) || !battle.VisibleAreaComplete!.Value)
        {
            Abstain("Faltam centro, grupo ou cobertura confirmada da área visível no instante avaliado.");
            return;
        }
        var own = s.Units.Where(u => u.PlayerId == s.PlayerId && u.Knowledge == UnitKnowledge.Owned
            && u.GroupId == battle.GroupId).OrderBy(u => u.Id).ToArray();
        var visible = s.Units.Where(u => u.PlayerId != s.PlayerId && u.Knowledge == UnitKnowledge.VisibleEnemy).OrderBy(u => u.Id).ToArray();
        // Never silently drop unreliable participants: doing so would bias the ratio.
        if (own.Length == 0 || own.Concat(visible).Any(u => !ValidUnit(u, doc, s)))
        {
            Abstain("Faltam unidades próprias ou posição, HP ou perfil confiável de participantes conhecidos.");
            return;
        }
        var center = battle.Center.Value;
        var local = own.Where(u => u.Position!.Value.DistanceTo(center) <= options.LocalRadius).ToArray();
        var enemies = visible.Where(u => u.Position!.Value.DistanceTo(center) <= options.LocalRadius).ToArray();
        if (local.Length == 0 || enemies.Length == 0)
        {
            results.Add(None(LocalCode, s, "Sem dois grupos locais visíveis para comparar."));
            results.Add(None(DispersionCode, s, "Sem confronto local visível para contextualizar reforços."));
            return;
        }
        var ownPower = Power(local, enemies);
        var enemyPower = Power(enemies, local);
        var wholePower = Power(own, enemies);
        var ratio = ownPower / enemyPower;
        if (!double.IsFinite(ownPower) || !double.IsFinite(enemyPower) || !double.IsFinite(wholePower) || !double.IsFinite(ratio)) { Abstain("Índice de força fora da faixa numérica válida."); return; }
        var participants = local.Concat(enemies).ToArray();
        var metrics = new[] { new Metric("ownLocalPower", Power(local, enemies), "index"),
            new Metric("enemyLocalPower", Power(enemies, local), "index"), new Metric("localPowerRatio", ratio, "ratio") };
        var evidence = new[] { $"{local.Length} unidades próprias e {enemies.Length} inimigas visíveis no raio de {options.LocalRadius} quadrados.",
            "Índice = soma de sqrt(HP atual × DPS médio contra a composição oposta).",
            "Sem simulação de caminho, foco de fogo, projéteis ou resultado da batalha." };
        results.Add(Below(ratio, options.InferiorityRatio)
            ? Hit(doc, s, LocalCode, "Superioridade militar local", participants,
                $"O grupo tem índice de força local {Number(ratio)} em relação ao inimigo visível. Considere reunir tropas ou evitar a troca imediata.", metrics, evidence)
            : None(LocalCode, s, "A razão de força não cruza o limiar de inferioridade."));

        var delayed = own.Where(u => Math.Max(0, u.Position!.Value.DistanceTo(center) - options.LocalRadius)
            / u.Profile!.Value.Speed > options.ReinforcementDelaySeconds).ToArray();
        var fraction = delayed.Sum(u => UnitPower(u, enemies)) / Power(own, enemies);
        if (delayed.Length > 0 && fraction >= options.DistantPowerFraction && Below(ratio, 1))
        {
            var fastest = delayed.Min(u => Math.Max(0, u.Position!.Value.DistanceTo(center) - options.LocalRadius) / u.Profile!.Value.Speed);
            results.Add(Hit(doc, s, DispersionCode, "Concentração do exército", own.Concat(enemies).ToArray(),
                $"{delayed.Length} unidades do mesmo grupo estão a pelo menos {Number(fastest)} s da área local, em estimativa sem obstáculos. O grupo local está em inferioridade; considere concentrar as tropas.",
                metrics.Concat(new[] { new Metric("delayedPowerFraction", fraction, "fraction"),
                    new Metric("minimumArrivalSeconds", fastest, "seconds") }).ToArray(),
                evidence.Concat(new[] { "Reforços pertencem ao mesmo grupo explícito. Distância em linha reta até a borda do raio ÷ velocidade; não comprova intenção de reforçar." }).ToArray()));
        }
        else results.Add(None(DispersionCode, s, "Atraso, fração de força distante ou inferioridade local não cruzam os limiares."));
    }

    private Assessment EvaluateEconomy(AnalysisDocument doc, Snapshot s)
    {
        var e = s.Economy;
        if (e is null || !Reliable(e.Stock, doc, s) || !Reliable(e.PlannedReserve, doc, s)
            || !Reliable(e.IncomePerSecond, doc, s) || !Reliable(e.AffordableSpendCapacityPerSecond, doc, s)
            || !Reliable(e.IdleProductionFraction, doc, s) || !Reliable(e.SustainedExcessSeconds, doc, s))
            return None(EconomyCode, s, "Faltam estoque, reserva planejada, renda, capacidade acessível, ociosidade ou duração do excesso.", true);
        var stock = e.Stock!.Value; var reserve = e.PlannedReserve!.Value;
        var income = e.IncomePerSecond!.Value; var capacity = e.AffordableSpendCapacityPerSecond!.Value;
        var idle = e.IdleProductionFraction!.Value; var duration = e.SustainedExcessSeconds!.Value;
        if (!stock.IsValid || !reserve.IsValid || !double.IsFinite(income) || income < 0
            || !double.IsFinite(capacity) || capacity < 0 || !double.IsFinite(idle) || idle < 0 || idle > 1
            || !double.IsFinite(duration) || duration < 0 || duration > s.TimeSeconds)
            return None(EconomyCode, s, "Valores econômicos inválidos.", true);
        var excess = stock.ExcessBeyond(reserve);
        if (!double.IsFinite(excess))
            return None(EconomyCode, s, "Excesso econômico fora da faixa numérica válida.", true);
        if (excess < options.ExcessStockThreshold || duration < options.ExcessDurationSeconds
            || capacity <= income || idle < options.MinimumIdleFraction)
            return None(EconomyCode, s, "Sem excesso persistente com capacidade acessível ociosa acima da renda.");
        return Hit(doc, s, EconomyCode, "Uso da capacidade econômica", Array.Empty<UnitState>(),
            $"Há {Number(excess)} recursos acima da reserva planejada há {Number(duration)} s, com produção ociosa e capacidade de gasto superior à renda. Considere usar a capacidade disponível conforme seu plano.",
            new[] { new Metric("excessResources", excess, "resources"), new Metric("sustainedExcessSeconds", duration, "seconds"),
                new Metric("incomePerSecond", income, "resources/second"), new Metric("affordableSpendCapacityPerSecond", capacity, "resources/second"),
                new Metric("idleProductionFraction", idle, "fraction") },
            new[] { "Reserva planejada explícita por recurso; estoque sozinho não comprova erro.",
                "Capacidade deve descontar custos inacessíveis, população bloqueada e produção indisponível.",
                "Persistência do excesso é fornecida pelo adaptador com histórico; não é inferida de um único estoque." });
    }

    private static Assessment Hit(AnalysisDocument doc, Snapshot s, string code, string theme,
        UnitState[] units, string message, Metric[] metrics, string[] evidence)
    {
        var finding = new Finding(code, theme, s.Id, s.TimeSeconds, s.PlayerId, doc.Source,
            doc.Source == DataSource.Simulated ? "Simulada — heurística não calibrada" : "Heurística — não é probabilidade",
            message, metrics, evidence, units.Select(u => u.Id).Distinct().Order().ToArray());
        return new(code, s.Id, s.TimeSeconds, EvaluationStatus.Finding, message, finding);
    }
}
