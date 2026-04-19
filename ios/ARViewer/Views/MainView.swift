//
//  MainView.swift
//  ARViewer
//
//  Главный экран: сканер QR, ввод ID вручную, кнопка «Открыть».
//

import SwiftUI
import SafariServices
import CoreImage
import UIKit

struct MainView: View {
    @Environment(\.openURL) private var openURL
    @AppStorage("privacy_consent_accepted_v1") private var privacyConsentAccepted = false

    @State private var uniqueIdInput: String = ""
    @State private var isLoading = false
    @State private var errorMessage: String?
    @State private var showQRScanner = false
    @State private var showWebAR = false
    @State private var loadedManifest: ViewerManifest?
    @State private var forceRefreshAssets = false
    @State private var useNativeARViewer = true
    @State private var showPhotoPicker = false
    @State private var showHowToUseDialog = false
    @State private var showDemoPicker = false
    @State private var demoItems: [DemoItem] = []

    // Dialog states
    @State private var showAboutDialog = false
    @State private var showSupportDialog = false
    @State private var showPrivacyPolicy = false
    
    var body: some View {
        NavigationView {
            ZStack {
                Color(.systemGroupedBackground).ignoresSafeArea()
                
                if showWebAR, let manifest = loadedManifest {
                    if useNativeARViewer {
                        NativeARViewerView(
                            manifest: manifest,
                            forceRefreshAssets: forceRefreshAssets,
                            onClose: {
                                showWebAR = false
                                loadedManifest = nil
                                forceRefreshAssets = false
                            },
                            onFallbackRequested: {
                                useNativeARViewer = false
                            }
                        )
                    } else {
                        WebARView(
                            uniqueId: manifest.uniqueId,
                            orderNumber: manifest.orderNumber,
                            onClose: {
                                showWebAR = false
                                loadedManifest = nil
                                forceRefreshAssets = false
                                useNativeARViewer = true
                            }
                        )
                    }
                } else if showQRScanner {
                    QRScannerView(
                        onScanned: { id in
                            uniqueIdInput = id
                            showQRScanner = false
                            openViewer(uniqueId: id, forceRefresh: true)
                        },
                        onCancel: {
                            showQRScanner = false
                        }
                    )
                } else {
                    mainContent
                }
            }
            .navigationTitle("V-Portal")
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
        .fullScreenCover(isPresented: $showHowToUseDialog) {
            HowToUseDialogView()
        }
        .sheet(isPresented: $showPhotoPicker) {
            PhotoQRPickerView(
                onPicked: { image in
                    handlePickedImage(image)
                },
                onCancel: {}
            )
        }
        .sheet(isPresented: $showDemoPicker) {
            DemoPickerSheetView(
                demos: demoItems,
                onSelect: { uniqueId in
                    showDemoPicker = false
                    openViewer(uniqueId: uniqueId)
                },
                onClose: {
                    showDemoPicker = false
                }
            )
        }
        .fullScreenCover(
            isPresented: Binding(
                get: { !privacyConsentAccepted },
                set: { _ in }
            )
        ) {
            PrivacyConsentView(onAccept: {
                privacyConsentAccepted = true
            })
        }
    }
    
    private var mainContent: some View {
        ScrollView {
            VStack(spacing: 24) {
                logoSection
                scanButton
                galleryButton
                manualInputSection
                quickActionSection
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
                openViewer(uniqueId: id, forceRefresh: true)
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

    private var galleryButton: some View {
        Button {
            showPhotoPicker = true
        } label: {
            Label("Загрузить QR из галереи", systemImage: "photo.on.rectangle")
                .font(.headline)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
        }
        .buttonStyle(.bordered)
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

    private var quickActionSection: some View {
        VStack(spacing: 10) {
            Button {
                loadDemoAndOpenPicker()
            } label: {
                Label("Попробовать демо", systemImage: "sparkles.rectangle.stack")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)

            Button {
                showHowToUseDialog = true
            } label: {
                Label("Как использовать", systemImage: "questionmark.circle")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)

            Button {
                openOrderPage()
            } label: {
                Label("Заказать AR", systemImage: "plus.circle")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
        }
        .tint(.primary)
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
    
    private func openViewer(uniqueId: String, forceRefresh: Bool = false) {
        errorMessage = nil
        isLoading = true
        Task {
            do {
                let manifest = try await ViewerService.shared.prepareManifest(
                    uniqueId: uniqueId,
                    forceRefresh: forceRefresh
                )
                await MainActor.run {
                    loadedManifest = manifest
                    forceRefreshAssets = forceRefresh
                    useNativeARViewer = true
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

    private func loadDemoAndOpenPicker() {
        errorMessage = nil
        isLoading = true
        Task {
            do {
                let demos = try await ViewerService.shared.loadDemoList()
                await MainActor.run {
                    isLoading = false
                    demoItems = demos
                    if demos.isEmpty {
                        errorMessage = "Демо пока недоступны."
                    } else {
                        showDemoPicker = true
                    }
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    errorMessage = "Не удалось загрузить демо. Проверьте интернет."
                }
            }
        }
    }

    private func openOrderPage() {
        guard let url = URL(string: "https://vertex-art.ru/ar") else { return }
        openURL(url)
    }

    private func handlePickedImage(_ image: UIImage) {
        errorMessage = nil

        guard let payload = parseQRCodePayload(from: image) else {
            errorMessage = "Не удалось найти QR-код на изображении."
            return
        }

        guard let uniqueId = UniqueIdParser.extractFromInput(payload) else {
            errorMessage = "QR-код распознан, но ссылка или ID не относятся к V-Portal."
            return
        }

        uniqueIdInput = uniqueId
        openViewer(uniqueId: uniqueId, forceRefresh: true)
    }

    private func parseQRCodePayload(from image: UIImage) -> String? {
        var ciImage: CIImage?
        if let cg = image.cgImage {
            ciImage = CIImage(cgImage: cg)
        } else if let data = image.pngData() {
            ciImage = CIImage(data: data)
        }
        guard let sourceImage = ciImage else { return nil }

        let detector = CIDetector(
            ofType: CIDetectorTypeQRCode,
            context: nil,
            options: [CIDetectorAccuracy: CIDetectorAccuracyHigh]
        )
        let features = detector?.features(in: sourceImage) ?? []

        for feature in features {
            guard let qrFeature = feature as? CIQRCodeFeature,
                  let payload = qrFeature.messageString else { continue }
            if UniqueIdParser.extractFromInput(payload) != nil {
                return payload
            }
        }
        return nil
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
    
    private var appVersion: String {
        let shortVersion = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "-"
        let build = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "-"
        return "\(shortVersion) (\(build))"
    }

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
                                Text(appVersion)
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

struct HowToUseDialogView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ZStack {
            Color.black.opacity(0.8).ignoresSafeArea()

            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        Text("Как использовать")
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

                    Text("1. Купите подарок с QR-кодом")
                    Text("2. Установите приложение")
                    Text("3. Нажмите «Сканировать QR-код»")
                    Text("4. Наведите камеру на QR-код")
                    Text("5. Смотрите, как изображение оживает")
                }
                .foregroundStyle(.white.opacity(0.94))
                .padding(24)
                .background(Color(hex: "121212"))
                .cornerRadius(20)
                .padding(.horizontal, 32)
            }
        }
    }
}

struct PrivacyConsentView: View {
    @Environment(\.openURL) private var openURL
    let onAccept: () -> Void

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            VStack(alignment: .leading, spacing: 16) {
                Text("Политика конфиденциальности")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundStyle(.white)

                Text("Перед первым использованием приложения ознакомьтесь с политикой конфиденциальности и подтвердите согласие на обработку данных.")
                    .foregroundStyle(.white.opacity(0.9))

                Button("Открыть политику") {
                    guard let url = URL(string: "https://vertex-art.ru/privacy-v-portal") else { return }
                    openURL(url)
                }
                .buttonStyle(.bordered)

                Button("Принимаю и продолжить") {
                    onAccept()
                }
                .buttonStyle(.borderedProminent)
            }
            .padding(24)
        }
        .interactiveDismissDisabled(true)
    }
}

struct DemoPickerSheetView: View {
    let demos: [DemoItem]
    let onSelect: (String) -> Void
    let onClose: () -> Void

    var body: some View {
        NavigationView {
            List(demos) { demo in
                Button {
                    onSelect(demo.uniqueId)
                } label: {
                    HStack(spacing: 12) {
                        if let marker = demo.markerImageUrl, let url = URL(string: marker) {
                            AsyncImage(url: url) { image in
                                image
                                    .resizable()
                                    .scaledToFill()
                            } placeholder: {
                                Color.gray.opacity(0.2)
                            }
                            .frame(width: 64, height: 64)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        } else {
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.gray.opacity(0.2))
                                .frame(width: 64, height: 64)
                        }
                        VStack(alignment: .leading, spacing: 2) {
                            Text(demo.title)
                                .font(.headline)
                            Text(demo.uniqueId)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
                .buttonStyle(.plain)
            }
            .navigationTitle("Демо AR")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Закрыть") {
                        onClose()
                    }
                }
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

