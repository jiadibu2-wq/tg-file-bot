import SwiftUI

struct DiagnosticsView: View {
    let diagnostics: Diagnostics
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("数据源") {
                    infoRow(title: "后端", value: diagnostics.backend)
                    infoRow(
                        title: "更新时间",
                        value: diagnostics.updatedAt.formatted(date: .omitted, time: .standard)
                    )
                }

                if diagnostics.entries.isEmpty {
                    Section("原始数据") {
                        Text("未读取到 IOPMPowerSource 数据。系统可能限制了该接口，应用已回退到电量变化估算。")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Section("IOPMPowerSource 原始键值") {
                        ForEach(diagnostics.entries) { entry in
                            infoRow(title: entry.key, value: entry.value)
                        }
                    }
                }

                Section("说明") {
                    Text("iOS 不提供公开的充电功率 API。应用优先读取 IOPMPowerSource 的 Voltage / Amperage 寄存器；若系统屏蔽，则用电池电量变化率估算平均值，刷新较慢且精度有限。")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("数据源诊断")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("完成") { dismiss() }
                }
            }
        }
    }

    private func infoRow(title: String, value: String) -> some View {
        HStack(spacing: 12) {
            Text(title)
                .font(.subheadline)
            Spacer(minLength: 8)
            Text(value)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .lineLimit(1)
                .truncationMode(.middle)
        }
    }
}
