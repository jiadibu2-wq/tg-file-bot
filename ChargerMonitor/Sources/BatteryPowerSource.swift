import Foundation
import Darwin

/// 通过运行时 dlopen/dlsym 访问 IOKit 私有接口读取 IOPMPowerSource。
/// iOS SDK 不公开 IOKit 模块，所以不能 `import IOKit`，只能在运行时找符号。
/// 若系统禁止（沙盒/无该框架），`read()` 返回 nil，上层回退到电量变化估算。
struct PowerSourceReading {
    var voltageMillivolts: Double?
    /// 毫安，符号因机型而异
    var currentMilliamps: Double?
    /// 0...1
    var level: Double?
    var isCharging: Bool?
    var externalConnected: Bool?
    var cycleCount: Int?
    var rawEntries: [DiagnosticEntry]
}

final class IOMPowerSourceReader {
    private typealias MatchingServicesFn = @convention(c) (UInt32, UnsafeRawPointer?, UnsafeMutablePointer<UInt32>?) -> Int32
    private typealias IteratorNextFn = @convention(c) (UInt32) -> UInt32
    private typealias ObjectReleaseFn = @convention(c) (UInt32) -> Int32
    private typealias CreatePropertyFn = @convention(c) (UInt32, UnsafeRawPointer?, UnsafeRawPointer?, UInt32) -> UnsafeMutableRawPointer?
    private typealias ServiceMatchingFn = @convention(c) (UnsafePointer<CChar>?) -> UnsafeMutableRawPointer?

    private let matchingServices: MatchingServicesFn?
    private let iteratorNext: IteratorNextFn?
    private let objectRelease: ObjectReleaseFn?
    private let createProperty: CreatePropertyFn?
    private let serviceMatching: ServiceMatchingFn?

    /// 加载失败原因，展示在诊断页
    let loadError: String?

    private static let keys: [String] = [
        "Voltage", "Current", "Amperage", "InstantAmperage", "BatteryPower",
        "CurrentCapacity", "MaxCapacity", "AppleRawCurrentCapacity", "AppleRawMaxCapacity",
        "NominalChargeCapacity", "DesignCapacity", "CycleCount", "Temperature",
        "ExternalConnected", "IsCharging", "FullyCharged", "TimeRemaining", "TimeToFullCharge"
    ]

    init() {
        let paths = [
            "/System/Library/PrivateFrameworks/IOKit.framework/IOKit",
            "/System/Library/Frameworks/IOKit.framework/IOKit",
            "/usr/lib/libIOKit.dylib",
            "IOKit"
        ]

        var handle: UnsafeMutableRawPointer?
        for path in paths {
            if let opened = dlopen(path, RTLD_LAZY) {
                handle = opened
                break
            }
        }

        guard let handle else {
            matchingServices = nil
            iteratorNext = nil
            objectRelease = nil
            createProperty = nil
            serviceMatching = nil
            loadError = "无法加载 IOKit 框架"
            return
        }

        func symbol<T>(_ name: String, _ type: T.Type) -> T? {
            guard let pointer = dlsym(handle, name) else { return nil }
            return unsafeBitCast(pointer, to: T.self)
        }

        matchingServices = symbol("IOServiceGetMatchingServices", MatchingServicesFn.self)
        iteratorNext = symbol("IOIteratorNext", IteratorNextFn.self)
        objectRelease = symbol("IOObjectRelease", ObjectReleaseFn.self)
        createProperty = symbol("IORegistryEntryCreateCFProperty", CreatePropertyFn.self)
        serviceMatching = symbol("IOServiceMatching", ServiceMatchingFn.self)

        if matchingServices == nil || iteratorNext == nil || objectRelease == nil ||
            createProperty == nil || serviceMatching == nil {
            loadError = "IOKit 符号缺失"
        } else {
            loadError = nil
        }
    }

    func read() -> PowerSourceReading? {
        guard let matchingServices, let iteratorNext, let objectRelease,
              let createProperty, let serviceMatching else { return nil }

        var iterator: UInt32 = 0
        let matching = "IOPMPowerSource".withCString { serviceMatching($0) }
        guard let matching else { return nil }

        let status = matchingServices(0, UnsafeRawPointer(matching), &iterator)
        if status != 0 {
            // 失败时字典未被消费，需要手动释放
            Unmanaged<AnyObject>.fromOpaque(matching).release()
            return nil
        }
        guard iterator != 0 else { return nil }

        let entry = iteratorNext(iterator)
        _ = objectRelease(iterator)
        guard entry != 0 else { return nil }
        defer { _ = objectRelease(entry) }

        var values: [String: Any] = [:]
        var entries: [DiagnosticEntry] = []
        for key in Self.keys {
            let cfKey = key as NSString
            let keyPointer = Unmanaged.passUnretained(cfKey).toOpaque()
            guard let raw = createProperty(entry, keyPointer, nil, 0) else { continue }
            let value = Unmanaged<AnyObject>.fromOpaque(raw).takeRetainedValue()
            values[key] = value
            entries.append(DiagnosticEntry(key: key, value: Self.describe(value)))
        }
        guard !entries.isEmpty else { return nil }

        let voltage = Self.number(values["Voltage"])
        let current = Self.number(values["Amperage"])
            ?? Self.number(values["InstantAmperage"])
            ?? Self.number(values["Current"])

        var level: Double?
        if let currentCapacity = Self.number(values["CurrentCapacity"]),
           let maxCapacity = Self.number(values["MaxCapacity"]), maxCapacity > 0 {
            level = min(max(currentCapacity / maxCapacity, 0), 1)
        } else if let rawCapacity = Self.number(values["AppleRawCurrentCapacity"]),
                  let rawMaxCapacity = Self.number(values["AppleRawMaxCapacity"]), rawMaxCapacity > 0 {
            level = min(max(rawCapacity / rawMaxCapacity, 0), 1)
        }

        return PowerSourceReading(
            voltageMillivolts: voltage,
            currentMilliamps: current,
            level: level,
            isCharging: Self.boolean(values["IsCharging"]),
            externalConnected: Self.boolean(values["ExternalConnected"]),
            cycleCount: Self.number(values["CycleCount"]).map { Int($0) },
            rawEntries: entries
        )
    }

    private static func describe(_ value: Any) -> String {
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
