import Foundation
import IOKit

/// 从 IOPMPowerSource 读取电源管理寄存器。
/// 注意：iOS 没有公开这个接口，部分系统版本可能读取不到（沙盒限制），
/// 此时 `read()` 返回 nil，上层会自动回退到电量变化估算。
struct BatteryPowerSourceReading {
    var voltageMillivolts: Double?
    /// 毫安，符号因机型而异（充电时可能为负）
    var currentMilliamps: Double?
    /// 0...1
    var level: Double?
    var isCharging: Bool?
    var externalConnected: Bool?
    var cycleCount: Int?
    var rawEntries: [DiagnosticEntry]
}

enum BatteryPowerSourceReader {
    private static let keys: [String] = [
        "Voltage", "Current", "Amperage", "InstantAmperage", "BatteryPower",
        "CurrentCapacity", "MaxCapacity", "AppleRawCurrentCapacity", "AppleRawMaxCapacity",
        "NominalChargeCapacity", "DesignCapacity", "CycleCount", "Temperature",
        "ExternalConnected", "IsCharging", "FullyCharged", "TimeRemaining", "TimeToFullCharge"
    ]

    static func read() -> BatteryPowerSourceReading? {
        var iterator: io_iterator_t = 0
        guard IOServiceGetMatchingServices(0, IOServiceMatching("IOPMPowerSource"), &iterator) == KERN_SUCCESS,
              iterator != 0 else {
            return nil
        }
        defer { IOObjectRelease(iterator) }

        let entry = IOIteratorNext(iterator)
        guard entry != 0 else { return nil }
        defer { IOObjectRelease(entry) }

        var values: [String: Any] = [:]
        var entries: [DiagnosticEntry] = []
        for key in keys {
            guard let unmanaged = IORegistryEntryCreateCFProperty(entry, key as CFString, kCFAllocatorDefault, 0) else {
                continue
            }
            let value = unmanaged.takeRetainedValue()
            values[key] = value
            entries.append(DiagnosticEntry(key: key, value: describe(value)))
        }
        guard !entries.isEmpty else { return nil }

        let voltage = number(values["Voltage"])
        let current = number(values["Amperage"])
            ?? number(values["InstantAmperage"])
            ?? number(values["Current"])

        var level: Double?
        if let currentCapacity = number(values["CurrentCapacity"]),
           let maxCapacity = number(values["MaxCapacity"]), maxCapacity > 0 {
            level = min(max(currentCapacity / maxCapacity, 0), 1)
        } else if let rawCapacity = number(values["AppleRawCurrentCapacity"]),
                  let rawMaxCapacity = number(values["AppleRawMaxCapacity"]), rawMaxCapacity > 0 {
            level = min(max(rawCapacity / rawMaxCapacity, 0), 1)
        }

        return BatteryPowerSourceReading(
            voltageMillivolts: voltage,
            currentMilliamps: current,
            level: level,
            isCharging: boolean(values["IsCharging"]),
            externalConnected: boolean(values["ExternalConnected"]),
            cycleCount: number(values["CycleCount"]).map { Int($0) },
            rawEntries: entries
        )
    }

    private static func describe(_ value: CFTypeRef) -> String {
        if let number = value as? NSNumber {
            return number.stringValue
        }
        if let string = value as? String {
            return string
        }
        return String(describing: value)
    }

    private static func number(_ value: Any?) -> Double? {
        if let number = value as? NSNumber {
            return number.doubleValue
        }
        if let string = value as? String {
            if let parsed = Double(string) { return parsed }
            switch string.lowercased() {
            case "true", "yes": return 1
            case "false", "no": return 0
            default: return nil
            }
        }
        return nil
    }

    private static func boolean(_ value: Any?) -> Bool? {
        if let number = value as? NSNumber {
            return number.boolValue
        }
        if let string = value as? String {
            switch string.lowercased() {
            case "true", "yes", "1": return true
            case "false", "no", "0": return false
            default: return nil
            }
        }
        return nil
    }
}
