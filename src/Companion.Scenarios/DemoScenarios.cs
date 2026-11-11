using Companion.Core;
namespace Companion.Scenarios;

// Invented profiles and positions. These are not AoE2 balance data or replay observations.
public static class DemoScenarios
{
    public static Evidence<T> Sim<T>(T value, double time) => new(value, EvidenceOrigin.Simulated, time);
    public static UnitState Unit(int id, int player, double x, double y, double time, string group = "main",
        UnitClass kind = UnitClass.Infantry) => new(id, player, group,
        player == 1 ? UnitKnowledge.Owned : UnitKnowledge.VisibleEnemy,
        Sim(new Point(x, y), time), Sim(60d, time),
        Sim(new CombatProfile(kind, DamageKind.Melee, 6, 2, 0, 0, 1, 1,
            kind == UnitClass.Spearman ? new() { [UnitClass.Cavalry] = 12 } : null), time));
    public static Snapshot Military(string id, double time, int allies, int enemies, int distant = 0)
    {
        var units = Enumerable.Range(1, allies).Select(i => Unit(i, 1, 50 + i * .1, 50, time))
            .Concat(Enumerable.Range(101, enemies).Select(i => Unit(i, 2, 55 + (i - 100) * .1, 50, time)))
            .Concat(Enumerable.Range(201, distant).Select(i => Unit(i, 1, 110, 50 + (i - 200) * .1, time))).ToArray();
        return new(id, time, 1, new("main", Sim(new Point(50, 50), time), Sim(true, time)), units, null);
    }
    public static EconomyState Economy(double time, double reserve = 0, double capacity = 20,
        double income = 8, double duration = 90, double idle = .8) => new(
            Sim(new Resources(1000, 1000, 400, 0), time), Sim(new Resources(reserve, reserve, reserve, 0), time),
            Sim(income, time), Sim(capacity, time), Sim(idle, time), Sim(duration, time));
    public static AnalysisDocument Wrap(params Snapshot[] snapshots) => new(1, "simulated-demonstration-v1",
        DataSource.Simulated, Perspective.Player, snapshots);
    public static AnalysisDocument Create() => Wrap(
        Military("equilibrio", 480, 8, 8),
        Military("inferioridade-local", 600, 4, 10),
        Military("reforcos-distantes", 630, 4, 10, 8),
        new Snapshot("capacidade-ociosa", 840, 1, null, Array.Empty<UnitState>(), Economy(840)),
        new Snapshot("reserva-para-plano", 900, 1, null, Array.Empty<UnitState>(), Economy(900, reserve: 1200)),
        Military("cobertura-desconhecida", 960, 4, 10) with
            { Battle = new("main", Sim(new Point(50, 50), 960), null) });
}
