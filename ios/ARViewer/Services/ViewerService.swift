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
        return try JSONDecoder().decode(ViewerManifest.self, from: data)
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
}

private func rstripSlash(_ s: String) -> String {
    s.hasSuffix("/") ? String(s.dropLast()) : s
}
