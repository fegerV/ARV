package ru.neuroimagen.arviewer

import android.content.ContentValues
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.view.LayoutInflater
import android.view.View
import android.view.animation.AlphaAnimation
import android.view.animation.LinearInterpolator
import android.widget.GridLayout
import android.widget.ImageView
import android.widget.ImageButton
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import coil.load
import com.google.gson.Gson
import ru.neuroimagen.arviewer.data.model.ViewerManifest
import ru.neuroimagen.arviewer.data.model.ViewerManifestVideo
import java.io.OutputStream

/**
 * Offline demo gallery for store reviewers and first-time users.
 *
 * Each card contains a built-in marker image that can be saved to gallery or
 * shared to another device. After opening the marker elsewhere, the user can
 * launch the matching AR demo directly from the card.
 */
class DemoIntroActivity : AppCompatActivity() {

    private lateinit var container: GridLayout
    private lateinit var progressView: View
    private lateinit var textError: TextView
    private val gson = Gson()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_demo_intro)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        container = findViewById(R.id.container_demo_cards)
        progressView = findViewById(R.id.progress_demo_loading)
        textError = findViewById(R.id.text_demo_error)

        startHeroStarAnimation()
        displayDemos(buildLocalDemos())
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun displayDemos(demos: List<LocalDemo>) {
        progressView.visibility = View.GONE
        textError.visibility = View.GONE
        container.visibility = View.VISIBLE
        container.removeAllViews()

        val inflater = LayoutInflater.from(this)
        demos.forEachIndexed { index, demo ->
            val card = inflater.inflate(R.layout.item_demo_card, container, false)
            val imageView = card.findViewById<ImageView>(R.id.image_demo_marker)
            val badgeView = card.findViewById<TextView>(R.id.text_demo_badge)
            val buttonSave = card.findViewById<ImageButton>(R.id.button_download_marker)
            val buttonShare = card.findViewById<ImageButton>(R.id.button_share_marker)

            badgeView.text = getString(R.string.demo_title_format, index + 1)
            imageView.load("file:///android_asset/${demo.markerAssetPath}")

            card.setOnClickListener { startDemo(demo) }
            imageView.setOnClickListener { startDemo(demo) }
            buttonSave.setOnClickListener { saveDemoMarker(demo) }
            buttonShare.setOnClickListener { shareDemoMarker(demo) }

            val params = GridLayout.LayoutParams().apply {
                width = 0
                height = GridLayout.LayoutParams.WRAP_CONTENT
                columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f)
                setMargins(0, 0, 0, dp(16))
            }
            card.layoutParams = params
            container.addView(card)
        }
    }

    private fun startHeroStarAnimation() {
        val stars = listOf(
            findViewById<View>(R.id.star_one),
            findViewById<View>(R.id.star_two),
            findViewById<View>(R.id.star_three),
        )
        stars.forEachIndexed { index, star ->
            val animation = AlphaAnimation(0.28f, 1f).apply {
                duration = 3300L + (index * 750L)
                repeatCount = AlphaAnimation.INFINITE
                repeatMode = AlphaAnimation.REVERSE
                interpolator = LinearInterpolator()
                startOffset = index * 420L
            }
            star.startAnimation(animation)
        }
    }

    private fun startDemo(demo: LocalDemo) {
        val manifest = ViewerManifest(
            manifestVersion = "1.0",
            uniqueId = demo.uniqueId,
            orderNumber = demo.orderNumber,
            markerImageUrl = "asset://${demo.markerAssetPath}",
            photoUrl = "asset://${demo.markerAssetPath}",
            video = ViewerManifestVideo(
                id = demo.videoId,
                title = demo.title,
                videoUrl = DEMO_VIDEO_URL,
                thumbnailUrl = null,
                duration = null,
                width = 320,
                height = 180,
                mimeType = "video/mp4",
                selectionSource = "demo",
                scheduleId = null,
                expiresInDays = null,
                selectedAt = null,
                previewUrl = null,
                isActive = true,
                rotationType = null,
                subscriptionEnd = null,
                videoCreatedAt = null,
            ),
            expiresAt = "2099-12-31T23:59:59Z",
            status = "active",
        )

        startActivity(
            Intent(this, ArViewerActivity::class.java).apply {
                putExtra(ArViewerActivity.EXTRA_MANIFEST_JSON, gson.toJson(manifest))
                putExtra(ArViewerActivity.EXTRA_UNIQUE_ID, demo.uniqueId)
            },
        )
    }

    private fun saveDemoMarker(demo: LocalDemo) {
        val bitmap = loadDemoBitmap(demo) ?: run {
            Toast.makeText(this, R.string.photo_save_failed, Toast.LENGTH_SHORT).show()
            return
        }
        val uri = saveBitmapToGallery(bitmap, demo)
        bitmap.recycle()
        if (uri != null) {
            Toast.makeText(this, R.string.photo_saved, Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, R.string.photo_save_failed, Toast.LENGTH_SHORT).show()
        }
    }

    private fun shareDemoMarker(demo: LocalDemo) {
        val bitmap = loadDemoBitmap(demo) ?: run {
            Toast.makeText(this, R.string.photo_save_failed, Toast.LENGTH_SHORT).show()
            return
        }
        val uri = saveBitmapToGallery(bitmap, demo)
        bitmap.recycle()
        if (uri == null) {
            Toast.makeText(this, R.string.photo_save_failed, Toast.LENGTH_SHORT).show()
            return
        }

        val shareIntent = Intent(Intent.ACTION_SEND).apply {
            type = "image/png"
            putExtra(Intent.EXTRA_STREAM, uri)
            putExtra(Intent.EXTRA_TEXT, getString(R.string.demo_save_hint))
            putExtra(Intent.EXTRA_TITLE, demo.title)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(shareIntent, getString(R.string.demo_share)))
    }

    private fun loadDemoBitmap(demo: LocalDemo): Bitmap? =
        runCatching {
            assets.open(demo.markerAssetPath).use { stream ->
                BitmapFactory.decodeStream(stream)
            }
        }.getOrNull()

    private fun saveBitmapToGallery(bitmap: Bitmap, demo: LocalDemo): Uri? {
        val fileName = "${demo.uniqueId}.png"
        val contentValues = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
            put(MediaStore.MediaColumns.MIME_TYPE, "image/png")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/V-Portal Demo")
            }
        }

        val uri = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            contentResolver.insert(
                MediaStore.Images.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY),
                contentValues,
            )
        } else {
            @Suppress("DEPRECATION")
            contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
        } ?: return null

        return try {
            contentResolver.openOutputStream(uri)?.use { output: OutputStream ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, output)
            }
            uri
        } catch (_: Exception) {
            null
        }
    }

    private fun buildLocalDemos(): List<LocalDemo> =
        listOf(
            LocalDemo("demo_local_1", "Портрет V-Portal", "demo/demo_marker_1.png", "VP-2401-001", 1),
            LocalDemo("demo_local_2", "Афиша мероприятия", "demo/demo_marker_2.png", "VP-2401-002", 2),
            LocalDemo("demo_local_3", "Упаковка продукта", "demo/demo_marker_3.png", "VP-2401-003", 3),
            LocalDemo("demo_local_4", "Меню ресторана", "demo/demo_marker_4.png", "VP-2401-004", 4),
            LocalDemo("demo_local_5", "Промо-постер", "demo/demo_marker_5.png", "VP-2401-005", 5),
            LocalDemo("demo_local_6", "Каталог для витрины", "demo/demo_marker_6.png", "VP-2401-006", 6),
        )

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private data class LocalDemo(
        val uniqueId: String,
        val title: String,
        val markerAssetPath: String,
        val orderNumber: String,
        val videoId: Int,
    )

    companion object {
        // Stable public sample video for the built-in demo mode.
        private const val DEMO_VIDEO_URL =
            "https://storage.googleapis.com/exoplayer-test-media-0/BigBuckBunny_320x180.mp4"
    }
}
