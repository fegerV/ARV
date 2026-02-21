//
//  WebARView.swift
//  ARViewer
//
//  Открывает /view/{unique_id} в WKWebView (Web AR на том же бэкенде).
//

import SwiftUI
import WebKit

struct WebARView: View {
    let uniqueId: String
    let orderNumber: String
    let onClose: () -> Void
    
    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text(orderNumber)
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
            
            if let url = ViewerService.shared.viewWebURL(uniqueId: uniqueId) {
                WebARWebView(url: url, uniqueId: uniqueId)
            } else {
                Text("Неверная ссылка")
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .ignoresSafeArea(edges: .bottom)
    }
}

private struct WebARWebView: UIViewRepresentable {
    let url: URL
    let uniqueId: String
    
    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isInspectable = true
        webView.load(URLRequest(url: url))
        Task {
            _ = try? await ViewerService.shared.createSession(uniqueId: uniqueId)
        }
        return webView
    }
    
    func updateUIView(_ uiView: WKWebView, context: Context) {}
}
