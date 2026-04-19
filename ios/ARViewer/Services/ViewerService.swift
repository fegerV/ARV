//
//  ViewerService.swift
//  ARViewer
//
//  Загрузка check + manifest, создание сессии аналитики (mobile/sessions, ar-session).
//

import Foundation
import UIKit

enum ViewerError: Error {
    case invalidId
    case unavailable(reason: String)
    case server(code: Int, message: String?)
    case network(Error)
}

final class ViewerService {
    static let shared = ViewerService()
    
    /// Базовый URL API (без завершающего слэша). По умолчанию — production.
    var baseURL: String = "https://ar.neuroimagen.ru"
    
    private let session: URLSession = {
        let c = URLSessionConfiguration.default
        c.timeoutIntervalForRequest = 20
        c.timeoutIntervalForResource = 30
        return URLSession(configuration: c)
    }()

    private let manifestCacheTTL: TimeInterval = 7 * 24 * 60 * 60
    private let markerCacheTTL: TimeInterval = 7 * 24 * 60 * 60
    private let videoCacheTTL: TimeInterval = 7 * 24 * 60 * 60
    private let videoCacheMaxBytes: Int64 = 256 * 1024 * 1024
    private let cacheDirectory: URL = {
        let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first
            ?? URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
        return base.appendingPathComponent("ViewerCache", isDirectory: true)
    }()
    
    private init() {}
    
    // MARK: - Check
    
    /// GET /api/viewer/ar/{uniqueId}/check
    func checkContent(uniqueId: String) async throws -> ContentCheckResponse {
        let url = try checkURL(uniqueId: uniqueId)
        let (data, response) = try await session.data(from: url)
        try validateResponse(response, data: data, url: url)
        let decoded = try JSONDecoder().decode(ContentCheckResponse.self, from: data)
        if !decoded.contentAvailable {
            throw ViewerError.unavailable(reason: decoded.reason ?? "content_unavailable")
        }
        return decoded
    }
    
    // MARK: - Manifest
    
    /// GET /api/viewer/ar/{uniqueId}/manifest
    func loadManifest(uniqueId: String) async throws -> ViewerManifest {
        let url = try manifestURL(uniqueId: uniqueId)
        let (data, response) = try await session.data(from: url)
        try validateResponse(response, data: data, url: url)
        let manifest = try JSONDecoder().decode(ViewerManifest.self, from: data)
        try? saveManifestToCache(manifest, uniqueId: uniqueId)
        return manifest
    }

    /// Cache-first manifest loading to mirror Android UX on repeated opens.
    /// Returns cached manifest immediately when available and refreshes it in background.
    func prepareManifest(uniqueId: String, forceRefresh: Bool = false) async throws -> ViewerManifest {
        let normalizedId = uniqueId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalizedId.isEmpty else {
            throw ViewerError.invalidId
        }

        if !forceRefresh, let cached = loadManifestFromCache(uniqueId: normalizedId) {
            Task.detached(priority: .utility) { [weak self] in
                guard let self else { return }
                try? await self.refreshManifest(uniqueId: normalizedId)
            }
            return cached
        }

        return try await refreshManifest(uniqueId: normalizedId)
    }

    // MARK: - Demo list

    /// GET /api/viewer/demo/list
    func loadDemoList() async throws -> [DemoItem] {
        guard let url = URL(string: "\(rstripSlash(baseURL))/api/viewer/demo/list") else {
            throw ViewerError.invalidId
        }
        let (data, response) = try await session.data(from: url)
        try validateResponse(response, data: data, url: url)
        return try JSONDecoder().decode(DemoListResponse.self, from: data).demos
    }
    
    // MARK: - Analytics: создать сессию (POST /api/mobile/sessions), затем обновить (POST /api/mobile/analytics)
    
    /// Создаёт сессию просмотра. Вызвать при старте просмотра. Возвращает session_id (UUID).
    func createSession(uniqueId: String) async throws -> String {
        let sessionId = UUID().uuidString
        let url = URL(string: "\(rstripSlash(baseURL))/api/mobile/sessions")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body: [String: Any] = [
            "ar_content_unique_id": uniqueId,
            "session_id": sessionId,
            "device_type": "mobile",
            "device_model": deviceModel,
            "os": "iOS",
            "user_agent": userAgent
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw ViewerError.network(NSError(domain: "ViewerService", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"]))
        }
        if http.statusCode == 200 {
            return sessionId
        }
        if http.statusCode == 404 {
            throw ViewerError.unavailable(reason: "not_found")
        }
        throw ViewerError.server(code: http.statusCode, message: String(data: data, encoding: .utf8))
    }
    
    /// Обновить сессию (длительность, video_played). Опционально.
    func updateSession(sessionId: String, durationSeconds: Int?, videoPlayed: Bool?) async {
        guard let url = URL(string: "\(rstripSlash(baseURL))/api/mobile/analytics") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        var body: [String: Any] = ["session_id": sessionId]
        if let d = durationSeconds { body["duration_seconds"] = d }
        if let v = videoPlayed { body["video_played"] = v }
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        _ = try? await session.data(for: request)
    }
    
    // MARK: - URLs
    
    func checkURL(uniqueId: String) throws -> URL {
        guard let encoded = uniqueId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) else {
            throw ViewerError.invalidId
        }
        guard let url = URL(string: "\(rstripSlash(baseURL))/api/viewer/ar/\(encoded)/check") else {
            throw ViewerError.invalidId
        }
        return url
    }
    
    func manifestURL(uniqueId: String) throws -> URL {
        guard let encoded = uniqueId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) else {
            throw ViewerError.invalidId
        }
        guard let url = URL(string: "\(rstripSlash(baseURL))/api/viewer/ar/\(encoded)/manifest") else {
            throw ViewerError.invalidId
        }
        return url
    }
    
