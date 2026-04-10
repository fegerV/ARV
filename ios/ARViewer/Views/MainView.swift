//
//  MainView.swift
//  ARViewer
//
//  Главный экран: сканер QR, ввод ID вручную, кнопка «Открыть».
//

import SwiftUI
import SafariServices

struct MainView: View {
    @State private var uniqueIdInput: String = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showQRScanner = false
    @State private var showWebAR = false
    @State private var loadedManifest: ViewerManifest?

    // Dialog states
    @State private var showAboutDialog = false
    @State private var showSupportDialog = false
    @State private var showPrivacyPolicy = false
    
    var body: some View {
        NavigationView {
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
        .fullScreenCover(isPresented: $showAboutDialog) {
            AboutDialogView()
        }
        .fullScreenCover(isPresented: $showSupportDialog) {
            SupportDialogView()
        }
        .fullScreenCover(isPresented: $showPrivacyPolicy) {
            PrivacyPolicyView()
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

                Spacer(minLength: 32)

                footerLinks
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
        .tint(Color("AccentColor"))
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

    // MARK: - Footer Links

    private var footerLinks: some View {
        VStack(spacing: 0) {
            Divider()
                .padding(.vertical, 16)

            HStack(spacing: 0) {
                Button("Поддержка") {
                    showSupportDialog = true
                }
                .buttonStyle(LinkButtonStyle())

                Text("•")
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 6)

                Button("Политика") {
                    showPrivacyPolicy = true
                }
                .buttonStyle(LinkButtonStyle())

                Text("•")
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 6)

                Button("О приложении") {
                    showAboutDialog = true
                }
                .buttonStyle(LinkButtonStyle())
            }
        }
        .font(.subheadline)
        .foregroundStyle(.secondary)
    }
}

// MARK: - Dialog Views

struct AboutDialogView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Color.black.opacity(0.8).ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Text("О приложении")
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundStyle(.white)
                        Spacer()
                        Button {
                            dismiss()
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.title2)
                                .foregroundStyle(.white.opacity(0.7))
                        }
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Описание приложения V-Portal")
                            .fontWeight(.semibold)
                            .foregroundStyle(.white)
                        Text("V-Portal — это приложение для просмотра и создания дополненной реальности (AR) для печатных изображений.")
                            .foregroundStyle(.white.opacity(0.9))
                        Text("С помощью приложения вы можете:")
                            .fontWeight(.medium)
                            .foregroundStyle(.white)
                        VStack(alignment: .leading, spacing: 6) {
                            Text("• Сканировать изображения и просматривать AR-контент")
                            Text("• Оживлять портреты, постеры, меню, фотографии и другие материалы")
                            Text("• Просматривать демонстрационные AR-сцены")
                            Text("• Создавать собственные AR-проекты и отправлять заказы")
                        }
                        .foregroundStyle(.white.opacity(0.9))
                        Text("Приложение используется для работы с печатной продукцией, содержащей AR-маркеры или QR-коды.")
                            .foregroundStyle(.white.opacity(0.9))
                        Text("V-Portal подходит для:")
                            .fontWeight(.medium)
                            .foregroundStyle(.white)
                        VStack(alignment: .leading, spacing: 6) {
                            Text("• персональных подарков")
                            Text("• рекламных материалов")
                            Text("• ресторанных меню")
                            Text("• сувениров и полиграфии")
                        }
                        .foregroundStyle(.white.opacity(0.9))
                        Text("Для корректной работы требуется доступ к камере устройства.")
                            .foregroundStyle(.white.opacity(0.9))
                        Text("© 2026 Vertex Art")
                            .foregroundStyle(.white.opacity(0.6))
                            .padding(.top, 8)
                    }
                }
                .padding(24)
                .background(Color(hex: "121212"))
                .cornerRadius(20)
                .padding(.horizontal, 32)
            }
        }
    }
}

struct SupportDialogView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Color.black.opacity(0.8).ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        Text("Поддержка")
                            .font(.title2)
                            .fontWeight(.bold)
                            .foregroundStyle(.white)
                        Spacer()
                        Button {
                            dismiss()
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.title2)
                                .foregroundStyle(.white.opacity(0.7))
                        }
                    }

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Есть вопрос или проблема?")
                            .fontWeight(.semibold)
                            .foregroundStyle(.white)
                        Text("Мы поможем вам")
                            .foregroundStyle(.white.opacity(0.9))

                        VStack(alignment: .leading, spacing: 16) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Разработчик:")
                                    .fontWeight(.medium)
                                    .foregroundStyle(.white)
                                Text("V-Portal / Vertex Art")
                                    .foregroundStyle(.white.opacity(0.9))
                            }
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Email поддержки:")
                                    .fontWeight(.medium)
                                    .foregroundStyle(.white)
                                Link("info@vertex-art.ru", destination: URL(string: "mailto:info@vertex-art.ru")!)
                                    .foregroundStyle(Color(hex: "BB86FC"))
                            }
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Telegram:")
                                    .fontWeight(.medium)
                                    .foregroundStyle(.white)
                                Link("https://t.me/vertex_art", destination: URL(string: "https://t.me/vertex_art")!)
                                    .foregroundStyle(Color(hex: "BB86FC"))
                            }
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Сайт:")
                                    .fontWeight(.medium)
                                    .foregroundStyle(.white)
                                Link("https://vertex-art.ru", destination: URL(string: "https://vertex-art.ru")!)
                                    .foregroundStyle(Color(hex: "BB86FC"))
                            }
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Версия:")
                                    .fontWeight(.medium)
                                    .foregroundStyle(.white)
                                Text("1.0.2")
                                    .foregroundStyle(.white.opacity(0.9))
                            }
                        }
                    }
                }
                .padding(24)
                .background(Color(hex: "121212"))
                .cornerRadius(20)
                .padding(.horizontal, 32)
            }
        }
    }
}

struct PrivacyPolicyView: View {
    @Environment(\.dismiss) private var dismiss
    private let url = URL(string: "https://vertex-art.ru/privacy-v-portal")!

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack {
                HStack {
                    Text("Политика конфиденциальности")
                        .font(.headline)
                        .foregroundStyle(.white)
                    Spacer()
                    Button {
                        dismiss()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title3)
                            .foregroundStyle(.white.opacity(0.7))
                    }
                }
                .padding()

                SafariView(url: url)
            }
        }
    }
}

struct SafariView: UIViewControllerRepresentable {
    let url: URL

    func makeUIViewController(context: Context) -> SFSafariViewController {
        SFSafariViewController(url: url)
    }

    func updateUIViewController(_ uiViewController: SFSafariViewController, context: Context) {}
}

struct LinkButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .padding(.vertical, 4)
            .padding(.horizontal, 6)
            .opacity(configuration.isPressed ? 0.6 : 1.0)
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

struct MainView_Previews: PreviewProvider {
    static var previews: some View {
        MainView()
    }
}

