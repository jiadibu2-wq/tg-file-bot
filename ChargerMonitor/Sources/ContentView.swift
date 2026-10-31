import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var monitor: PowerMonitor
    @Environment(\.scenePhase) private var scenePhase

    @State private var range: ChartRange = .oneMinute
    @State private var showDiagnostics = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 14) {
                    headlineCard
                    chartCard
                    metricsGrid
                    sessionCard
                    disclaimer
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
            }
            .background(Color(uiColor: .systemGroupedBackground))
            .navigationTitle("充电功率")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showDiagnostics = true
                    } label: {
                        Image(systemName: "waveform.path.ecg")
                    }
                    .accessibilityLabel("数据源诊断")
                }
            }
            .sheet(isPresented: $showDiagnostics) {
                DiagnosticsView(diagnostics: monitor.diagnostics)
            }
            .onAppear { monitor.start() }
            .onChange(of: scenePhase) { phase in
                if phase == .active {
                    monitor.start()
                } else {
                    monitor.stop()
                }
            }
        }
    }

    // MARK: - 顶部大数字

    private var headlineCard: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                statusPill
                Spacer()
                Text(monitor.latest?.source ?? "未开始")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
            }

            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(powerText)
                    .font(.system(size: 60, weight: .bold, design: .rounded))
                    .monospacedDigit()
                    .foregroundStyle(powerColor)
                    .contentTransition(.numericText())
                Text("W")
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(.secondary)
            }

            batteryBar
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            LinearGradient(
                colors: [powerColor.opacity(0.16), Color(uiColor: .secondarySystemGroupedBackground)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            ),
            in: RoundedRectangle(cornerRadius: 22, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 22, style: .continuous)
                .stroke(powerColor.opacity(0.18), lineWidth: 1)
        )
    }

    private var statusPill: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(powerColor)
                .frame(width: 7, height: 7)
            Text(statusText)
                .font(.subheadline.weight(.semibold))
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(powerColor.opacity(0.12), in: Capsule())
        .foregroundStyle(powerColor)
    }

    private var batteryBar: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text("电池 \(levelText)%")
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(.secondary)
                Spacer()
                if let cycle = cycleCountText {
                    Text(cycle)
                        .font(.footnote)
                        .foregroundStyle(.tertiary)
                }
            }

            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.primary.opacity(0.08))
                    Capsule()
                        .fill(
                            LinearGradient(
                                colors: [powerColor.opacity(0.95), powerColor.opacity(0.55)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .frame(width: max(6, proxy.size.width * CGFloat(monitor.latest?.level ?? 0)))
                        .animation(.easeInOut(duration: 0.3), value: monitor.latest?.level ?? 0)
                }
            }
            .frame(height: 6)
        }
    }

    // MARK: - 曲线

    private var chartCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("实时功率")
                    .font(.headline)
                Spacer()
                Picker("时间范围", selection: $range) {
                    ForEach(ChartRange.allCases) { item in
                        Text(item.label).tag(item)
                    }
                }
                .pickerStyle(.segmented)
                .frame(width: 168)
            }

            if chartSamples.count < 2 {
                Text("正在采集数据…")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, minHeight: 170)
            } else {
                powerChart
            }
        }
        .cardStyle()
    }

    private var powerChart: some View {
        Chart(chartSamples) { sample in
            AreaMark(
                x: .value("时间", sample.timestamp),
                y: .value("功率", sample.watts)
            )
            .foregroundStyle(
                LinearGradient(
                    colors: [Color.green.opacity(0.28), Color.green.opacity(0.02)],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )
            .interpolationMethod(.catmullRom)

            LineMark(
                x: .value("时间", sample.timestamp),
                y: .value("功率", sample.watts)
            )
            .foregroundStyle(Color.green)
            .lineStyle(StrokeStyle(lineWidth: 2))
            .interpolationMethod(.catmullRom)
        }
        .chartYScale(domain: yDomain)
        .chartXScale(domain: xDomain)
        .chartXAxis {
            AxisMarks(values: .automatic(desiredCount: 3)) { _ in
                AxisGridLine().foregroundStyle(Color.secondary.opacity(0.15))
                AxisValueLabel(format: .dateTime.minute().second())
            }
        }
        .chartYAxis {
            AxisMarks(position: .leading, values: .automatic(desiredCount: 4)) { _ in
                AxisGridLine().foregroundStyle(Color.secondary.opacity(0.15))
                AxisValueLabel()
            }
        }
        .frame(height: 170)
    }

    // MARK: - 指标

    private var metricsGrid: some View {
        LazyVGrid(columns: [GridItem(.flexible(), spacing: 12), GridItem(.flexible(), spacing: 12)], spacing: 12) {
            MetricTile(title: "电压", value: voltageText, unit: "V", icon: "bolt.fill", tint: .blue)
            MetricTile(title: "电流", value: currentText, unit: "A", icon: "arrow.left.arrow.right", tint: .orange)
            MetricTile(title: "电池电量", value: levelText, unit: "%", icon: "battery.75", tint: .green)
            MetricTile(title: "60 秒均值", value: averageText, unit: "W", icon: "speedometer", tint: .purple)
        }
    }

    // MARK: - 本次充电

    private var sessionCard: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label("本次充电", systemImage: "leaf.fill")
                    .font(.headline)
                Spacer()
                Button("重置") {
                    monitor.resetSession()
                }
                .font(.subheadline.weight(.medium))
                .buttonStyle(.borderless)
            }

            HStack(alignment: .top, spacing: 0) {
                sessionItem(title: "充入能量", value: String(format: "%.2f Wh", monitor.stats.sessionEnergyWh))
                Divider().frame(height: 34)
                sessionItem(title: "峰值功率", value: String(format: "%.1f W", monitor.stats.peakWatts))
                Divider().frame(height: 34)
                sessionItem(title: "充电时长", value: durationText)
            }
        }
        .cardStyle()
    }

    private func sessionItem(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.system(.body, design: .rounded).weight(.semibold))
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var disclaimer: some View {
        Text("iOS 未公开充电功率接口。应用优先读取电源管理寄存器；读取不到时按电量变化估算，数值仅供参考。")
            .font(.caption2)
            .foregroundStyle(.tertiary)
            .padding(.top, 2)
    }

    // MARK: - 计算属性

    private var powerColor: Color {
        guard let latest = monitor.latest else { return .gray }
        if latest.isCharging && abs(latest.watts) > 0.2 { return .green }
        if latest.isExternalPower { return .orange }
        return .secondary
    }

    private var statusText: String {
        guard let latest = monitor.latest else { return "初始化中" }
        if latest.isCharging && abs(latest.watts) > 0.2 { return "正在充电" }
        if latest.isExternalPower { return "已接电源 · 未充电" }
        return "未接电源"
    }

    private var powerText: String {
        guard let latest = monitor.latest, latest.source != "等待数据" else { return "—" }
        return String(format: "%.1f", abs(latest.watts))
    }

    private var levelText: String {
        guard let latest = monitor.latest else { return "—" }
        return "\(Int(latest.level * 100))"
    }

    private var voltageText: String {
        guard let voltage = monitor.latest?.voltage else { return "—" }
        return String(format: "%.2f", voltage)
    }

    private var currentText: String {
        guard let current = monitor.latest?.current else { return "—" }
        return String(format: "%.2f", current)
    }

    private var averageText: String {
        guard let average = averageWatts else { return "—" }
        return String(format: "%.1f", average)
    }

    private var averageWatts: Double? {
        guard let end = monitor.latest?.timestamp else { return nil }
        let start = end.addingTimeInterval(-60)
        let values = monitor.samples.filter { $0.timestamp >= start }.map { abs($0.watts) }
        guard !values.isEmpty else { return nil }
        return values.reduce(0, +) / Double(values.count)
    }

    private var cycleCountText: String? {
        guard let entry = monitor.diagnostics.entries.first(where: { $0.key == "CycleCount" }) else {
            return nil
        }
        return "循环 \(entry.value) 次"
    }

    private var durationText: String {
        guard let start = monitor.stats.chargeStart else { return "00:00" }
        let seconds = Int(Date().timeIntervalSince(start))
        return String(format: "%02d:%02d", seconds / 60, seconds % 60)
    }

    private var chartEnd: Date {
        monitor.latest?.timestamp ?? Date()
    }

    private var chartSamples: [PowerSample] {
        let end = chartEnd
        let start = end.addingTimeInterval(-range.window)
        return monitor.samples.filter { $0.timestamp >= start }
    }

    private var xDomain: ClosedRange<Date> {
        chartEnd.addingTimeInterval(-range.window)...chartEnd
    }

    private var yDomain: ClosedRange<Double> {
        let values = chartSamples.map { $0.watts }
        let lower = min(0, values.min() ?? 0)
        let upper = max(5, (values.max() ?? 0) * 1.15)
        return lower...upper
    }
}

