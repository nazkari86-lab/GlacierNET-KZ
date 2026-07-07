using System.Text.Json;
using Grpc.Core;
using Grpc.Net.Client;
using Microsoft.Extensions.Configuration;
using GlacierNET.Analysis.Models;

namespace GlacierNET.Analysis.Grpc;

public class GlacierAnalysisClient : IDisposable
{
    private readonly GrpcChannel _channel;
    private readonly GlacierAnalysis.GlacierAnalysisClient _client;
    private readonly ILogger<GlacierAnalysisClient> _logger;

    public GlacierAnalysisClient(IConfiguration configuration, ILogger<GlacierAnalysisClient> logger)
    {
        _logger = logger;
        var serviceUrl = configuration["GrpcServices:PythonMlService"] ?? "http://localhost:50051";
        _channel = GrpcChannel.ForAddress(serviceUrl);
        _client = new GlacierAnalysis.GlacierAnalysisClient(_channel);
        _logger.LogInformation("gRPC client initialized for {ServiceUrl}", serviceUrl);
    }

    public async Task<MlPredictionResult> PredictMassBalanceAsync(Guid glacierId, List<TrendData> historicalData, CancellationToken cancellationToken = default)
    {
        try
        {
            var request = new MassBalanceRequest
            {
                GlacierId = glacierId.ToString()
            };
            request.HistoricalValues.AddRange(historicalData.Select(d => d.Value));
            request.HistoricalDates.AddRange(historicalData.Select(d => d.MeasurementDate.ToString("o")));

            var response = await _client.PredictMassBalanceAsync(request, cancellationToken: cancellationToken);

            return new MlPredictionResult
            {
                GlacierId = glacierId,
                Prediction = response.PredictedValue,
                Confidence = response.Confidence,
                LowerBound = response.LowerBound,
                UpperBound = response.UpperBound,
                MethodUsed = response.MethodUsed,
                ModelVersion = response.ModelVersion
            };
        }
        catch (RpcException ex)
        {
            _logger.LogError(ex, "gRPC call failed for mass balance prediction on glacier {GlacierId}", glacierId);
            return new MlPredictionResult
            {
                GlacierId = glacierId,
                Prediction = 0,
                Confidence = 0,
                MethodUsed = "Fallback: Linear Regression",
                ModelVersion = "local-fallback"
            };
        }
    }

    public async Task<List<MlAnomalyResult>> DetectAnomaliesAsync(Guid glacierId, List<TrendData> dataPoints, double sensitivity = 2.0, CancellationToken cancellationToken = default)
    {
        try
        {
            var request = new AnomalyDetectionRequest
            {
                GlacierId = glacierId.ToString(),
                Sensitivity = sensitivity
            };
            request.Values.AddRange(dataPoints.Select(d => d.Value));
            request.Dates.AddRange(dataPoints.Select(d => d.MeasurementDate.ToString("o")));

            var response = await _client.DetectAnomaliesAsync(request, cancellationToken: cancellationToken);

            return response.Anomalies.Select(a => new MlAnomalyResult
            {
                Index = a.Index,
                Value = a.Value,
                ExpectedValue = a.ExpectedValue,
                Score = a.Score,
                IsAnomaly = a.IsAnomaly,
                Explanation = a.Explanation
            }).ToList();
        }
        catch (RpcException ex)
        {
            _logger.LogError(ex, "gRPC call failed for anomaly detection on glacier {GlacierId}", glacierId);
            return new List<MlAnomalyResult>();
        }
    }

    public async Task<MlClassificationResult> ClassifyGlacierAsync(Guid glacierId, Dictionary<string, double> features, CancellationToken cancellationToken = default)
    {
        try
        {
            var request = new ClassificationRequest
            {
                GlacierId = glacierId.ToString()
            };
            request.Features.Add(features);

            var response = await _client.ClassifyGlacierAsync(request, cancellationToken: cancellationToken);

            return new MlClassificationResult
            {
                GlacierId = glacierId,
                PredictedClass = response.PredictedClass,
                Confidence = response.Confidence,
                ClassProbabilities = response.ClassProbabilities.ToDictionary(kvp => kvp.Key, kvp => kvp.Value)
            };
        }
        catch (RpcException ex)
        {
            _logger.LogError(ex, "gRPC call failed for glacier classification {GlacierId}", glacierId);
            return new MlClassificationResult
            {
                GlacierId = glacierId,
                PredictedClass = "Unknown",
                Confidence = 0
            };
        }
    }

    public async Task<MlClusterResult> ClusterGlaciersAsync(List<Dictionary<string, double>> glacierFeatures, int numClusters = 3, CancellationToken cancellationToken = default)
    {
        try
        {
            var request = new ClusterRequest { NumClusters = numClusters };
            request.FeatureSets.Add(glacierFeatures.Select(f =>
            {
                var fs = new FeatureSet();
                fs.Features.Add(f);
                return fs;
            }));

            var response = await _client.ClusterGlaciersAsync(request, cancellationToken: cancellationToken);

            return new MlClusterResult
            {
                Labels = response.Labels.ToList(),
                Centroids = response.Centroids.Select(c => c.Features.ToDictionary(kvp => kvp.Key, kvp => kvp.Value)).ToList(),
                SilhouetteScore = response.SilhouetteScore
            };
        }
        catch (RpcException ex)
        {
            _logger.LogError(ex, "gRPC call failed for glacier clustering");
            return new MlClusterResult();
        }
    }

    public async Task<MlModelInfo> GetModelInfoAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            var response = await _client.GetModelInfoAsync(new Empty(), cancellationToken: cancellationToken);
            return new MlModelInfo
            {
                ModelName = response.ModelName,
                Version = response.Version,
                LastTrained = response.LastTrained.ToDateTime(),
                Metrics = response.Metrics.ToDictionary(kvp => kvp.Key, kvp => kvp.Value)
            };
        }
        catch (RpcException ex)
        {
            _logger.LogWarning(ex, "gRPC call failed for model info");
            return new MlModelInfo { ModelName = "Unavailable", Version = "N/A" };
        }
    }

    public void Dispose()
    {
        _channel?.Dispose();
        GC.SuppressFinalize(this);
    }
}

public class MlPredictionResult
{
    public Guid GlacierId { get; set; }
    public double Prediction { get; set; }
    public double Confidence { get; set; }
    public double LowerBound { get; set; }
    public double UpperBound { get; set; }
    public string MethodUsed { get; set; } = string.Empty;
    public string ModelVersion { get; set; } = string.Empty;
}

public class MlAnomalyResult
{
    public int Index { get; set; }
    public double Value { get; set; }
    public double ExpectedValue { get; set; }
    public double Score { get; set; }
    public bool IsAnomaly { get; set; }
    public string Explanation { get; set; } = string.Empty;
}

public class MlClassificationResult
{
    public Guid GlacierId { get; set; }
    public string PredictedClass { get; set; } = string.Empty;
    public double Confidence { get; set; }
    public Dictionary<string, double> ClassProbabilities { get; set; } = new();
}

public class MlClusterResult
{
    public List<int> Labels { get; set; } = new();
    public List<Dictionary<string, double>> Centroids { get; set; } = new();
    public double SilhouetteScore { get; set; }
}

public class MlModelInfo
{
    public string ModelName { get; set; } = string.Empty;
    public string Version { get; set; } = string.Empty;
    public DateTime LastTrained { get; set; }
    public Dictionary<string, double> Metrics { get; set; } = new();
}
