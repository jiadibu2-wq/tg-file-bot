import Foundation
import Combine
import UIKit

@MainActor
final class PowerMonitor: ObservableObject {
    @Published private(set) var samples: [PowerSample] = []
    @Published private(set) var latest: PowerSample?
    @Published private(set) var stats = PowerStatistics()
    @Published private(set) var diagnostics: Diagnostics = .unknown
    @Published private(set) var isSampling = false

    private var timer: Timer?
    private var estimator = ChargePowerEstimator()
    private var lastTick: Date?
    private let historyWindow: TimeInterval = 600

    func start() {
        guard timer == nil else { return }
        UIDevice.current.isBatteryMonitoringEnabled = true
        isSampling = true
        tick()

        let newTimer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.tick()
            }
        }
        newTimer.tolerance = 0.1
        timer = newTimer
    }

    func stop() {
        timer?.invalidate()
        timer = nil
        isSampling = false
    }

    func resetSession() {
        stats = PowerStatistics()
        samples.removeAll()
        latest = nil
        estimator.reset()
        lastTick = nil
    }

    private func tick() {
        let now = Date()
        let device = UIDevice.current
        let deviceLevel = device.batteryLevel >= 0 ? Double(device.batteryLevel) : nil
        let deviceState = device.batteryState
        let reading = BatteryPowerSourceReader.read()

        let level = reading?.level ?? deviceLevel ?? 0
        let isCharging = reading?.isCharging ?? (deviceState == .charging || deviceState == .full)
        let isExternal = reading?.externalConnected ?? (deviceState != .unplugged)

        let estimated = estimator.estimatedWatts(level: level, at: now, charging: isCharging)

        let voltage: Double?
        let current: Double?
        let watts: Double
        let source: String

        if let millivolts = reading?.voltageMillivolts,
           let milliamps = reading?.currentMilliamps,
           millivolts > 0, milliamps != 0 {
            let volts = millivolts / 1000
            let amps = milliamps / 1000
            var power = volts * amps
            // 部分机型充电时电流为负，统一为“进入电池为正”
            if isCharging && power < 0 { power = -power }
            voltage = volts
            current = amps
            watts = power
            source = "硬件寄存器实测"
        } else if let estimated {
            voltage = nil
            current = nil
            watts = estimated
            source = "电量变化估算"
        } else {
            voltage = nil
            current = nil
            watts = 0
            source = "等待数据"
        }

        let sample = PowerSample(
            timestamp: now,
            watts: watts,
            voltage: voltage,
            current: current,
            level: level,
            isCharging: isCharging,
            isExternalPower: isExternal,
            source: source
        )

        latest = sample
        samples.append(sample)
        samples.removeAll { now.timeIntervalSince($0.timestamp) > historyWindow }

        let deltaTime = lastTick.map { min(max(now.timeIntervalSince($0), 0), 5) } ?? 0
        if isCharging && isExternal && source != "等待数据" {
            if stats.chargeStart == nil { stats.chargeStart = now }
            stats.sessionEnergyWh += abs(watts) * deltaTime / 3600
            stats.peakWatts = max(stats.peakWatts, abs(watts))
        }
        lastTick = now

        diagnostics = Diagnostics(
            backend: reading == nil ? "不可用（使用电量估算）" : "IOPMPowerSource",
            updatedAt: now,
            entries: reading?.rawEntries ?? []
        )
    }
}
