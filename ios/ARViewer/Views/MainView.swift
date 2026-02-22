//
//  MainView.swift
//  ARViewer
//
//  Главный экран: сканер QR, ввод ID вручную, кнопка «Открыть».
//

import SwiftUI

struct MainView: View {
    @State private var uniqueIdInput: String = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showQRScanner = false
    @State private var showWebAR = false
    @State private var loadedManifest: ViewerManifest?
    
    var body: some View {
        NavigationStack {
            ZStack {
                Color(.systemGroupedBackground).ignoresSafeArea()
                
                if showWebAR, let manifest = loadedManifest {
                    WebARView(
                        uniqueId: manifest.uniqueId,
                        orderNumber: manifest.orderNumber,
                        onClose: {
                            showWebAR = false
                            loadedManifest = nil
                        }
                    )
                } else if showQRScanner {
                    QRScannerView(
                        onScanned: { id in
                            uniqueIdInput = id
                            showQRScanner = false
                            openViewer(uniqueId: id)
                        },
                        onCancel: {
                            showQRScanner = false
                        }
                    )
                } else {
                    mainContent
                }
            }
            .navigationTitle("AR Viewer")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
    
    private var mainContent: some View {
        ScrollView {
            VStack(spacing: 24) {
                logoSection
                scanButton
                manualInputSection
                if let msg = errorMessage {
                    Text(msg)
                        .font(.subheadline)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }
            }
            .padding(24)
        }
        .overlay {
            if isLoading {
                ProgressView("Загрузка…")
                    .padding(20)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12))
            }
        }
        .onOpenURL { url in
            if let id = UniqueIdParser.parseFromURL(url) {
                uniqueIdInput = id
                openViewer(uniqueId: id)
            }
        }
    }
    
    private var logoSection: some View {
        VStack(spacing: 8) {
            Image(systemName: "viewfinder")
                .font(.system(size: 56))
                .foregroundStyle(.secondary)
            Text("Сканируйте QR-код или введите ссылку")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, 20)
    }
    
    private var scanButton: some View {
        Button {
            showQRScanner = true
        } label: {
            Label("Сканировать QR-код", systemImage: "qrcode.viewfinder")
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
        }
        .buttonStyle(.borderedProminent)
        .tint(.blue)
    }
    
    private var manualInputSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Или введите ID или ссылку")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            TextField("UUID или https://ar.neuroimagen.ru/view/…", text: $uniqueIdInput)
                .textFieldStyle(.roundedBorder)
                .textContentType(.URL)
                .autocapitalization(.none)
                .autocorrectionDisabled()
            Button("Открыть") {
                openFromInput()
            }
            .buttonStyle(.bordered)
            .frame(maxWidth: .infinity)
        }
    }
    
    private func openFromInput() {
        errorMessage = nil
        guard let id = UniqueIdParser.extractFromInput(uniqueIdInput) else {
            errorMessage = UniqueIdParser.looksLikeURL(uniqueIdInput)
                ? "Неверный формат ссылки. Ожидается https://ar.neuroimagen.ru/view/{id} или arv://view/{id}."
                : "Введите корректный UUID или ссылку на AR-контент."
            return
        }
        openViewer(uniqueId: id)
    }
    
    private func openViewer(uniqueId: String) {
        errorMessage = nil
        isLoading = true
        Task {
            do {
                _ = try await ViewerService.shared.checkContent(uniqueId: uniqueId)
                let manifest = try await ViewerService.shared.loadManifest(uniqueId: uniqueId)
                await MainActor.run {
                    loadedManifest = manifest
                    showWebAR = true
                    isLoading = false
                }
            } catch let e as ViewerError {
                await MainActor.run {
                    isLoading = false
                    errorMessage = messageForError(e)
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    errorMessage = "Ошибка: \(error.localizedDescription)"
                }
            }
        }
    }
    
    private func messageForError(_ e: ViewerError) -> String {
        switch e {
        case .invalidId:
            return "Неверный идентификатор."
        case .unavailable(let reason):
            switch reason {
            case "not_found": return "Контент не найден."
            case "subscription_expired": return "Срок действия контента истёк."
            case "content_not_active": return "Контент недоступен."
            case "marker_still_generating": return "Маркер ещё создаётся. Попробуйте позже."
            default: return "Контент недоступен: \(reason)"
            }
        case .server(let code, let msg):
            return "Ошибка сервера (\(code)). \(msg ?? "")"
        case .network(let err):
            return "Нет соединения. Проверьте интернет. \(err.localizedDescription)"
        }
    }
}

struct MainView_Previews: PreviewProvider {
    static var previews: some View {
        MainView()
    }
}
