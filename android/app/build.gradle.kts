import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.devtools.ksp")
    id("com.google.dagger.hilt.android")
    id("com.google.gms.google-services")
    id("com.google.firebase.crashlytics")
}

android {
    namespace = "ru.neuroimagen.arviewer"
    compileSdk = 35

    defaultConfig {
        applicationId = "ru.neuroimagen.arviewer"
        minSdk = 24
        targetSdk = 35
        versionCode = 2
        versionName = "1.0.1"
        buildConfigField("String", "API_BASE_URL", "\"https://ar.neuroimagen.ru\"")
    }

    signingConfigs {
        val keystorePropsFile = file("keystore.properties")
        if (keystorePropsFile.exists()) {
            create("release") {
                val keystoreProps = Properties()
                keystoreProps.load(keystorePropsFile.inputStream())
                storeFile = file(keystoreProps["storeFile"]!!.toString())
                storePassword = keystoreProps["storePassword"]!!.toString()
                keyAlias = keystoreProps["keyAlias"]!!.toString()
                keyPassword = keystoreProps["keyPassword"]!!.toString()
            }
        }
    }

    buildTypes {
        debug {
            buildConfigField("String", "API_BASE_URL", "\"https://ar.neuroimagen.ru\"")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            signingConfigs.findByName("release")?.let { signingConfig = it }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        viewBinding = true
        buildConfig = true
    }
}

dependencies {
    // Kotlin & Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")

    // AndroidX Core
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.core:core-splashscreen:1.0.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.activity:activity-ktx:1.10.0")

    // Lifecycle & ViewModel
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7")

    // UI
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // Hilt DI
    implementation("com.google.dagger:hilt-android:2.51.1")
    ksp("com.google.dagger:hilt-android-compiler:2.51.1")

    // ARCore
    implementation("com.google.ar:core:1.52.0")

    // Network
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.retrofit2:retrofit:2.12.0")
    implementation("com.squareup.retrofit2:converter-gson:2.12.0")

    // Media3 (replaces deprecated ExoPlayer)
    val media3Version = "1.7.1"
    implementation("androidx.media3:media3-exoplayer:$media3Version")
    implementation("androidx.media3:media3-datasource:$media3Version")
    implementation("androidx.media3:media3-database:$media3Version")

    // CameraX
    val cameraxVersion = "1.4.0"
    implementation("androidx.camera:camera-core:$cameraxVersion")
    implementation("androidx.camera:camera-camera2:$cameraxVersion")
    implementation("androidx.camera:camera-lifecycle:$cameraxVersion")
    implementation("androidx.camera:camera-view:$cameraxVersion")

    // ML Kit Barcode Scanning
    implementation("com.google.mlkit:barcode-scanning:17.3.0")

    // Firebase Crashlytics & Analytics
    implementation(platform("com.google.firebase:firebase-bom:33.6.0"))
    implementation("com.google.firebase:firebase-crashlytics-ktx")
    implementation("com.google.firebase:firebase-analytics-ktx")
}