    /// URL веб-просмотра AR (тот же бэкенд, /view/{id}).
    func viewWebURL(uniqueId: String) -> URL? {
        URL(string: "\(rstripSlash(baseURL))/view/\(uniqueId)")
    }

    // MARK: - Marker image

    func loadMarkerImage(uniqueId: String, markerURL: String, forceRefresh: Bool = false) async throws -> UIImage {
        let normalizedId = uniqueId.trimmingCharacters(in: .whitespacesAndNewlines)
        if !forceRefresh, let cachedImage = loadCachedMarkerImage(uniqueId: normalizedId) {
            Task.detached(priority: .utility) { [weak self] in
                guard let self else { return }
                try? await self.refreshMarkerImage(uniqueId: normalizedId, markerURL: markerURL)
            }
            return cachedImage
        }

        return try await refreshMarkerImage(uniqueId: normalizedId, markerURL: markerURL)
    }

    // MARK: - Video

    func cachedVideoURLIfAvailable(uniqueId: String, video: ViewerManifestVideo) -> URL? {
        guard isRemoteURL(video.videoUrl) else {
            return URL(string: video.videoUrl)
        }
        let url = videoCacheURL(uniqueId: uniqueId, video: video)
        return isCacheEntryFresh(url: url, ttl: videoCacheTTL) ? url : nil
    }

    @discardableResult
    func cacheVideo(uniqueId: String, video: ViewerManifestVideo, forceRefresh: Bool = false) async throws -> URL {
        let normalizedId = uniqueId.trimmingCharacters(in: .whitespacesAndNewlines)
        if !forceRefresh, let cachedURL = cachedVideoURLIfAvailable(uniqueId: normalizedId, video: video) {
            return cachedURL
        }

        guard let remoteURL = URL(string: video.videoUrl), isRemoteURL(video.videoUrl) else {
            throw ViewerError.invalidId
        }

        let destination = videoCacheURL(uniqueId: normalizedId, video: video)
        do {
            let (downloadedURL, response) = try await session.download(from: remoteURL)
            try validateDownloadResponse(response)
            try? FileManager.default.removeItem(at: destination)
            try FileManager.default.moveItem(at: downloadedURL, to: destination)
            pruneVideoCacheIfNeeded()
            return destination
        } catch {
            if let staleURL = existingVideoCacheURL(uniqueId: normalizedId, video: video) {
                return staleURL
            }
            throw error
        }
    }
    
    // MARK: - Helpers
    
    private func validateResponse(_ response: URLResponse, data: Data, url: URL) throws {
        guard let http = response as? HTTPURLResponse else { return }
        if http.statusCode == 200 { return }
        if http.statusCode == 404 {
            throw ViewerError.unavailable(reason: "not_found")
        }
        if http.statusCode == 403 {
            throw ViewerError.unavailable(reason: "subscription_expired")
        }
        throw ViewerError.server(code: http.statusCode, message: String(data: data, encoding: .utf8))
    }
    
