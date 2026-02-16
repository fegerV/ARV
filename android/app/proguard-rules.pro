# ── General ───────────────────────────────────────────────────────
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes InnerClasses
-keepattributes EnclosingMethod

# ── Kotlin Coroutines ─────────────────────────────────────────────
-keep class kotlinx.coroutines.** { *; }
-dontwarn kotlinx.coroutines.**

# ── Retrofit ──────────────────────────────────────────────────────
-keep,allowobfuscation,allowshrinking interface retrofit2.Call
-keep,allowobfuscation,allowshrinking class retrofit2.Response
-keep,allowobfuscation,allowshrinking class kotlin.coroutines.Continuation

# ── Gson — keep model fields for (de)serialization ───────────────
-keep class ru.neuroimagen.arviewer.data.model.** { <fields>; }

# ── OkHttp ────────────────────────────────────────────────────────
-dontwarn okhttp3.internal.platform.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**

# ── ARCore ────────────────────────────────────────────────────────
-keep class com.google.ar.** { *; }

# ── Media3 ────────────────────────────────────────────────────────
-dontwarn androidx.media3.**

# ── ML Kit ────────────────────────────────────────────────────────
-dontwarn com.google.mlkit.**

# ── Hilt (consumer rules ship with AAR, these are safety extras) ─
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }
-keep @dagger.hilt.android.lifecycle.HiltViewModel class * { *; }
-keep @dagger.hilt.InstallIn class * { *; }

# ── Firebase Crashlytics ─────────────────────────────────────────
-keepattributes SourceFile,LineNumberTable
-keep public class * extends java.lang.Exception