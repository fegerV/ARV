package ru.neuroimagen.arviewer

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.data.api.ApiProvider
import ru.neuroimagen.arviewer.data.model.ViewerError
import ru.neuroimagen.arviewer.databinding.ActivityMainBinding
import ru.neuroimagen.arviewer.ui.ViewerErrorMessages

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val repository get() = ApiProvider.viewerRepository
    private val gson = Gson()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.buttonOpen.setOnClickListener { onOpenClicked() }
        binding.buttonRetry.setOnClickListener { showMainPanel() }

        handleIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        val data: Uri = intent?.data ?: return
        val uniqueId = parseUniqueIdFromUri(data) ?: return
        if (uniqueId.isNotBlank()) {
            binding.editUniqueId.setText(uniqueId)
            openViewer(uniqueId)
        }
    }

    private fun onOpenClicked() {
        val uniqueId = binding.editUniqueId.text.toString().trim()
        if (uniqueId.isEmpty()) {
            Toast.makeText(this, getString(R.string.enter_unique_id), Toast.LENGTH_SHORT).show()
            return
        }
        openViewer(uniqueId)
    }

    private fun openViewer(uniqueId: String) {
        showLoadingPanel()
        lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) { repository.loadManifest(uniqueId) }
            result.fold(
                onSuccess = { manifest ->
                    val json = gson.toJson(manifest)
                    startActivity(Intent(this@MainActivity, ArViewerActivity::class.java).apply {
                        putExtra(ArViewerActivity.EXTRA_MANIFEST_JSON, json)
                        putExtra(ArViewerActivity.EXTRA_UNIQUE_ID, uniqueId)
                    })
                    showMainPanel()
                },
                onFailure = { throwable ->
                    val message = when (val error = throwable as? ViewerError) {
                        is ViewerError.Server -> getString(R.string.error_server, error.code)
                        is ViewerError -> getString(ViewerErrorMessages.getMessageResId(error))
                        else -> getString(R.string.error_unknown)
                    }
                    showErrorPanel(message)
                }
            )
        }
    }

    private fun showMainPanel() {
        binding.panelMain.visibility = View.VISIBLE
        binding.panelLoading.visibility = View.GONE
        binding.panelError.visibility = View.GONE
    }

    private fun showLoadingPanel() {
        binding.panelMain.visibility = View.GONE
        binding.panelLoading.visibility = View.VISIBLE
        binding.panelError.visibility = View.GONE
    }

    private fun showErrorPanel(message: String) {
        binding.panelMain.visibility = View.GONE
        binding.panelLoading.visibility = View.GONE
        binding.panelError.visibility = View.VISIBLE
        binding.textError.text = message
    }

    companion object {
        /**
         * Parses unique_id from viewer deep link URI.
         * Supports https://ar.neuroimagen.ru/view/{unique_id} and arv://view/{unique_id}.
         */
        fun parseUniqueIdFromUri(uri: Uri): String? {
            return when (uri.scheme) {
                "arv" -> uri.pathSegments.firstOrNull() ?: uri.path?.trimStart('/')?.takeIf { it.isNotBlank() }
                "https", "http" -> uri.pathSegments.getOrNull(1)
                else -> null
            }
        }
    }
}