    private var deviceModel: String {
        var systemInfo = utsname()
        uname(&systemInfo)
        let machine = withUnsafePointer(to: &systemInfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) { String(cString: $0) }
        }
        return machine
    }
    
    private var userAgent: String {
        "ARViewer-iOS/1.0 (\(UIDevice.current.systemVersion))"
    }

    private func refreshManifest(uniqueId: String) async throws -> ViewerManifest {
        _ = try await checkContent(uniqueId: uniqueId)
        return try await loadManifest(uniqueId: uniqueId)
    }

    private func refreshMarkerImage(uniqueId: String, markerURL: String) async throws -> UIImage {
        guard let url = URL(string: markerURL) else {
            throw ViewerError.invalidId
        }
        let (data, response) = try await session.data(from: url)
        try validateBinaryResponse(response, data: data)
        guard let image = UIImage(data: data) else {
            throw ViewerError.server(code: -1, message: "Invalid marker image")
        }
        try? saveMarkerImageToCache(data, uniqueId: uniqueId)
        return image
    }

    private func validateBinaryResponse(_ response: URLResponse, data: Data) throws {
        guard let http = response as? HTTPURLResponse else { return }
        if (200...299).contains(http.statusCode) { return }
        throw ViewerError.server(code: http.statusCode, message: String(data: data, encoding: .utf8))
    }

    private func validateDownloadResponse(_ response: URLResponse) throws {
        guard let http = response as? HTTPURLResponse else { return }
        if (200...299).contains(http.statusCode) { return }
        throw ViewerError.server(code: http.statusCode, message: nil)
    }

    private func cacheFileURL(name: String) -> URL {
        try? FileManager.default.createDirectory(at: cacheDirectory, withIntermediateDirectories: true)
        return cacheDirectory.appendingPathComponent(name)
    }

    private func manifestCacheURL(uniqueId: String) -> URL {
        cacheFileURL(name: "manifest_\(cacheKey(from: uniqueId)).json")
    }

    private func markerCacheURL(uniqueId: String) -> URL {
        cacheFileURL(name: "marker_\(cacheKey(from: uniqueId)).bin")
    }

    private func videoCacheURL(uniqueId: String, video: ViewerManifestVideo) -> URL {
        let ext = videoFileExtension(video: video)
        return cacheFileURL(name: "video_\(cacheKey(from: uniqueId))_\(video.id).\(ext)")
    }

    private func loadManifestFromCache(uniqueId: String) -> ViewerManifest? {
        let url = manifestCacheURL(uniqueId: uniqueId)
        guard let data = try? Data(contentsOf: url),
              let envelope = try? JSONDecoder().decode(CachedManifestEnvelope.self, from: data),
              Date().timeIntervalSince1970 - envelope.cachedAt <= manifestCacheTTL else {
            return nil
        }
        return envelope.manifest
    }

    private func saveManifestToCache(_ manifest: ViewerManifest, uniqueId: String) throws {
        let envelope = CachedManifestEnvelope(
            cachedAt: Date().timeIntervalSince1970,
            manifest: manifest
        )
        let data = try JSONEncoder().encode(envelope)
        try data.write(to: manifestCacheURL(uniqueId: uniqueId), options: .atomic)
    }

    private func loadCachedMarkerImage(uniqueId: String) -> UIImage? {
        let url = markerCacheURL(uniqueId: uniqueId)
        guard isCacheEntryFresh(url: url, ttl: markerCacheTTL),
              let data = try? Data(contentsOf: url) else {
            return nil
        }
        return UIImage(data: data)
    }

    private func saveMarkerImageToCache(_ data: Data, uniqueId: String) throws {
        try data.write(to: markerCacheURL(uniqueId: uniqueId), options: .atomic)
    }

    private func existingVideoCacheURL(uniqueId: String, video: ViewerManifestVideo) -> URL? {
        let url = videoCacheURL(uniqueId: uniqueId, video: video)
        return FileManager.default.fileExists(atPath: url.path) ? url : nil
    }

    private func pruneVideoCacheIfNeeded() {
        guard let files = try? FileManager.default.contentsOfDirectory(
            at: cacheDirectory,
            includingPropertiesForKeys: [.contentModificationDateKey, .fileSizeKey],
            options: [.skipsHiddenFiles]
        ) else {
            return
        }

        let videoFiles = files.filter { $0.lastPathComponent.hasPrefix("video_") }
        let entries: [(url: URL, modified: Date, size: Int64)] = videoFiles.compactMap { url in
            guard let values = try? url.resourceValues(forKeys: [.contentModificationDateKey, .fileSizeKey]),
                  let modified = values.contentModificationDate,
                  let size = values.fileSize else {
                return nil
            }
            return (url, modified, Int64(size))
        }

        var total = entries.reduce(Int64(0)) { $0 + $1.size }
        for entry in entries.sorted(by: { $0.modified < $1.modified }) where total > videoCacheMaxBytes {
            try? FileManager.default.removeItem(at: entry.url)
            total -= entry.size
        }
    }

    private func videoFileExtension(video: ViewerManifestVideo) -> String {
        if let ext = URL(string: video.videoUrl)?.pathExtension, !ext.isEmpty {
            return cacheKey(from: ext.lowercased())
        }
        if video.mimeType?.lowercased().contains("quicktime") == true {
            return "mov"
        }
        return "mp4"
    }

    private func isRemoteURL(_ raw: String) -> Bool {
        guard let scheme = URL(string: raw)?.scheme?.lowercased() else {
            return false
        }
        return scheme == "http" || scheme == "https"
    }

    private func isCacheEntryFresh(url: URL, ttl: TimeInterval) -> Bool {
        guard let attrs = try? FileManager.default.attributesOfItem(atPath: url.path),
              let modified = attrs[.modificationDate] as? Date else {
            return false
        }
        return Date().timeIntervalSince(modified) <= ttl
    }

    private func cacheKey(from uniqueId: String) -> String {
        let allowed = CharacterSet.alphanumerics
        return uniqueId.unicodeScalars.map { allowed.contains($0) ? String($0) : "_" }.joined()
    }
}

private struct CachedManifestEnvelope: Codable {
    let cachedAt: TimeInterval
    let manifest: ViewerManifest
}

private func rstripSlash(_ s: String) -> String {
    s.hasSuffix("/") ? String(s.dropLast()) : s
}
