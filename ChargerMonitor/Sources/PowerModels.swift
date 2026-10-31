import Foundation

/// 一次采样结果
struct PowerSample: Identifiable {
    let id = UUID()
    let timestamp: Date
    /// 瞬时功率（W）。充电时为正值
    let watts: Double
    let voltage: Double?
    let current: Double?
    /// 0...1
    let level: Double
    let isCharging: Bool
    let isExternalPower: Bool
    /// 数据来源说明，展示给用户，便于判断精度
    let source: String
}

struct PowerStatistics {
    /// 本次会话累计充入能量（Wh）
    var sessionEnergyWh: Double = 0
    var peakWatts: Double = 0
    var chargeStart: Date?
}

struct Diagnostics {
    var backend: String
    var updatedAt: Date
    var entries: [DiagnosticEntry]

    static let unknown = Diagnostics(backend: "尚未开始采样", updatedAt: .distantPast, entries: [])
}

struct DiagnosticEntry: Identifiable {
    let key: String
    let value: String
    var id: String { key }
}

/// 读不到硬件寄存器时的兜底：用电池电量变化率估算平均功率。
/// 计算的是最近一段时间（≥90 秒）的平均值，所以刷新慢、精度有限。
struct ChargePowerEstimator {
    /// 电池额定能量（Wh），iPhone 大致 12~14 Wh
    var batteryCapacityWh: Double = 13.0

    private var history: [(date: Date, level: Double)] = []
    private let window: TimeInterval = 900
    private let minimumSpan: TimeInterval = 120

    mutating func estimatedWatts(level: Double, at date: Date, charging: Bool) -> Double? {
        history.append((date, level))
        history.removeAll { date.timeIntervalSince($0.date) > window }

        guard charging,
              let first = history.first,
              let newest = history.last else { return nil }

        let span = newest.date.timeIntervalSince(first.date)
        let delta = newest.level - first.level
        // 系统电量只能按 1%~5% 跳变，跨度太短会算出离谱的数字，所以要求至少 2 分钟
        guard span >= minimumSpan, delta > 0.03 else { return nil }
        return delta * batteryCapacityWh * 3600 / span
    }

    mutating func reset() {
        history.removeAll()
    }
}
