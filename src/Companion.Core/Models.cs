namespace Companion.Core;

public enum EvidenceOrigin { Unknown, Observed, Reconstructed, Simulated }
public enum DataSource { Unknown, Simulated, Replay, Live }
public enum Perspective { Unknown, Player, Omniscient }
public enum UnitKnowledge { Unknown, Owned, VisibleEnemy, HiddenEnemy }
public enum DamageKind { Melee, Ranged }
public enum UnitClass { Infantry, Archer, Cavalry, Spearman, Siege }
public enum EvaluationStatus { Finding, NoFinding, InsufficientEvidence }

// Evidence has a timestamp, even when its value is a static profile.
public sealed record Evidence<T>(T Value, EvidenceOrigin Origin, double AtSeconds);
public sealed record Point(double X, double Y)
{
    public double DistanceTo(Point other) => double.Hypot(X - other.X, Y - other.Y);
}
public sealed record CombatProfile(UnitClass Class, DamageKind DamageKind,
    double Attack, double ReloadSeconds, double MeleeArmor, double RangedArmor,
    double Range, double Speed, Dictionary<UnitClass, double>? BonusDamage = null);
public sealed record UnitState(int Id, int PlayerId, string GroupId, UnitKnowledge Knowledge,
    Evidence<Point>? Position, Evidence<double>? HitPoints, Evidence<CombatProfile>? Profile);
public sealed record Resources(double Food, double Wood, double Gold, double Stone)
{
    public double Total => Food + Wood + Gold + Stone;
    public bool IsValid => new[] { Food, Wood, Gold, Stone }.All(x => double.IsFinite(x) && x >= 0);
    public double ExcessBeyond(Resources reserve) => Math.Max(0, Food - reserve.Food)
        + Math.Max(0, Wood - reserve.Wood) + Math.Max(0, Gold - reserve.Gold)
        + Math.Max(0, Stone - reserve.Stone);
}
// Capacity is affordable spendable resources/sec, supplied by the adapter, not inferred from stock.
public sealed record EconomyState(Evidence<Resources>? Stock,
    Evidence<Resources>? PlannedReserve, Evidence<double>? IncomePerSecond,
    Evidence<double>? AffordableSpendCapacityPerSecond, Evidence<double>? IdleProductionFraction,
    Evidence<double>? SustainedExcessSeconds);
public sealed record BattleContext(string GroupId, Evidence<Point>? Center,
    Evidence<bool>? VisibleAreaComplete);
public sealed record Snapshot(string Id, double TimeSeconds, int PlayerId,
    BattleContext? Battle, UnitState[] Units, EconomyState? Economy);
public sealed record AnalysisDocument(int SchemaVersion, string DatasetId, DataSource Source,
    Perspective Perspective, Snapshot[] Snapshots);
public sealed record Metric(string Name, double Value, string Unit);
public sealed record Finding(string Code, string Theme, string SnapshotId, double TimeSeconds,
    int PlayerId, DataSource Source, string Confidence, string Message, Metric[] Metrics,
    string[] Evidence, int[] UnitIds)
{
    public string TimeLabel => TimeSpan.FromSeconds(TimeSeconds).ToString(@"hh\:mm\:ss");
}
public sealed record Assessment(string Code, string SnapshotId, double TimeSeconds,
    EvaluationStatus Status, string Reason, Finding? Finding);
public sealed record AnalysisReport(string DatasetId, DataSource Source, Assessment[] Assessments)
{
    public Finding[] Findings => Assessments.Where(a => a.Finding is not null)
        .Select(a => a.Finding!).OrderBy(f => f.TimeSeconds).ThenBy(f => f.SnapshotId,
            StringComparer.Ordinal).ThenBy(f => f.Code, StringComparer.Ordinal).ToArray();
}
