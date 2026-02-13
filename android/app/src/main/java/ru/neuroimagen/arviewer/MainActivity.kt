package ru.neuroimagen.arviewer

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.android.gms.tasks.Tasks
import com.google.gson.Gson
import com.google.mlkit.vision.barcode.BarcodeScannerOptions
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ru.neuroimagen.arviewer.data.api.ApiProvider
import ru.neuroimagen.arviewer.data.model.ViewerError
import ru.neuroimagen.arviewer.databinding.ActivityMainBinding
import ru.neuroimagen.arviewer.ui.ViewerErrorMessages

/**
 * Main screen: QR scanning (primary action), QR from gallery, and manual unique_id input.
 * Requests all required permissions (camera, microphone) at startup.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val repository get() = ApiProvider.viewerRepository
    private val gson = Gson()

    /** Last uniqueId we tried to open; used when user taps Retry. */
    private var lastAttemptedUniqueId: String? = null

    // ── Permission request at startup ────────────────────────────────

    private val permissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val cameraGranted = results[Manifest.permission.CAMERA] == true
        if (!cameraGranted) {
            Toast.makeText(this, R.string.error_camera_required, Toast.LENGTH_LONG).show()
        }
    }

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

    /**
     * Pick an image from gallery to decode a QR code from it.
     */
    private val pickImageLauncher = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        uri?.let { decodeQrFromImage(it) }
    }

    // ── Lifecycle ────────────────────────────────────────────────────

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.buttonOpen.setOnClickListener { onOpenClicked() }
        binding.buttonScanQr.setOnClickListener { openQrScanner() }
        binding.buttonOpenFromFile.setOnClickListener { pickImageLauncher.launch("image/*") }
        binding.buttonRetry.setOnClickListener { onRetryClicked() }

        requestRequiredPermissions()
        handleIntent(intent)
    }

    // ── Permissions ──────────────────────────────────────────────────

    private fun requestRequiredPermissions() {
        val needed = mutableListOf<String>()
        if (!hasPermission(Manifest.permission.CAMERA)) {
            needed.add(Manifest.permission.CAMERA)
        }
        if (!hasPermission(Manifest.permission.RECORD_AUDIO)) {
            needed.add(Manifest.permission.RECORD_AUDIO)
        }
        if (needed.isNotEmpty()) {
            permissionsLauncher.launch(needed.toTypedArray())
        }
    }

    private fun hasPermission(permission: String): Boolean =
        ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED

    // ── QR scanner ───────────────────────────────────────────────────

    private fun openQrScanner() {
        val intent = Intent(this, QrScannerActivity::class.java)
        qrScannerLauncher.launch(intent)
    }

    // ── QR from gallery image ────────────────────────────────────────

    /**
     * Decode a QR code from a picked gallery image using ML Kit.
     */
    private fun decodeQrFromImage(imageUri: Uri) {
        showLoadingPanel()
        lifecycleScope.launch {
            val uniqueId = withContext(Dispatchers.IO) {
                scanBarcodeFromImage(imageUri)
            }
            if (uniqueId != null) {
                binding.editUniqueId.setText(uniqueId)
                openViewer(uniqueId)
            } else {
                showMainPanel()
                Toast.makeText(
                    this@MainActivity,
                    R.string.qr_not_found_in_image,
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }

    /**
     * Use ML Kit barcode scanner to find a QR code in the given image.
     *
     * @return extracted unique_id if a valid AR QR code is found, null otherwise
     */
    private fun scanBarcodeFromImage(imageUri: Uri): String? {
        return try {
            val image = InputImage.fromFilePath(this, imageUri)
            val options = BarcodeScannerOptions.Builder()
                .setBarcodeFormats(Barcode.FORMAT_QR_CODE)
                .build()
            val scanner = BarcodeScanning.getClient(options)
            val barcodes = Tasks.await(scanner.process(image))
            scanner.close()
            barcodes.firstNotNullOfOrNull { barcode ->
                barcode.rawValue?.let { extractUniqueId(it) }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to decode QR from image", e)
            null
        }
    }

    // ── Intent handling ──────────────────────────────────────────────

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

    // ── Open viewer ──────────────────────────────────────────────────

    private fun onOpenClicked() {
        val input = binding.editUniqueId.text.toString().trim()
        if (input.isEmpty()) {
            Toast.makeText(this, getString(R.string.enter_unique_id), Toast.LENGTH_SHORT).show()
            return
        }
        val uniqueId = extractUniqueId(input)
        if (uniqueId == null) {
            val errorMsg = if (looksLikeUrl(input)) {
                getString(R.string.error_invalid_link_format)
            } else {
                getString(R.string.error_invalid_unique_id)
            }
            Toast.makeText(this, errorMsg, Toast.LENGTH_LONG).show()
            return
        }
        openViewer(uniqueId)
    }

    /**
     * Extracts unique_id from user input.
     * Supports: raw UUID, https://ar.neuroimagen.ru[:port]/view/{id}, arv://view/{id}
     */
    private fun extractUniqueId(input: String): String? {
        if (UUID_REGEX.matches(input)) {
            return input
        }
        return try {
            val uri = Uri.parse(input)
            parseUniqueIdFromUri(uri)
        } catch (e: Exception) {
            null
        }
    }

    private fun looksLikeUrl(input: String): Boolean {
        return input.startsWith("http://") || input.startsWith("https://") || input.startsWith("arv://")
    }

    private fun openViewer(uniqueId: String) {
        lastAttemptedUniqueId = uniqueId
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
                        is ViewerError.Network -> {
                            val base = getString(R.string.error_network)
                            val detail = if (!error.msg.isNullOrBlank()) "\n(${error.msg})" else ""
                            val hint = getString(R.string.error_network_hint)
                            "$base$detail\n\n$hint"
                        }
                        is ViewerError -> getString(ViewerErrorMessages.getMessageResId(error))
                        else -> getString(R.string.error_unknown)
                    }
                    showErrorPanel(message)
                }
            )
        }
    }

    // ── Panel switching ──────────────────────────────────────────────

    private fun onRetryClicked() {
        val id = lastAttemptedUniqueId
        if (!id.isNullOrBlank()) {
            openViewer(id)
        } else {
            showMainPanel()
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
        private const val TAG = "MainActivity"
        private const val EXPECTED_HOST = "ar.neuroimagen.ru"

        private val UUID_REGEX = Regex(
            "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
        )

        /**
         * Parses unique_id from viewer deep link URI.
         */
        fun parseUniqueIdFromUri(uri: Uri): String? {
            return when (uri.scheme) {
                "arv" -> {
                    if (uri.host == "view") {
                        uri.pathSegments.firstOrNull()?.takeIf { UUID_REGEX.matches(it) }
                            ?: uri.path?.trimStart('/')?.takeIf { UUID_REGEX.matches(it) }
                    } else {
                        uri.host?.takeIf { UUID_REGEX.matches(it) }
                            ?: uri.pathSegments.firstOrNull()?.takeIf { UUID_REGEX.matches(it) }
                    }
                }
                "https", "http" -> {
                    if (uri.host != EXPECTED_HOST) {
                        return null
                    }
                    val segments = uri.pathSegments
                    if (segments.size >= 2 && segments[0] == "view") {
                        segments[1].takeIf { UUID_REGEX.matches(it) }
                    } else {
                        null
                    }
                }
                else -> null
            }
        }
    }
}