enum ChartRange: String, CaseIterable, Identifiable {
    case oneMinute
    case fiveMinutes
    case tenMinutes

    var id: String { rawValue }

    var label: String {
        switch self {
        case .oneMinute: return "1 分"
        case .fiveMinutes: return "5 分"
        case .tenMinutes: return "10 分"
        }
    }

    var window: TimeInterval {
        switch self {
        case .oneMinute: return 60
        case .fiveMinutes: return 300
        case .tenMinutes: return 600
        }
    }
}

struct MetricTile: View {
    let title: String
    let value: String
    let unit: String
    let icon: String
    let tint: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.caption)
                    .foregroundStyle(tint)
                Text(title)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            HStack(alignment: .firstTextBaseline, spacing: 3) {
                Text(value)
                    .font(.system(.title2, design: .rounded).weight(.semibold))
                    .monospacedDigit()
                Text(unit)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            Color(uiColor: .secondarySystemGroupedBackground),
            in: RoundedRectangle(cornerRadius: 16, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.primary.opacity(0.05), lineWidth: 1)
        )
    }
}

private extension View {
    func cardStyle(padding: CGFloat = 16) -> some View {
        self
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(
                Color(uiColor: .secondarySystemGroupedBackground),
                in: RoundedRectangle(cornerRadius: 20, style: .continuous)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 20, style: .continuous)
                    .stroke(Color.primary.opacity(0.05), lineWidth: 1)
            )
    }
}
