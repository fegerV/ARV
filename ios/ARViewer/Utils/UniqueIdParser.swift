//
//  UniqueIdParser.swift
//  ARViewer
//
//  Извлечение unique_id из UUID, URL (https://ar.neuroimagen.ru/view/{id}), arv://view/{id}.
//

import Foundation

enum UniqueIdParser {
    private static let expectedHost = "ar.neuroimagen.ru"
    private static let uuidPattern = try! NSRegularExpression(
        pattern: "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )
    
    /// Проверяет, что строка — валидный UUID (формат).
    static func isValidUUID(_ s: String) -> Bool {
        let range = NSRange(s.trimmingCharacters(in: .whitespaces).startIndex..., in: s)
        return uuidPattern.firstMatch(in: s, range: range) != nil
    }
    
    /// Извлекает unique_id из ввода пользователя: сырой UUID или URL.
    static func extractFromInput(_ input: String) -> String? {
        let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
        if isValidUUID(trimmed) { return trimmed }
        guard let url = URL(string: trimmed) else { return nil }
        return parseFromURL(url)
    }
    
    /// Извлекает unique_id из URL (deep link или https).
    static func parseFromURL(_ url: URL) -> String? {
        if url.scheme?.lowercased() == "arv" {
            return parseArvScheme(url)
        }
        if url.scheme?.lowercased() == "https" || url.scheme?.lowercased() == "http" {
            return parseHTTPScheme(url)
        }
        return nil
    }
    
    static func looksLikeURL(_ input: String) -> Bool {
        let t = input.trimmingCharacters(in: .whitespacesAndNewlines)
        return t.hasPrefix("http://") || t.hasPrefix("https://") || t.hasPrefix("arv://")
    }
    
    private static func parseArvScheme(_ url: URL) -> String? {
        guard url.host?.lowercased() == "view" else { return nil }
        let path = url.path.trimmingCharacters(in: "/")
        let first = path.split(separator: "/").first.flatMap(String.init) ?? path
        return first.isEmpty ? nil : (isValidUUID(first) ? first : nil)
    }
    
    private static func parseHTTPScheme(_ url: URL) -> String? {
        guard url.host?.lowercased() == expectedHost else { return nil }
        let comps = url.pathComponents.filter { $0 != "/" }
        if comps.count >= 2 && comps[0].lowercased() == "view" {
            let id = comps[1]
            return isValidUUID(id) ? id : nil
        }
        return nil
    }
}
