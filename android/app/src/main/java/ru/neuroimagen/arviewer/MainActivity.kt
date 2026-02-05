package ru.neuroimagen.arviewer

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
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

    private val qrScannerLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            val uniqueId = result.data?.getStringExtra(QrScannerActivity.EXTRA_UNIQUE_ID)
            if (!uniqueId.isNullOrBlank()) {
                binding.editUniqueId.setText(uniqueId)
                openViewer(uniqueId)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.buttonOpen.setOnClickListener { onOpenClicked() }
        binding.buttonScanQr.setOnClickListener { openQrScanner() }
        binding.buttonRetry.setOnClickListener { showMainPanel() }

        handleIntent(intent)
    }

    private fun openQrScanner() {
        val intent = Intent(this, QrScannerActivity::class.java)
        qrScannerLauncher.launch(intent)
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
        val input = binding.editUniqueId.text.toString().trim()
        if (input.isEmpty()) {
            Toast.makeText(this, getString(R.string.enter_unique_id), Toast.LENGTH_SHORT).show()
            return
        }
        // Парсим ввод: может быть UUID, URL или deep link
        val uniqueId = extractUniqueId(input)
        if (uniqueId == null) {
            Toast.makeText(this, getString(R.string.error_invalid_unique_id), Toast.LENGTH_SHORT).show()
            return
        }
        openViewer(uniqueId)
    }

    /**
     * Извлекает unique_id из ввода пользователя.
     * Поддерживает: UUID напрямую, https://...view/{id}, arv://view/{id}
     */
    private fun extractUniqueId(input: String): String? {
        // Если это уже UUID — вернуть как есть
        if (UUID_REGEX.matches(input)) {
            return input
        }
        // Попробовать распарсить как URL
        return try {
            val uri = Uri.parse(input)
            parseUniqueIdFromUri(uri)
        } catch (e: Exception) {
            null
        }
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
        private val UUID_REGEX = Regex(
            "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )

        /**
         * Parses unique_id from viewer deep link URI.
         * Supports https://ar.neuroimagen.ru/view/{unique_id} and arv://view/{unique_id}.
         */
        fun parseUniqueIdFromUri(uri: Uri): String? {
            return when (uri.scheme) {
                "arv" -> uri.pathSegments.firstOrNull() ?: uri.path?.trimStart('/')?.takeIf { it.isNotBlank() }
                "https", "http" -> uri.pathSegments.getOrNull(1)?.takeIf { UUID_REGEX.matches(it) }
                else -> null
            }
        }
    }
}
