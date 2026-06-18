# V-Portal iOS Development Plan

## Goal
Ship an iOS app with user flow parity to Android for the core scenario:
scan QR -> open AR content -> track viewing session.

## Current Status
- Done: QR scanner flow on iOS.
- Done: Manual input flow for `UUID` and `https://ar.neuroimagen.ru/view/{id}`.
- Done: In-app WebAR view (`/view/{id}`).
- Done: Session analytics via `POST /api/mobile/sessions`.
- Done (this iteration): QR from gallery image.
- Done (this iteration): GitHub Actions release workflow hardened for tags/manual runs.

## Roadmap
1. Core UX parity (in progress)
- Keep branded UI consistent with Android (`V-Portal` naming and labels).
- Add gallery QR import and robust error messages.
- Validate deep links end-to-end (`arv://view/{id}` and web links).

2. iOS product hardening
- Add first-launch privacy notice and consent state.
- Add localized strings (`ru`, `en`) via `Localizable.strings`.
- Add lightweight diagnostics for failed scans/network errors.

3. Release readiness
- Prepare App Store metadata, screenshots, privacy questionnaire.
- Enable TestFlight upload from GitHub Actions with signing secrets.
- Define versioning policy (`CFBundleShortVersionString` + incrementing build number).

## GitHub Actions
Yes, iOS can be built in GitHub Actions on `macos-*` runners.

Implemented pipeline split:
- `.github/workflows/build-mobile.yml`: unsigned simulator build for CI validation.
- `.github/workflows/ios-release.yml`: signed archive + IPA export (tag/manual), optional TestFlight upload.

## Next Milestone
Deliver iOS `1.0.0` beta to TestFlight with:
- QR camera scan
- QR from gallery
- AR Web view open
- privacy notice at first launch
