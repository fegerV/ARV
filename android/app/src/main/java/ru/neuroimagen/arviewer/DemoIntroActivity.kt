package ru.neuroimagen.arviewer

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import coil.load
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.data.api.DemoApi
import ru.neuroimagen.arviewer.data.api.DemoItem
import javax.inject.Inject

/**
 * Intro screen for demo mode: fetches 5 demos from server and shows cards.
 * User picks one, taps "Запустить" — AR viewer loads manifest from API.
 */
@AndroidEntryPoint
class DemoIntroActivity : AppCompatActivity() {

    @Inject lateinit var demoApi: DemoApi

    private lateinit var container: LinearLayout
    private lateinit var progressBar: ProgressBar
    private lateinit var textError: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_demo_intro)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        container = findViewById(R.id.container_demo_cards)
        progressBar = findViewById(R.id.progress_demo_loading)
        textError = findViewById(R.id.text_demo_error)

        loadDemoList()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }

    private fun loadDemoList() {
        lifecycleScope.launch {
            progressBar.visibility = View.VISIBLE
            textError.visibility = View.GONE
            container.visibility = View.GONE

            val result = withContext(Dispatchers.IO) {
                runCatching { demoApi.getDemoList() }
            }

            progressBar.visibility = View.GONE

            result.fold(
                onSuccess = { response ->
                    if (response.isSuccessful) {
                        val body = response.body()
                        val demos = body?.demos?.filter { it.marker_image_url != null }.orEmpty()
                        if (demos.isEmpty()) {
                            textError.visibility = View.VISIBLE
                            textError.text = getString(R.string.demo_load_error_empty)
                        } else {
                            displayDemos(demos)
                            container.visibility = View.VISIBLE
                        }
                    } else {
                        textError.visibility = View.VISIBLE
                        textError.text = getString(R.string.demo_load_error)
                    }
                },
                onFailure = {
                    textError.visibility = View.VISIBLE
                    textError.text = getString(R.string.demo_load_error)
                },
            )
        }
    }

    private fun displayDemos(demos: List<DemoItem>) {
        container.removeAllViews()
        val inflater = LayoutInflater.from(this)

        val baseUrl = ru.neuroimagen.arviewer.BuildConfig.API_BASE_URL.trimEnd('/')

        for (demo in demos) {
            val card = inflater.inflate(R.layout.item_demo_card, container, false)
            val imageView = card.findViewById<ImageView>(R.id.image_demo_marker)
            val titleView = card.findViewById<TextView>(R.id.text_demo_title)
            val button = card.findViewById<Button>(R.id.button_start_demo)
            val buttonDownload = card.findViewById<Button>(R.id.button_download_marker)
            val buttonShare = card.findViewById<Button>(R.id.button_share_marker)

            val markerUrl = demo.marker_image_url
            if (!markerUrl.isNullOrBlank()) {
                imageView.load(markerUrl) {
                    crossfade(true)
                    error(android.R.drawable.ic_menu_gallery)
                }
            }
            titleView.text = demo.title
            button.tag = demo.unique_id
            button.setOnClickListener {
                val uniqueId = (it.tag as? String) ?: return@setOnClickListener
                startArViewer(uniqueId)
            }

            buttonDownload.tag = markerUrl
            buttonDownload.setOnClickListener {
                val url = (it.tag as? String) ?: return@setOnClickListener
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            }

            val viewUrl = "$baseUrl/view/${demo.unique_id}"
            buttonShare.tag = viewUrl
            buttonShare.setOnClickListener {
                val url = (it.tag as? String) ?: return@setOnClickListener
                val shareIntent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, url)
                    putExtra(Intent.EXTRA_TITLE, demo.title)
                }
                startActivity(Intent.createChooser(shareIntent, getString(R.string.demo_share_marker)))
            }
            container.addView(card)
        }
    }

    private fun startArViewer(uniqueId: String) {
        startActivity(
            Intent(this, ArViewerActivity::class.java).apply {
                putExtra(ArViewerActivity.EXTRA_UNIQUE_ID, uniqueId)
            },
        )
        finish()
    }
}
