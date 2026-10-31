import SwiftUI

@main
struct ChargerMonitorApp: App {
    @StateObject private var monitor = PowerMonitor()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(monitor)
        }
    }
}
