namespace Companion.Core;

// Heuristic defaults for demonstration; not calibrated against real matches.
public sealed record AnalysisOptions
{
    public double MaximumEvidenceAgeSeconds { get; init; } = 2;
    public double LocalRadius { get; init; } = 18;
    public double InferiorityRatio { get; init; } = .8;
    public double ReinforcementDelaySeconds { get; init; } = 20;
    public double DistantPowerFraction { get; init; } = .3;
    public double ExcessStockThreshold { get; init; } = 1000;
    public double ExcessDurationSeconds { get; init; } = 60;
    public double MinimumIdleFraction { get; init; } = .5;

    internal void Validate()
    {
        var positive = new[] { MaximumEvidenceAgeSeconds, LocalRadius, ReinforcementDelaySeconds,
            ExcessStockThreshold, ExcessDurationSeconds };
        if (positive.Any(x => !double.IsFinite(x) || x <= 0)
            || !double.IsFinite(InferiorityRatio) || InferiorityRatio <= 0 || InferiorityRatio >= 1
            || !double.IsFinite(DistantPowerFraction) || DistantPowerFraction <= 0 || DistantPowerFraction >= 1
            || !double.IsFinite(MinimumIdleFraction) || MinimumIdleFraction < 0 || MinimumIdleFraction > 1)
            throw new ArgumentException("Parâmetros de análise inválidos.");
    }
}
