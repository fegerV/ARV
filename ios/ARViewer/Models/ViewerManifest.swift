//
//  ViewerManifest.swift
//  ARViewer
//
//  Модели ответа API viewer (check, manifest). Совместимы с бэкендом ARV.
//

import Foundation

// MARK: - Content check (GET /api/viewer/ar/{id}/check)
struct ContentCheckResponse: Codable {
    let contentAvailable: Bool
    let reason: String?
    
    enum CodingKeys: String, CodingKey {
        case contentAvailable = "content_available"
        case reason
    }
}

// MARK: - Manifest video
struct ViewerManifestVideo: Codable {
    let id: Int
    let title: String
    let videoUrl: String
    let thumbnailUrl: String?
    let duration: Int?
    let width: Int?
    let height: Int?
    let mimeType: String?
    let selectionSource: String?
    let scheduleId: Int?
    let expiresInDays: Int?
    let selectedAt: String?
    
    enum CodingKeys: String, CodingKey {
        case id, title, duration, width, height
        case videoUrl = "video_url"
        case thumbnailUrl = "thumbnail_url"
        case mimeType = "mime_type"
        case selectionSource = "selection_source"
        case scheduleId = "schedule_id"
        case expiresInDays = "expires_in_days"
        case selectedAt = "selected_at"
    }
}

// MARK: - Viewer manifest (GET /api/viewer/ar/{id}/manifest)
struct ViewerManifest: Codable {
    let manifestVersion: String
    let uniqueId: String
    let orderNumber: String
    let markerImageUrl: String
    let photoUrl: String
    let video: ViewerManifestVideo
    let expiresAt: String
    let status: String
    
    enum CodingKeys: String, CodingKey {
        case status
        case manifestVersion = "manifest_version"
        case uniqueId = "unique_id"
        case orderNumber = "order_number"
        case markerImageUrl = "marker_image_url"
        case photoUrl = "photo_url"
        case video
        case expiresAt = "expires_at"
    }
}
