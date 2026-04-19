//
//  NativeARViewerView.swift
//  ARViewer
//
//  Native AR viewer based on ARKit image tracking.
//

import ARKit
import AVFoundation
import SceneKit
import SwiftUI

struct NativeARViewerView: View {
    let manifest: ViewerManifest
    let forceRefreshAssets: Bool
    let onClose: () -> Void
    let onFallbackRequested: () -> Void

    @State private var runtimeError: String?

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text(manifest.orderNumber)
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                Button("Закрыть") {
                    onClose()
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(Color(UIColor.systemBackground))

            ZStack(alignment: .bottom) {
                NativeARContainerView(
                    manifest: manifest,
                    forceRefreshAssets: forceRefreshAssets,
                    onError: { message in
                        runtimeError = message
                    },
                    onFallbackRequested: onFallbackRequested
                )

                if let error = runtimeError {
                    Text(error)
                        .font(.footnote)
                        .multilineTextAlignment(.center)
                        .foregroundStyle(.white)
                        .padding(12)
                        .background(Color.black.opacity(0.7), in: RoundedRectangle(cornerRadius: 10))
                        .padding()
                }
            }
        }
        .ignoresSafeArea(edges: .bottom)
    }
}

private struct NativeARContainerView: UIViewControllerRepresentable {
    let manifest: ViewerManifest
    let forceRefreshAssets: Bool
    let onError: (String) -> Void
    let onFallbackRequested: () -> Void

    func makeUIViewController(context: Context) -> NativeARViewController {
        NativeARViewController(
            manifest: manifest,
            forceRefreshAssets: forceRefreshAssets,
            onError: onError,
            onFallbackRequested: onFallbackRequested
        )
    }

    func updateUIViewController(_ uiViewController: NativeARViewController, context: Context) {}
}

private final class NativeARViewController: UIViewController, ARSCNViewDelegate {
    private let manifest: ViewerManifest
    private let forceRefreshAssets: Bool
    private let onError: (String) -> Void
    private let onFallbackRequested: () -> Void

    private let sceneView = ARSCNView(frame: .zero)
    private var player: AVPlayer?
    private var loopObserver: NSObjectProtocol?
    private var videoCacheTask: Task<Void, Never>?
    private var cachedVideoURL: URL?
    private var hasShownVideo = false
    private var fallbackRequested = false

    init(
        manifest: ViewerManifest,
        forceRefreshAssets: Bool,
        onError: @escaping (String) -> Void,
        onFallbackRequested: @escaping () -> Void
    ) {
        self.manifest = manifest
        self.forceRefreshAssets = forceRefreshAssets
        self.onError = onError
        self.onFallbackRequested = onFallbackRequested
        super.init(nibName: nil, bundle: nil)
    }

    @available(*, unavailable)
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .black

        sceneView.frame = view.bounds
        sceneView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        sceneView.delegate = self
        sceneView.scene = SCNScene()
        view.addSubview(sceneView)
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        warmVideoCache()
        Task { [weak self] in
            await self?.startTrackingSession()
        }
    }

    override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        sceneView.session.pause()
        player?.pause()
        videoCacheTask?.cancel()
        if let loopObserver {
            NotificationCenter.default.removeObserver(loopObserver)
        }
    }

    private func startTrackingSession() async {
        guard ARImageTrackingConfiguration.isSupported else {
            reportFatalError("ARKit image tracking не поддерживается на этом устройстве.")
            return
        }

        guard let markerURL = URL(string: manifest.markerImageUrl) else {
            reportFatalError("Некорректная ссылка маркера.")
            return
        }

        do {
            let image = try await ViewerService.shared.loadMarkerImage(
                uniqueId: manifest.uniqueId,
                markerURL: markerURL.absoluteString,
                forceRefresh: forceRefreshAssets
            )
            guard let cgImage = image.cgImage else {
                reportFatalError("Не удалось загрузить изображение маркера.")
                return
            }

            let refImage = ARReferenceImage(cgImage, orientation: .up, physicalWidth: 0.2)
            refImage.name = manifest.uniqueId

            let config = ARImageTrackingConfiguration()
            config.trackingImages = [refImage]
            config.maximumNumberOfTrackedImages = 1

            sceneView.session.run(config, options: [.resetTracking, .removeExistingAnchors])
        } catch {
            reportFatalError("Ошибка запуска AR-сессии: \(error.localizedDescription)")
        }
    }

    func renderer(_ renderer: SCNSceneRenderer, didAdd node: SCNNode, for anchor: ARAnchor) {
        guard let imageAnchor = anchor as? ARImageAnchor else { return }
        if hasShownVideo { return }
        hasShownVideo = true

        guard let videoURL = cachedVideoURL ?? URL(string: manifest.video.videoUrl) else {
            reportError("Некорректная ссылка видео.")
            return
        }

        let videoAspect: CGFloat = {
            if let w = manifest.video.width, let h = manifest.video.height, h > 0 {
                return CGFloat(w) / CGFloat(h)
            }
            return 16.0 / 9.0
        }()

        let width = imageAnchor.referenceImage.physicalSize.width
        let height = width / max(videoAspect, 0.01)

        let plane = SCNPlane(width: width, height: height)
        plane.cornerRadius = 0
        plane.firstMaterial?.isDoubleSided = true

        let player = AVPlayer(url: videoURL)
        plane.firstMaterial?.diffuse.contents = player
        self.player = player

        let planeNode = SCNNode(geometry: plane)
        planeNode.position = SCNVector3(0, 0, 0.001)
        node.addChildNode(planeNode)

        loopObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: player.currentItem,
            queue: .main
        ) { _ in
            player.seek(to: .zero)
            player.play()
        }

        DispatchQueue.main.async {
            player.play()
        }
    }

    private func warmVideoCache() {
        if !forceRefreshAssets {
            cachedVideoURL = ViewerService.shared.cachedVideoURLIfAvailable(
                uniqueId: manifest.uniqueId,
                video: manifest.video
            )
        }

        videoCacheTask?.cancel()
        let manifest = self.manifest
        let forceRefresh = self.forceRefreshAssets
        videoCacheTask = Task { [weak self] in
            guard let localURL = try? await ViewerService.shared.cacheVideo(
                uniqueId: manifest.uniqueId,
                video: manifest.video,
                forceRefresh: forceRefresh
            ), !Task.isCancelled else {
                return
            }
            DispatchQueue.main.async {
                self?.cachedVideoURL = localURL
            }
        }
    }

    private func reportError(_ message: String) {
        DispatchQueue.main.async {
            self.onError(message)
        }
    }

    private func reportFatalError(_ message: String) {
        reportError(message)
        guard !fallbackRequested else { return }
        fallbackRequested = true
        DispatchQueue.main.async {
            self.onFallbackRequested()
        }
    }
}
